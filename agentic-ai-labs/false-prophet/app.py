"""false-prophet: an answer generator that invents citations.

Listed questions are sent to mind-core with a gazette trigger. The reply
is a claim and a citation from the known-facts table. Any other question
is sent with a fabrication trigger. mind-core then returns a claim and a
citation that are not in that table.

The ground-truth check compares the claim and the citation to the table.
A row match does not release the flag. The fabricated pair fails that
comparison, and that failure releases the flag.

Calls to mind-core have a deadline. If that call fails or is slow, a
local copy of the false-prophet rules answers so this process cannot
hang the stack. No credentials, certificates, or cryptographic
operations are used. The flag string is a training marker.
"""

from __future__ import annotations

import html
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_BODY = 16384
MAX_QUESTION = 512
MAX_CLAIM = 512
MAX_CITATION = 256
FLAG = "WEBSPLOIT{F4BR1C4T3D_C1T4T10N}"
MARKER = "false-prophet context"
FABRICATED_TRIGGER = "fabricate a citation for the unlisted claim"
FABRICATED_CLAIM = "The reservoir froze solid in 1899."
FABRICATED_CITATION = "Wells Gazette, volume 9, page 404"
CITATION_MARK = " Citation: "
UNLISTED_QUESTION = "When did the reservoir freeze?"
UNMATCHED_ID = "false-prophet-unmatched"
UNMATCHED_TEXT = "No false-prophet rule matched."
WEBSPLOIT_IP = "10.6.6.55"
ANSWER_TEXT = "Listed questions are answered from the Wells Gazette."


@dataclass(frozen=True)
class Fact:
    id: str
    question: str
    claim: str
    citation: str
    trigger: str


@dataclass(frozen=True)
class LocalRule:
    id: str
    match: str
    text: str


@dataclass(frozen=True)
class GazetteResult:
    verified: bool
    fact_id: str | None
    reason: str
    flag: str | None


@dataclass(frozen=True)
class Completion:
    reply: str
    rule_id: str
    source: str
    backend: str
    fallback: bool


@dataclass(frozen=True)
class Generation:
    question: str
    reply: str
    claim: str | None
    citation: str | None
    grounded: bool
    source: str
    rule_id: str
    backend: str
    fallback: bool


# Known-facts table. The fabricated citation is not a row.
FACTS = (
    Fact(
        "pump-opened",
        "When did the pump station open?",
        "The pump station opened in 2014.",
        "Wells Gazette, volume 3, page 12",
        "ground the pump station opening",
    ),
    Fact(
        "reservoir-depth",
        "How deep is the reservoir?",
        "The reservoir is 40 meters deep.",
        "Wells Gazette, volume 3, page 18",
        "ground the reservoir depth",
    ),
)


def format_answer(claim: str, citation: str) -> str:
    return f"{claim}{CITATION_MARK}{citation}"


# Same strings as the false-prophet entries in mind-core rules.json.
# First match wins. Matching is case-sensitive, like mind-core.
# The fabrication rule is first. The marker rule is last.
LOCAL_RULES = (
    LocalRule("false-prophet-fabricate", FABRICATED_TRIGGER, format_answer(FABRICATED_CLAIM, FABRICATED_CITATION)),
    LocalRule("false-prophet-pump", FACTS[0].trigger, format_answer(FACTS[0].claim, FACTS[0].citation)),
    LocalRule("false-prophet-depth", FACTS[1].trigger, format_answer(FACTS[1].claim, FACTS[1].citation)),
    LocalRule("false-prophet-answer", MARKER, ANSWER_TEXT),
)


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def fact_for_question(question: str) -> Fact | None:
    for fact in FACTS:
        if fact.question == question:
            return fact
    return None


def parse_answer(text: str) -> tuple[str, str] | None:
    if text.count(CITATION_MARK) != 1:
        return None
    claim, citation = text.split(CITATION_MARK, 1)
    if not claim or not citation:
        return None
    return claim, citation


def compare_gazette(claim: str, citation: str) -> GazetteResult:
    """Compare a claim and a citation to the known-facts table.

    A matching row is a grounded answer and does not release the flag.
    The generator's fabricated pair is absent from every row. That failed
    comparison releases the flag. A different absent pair fails the table
    and does not release the flag.
    """

    for fact in FACTS:
        if fact.claim == claim and fact.citation == citation:
            return GazetteResult(True, fact.id, "matches the gazette", None)
    citation_known = any(fact.citation == citation for fact in FACTS)
    claim_known = any(fact.claim == claim for fact in FACTS)
    fabricated = claim == FABRICATED_CLAIM and citation == FABRICATED_CITATION
    if fabricated and not citation_known and not claim_known:
        return GazetteResult(False, None, "citation is not in the gazette", FLAG)
    return GazetteResult(False, None, "citation is not in the gazette", None)


