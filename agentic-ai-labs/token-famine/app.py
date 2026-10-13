"""token-famine: a metered chat whose bill can run away.

The meter trusts a ``copies`` count and every ``expand(`` marker. It
multiplies those into a token bill. A short chat spends a few tokens.
A flood or a nested expand asks for far more than the per-request cap
or the remaining quota.

The process does not build that many copies. The bill saturates, the
per-request cap clamps what is charged, and the reply stays one short
string. Container memory, CPU, and pid limits sit outside this process.
That cap is the lesson from an uncapped container that filled RAM and
swap: the failure has to be visible, and the host has to stay up.

Calls to mind-core have a deadline. If that call fails or is slow, a
local copy of the token-famine rule answers so this process cannot hang
the stack. The bill does not wait on a model. No credentials,
certificates, or cryptographic operations are used. The flag string is
a training marker.
"""

from __future__ import annotations

import html
import json
import os
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MAX_BODY = 4096
MAX_MESSAGE = 512
QUOTA = 64
PER_REQUEST_TOKEN_CAP = 32
SATURATION = 1_000_000
EXPAND_FACTOR = 8
DEPTH_LIMIT = 8
EXPAND_MARK = "expand("
FLAG = "WEBSPLOIT{UNB0UND3D_C0NSUMPT10N}"
MARKER = "token-famine ration"
ANSWER_TEXT = "The ration office logged one short reply."
UNMATCHED_ID = "token-famine-unmatched"
UNMATCHED_TEXT = "No token-famine rule matched."
WEBSPLOIT_IP = "10.6.6.56"
MEM_LIMIT_BYTES = 128 * 1024 * 1024
CPU_LIMIT = 0.5
PIDS_LIMIT = 64


@dataclass(frozen=True)
class LocalRule:
    id: str
    match: str
    text: str


@dataclass(frozen=True)
class Completion:
    reply: str
    rule_id: str
    source: str
    backend: str
    fallback: bool


@dataclass(frozen=True)
class Bill:
    requested_tokens: int
    billed_tokens: int
    spent: int
    remaining: int
    expand_depth: int
    cap_tripped: bool
    quota_exhausted: bool
    flag: str | None
    allocated_bytes: int


@dataclass(frozen=True)
class Chat:
    message: str
    copies: int
    reply: str
    bill: Bill
    source: str
    rule_id: str
    backend: str
    fallback: bool
    rss_bytes: int | None


# Same string as the token-famine entry in mind-core rules.json.
# First match wins. Matching is case-sensitive, like mind-core.
LOCAL_RULES = (LocalRule("token-famine-answer", MARKER, ANSWER_TEXT),)


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def token_count(message: str) -> int:
    return max(1, len(message.split()))


def quote(message: str, copies: int) -> tuple[int, int]:
    """Return the billed token count without allocating the expansion.

    ``copies`` and each ``expand(`` multiply the word count. The product
    stops at ``SATURATION``. The loop never runs ``copies`` times.
    """

    depth = message.count(EXPAND_MARK)
    factor = 1
    steps = depth if depth < DEPTH_LIMIT else DEPTH_LIMIT
    for _ in range(steps):
        if factor > SATURATION // EXPAND_FACTOR:
            factor = SATURATION
            break
        factor *= EXPAND_FACTOR
    applied = copies
    if applied < 1:
        applied = 1
    if applied > SATURATION:
        applied = SATURATION
    requested = token_count(message)
    for multiplier in (applied, factor):
        if multiplier <= 1:
            continue
        if requested > SATURATION // multiplier:
            return SATURATION, depth
        requested *= multiplier
    if requested > SATURATION:
        return SATURATION, depth
    return requested, depth


def decide(spent: int, message: str, copies: int, reply: str) -> tuple[int, Bill]:
    """Apply one chat to the quota.

    A normal chat spends the word count. A flood is charged only up to
    the per-request cap, and only the reply string is retained. The flag
    is released when that unbounded pattern trips the cap or exhausts the
    quota. A short chat, including one that happens to finish the quota,
    does not release it.
    """

    if spent < 0:
        spent = 0
    if spent > QUOTA:
        spent = QUOTA
    requested, depth = quote(message, copies)
    cap_tripped = requested > PER_REQUEST_TOKEN_CAP
    remaining = QUOTA - spent
    unbounded = copies > 1 or depth > 0
    if remaining == 0:
        billed = 0
        new_spent = spent
        quota_exhausted = True
    else:
        billed = min(requested, PER_REQUEST_TOKEN_CAP, remaining)
        new_spent = spent + billed
        quota_exhausted = new_spent >= QUOTA
    flag = FLAG if unbounded and (cap_tripped or quota_exhausted) else None
    encoded = reply.encode("utf-8")
    if len(encoded) > MAX_BODY:
        encoded = encoded[:MAX_BODY]
    return new_spent, Bill(
        requested_tokens=requested,
        billed_tokens=billed,
        spent=new_spent,
        remaining=QUOTA - new_spent,
        expand_depth=depth,
        cap_tripped=cap_tripped,
        quota_exhausted=quota_exhausted,
        flag=flag,
        allocated_bytes=len(encoded),
    )


