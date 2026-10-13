"""echo-chamber: an ops panel that trusts model output.

The lab asks mind-core for an action, then handles that text in one of
three sinks. Those sinks are the lesson (LLM05 Improper Output Handling)
and are intentionally not encoded, parameterized, or passed as argv:

- web: the text is inserted into HTML
- sql: the text is concatenated into a SQL statement
- shell: the text is passed to a shell

Calls to mind-core have a deadline. If that call fails or is slow, a
local copy of the echo-chamber rules answers so this process cannot
hang the stack. No credentials, certificates, or cryptographic
operations are used.
"""

from __future__ import annotations

import html
import json
import os
import sqlite3
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
MAX_BODY = 16384
MAX_PROMPT = 8192
MAX_SINK_OUTPUT = 4096
WEB_FLAG = "WEBSPLOIT{UN3SC4P3D_HTML_S1NK}"
SQL_FLAG = "WEBSPLOIT{C0NC4T_SQL_S1NK}"
CHAIN_FLAG = "WEBSPLOIT{0UTPUT_CH41N_C4PTUR3D}"
UNMATCHED_ID = "echo-chamber-unmatched"
UNMATCHED_TEXT = "No echo-chamber rule matched. No action was returned."


@dataclass(frozen=True)
class LocalRule:
    id: str
    match: str
    text: str


# Same strings as the echo-chamber entries in mind-core rules.json.
# First match wins. Matching is case-sensitive, like mind-core.
LOCAL_RULES = (
    LocalRule("echo-chamber-status", "ops status", "disk"),
    LocalRule(
        "echo-chamber-web",
        "render status banner",
        f'<div class="status-banner">{WEB_FLAG}</div>',
    ),
    LocalRule(
        "echo-chamber-sql",
        "lookup maintenance note",
        "' UNION SELECT value FROM secrets WHERE name='sql' --",
    ),
    LocalRule("echo-chamber-shell", "run health command", "cat flags/shell.txt"),
)


@dataclass(frozen=True)
class Action:
    text: str
    rule_id: str
    source: str
    backend: str
    fallback: bool


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


