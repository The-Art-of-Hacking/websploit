"""Small HTTP contract for later AI-track labs.

GET /health and POST /v1/complete. Request bodies are size-capped and
validated before the rules engine sees them. Logs omit prompts, metadata,
and response text so lab flags do not land in container logs.

No credentials, certificates, or cryptographic operations are used.
The listener is HTTP because this service runs on the isolated lab
bridge; TLS material is intentionally not embedded in the image.
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Mapping
from urllib import parse as urlparse

from mindcore.engine import CompletionRequest, Engine, build_engine, default_rules_path

MAX_BODY = 16384
MAX_PROMPT = 8192
MAX_METADATA_KEYS = 16
MAX_METADATA_STRING = 256
_LAB_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?$")
_META_KEY_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_BIND_CHOICES = frozenset({"0.0.0.0", "127.0.0.1"})
_COMPLETE_FIELDS = frozenset({"prompt", "lab", "metadata"})


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


class Settings:
    def __init__(
        self,
        bind: str,
        port: int,
        requested_backend: str,
        timeout_seconds: float,
        max_concurrency: int,
        rules_path: Path,
    ) -> None:
        self.bind = bind
        self.port = port
        self.requested_backend = requested_backend
        self.timeout_seconds = timeout_seconds
        self.max_concurrency = max_concurrency
        self.rules_path = rules_path


def load_settings() -> Settings:
    backend = os.environ.get("MIND_CORE_BACKEND", "deterministic")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", backend):
        raise ValueError("MIND_CORE_BACKEND must match [A-Za-z0-9_-]{1,64}")
    timeout = _env_float("MIND_CORE_BACKEND_TIMEOUT_SECONDS", 2.0, 0.05, 30.0)
    port = _env_int("MIND_CORE_PORT", 5030, 1, 65535)
    bind = os.environ.get("MIND_CORE_BIND", "0.0.0.0")
    if bind not in _BIND_CHOICES:
        raise ValueError("MIND_CORE_BIND must be 0.0.0.0 or 127.0.0.1")
    concurrency = _env_int("MIND_CORE_MAX_CONCURRENCY", 8, 1, 32)
    rules_path = Path(os.environ.get("MIND_CORE_RULES_PATH", str(default_rules_path())))
    return Settings(bind, port, backend, timeout, concurrency, rules_path)


class BoundedHTTPServer(ThreadingHTTPServer):
    """Cap in-flight requests so a small memory limit cannot be thread-bombed."""

    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        handler: type[BaseHTTPRequestHandler],
        max_concurrency: int,
    ) -> None:
        self.engine: Engine | None = None
        self._slots = threading.BoundedSemaphore(max_concurrency)
        super().__init__(server_address, handler)

    def process_request(self, request, client_address) -> None:  # type: ignore[no-untyped-def]
        if not self._slots.acquire(blocking=False):
            _reject_busy(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address) -> None:  # type: ignore[no-untyped-def]
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "mind-core"
    sys_version = ""

    def version_string(self) -> str:
        return "mind-core"

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(5)

    def handle(self) -> None:
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            return

    def do_GET(self) -> None:  # noqa: N802
        started = time.perf_counter()
        try:
            path = self._path()
        except ApiError as exc:
            self._send(exc.status, {"error": exc.code, "message": exc.message})
            self._log(exc.status, started, lab=None, rule_id=None, fallback=False)
            return
        if path == "/health":
            engine = self._engine()
            self._send(200, {
                "status": "ok",
                "ready": True,
                "backend": engine.configured_backend,
                "requested_backend": engine.requested_backend,
            })
            self._log(200, started, lab=None, rule_id=None, fallback=False)
            return
        if path == "/v1/complete":
            self._send(405, {"error": "method_not_allowed", "message": "use POST"})
            self._log(405, started, lab=None, rule_id=None, fallback=False)
            return
        self._send(404, {"error": "not_found", "message": "unknown path"})
        self._log(404, started, lab=None, rule_id=None, fallback=False)

    def do_POST(self) -> None:  # noqa: N802
        started = time.perf_counter()
        try:
            path = self._path()
            if path == "/health":
                raise ApiError(405, "method_not_allowed", "use GET")
            if path != "/v1/complete":
                raise ApiError(404, "not_found", "unknown path")
            request = self._read_completion()
            completion = self._engine().complete(request)
        except ApiError as exc:
            self._send(exc.status, {"error": exc.code, "message": exc.message})
            self._log(exc.status, started, lab=None, rule_id=None, fallback=False)
            return
        except Exception:
            self._send(500, {"error": "internal_error", "message": "request failed"})
            self._log(500, started, lab=None, rule_id=None, fallback=False)
            return
        self._send(200, {
            "text": completion.text,
            "backend": completion.backend,
            "fallback": completion.fallback,
            "rule_id": completion.rule_id,
            "requested_backend": completion.requested_backend,
        })
        self._log(
            200,
            started,
            lab=request.lab,
            rule_id=completion.rule_id,
            fallback=completion.fallback,
        )

    def _path(self) -> str:
        parsed = urlparse.urlsplit(self.path)
        if parsed.query or parsed.fragment or parsed.path != urlparse.unquote(parsed.path):
            raise ApiError(400, "invalid_request", "query strings are not accepted")
        return parsed.path

    def _read_completion(self) -> CompletionRequest:
        if self.headers.get("Transfer-Encoding"):
            raise ApiError(400, "invalid_request", "chunked bodies are not accepted")
        if not _is_json(self.headers.get("Content-Type", "")):
            raise ApiError(415, "unsupported_media_type", "Content-Type must be application/json")
        raw_length = self.headers.get("Content-Length")
        if raw_length is None or not raw_length.isdigit():
            raise ApiError(411, "length_required", "Content-Length is required")
        length = int(raw_length)
        if length <= 0 or length > MAX_BODY:
            raise ApiError(413, "payload_too_large", "body must be 1 to 16384 bytes")
        raw = self.rfile.read(length)
        if len(raw) != length:
            raise ApiError(400, "invalid_request", "truncated body")
        try:
            payload = json.loads(raw)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ApiError(400, "invalid_request", "body must be a JSON object") from exc
        if not isinstance(payload, dict):
            raise ApiError(400, "invalid_request", "body must be a JSON object")
        if set(payload) - _COMPLETE_FIELDS:
            raise ApiError(400, "invalid_request", "unknown fields are not accepted")
        if "prompt" not in payload:
            raise ApiError(400, "invalid_request", "prompt is required")
        prompt = payload["prompt"]
        if not isinstance(prompt, str):
            raise ApiError(400, "invalid_request", "prompt must be a string")
        if not prompt.strip():
            raise ApiError(400, "invalid_request", "prompt must not be empty")
        if len(prompt) > MAX_PROMPT:
            raise ApiError(400, "invalid_request", "prompt is too long")
        lab = payload.get("lab")
        if lab is not None and (not isinstance(lab, str) or _LAB_RE.fullmatch(lab) is None):
            raise ApiError(400, "invalid_request", "lab must be a lowercase id")
        metadata = payload.get("metadata", {})
        if metadata is None:
            metadata = {}
        if not isinstance(metadata, dict):
            raise ApiError(400, "invalid_request", "metadata must be an object")
        _validate_metadata(metadata)
        return CompletionRequest(prompt=prompt, lab=lab, metadata=metadata)

    def _engine(self) -> Engine:
        engine = self.server.engine
        if engine is None:
            raise RuntimeError("engine is not configured")
        return engine

    def _send(self, status: int, payload: Mapping[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("ascii")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'none'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Connection", "close")
        if status == 405:
            allow = "GET" if urlparse.urlsplit(self.path).path == "/health" else "POST"
            self.send_header("Allow", allow)
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def _log(
        self,
        status: int,
        started: float,
        lab: str | None,
        rule_id: str | None,
        fallback: bool,
    ) -> None:
        engine = self.server.engine
        event = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "level": "info" if status < 500 else "error",
            "event": "http",
            "method": _safe_token(self.command, 8),
            "path": _safe_token(urlparse.urlsplit(self.path).path, 64),
            "status": status,
            "lab": lab,
            "rule_id": rule_id,
            "backend": None if engine is None else engine.configured_backend,
            "requested_backend": None if engine is None else engine.requested_backend,
            "fallback": fallback,
            "duration_ms": max(int((time.perf_counter() - started) * 1000), 0),
        }
        sys.stdout.write(json.dumps(event, separators=(",", ":")) + "\n")
        sys.stdout.flush()


def create_server(engine: Engine, bind: str, port: int, max_concurrency: int) -> BoundedHTTPServer:
    server = BoundedHTTPServer((bind, port), Handler, max_concurrency)
    server.engine = engine
    return server


def main() -> None:
    try:
        settings = load_settings()
        engine = build_engine(settings.rules_path, settings.requested_backend, settings.timeout_seconds)
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"mind-core configuration error: {exc}\n")
        raise SystemExit(2) from exc
    server = create_server(engine, settings.bind, settings.port, settings.max_concurrency)
    sys.stdout.write(json.dumps({
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "level": "info",
        "event": "startup",
        "backend": engine.configured_backend,
        "requested_backend": engine.requested_backend,
        "port": settings.port,
    }, separators=(",", ":")) + "\n")
    sys.stdout.flush()
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _validate_metadata(metadata: dict[str, object]) -> None:
    if len(metadata) > MAX_METADATA_KEYS:
        raise ApiError(400, "invalid_request", "metadata has too many keys")
    for key, value in metadata.items():
        if not isinstance(key, str) or _META_KEY_RE.fullmatch(key) is None:
            raise ApiError(400, "invalid_request", "metadata key is invalid")
        if isinstance(value, bool) or value is None:
            continue
        if isinstance(value, str):
            if len(value) > MAX_METADATA_STRING:
                raise ApiError(400, "invalid_request", "metadata string is too long")
            continue
        if isinstance(value, int):
            continue
        if isinstance(value, float) and value == value and value not in (float("inf"), float("-inf")):
            continue
        raise ApiError(400, "invalid_request", "metadata values must be scalar")


def _is_json(content_type: str) -> bool:
    parts = [part.strip() for part in content_type.split(";") if part.strip()]
    if not parts or parts[0].lower() != "application/json":
        return False
    for param in parts[1:]:
        name, separator, value = param.partition("=")
        if separator != "=" or name.strip().lower() != "charset":
            return False
        if value.strip().strip('"').lower() not in {"utf-8", "utf8"}:
            return False
    return True


def _reject_busy(request) -> None:  # type: ignore[no-untyped-def]
    body = b'{"error":"busy","message":"too many requests"}'
    raw = (
        b"HTTP/1.1 429 Too Many Requests\r\n"
        b"Content-Type: application/json; charset=utf-8\r\n"
        b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n"
        b"Cache-Control: no-store\r\n"
        b"Connection: close\r\n"
        b"\r\n"
        + body
    )
    try:
        request.sendall(raw)
    except OSError:
        pass
    finally:
        request.close()


def _env_int(name: str, default: int, low: int, high: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    if not raw.isdigit():
        raise ValueError(f"{name} must be an integer")
    value = int(raw)
    if value < low or value > high:
        raise ValueError(f"{name} is out of range")
    return value


def _env_float(name: str, default: float, low: float, high: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
    if value < low or value > high:
        raise ValueError(f"{name} is out of range")
    return value


def _safe_token(value: str, limit: int) -> str:
    cleaned = "".join(ch if ch.isprintable() and ch not in "\r\n" else "?" for ch in value)
    return cleaned[:limit]