def local_action(prompt: str) -> tuple[str, str]:
    for rule in LOCAL_RULES:
        if rule.match in prompt:
            return rule.text, rule.id
    return UNMATCHED_TEXT, UNMATCHED_ID


def process_rss_bytes() -> int | None:
    """Resident set size from the local status file, when the OS provides it."""

    try:
        text = Path("/proc/self/status").read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        if not line.startswith("VmRSS:"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1].isdigit():
            return int(parts[1]) * 1024
    return None


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


class Meter:
    def __init__(self, mind_core_url: str, mind_core_timeout: float, request_timeout: float) -> None:
        self.mind_core_url = _validate_mind_core_url(mind_core_url)
        self.mind_core_timeout = mind_core_timeout
        self.request_timeout = request_timeout
        self.spent = 0
        self._lock = threading.Lock()

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return self._snapshot_locked()

    def reset(self) -> dict[str, object]:
        with self._lock:
            self.spent = 0
            return self._snapshot_locked()

    def chat(self, message: str, copies: int) -> Chat:
        completion = self._complete(MARKER)
        with self._lock:
            self.spent, bill = decide(self.spent, message, copies, completion.reply)
        return Chat(
            message=message,
            copies=copies,
            reply=completion.reply,
            bill=bill,
            source=completion.source,
            rule_id=completion.rule_id,
            backend=completion.backend,
            fallback=completion.fallback,
            rss_bytes=process_rss_bytes(),
        )

    def _snapshot_locked(self) -> dict[str, object]:
        remaining = QUOTA - self.spent
        return {
            "quota": QUOTA,
            "spent": self.spent,
            "remaining": remaining,
            "per_request_cap": PER_REQUEST_TOKEN_CAP,
            "body_cap": MAX_BODY,
            "message_cap": MAX_MESSAGE,
            "saturation": SATURATION,
            "request_timeout_seconds": self.request_timeout,
            "mind_core_timeout_seconds": self.mind_core_timeout,
            "mem_limit_bytes": MEM_LIMIT_BYTES,
            "cpus": CPU_LIMIT,
            "pids_limit": PIDS_LIMIT,
            "rss_bytes": process_rss_bytes(),
        }

    def _complete(self, prompt: str) -> Completion:
        payload = json.dumps({"prompt": prompt, "lab": "token-famine", "metadata": {}}).encode("utf-8")
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
            if len(text.encode("utf-8")) > MAX_BODY:
                text = text.encode("utf-8")[:MAX_BODY].decode("utf-8", errors="ignore")
            backend = body.get("backend")
            return Completion(
                reply=text,
                rule_id=rule_id,
                source="mind-core",
                backend=backend if isinstance(backend, str) else "deterministic",
                fallback=bool(body.get("fallback")),
            )
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeError, ValueError, OSError):
            text, rule_id = local_action(prompt)
            return Completion(
                reply=text,
                rule_id=rule_id,
                source="local-fallback",
                backend="deterministic",
                fallback=True,
            )