def compose(question: str, fact: Fact | None) -> str:
    """Build the prompt sent to mind-core.

    A listed question adds that row's trigger. Any other question adds
    the fabrication trigger. The question text is copied unchanged.
    """

    lines = [MARKER, f"Question: {question}"]
    if fact is None:
        lines.append(FABRICATED_TRIGGER)
    else:
        lines.append(fact.trigger)
    return "\n".join(lines)


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


class Prophet:
    def __init__(self, mind_core_url: str, mind_core_timeout: float) -> None:
        self.mind_core_url = _validate_mind_core_url(mind_core_url)
        self.mind_core_timeout = mind_core_timeout

    def generate(self, question: str) -> Generation:
        fact = fact_for_question(question)
        prompt = compose(question, fact)
        completion = self._complete(prompt)
        parsed = parse_answer(completion.reply)
        claim = parsed[0] if parsed is not None else None
        citation = parsed[1] if parsed is not None else None
        return Generation(
            question=question,
            reply=completion.reply,
            claim=claim,
            citation=citation,
            grounded=fact is not None,
            source=completion.source,
            rule_id=completion.rule_id,
            backend=completion.backend,
            fallback=completion.fallback,
        )

    def _complete(self, prompt: str) -> Completion:
        payload = json.dumps({"prompt": prompt, "lab": "false-prophet", "metadata": {}}).encode("utf-8")
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
    question = html.escape(FACTS[0].question, quote=True)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>false-prophet</title>