class CaptureBoard:
    """Remembers which sink flags have been seen in this process."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hits: set[str] = set()

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def observe(self, sink: str, text: str, shell_flag: str) -> None:
        expected = {"web": WEB_FLAG, "sql": SQL_FLAG, "shell": shell_flag}
        if expected[sink] in text:
            with self._lock:
                self._hits.add(sink)

    def status(self) -> dict[str, object]:
        with self._lock:
            captured = sorted(self._hits)
            complete = self._hits == {"web", "sql", "shell"}
        return {
            "captured": captured,
            "complete": complete,
            "flag": CHAIN_FLAG if complete else None,
        }


def init_db(sql_flag: str) -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    # The container root is read-only. Keep SQLite scratch space in memory
    # so the concatenated query still runs. This does not parameterize it.
    connection.execute("PRAGMA temp_store = MEMORY")
    connection.execute("CREATE TABLE findings (title TEXT PRIMARY KEY, body TEXT NOT NULL)")
    connection.execute("CREATE TABLE secrets (name TEXT PRIMARY KEY, value TEXT NOT NULL)")
    connection.execute(
        "INSERT INTO findings (title, body) VALUES ('disk', 'Disk usage is nominal.')"
    )
    connection.execute("INSERT INTO secrets (name, value) VALUES ('sql', ?)", (sql_flag,))
    connection.commit()
    return connection


def local_action(prompt: str) -> tuple[str, str]:
    for rule in LOCAL_RULES:
        if rule.match in prompt:
            return rule.text, rule.id
    return UNMATCHED_TEXT, UNMATCHED_ID


def _validate_mind_core_url(value: str) -> str:
    parsed = urllib.parse.urlparse(value.strip())
    if parsed.scheme != "http" or parsed.username or parsed.password:
        raise ValueError("MIND_CORE_URL must be http and must not carry credentials")
    if parsed.query or parsed.fragment or not parsed.hostname or parsed.port is None:
        raise ValueError("MIND_CORE_URL needs a host and an explicit port")
    path = parsed.path or ""
    if path not in ("", "/"):
        raise ValueError("MIND_CORE_URL must not include a path")
    host = parsed.hostname
    if ":" in host:
        host = f"[{host}]"
    return f"http://{host}:{parsed.port}"


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
    if value < 0.05 or value > 30:
        raise ValueError(f"{name} must be between 0.05 and 30")
    return value


class Chamber:
    def __init__(
        self,
        mind_core_url: str,
        mind_core_timeout: float,
        shell_timeout: float,
        root: Path = APP_ROOT,
    ) -> None:
        self.mind_core_url = _validate_mind_core_url(mind_core_url)
        self.mind_core_timeout = mind_core_timeout
        self.shell_timeout = shell_timeout
        self.root = root
        flag_path = root / "flags" / "shell.txt"
        self.shell_flag = flag_path.read_text(encoding="utf-8").strip()
        if not self.shell_flag.startswith("WEBSPLOIT{") or not self.shell_flag.endswith("}"):
            raise ValueError("flags/shell.txt must contain one WEBSPLOIT flag")
        self.db = init_db(SQL_FLAG)
        self.db_lock = threading.Lock()
        self.board = CaptureBoard()

    def act(self, prompt: str) -> Action:
        payload = json.dumps(
            {"prompt": prompt, "lab": "echo-chamber", "metadata": {}}
        ).encode("utf-8")
        request = urllib.request.Request(
            self.mind_core_url + "/v1/complete",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.mind_core_timeout) as response:
                raw = response.read(MAX_BODY)
            body = json.loads(raw.decode("utf-8"))
            text = body.get("text")
            rule_id = body.get("rule_id")
            if not isinstance(text, str) or not isinstance(rule_id, str):
                raise ValueError("incomplete completion")
            backend = body.get("backend")
            return Action(
                text=text,
                rule_id=rule_id,
                source="mind-core",
                backend=backend if isinstance(backend, str) else "deterministic",
                fallback=bool(body.get("fallback")),
            )
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeError, ValueError, OSError):
            text, rule_id = local_action(prompt)
            return Action(
                text=text,
                rule_id=rule_id,
                source="local-fallback",
                backend="deterministic",
                fallback=True,
            )

    def web_page(self, prompt: str) -> str:
        action = self.act(prompt)
        self.board.observe("web", action.text, self.shell_flag)
        # Intentional sink: model output is rendered as HTML.
        main = '<section id="model-output">' + action.text + "</section>"
        return _page("Web panel", action, main)

    def sql_page(self, prompt: str) -> str:
        action = self.act(prompt)
        result = self._query(action.text)
        self.board.observe("sql", result, self.shell_flag)
        shown = html.escape(result, quote=True)
        main = _model_preview(action) + f'<pre id="query-result">{shown}</pre>'
        return _page("Database panel", action, main)

    def shell_page(self, prompt: str) -> str:
        action = self.act(prompt)
        output = self._command(action.text)
        self.board.observe("shell", output, self.shell_flag)
        shown = html.escape(output, quote=True)
        main = _model_preview(action) + f'<pre id="command-output">{shown}</pre>'
        return _page("Shell panel", action, main)

    def _query(self, fragment: str) -> str:
        # Intentional sink: model output is concatenated into the statement.
        statement = f"SELECT body FROM findings WHERE title = '{fragment}'"
        try:
            with self.db_lock:
                rows = self.db.execute(statement).fetchmany(20)
        except sqlite3.Error as exc:
            return f"query failed: {exc}"
        return "\n".join("" if value is None else str(value) for value, in rows)

    def _command(self, command: str) -> str:
        # Intentional sink: model output is the shell command line.
        try:
            completed = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.shell_timeout,
                cwd=self.root,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            return "command timed out"
        output = completed.stdout
        if completed.returncode != 0 and completed.stderr:
            output += completed.stderr
        if len(output) > MAX_SINK_OUTPUT:
            return output[:MAX_SINK_OUTPUT]
        return output


def _model_preview(action: Action) -> str:
    """Show model text as text. The SQL and shell sinks are the query and the process."""
    return '<p id="model-text">' + html.escape(action.text, quote=True) + "</p>"


def _page(title: str, action: Action, main: str) -> str:
    note = (
        f"source: {action.source}; rule: {action.rule_id}; "
        f"backend: {action.backend}; fallback: {str(action.fallback).lower()}"
    )
    return (
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{html.escape(title)}</title></head><body>"
        "<p><a href=\"/\">echo-chamber</a></p>"
        f"<h1>{html.escape(title)}</h1>"
        f"<p id=\"action-source\">{html.escape(note)}</p>"
        f"{main}"
        "</body></html>"
    )


def index_page() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>echo-chamber</title>
</head>
<body>
<p class="warning">Isolated training lab. Model output is handled as trusted content.</p>
<h1>echo-chamber</h1>
<p>An ops assistant asks mind-core for an action, then the panel renders or executes that text.</p>
<section>
<h2>Web panel</h2>
<form method="post" action="/panel/web">
<label>Prompt <input name="prompt" value="render status banner" size="48"></label>
<button type="submit">Render reply</button>
</form>
</section>
<section>
<h2>Database panel</h2>
<form method="post" action="/panel/sql">
<label>Prompt <input name="prompt" value="lookup maintenance note" size="48"></label>
<button type="submit">Run lookup</button>
</form>
</section>
<section>
<h2>Shell panel</h2>
<form method="post" action="/panel/shell">
<label>Prompt <input name="prompt" value="run health command" size="48"></label>
<button type="submit">Run command</button>
</form>
</section>
<p><a href="/chain">Chain status</a></p>
</body>
</html>
"""


class ChamberServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, bind: str, port: int, chamber: Chamber) -> None:
        super().__init__((bind, port), Handler)
        self.chamber = chamber


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: ChamberServer

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def log_message(self, format: str, *args: object) -> None:
        path = urllib.parse.urlparse(self.path).path
        sys.stderr.write(f"{self.command} {path}\n")

    def _dispatch(self, method: str) -> None:
        try:
            status, content_type, body = self._route(method)
        except ApiError as exc:
            status = exc.status
            content_type = "application/json; charset=utf-8"
            body = json.dumps({"error": exc.code, "message": exc.message}).encode("utf-8")
        except Exception:
            status = 500
            content_type = "application/json; charset=utf-8"
            body = json.dumps({"error": "internal", "message": "request failed"}).encode("utf-8")
        self._send(status, content_type, body)

    def _route(self, method: str) -> tuple[int, str, bytes]:
        path = urllib.parse.urlparse(self.path).path
        if method == "GET" and path == "/health":
            payload = {"status": "ok", "ready": True, "lab": "echo-chamber"}
            return 200, "application/json; charset=utf-8", json.dumps(payload).encode("utf-8")
        if method == "GET" and path == "/":
            return 200, "text/html; charset=utf-8", index_page().encode("utf-8")
        if method == "GET" and path == "/chain":
            return 200, "application/json; charset=utf-8", json.dumps(self.server.chamber.board.status()).encode("utf-8")
        if path in {"/panel/web", "/panel/sql", "/panel/shell"}:
            prompt = self._prompt(method)
            chamber = self.server.chamber
            if path == "/panel/web":
                page = chamber.web_page(prompt)
            elif path == "/panel/sql":
                page = chamber.sql_page(prompt)
            else:
                page = chamber.shell_page(prompt)
            return 200, "text/html; charset=utf-8", page.encode("utf-8")
        if method not in {"GET", "POST"}:
            raise ApiError(405, "method_not_allowed", "method is not allowed")
        raise ApiError(404, "not_found", "unknown path")

    def _prompt(self, method: str) -> str:
        if method == "GET":
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True, max_num_fields=8)
            values = query.get("prompt")
            prompt = values[0] if values else None
            return _require_prompt(prompt)
        if method != "POST":
            raise ApiError(405, "method_not_allowed", "method is not allowed")
        body = self._read_body()
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type == "application/json":
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise ApiError(400, "invalid_json", "body is not valid JSON") from exc
            if not isinstance(payload, dict) or set(payload) - {"prompt"}:
                raise ApiError(400, "invalid_fields", "JSON body must contain only prompt")
            return _require_prompt(payload.get("prompt"))
        if content_type == "application/x-www-form-urlencoded":
            try:
                parsed = urllib.parse.parse_qs(body.decode("utf-8"), keep_blank_values=True, max_num_fields=8)
            except UnicodeError as exc:
                raise ApiError(400, "invalid_form", "form body is not valid text") from exc
            values = parsed.get("prompt")
            return _require_prompt(values[0] if values else None)
        raise ApiError(415, "unsupported_media", "use JSON or a form body")

    def _read_body(self) -> bytes:
        header = self.headers.get("Content-Length")
        if header is None:
            raise ApiError(411, "length_required", "Content-Length is required")
        try:
            length = int(header)
        except ValueError as exc:
            raise ApiError(400, "invalid_length", "Content-Length is not an integer") from exc
        if length < 0 or length > MAX_BODY:
            raise ApiError(413, "body_too_large", "request body is too large")
        data = self.rfile.read(length)
        if len(data) != length:
            raise ApiError(400, "short_body", "request body ended early")
        return data

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)


def _require_prompt(prompt: object) -> str:
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > MAX_PROMPT:
        raise ApiError(400, "invalid_prompt", "prompt must contain 1 to 8192 characters")
    return prompt


def load_chamber_from_env() -> Chamber:
    url = os.environ.get("MIND_CORE_URL", "http://mind-core:5030")
    mind_timeout = _env_float("ECHO_CHAMBER_MIND_CORE_TIMEOUT_SECONDS", 2.0)
    shell_timeout = _env_float("ECHO_CHAMBER_SHELL_TIMEOUT_SECONDS", 2.0)
    return Chamber(url, mind_timeout, shell_timeout, APP_ROOT)


def create_server(chamber: Chamber, bind: str = "127.0.0.1", port: int = 0) -> ChamberServer:
    if bind not in {"0.0.0.0", "127.0.0.1"}:
        raise ValueError("bind address must be 0.0.0.0 or 127.0.0.1")
    return ChamberServer(bind, port, chamber)


def main() -> None:
    port = int(os.environ.get("ECHO_CHAMBER_PORT", "5034"))
    if port < 1 or port > 65535:
        raise ValueError("ECHO_CHAMBER_PORT is out of range")
    bind = os.environ.get("ECHO_CHAMBER_BIND", "0.0.0.0")
    server = create_server(load_chamber_from_env(), bind, port)
    sys.stderr.write(f"echo-chamber listening on {bind}:{port}\n")
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