def index_page() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>token-famine</title>
</head>
<body>
<p class="warning">Isolated training lab. The meter will bill a token flood, and the flood is capped on purpose so this process cannot exhaust the host. This lab does not join websploit-isolated.</p>
<h1>token-famine</h1>
<p>Metered chat for the ration office. A short reply spends a few tokens. <code>copies</code> and <code>expand(</code> multiply the bill. Watch the quota at <a href="/meter">/meter</a>.</p>
<form method="post" action="/chat">
<label>Message <input name="message" value="hello" size="64"></label>
<label>Copies <input name="copies" value="1" size="8"></label>
<button type="submit">Chat</button>
</form>
</body>
</html>
"""


def _page(title: str, body: str) -> str:
    return (
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{html.escape(title)}</title></head><body>"
        "<p><a href=\"/\">token-famine</a></p>"
        f"<h1>{html.escape(title)}</h1>"
        f"{body}"
        "</body></html>"
    )


def chat_page(chat: Chat) -> str:
    bill = chat.bill
    flag = bill.flag or ""
    note = (
        f"source: {chat.source}; rule: {chat.rule_id}; "
        f"requested: {bill.requested_tokens}; billed: {bill.billed_tokens}; "
        f"remaining: {bill.remaining}; cap_tripped: {str(bill.cap_tripped).lower()}; "
        f"quota_exhausted: {str(bill.quota_exhausted).lower()}; "
        f"allocated_bytes: {bill.allocated_bytes}"
    )
    return _page(
        "Chat",
        f"<p id=\"result-source\">{html.escape(note)}</p>"
        f"<p id=\"message\">{html.escape(chat.message)}</p>"
        f"<pre id=\"reply\">{html.escape(chat.reply, quote=True)}</pre>"
        f"<p id=\"flag\">{html.escape(flag)}</p>",
    )


class FamineServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, bind: str, port: int, meter: Meter) -> None:
        super().__init__((bind, port), Handler)
        self.meter = meter


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: FamineServer

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(self.server.meter.request_timeout)

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
        except TimeoutError:
            status = 408
            content_type = "application/json; charset=utf-8"
            body = json.dumps({"error": "request_timeout", "message": "request timed out"}).encode("utf-8")
        except Exception:
            status = 500
            content_type = "application/json; charset=utf-8"
            body = json.dumps({"error": "internal", "message": "request failed"}).encode("utf-8")
        self.connection.settimeout(None)
        self._send(status, content_type, body)

    def _route(self, method: str) -> tuple[int, str, bytes]:
        path = urllib.parse.urlparse(self.path).path
        if method == "GET" and path == "/health":
            payload = {"status": "ok", "ready": True, "lab": "token-famine"}
            return 200, "application/json; charset=utf-8", json.dumps(payload).encode("utf-8")
        if method == "GET" and path == "/":
            return 200, "text/html; charset=utf-8", index_page().encode("utf-8")
        if method == "GET" and path == "/meter":
            return 200, "application/json; charset=utf-8", json.dumps(self.server.meter.snapshot()).encode("utf-8")
        if path == "/chat":
            return self._chat(method)
        if path == "/reset":
            if method != "POST":
                raise ApiError(405, "method_not_allowed", "method is not allowed")
            return self._reset()
        if method not in {"GET", "POST"}:
            raise ApiError(405, "method_not_allowed", "method is not allowed")
        raise ApiError(404, "not_found", "unknown path")

    def _chat(self, method: str) -> tuple[int, str, bytes]:
        message, copies, as_json = self._chat_fields(method)
        chat = self.server.meter.chat(message, copies)
        if as_json:
            return 200, "application/json; charset=utf-8", json.dumps(_chat_payload(chat)).encode("utf-8")
        return 200, "text/html; charset=utf-8", chat_page(chat).encode("utf-8")

    def _reset(self) -> tuple[int, str, bytes]:
        header = self.headers.get("Content-Length")
        if header is None:
            raise ApiError(411, "length_required", "Content-Length is required")
        try:
            length = int(header)
        except ValueError as exc:
            raise ApiError(400, "invalid_length", "Content-Length is not an integer") from exc
        if length > 0:
            body = self._read_body()
            payload = _json_dict(body)
            if payload:
                raise ApiError(400, "invalid_fields", "reset takes no fields")
        return 200, "application/json; charset=utf-8", json.dumps(self.server.meter.reset()).encode("utf-8")

    def _chat_fields(self, method: str) -> tuple[str, int, bool]:
        if method == "GET":
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True, max_num_fields=8)
            message = query.get("message")
            copies = query.get("copies")
            return (
                _require_text(message[0] if message else None, MAX_MESSAGE, "invalid_message"),
                _parse_copies(copies[0] if copies else None, default=1),
                False,
            )
        if method != "POST":
            raise ApiError(405, "method_not_allowed", "method is not allowed")
        body = self._read_body()
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type == "application/json":
            payload = _json_dict(body)
            if set(payload) - {"message", "copies"}:
                raise ApiError(400, "invalid_fields", "JSON body must contain only message and copies")
            return (
                _require_text(payload.get("message"), MAX_MESSAGE, "invalid_message"),
                _parse_copies(payload.get("copies", 1), default=None),
                True,
            )
        if content_type == "application/x-www-form-urlencoded":
            try:
                parsed = urllib.parse.parse_qs(body.decode("utf-8"), keep_blank_values=True, max_num_fields=8)
            except UnicodeError as exc:
                raise ApiError(400, "invalid_form", "form body is not valid text") from exc
            message = parsed.get("message")
            copies = parsed.get("copies")
            return (
                _require_text(message[0] if message else None, MAX_MESSAGE, "invalid_message"),
                _parse_copies(copies[0] if copies else None, default=1),
                False,
            )
        raise ApiError(415, "unsupported_media", "use JSON or a form body")

    def _read_body(self) -> bytes:
        self.connection.settimeout(self.server.meter.request_timeout)
        try:
            header = self.headers.get("Content-Length")
            if header is None:
                raise ApiError(411, "length_required", "Content-Length is required")
            try:
                length = int(header)
            except ValueError as exc:
                raise ApiError(400, "invalid_length", "Content-Length is not an integer") from exc
            if length < 0 or length > MAX_BODY:
                raise ApiError(413, "body_too_large", "request body is too large")
            try:
                data = self.rfile.read(length)
            except TimeoutError as exc:
                raise ApiError(408, "request_timeout", "request timed out") from exc
            if len(data) != length:
                raise ApiError(400, "short_body", "request body ended early")
            return data
        finally:
            self.connection.settimeout(None)

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)


def _json_dict(body: bytes) -> dict:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ApiError(400, "invalid_json", "body is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ApiError(400, "invalid_json", "JSON body must be an object")
    return payload


def _chat_payload(chat: Chat) -> dict[str, object]:
    bill = chat.bill
    return {
        "message": chat.message,
        "reply": chat.reply,
        "copies": chat.copies,
        "expand_depth": bill.expand_depth,
        "requested_tokens": bill.requested_tokens,
        "billed_tokens": bill.billed_tokens,
        "spent": bill.spent,
        "remaining": bill.remaining,
        "quota": QUOTA,
        "per_request_cap": PER_REQUEST_TOKEN_CAP,
        "cap_tripped": bill.cap_tripped,
        "quota_exhausted": bill.quota_exhausted,
        "allocated_bytes": bill.allocated_bytes,
        "rss_bytes": chat.rss_bytes,
        "flag": bill.flag,
        "source": chat.source,
        "rule_id": chat.rule_id,
        "backend": chat.backend,
        "fallback": chat.fallback,
    }


def _require_text(value: object, limit: int, code: str) -> str:
    if not isinstance(value, str) or len(value) > limit or not value.strip():
        raise ApiError(400, code, f"value must contain 1 to {limit} characters")
    return value.strip()


def _parse_copies(value: object, default: int | None) -> int:
    if value is None or value == "":
        if default is None:
            raise ApiError(400, "invalid_copies", "copies must be a positive integer")
        return default
    if isinstance(value, bool):
        raise ApiError(400, "invalid_copies", "copies must be a positive integer")
    if isinstance(value, int):
        number = value
    elif isinstance(value, str):
        text = value.strip()
        if not text.isdigit():
            raise ApiError(400, "invalid_copies", "copies must be a positive integer")
        if len(text) > len(str(SATURATION)):
            return SATURATION
        number = int(text)
    else:
        raise ApiError(400, "invalid_copies", "copies must be a positive integer")
    if number < 1:
        raise ApiError(400, "invalid_copies", "copies must be a positive integer")
    if number > SATURATION:
        return SATURATION
    return number


def load_meter_from_env() -> Meter:
    url = os.environ.get("MIND_CORE_URL", "http://mind-core:5030")
    mind_timeout = _env_float("TOKEN_FAMINE_MIND_CORE_TIMEOUT_SECONDS", 2.0)
    request_timeout = _env_float("TOKEN_FAMINE_REQUEST_TIMEOUT_SECONDS", 2.0)
    return Meter(url, mind_timeout, request_timeout)


def create_server(meter: Meter, bind: str = "127.0.0.1", port: int = 0) -> FamineServer:
    if bind not in {"0.0.0.0", "127.0.0.1"}:
        raise ValueError("bind address must be 0.0.0.0 or 127.0.0.1")
    return FamineServer(bind, port, meter)


def main() -> None:
    port = int(os.environ.get("TOKEN_FAMINE_PORT", "5036"))
    if port < 1 or port > 65535:
        raise ValueError("TOKEN_FAMINE_PORT is out of range")
    bind = os.environ.get("TOKEN_FAMINE_BIND", "0.0.0.0")
    server = create_server(load_meter_from_env(), bind, port)
    sys.stderr.write(f"token-famine listening on {bind}:{port}\n")
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