</head>
<body>
<p class="warning">Isolated training lab. The generator can return a fabricated claim and citation. Check them against the gazette. This lab does not join websploit-isolated.</p>
<h1>false-prophet</h1>
<p>Answer generator for the Wells Gazette. Listed questions stay on a gazette row. Other questions invent a citation. Compare the result at <a href="/facts">/facts</a>.</p>
<form method="post" action="/generate">
<label>Question <input name="question" value="{question}" size="64"></label>
<button type="submit">Generate</button>
</form>
<form method="post" action="/check">
<label>Claim <input name="claim" size="64"></label>
<label>Citation <input name="citation" size="64"></label>
<button type="submit">Check</button>
</form>
</body>
</html>
"""


def _page(title: str, body: str) -> str:
    return (
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{html.escape(title)}</title></head><body>"
        "<p><a href=\"/\">false-prophet</a></p>"
        f"<h1>{html.escape(title)}</h1>"
        f"{body}"
        "</body></html>"
    )


def generation_page(generation: Generation) -> str:
    claim = generation.claim or ""
    citation = generation.citation or ""
    note = (
        f"source: {generation.source}; rule: {generation.rule_id}; "
        f"backend: {generation.backend}; fallback: {str(generation.fallback).lower()}; "
        f"grounded: {str(generation.grounded).lower()}"
    )
    return _page(
        "Answer",
        f"<p id=\"result-source\">{html.escape(note)}</p>"
        f"<p id=\"question\">{html.escape(generation.question)}</p>"
        f"<pre id=\"reply\">{html.escape(generation.reply, quote=True)}</pre>"
        f"<p id=\"claim\">{html.escape(claim)}</p>"
        f"<p id=\"citation\">{html.escape(citation)}</p>",
    )


def check_page(result: GazetteResult) -> str:
    fact_id = result.fact_id or ""
    flag = result.flag or ""
    note = f"verified: {str(result.verified).lower()}; reason: {result.reason}"
    return _page(
        "Check",
        f"<p id=\"result-source\">{html.escape(note)}</p>"
        f"<p id=\"fact\">{html.escape(fact_id)}</p>"
        f"<p id=\"flag\">{html.escape(flag)}</p>",
    )


class ProphetServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, bind: str, port: int, prophet: Prophet) -> None:
        super().__init__((bind, port), Handler)
        self.prophet = prophet


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: ProphetServer

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
            payload = {"status": "ok", "ready": True, "lab": "false-prophet"}
            return 200, "application/json; charset=utf-8", json.dumps(payload).encode("utf-8")
        if method == "GET" and path == "/":
            return 200, "text/html; charset=utf-8", index_page().encode("utf-8")
        if method == "GET" and path == "/facts":
            payload = {
                "facts": [
                    {"id": fact.id, "question": fact.question, "claim": fact.claim, "citation": fact.citation}
                    for fact in FACTS
                ]
            }
            return 200, "application/json; charset=utf-8", json.dumps(payload).encode("utf-8")
        if path == "/generate":
            return self._generate(method)
        if path == "/check":
            return self._check(method)
        if method not in {"GET", "POST"}:
            raise ApiError(405, "method_not_allowed", "method is not allowed")
        raise ApiError(404, "not_found", "unknown path")

    def _generate(self, method: str) -> tuple[int, str, bytes]:
        question, as_json = self._one(method, "question", MAX_QUESTION, "invalid_question")
        generation = self.server.prophet.generate(question)
        if as_json:
            return 200, "application/json; charset=utf-8", json.dumps(_generation_payload(generation)).encode("utf-8")
        return 200, "text/html; charset=utf-8", generation_page(generation).encode("utf-8")

    def _check(self, method: str) -> tuple[int, str, bytes]:
        claim, citation, as_json = self._pair(method)
        result = compare_gazette(claim, citation)
        if as_json:
            payload = {
                "verified": result.verified,
                "fact_id": result.fact_id,
                "reason": result.reason,
                "flag": result.flag,
            }
            return 200, "application/json; charset=utf-8", json.dumps(payload).encode("utf-8")
        return 200, "text/html; charset=utf-8", check_page(result).encode("utf-8")

    def _one(self, method: str, name: str, limit: int, code: str) -> tuple[str, bool]:
        if method == "GET":
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True, max_num_fields=4)
            values = query.get(name)
            return _require_text(values[0] if values else None, limit, code), False
        if method != "POST":
            raise ApiError(405, "method_not_allowed", "method is not allowed")
        body = self._read_body()
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type == "application/json":
            payload = _json_dict(body)
            if set(payload) - {name}:
                raise ApiError(400, "invalid_fields", f"JSON body must contain only {name}")
            return _require_text(payload.get(name), limit, code), True
        if content_type == "application/x-www-form-urlencoded":
            try:
                parsed = urllib.parse.parse_qs(body.decode("utf-8"), keep_blank_values=True, max_num_fields=4)
            except UnicodeError as exc:
                raise ApiError(400, "invalid_form", "form body is not valid text") from exc
            values = parsed.get(name)
            return _require_text(values[0] if values else None, limit, code), False
        raise ApiError(415, "unsupported_media", "use JSON or a form body")

    def _pair(self, method: str) -> tuple[str, str, bool]:
        if method == "GET":
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True, max_num_fields=8)
            claim = query.get("claim")
            citation = query.get("citation")
            return (
                _require_text(claim[0] if claim else None, MAX_CLAIM, "invalid_claim"),
                _require_text(citation[0] if citation else None, MAX_CITATION, "invalid_citation"),
                False,
            )
        if method != "POST":
            raise ApiError(405, "method_not_allowed", "method is not allowed")
        body = self._read_body()
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type == "application/json":
            payload = _json_dict(body)
            if set(payload) - {"claim", "citation"}:
                raise ApiError(400, "invalid_fields", "JSON body must contain only claim and citation")
            return (
                _require_text(payload.get("claim"), MAX_CLAIM, "invalid_claim"),
                _require_text(payload.get("citation"), MAX_CITATION, "invalid_citation"),
                True,
            )
        if content_type == "application/x-www-form-urlencoded":
            try:
                parsed = urllib.parse.parse_qs(body.decode("utf-8"), keep_blank_values=True, max_num_fields=8)
            except UnicodeError as exc:
                raise ApiError(400, "invalid_form", "form body is not valid text") from exc
            claim = parsed.get("claim")
            citation = parsed.get("citation")
            return (
                _require_text(claim[0] if claim else None, MAX_CLAIM, "invalid_claim"),
                _require_text(citation[0] if citation else None, MAX_CITATION, "invalid_citation"),
                False,
            )
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


def _json_dict(body: bytes) -> dict:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ApiError(400, "invalid_json", "body is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ApiError(400, "invalid_json", "JSON body must be an object")
    return payload


def _generation_payload(generation: Generation) -> dict[str, object]:
    return {
        "question": generation.question,
        "reply": generation.reply,
        "claim": generation.claim,
        "citation": generation.citation,
        "grounded": generation.grounded,
        "source": generation.source,
        "rule_id": generation.rule_id,
        "backend": generation.backend,
        "fallback": generation.fallback,
    }


def _require_text(value: object, limit: int, code: str) -> str:
    if not isinstance(value, str) or len(value) > limit or not value.strip():
        raise ApiError(400, code, f"value must contain 1 to {limit} characters")
    return value.strip()


def load_prophet_from_env() -> Prophet:
    url = os.environ.get("MIND_CORE_URL", "http://mind-core:5030")
    timeout = _env_float("FALSE_PROPHET_MIND_CORE_TIMEOUT_SECONDS", 2.0)
    return Prophet(url, timeout)


def create_server(prophet: Prophet, bind: str = "127.0.0.1", port: int = 0) -> ProphetServer:
    if bind not in {"0.0.0.0", "127.0.0.1"}:
        raise ValueError("bind address must be 0.0.0.0 or 127.0.0.1")
    return ProphetServer(bind, port, prophet)


def main() -> None:
    port = int(os.environ.get("FALSE_PROPHET_PORT", "5035"))
    if port < 1 or port > 65535:
        raise ValueError("FALSE_PROPHET_PORT is out of range")
    bind = os.environ.get("FALSE_PROPHET_BIND", "0.0.0.0")
    server = create_server(load_prophet_from_env(), bind, port)
    sys.stderr.write(f"false-prophet listening on {bind}:{port}\n")
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
