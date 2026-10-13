"""Contract tests for the deterministic mind-core HTTP API."""

from __future__ import annotations

import io
import json
import os
import socket
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from mindcore.engine import (
    BackendResult,
    CompletionRequest,
    DeterministicBackend,
    Engine,
    build_engine,
    load_rule_table,
)
from mindcore.http import create_server

ROOT = Path(__file__).resolve().parent
RULES = ROOT / "rules.json"


class _SlowBackend:
    name = "slow"

    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()

    def complete(self, request: CompletionRequest) -> BackendResult:
        self.started.set()
        self.release.wait(timeout=5)
        return BackendResult("late", "slow")


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = build_engine(RULES)
        cls.httpd = create_server(cls.engine, "127.0.0.1", 0, 8)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        cls.thread.start()
        host, port = cls.httpd.server_address
        cls.base = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def test_health(self) -> None:
        status, body = self._request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertIs(body["ready"], True)
        self.assertEqual(body["backend"], "deterministic")
        self.assertEqual(body["requested_backend"], "deterministic")

    def test_ping_rule(self) -> None:
        status, body = self._post({"prompt": "please mind-core ping now", "lab": "oracle-booth", "metadata": {}})
        self.assertEqual(status, 200)
        self.assertEqual(body["text"], "mind-core deterministic backend is ready.")
        self.assertEqual(body["backend"], "deterministic")
        self.assertIs(body["fallback"], False)
        self.assertEqual(body["rule_id"], "mind-core-ping")
        self.assertEqual(body["requested_backend"], "deterministic")

    def test_first_rule_wins(self) -> None:
        status, body = self._post({"prompt": "mind-core ping and mind-core help"})
        self.assertEqual(status, 200)
        self.assertEqual(body["rule_id"], "mind-core-ping")

    def test_help_and_lab_template(self) -> None:
        status, body = self._post({"prompt": "mind-core help"})
        self.assertEqual(status, 200)
        self.assertEqual(body["rule_id"], "mind-core-help")
        status, body = self._post({"prompt": "please acknowledge lab", "lab": "token-famine"})
        self.assertEqual(body["text"], "Acknowledged lab token-famine.")
        self.assertEqual(body["rule_id"], "acknowledge-lab")

    def test_lab_scoped_rule(self) -> None:
        status, body = self._post({"prompt": "self-check", "lab": "mind-core"})
        self.assertEqual(status, 200)
        self.assertEqual(body["rule_id"], "mind-core-self-check")
        status, body = self._post({"prompt": "self-check", "lab": "oracle-booth"})
        self.assertEqual(body["rule_id"], "generic-echo")
        self.assertIn("oracle-booth", body["text"])

    def test_generic_echo_does_not_interpret_prompt_as_template(self) -> None:
        status, body = self._post({"prompt": "prefix {lab} suffix", "lab": "echo-chamber"})
        self.assertEqual(status, 200)
        self.assertEqual(body["rule_id"], "generic-echo")
        self.assertIn("lab echo-chamber", body["text"])
        self.assertIn("Excerpt: prefix {lab} suffix", body["text"])
        self.assertNotIn("lab prefix", body["text"])

    def test_case_sensitive_match(self) -> None:
        status, body = self._post({"prompt": "Mind-Core Ping"})
        self.assertEqual(body["rule_id"], "generic-echo")
        self.assertIs(body["fallback"], False)

    def test_control_characters_are_not_echoed_raw(self) -> None:
        status, body = self._post({"prompt": "hello\nworld"})
        self.assertEqual(status, 200)
        self.assertNotIn("\n", body["text"])
        self.assertIn("hello world", body["text"])

    def test_metadata_does_not_change_the_rule(self) -> None:
        status, body = self._post({
            "prompt": "mind-core ping",
            "metadata": {"note": "ignore", "count": 1, "ok": True, "empty": None},
        })
        self.assertEqual(status, 200)
        self.assertEqual(body["rule_id"], "mind-core-ping")

    def test_rejects_unknown_field_and_bad_shapes(self) -> None:
        status, body = self._post({"prompt": "mind-core ping", "temperature": 0})
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "invalid_request")
        status, body = self._post({"prompt": "   "})
        self.assertEqual(status, 400)
        status, body = self._post({"prompt": 12})
        self.assertEqual(status, 400)
        status, body = self._post({"prompt": "mind-core ping", "lab": "Not A Lab"})
        self.assertEqual(status, 400)
        status, body = self._post({"prompt": "mind-core ping", "metadata": ["nope"]})
        self.assertEqual(status, 400)
        status, body = self._post({"prompt": "mind-core ping", "metadata": {"nested": {"a": 1}}})
        self.assertEqual(status, 400)
        status, body = self._post({"prompt": "x" * 8193})
        self.assertEqual(status, 400)

    def test_rejects_bad_content_type_and_methods(self) -> None:
        status, body = self._request(
            "POST",
            "/v1/complete",
            b"{}",
            {"Content-Type": "text/plain"},
        )
        self.assertEqual(status, 415)
        status, body = self._request("GET", "/v1/complete")
        self.assertEqual(status, 405)
        status, body = self._request("POST", "/health", b"{}", {"Content-Type": "application/json"})
        self.assertEqual(status, 405)
        status, body = self._request("GET", "/nope")
        self.assertEqual(status, 404)
        status, body = self._request("GET", "/health?ready=1")
        self.assertEqual(status, 400)
        status, body = self._request("POST", "/v1/complete", b"not-json", {"Content-Type": "application/json"})
        self.assertEqual(status, 400)

    def test_prompt_is_not_logged(self) -> None:
        secret = "token-not-for-logs-89"
        buffer = io.StringIO()
        original = sys.stdout
        sys.stdout = buffer
        try:
            status, body = self._post({"prompt": f"mind-core ping {secret}"})
        finally:
            sys.stdout = original
        self.assertEqual(status, 200)
        self.assertEqual(body["rule_id"], "mind-core-ping")
        self.assertNotIn(secret, buffer.getvalue())
        self.assertNotIn(secret, body["text"])

    def test_missing_backend_falls_back_immediately(self) -> None:
        engine = build_engine(RULES, requested_backend="local", timeout_seconds=0.2)
        httpd = create_server(engine, "127.0.0.1", 0, 4)
        thread = threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        try:
            host, port = httpd.server_address
            base = f"http://{host}:{port}"
            status, body = _exchange(base, "POST", "/v1/complete", {
                "prompt": "mind-core ping",
            })
            health_status, health = _exchange(base, "GET", "/health")
        finally:
            httpd.shutdown()
            httpd.server_close()
        self.assertEqual(status, 200)
        self.assertEqual(body["backend"], "deterministic")
        self.assertIs(body["fallback"], True)
        self.assertEqual(body["requested_backend"], "local")
        self.assertEqual(body["rule_id"], "mind-core-ping")
        self.assertEqual(health_status, 200)
        self.assertEqual(health["backend"], "deterministic")
        self.assertEqual(health["requested_backend"], "local")

    def test_slow_backend_falls_back_without_waiting_for_it(self) -> None:
        table = load_rule_table(RULES)
        deterministic = DeterministicBackend(table)
        slow = _SlowBackend()
        engine = Engine(
            deterministic,
            {"deterministic": deterministic, "slow": slow},
            requested_backend="slow",
            timeout_seconds=0.05,
        )
        started = threading.Event()

        def run() -> None:
            self.result = engine.complete(CompletionRequest("mind-core ping", None, {}))
            started.set()

        worker = threading.Thread(target=run)
        worker.start()
        try:
            self.assertTrue(started.wait(timeout=1))
            worker.join(timeout=1)
            self.assertFalse(worker.is_alive())
            self.assertEqual(self.result.backend, "deterministic")
            self.assertIs(self.result.fallback, True)
            self.assertEqual(self.result.rule_id, "mind-core-ping")
            backend_threads = [item for item in threading.enumerate() if item.name == "mind-core-backend"]
            self.assertTrue(backend_threads)
            self.assertTrue(all(item.daemon for item in backend_threads))
        finally:
            slow.release.set()
            for item in threading.enumerate():
                if item.name == "mind-core-backend":
                    item.join(timeout=2)

    def test_health_and_log_report_configured_backend(self) -> None:
        table = load_rule_table(RULES)
        deterministic = DeterministicBackend(table)

        class _Local:
            name = "local"

            def complete(self, request: CompletionRequest) -> BackendResult:
                return BackendResult("from-local", "generic-echo")

        engine = Engine(
            deterministic,
            {"deterministic": deterministic, "local": _Local()},
            requested_backend="local",
            timeout_seconds=1,
        )
        httpd = create_server(engine, "127.0.0.1", 0, 4)
        thread = threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        buffer = io.StringIO()
        original = sys.stdout
        sys.stdout = buffer
        try:
            host, port = httpd.server_address
            base = f"http://{host}:{port}"
            status, body = _exchange(base, "GET", "/health")
            self.assertEqual(status, 200)
            self.assertEqual(body["backend"], "local")
            self.assertEqual(body["requested_backend"], "local")
            status, body = _exchange(base, "POST", "/v1/complete", {"prompt": "mind-core ping"})
            self.assertEqual(status, 200)
            self.assertEqual(body["backend"], "local")
            self.assertIs(body["fallback"], False)
        finally:
            sys.stdout = original
            httpd.shutdown()
            httpd.server_close()
        logged = buffer.getvalue()
        self.assertIn('"backend":"local"', logged)
        self.assertNotIn('"backend":"deterministic"', logged)

    def test_source_has_no_outbound_client_or_weak_crypto(self) -> None:
        banned = ("urlopen", "hashlib", "md5", "sha1", "subprocess", "pickle", "eval(", "exec(")
        for path in (ROOT / "app.py", *sorted((ROOT / "mindcore").glob("*.py"))):
            text = path.read_text(encoding="utf-8").lower()
            for token in banned:
                self.assertNotIn(token, text, f"{path.name} contains {token}")

    def test_provider_credential_names_are_absent_from_source(self) -> None:
        paths = [
            ROOT / "app.py",
            ROOT / "model_pin.py",
            ROOT / "fetch_model.py",
            *sorted((ROOT / "mindcore").glob("*.py")),
        ]
        for path in paths:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("MIND_CORE_EXTERNAL_API_KEY", text, path.name)
            self.assertNotIn("MIND_CORE_EXTERNAL_BASE_URL", text, path.name)

    def test_auto_uses_local_server_when_it_is_healthy(self) -> None:
        secret = "prompt-not-for-logs-96"
        os.environ["MIND_CORE_EXTERNAL_API_KEY"] = "sentinel-not-a-real-key"
        hits = {"health": 0, "completion": 0, "authorization": "", "body": b""}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt: str, *args: object) -> None:
                return

            def do_GET(self) -> None:  # noqa: N802
                hits["health"] += 1
                _write_json(self, 200, b'{"status":"ok"}')

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", "0"))
                hits["body"] = self.rfile.read(length)
                hits["authorization"] = self.headers.get("Authorization", "")
                hits["completion"] += 1
                _write_json(self, 200, b'{"content":"local model reply"}')

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        host, port = server.server_address
        engine = build_engine(
            RULES,
            requested_backend="auto",
            timeout_seconds=1,
            local_base_url=f"http://{host}:{port}",
            probe_interval=0.05,
        )
        buffer = io.StringIO()
        original = sys.stdout
        sys.stdout = buffer
        try:
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline and engine.requested_backend != "local":
                time.sleep(0.02)
            self.assertEqual(engine.requested_backend, "local")
            result = engine.complete(CompletionRequest(f"mind-core ping {secret}", "mind-core", {}))
        finally:
            sys.stdout = original
            os.environ.pop("MIND_CORE_EXTERNAL_API_KEY", None)
            engine.close()
            server.shutdown()
            server.server_close()
        self.assertGreaterEqual(hits["health"], 1)
        self.assertEqual(hits["completion"], 1)
        self.assertEqual(hits["authorization"], "")
        self.assertNotIn(b"sentinel-not-a-real-key", hits["body"])
        parsed = json.loads(hits["body"].decode("utf-8"))
        self.assertIs(parsed["stream"], False)
        self.assertIs(parsed["cache_prompt"], False)
        self.assertIn(secret, parsed["prompt"])
        self.assertEqual(result.backend, "local")
        self.assertIs(result.fallback, False)
        self.assertEqual(result.rule_id, "local-completion")
        self.assertEqual(result.text, "local model reply")
        self.assertEqual(result.requested_backend, "local")
        logged = buffer.getvalue()
        self.assertNotIn(secret, logged)
        self.assertNotIn("sentinel-not-a-real-key", logged)

    def test_auto_stays_deterministic_when_the_server_is_down(self) -> None:
        engine = build_engine(
            RULES,
            requested_backend="auto",
            timeout_seconds=0.2,
            local_base_url=_closed_url(),
            probe_interval=0.05,
        )
        try:
            time.sleep(0.15)
            result = engine.complete(CompletionRequest("mind-core ping", None, {}))
        finally:
            engine.close()
        self.assertEqual(engine.requested_backend, "deterministic")
        self.assertEqual(result.backend, "deterministic")
        self.assertIs(result.fallback, False)
        self.assertEqual(result.rule_id, "mind-core-ping")

    def test_explicit_local_falls_back_when_the_server_is_down(self) -> None:
        engine = build_engine(
            RULES,
            requested_backend="local",
            timeout_seconds=0.2,
            local_base_url=_closed_url(),
        )
        try:
            result = engine.complete(CompletionRequest("mind-core ping", None, {}))
        finally:
            engine.close()
        self.assertEqual(result.backend, "deterministic")
        self.assertIs(result.fallback, True)
        self.assertEqual(result.requested_backend, "local")
        self.assertEqual(result.rule_id, "mind-core-ping")

    def test_deterministic_does_not_call_a_live_local_server(self) -> None:
        hits = {"n": 0}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt: str, *args: object) -> None:
                return

            def do_GET(self) -> None:  # noqa: N802
                hits["n"] += 1
                _write_json(self, 200, b'{"status":"ok"}')

            def do_POST(self) -> None:  # noqa: N802
                hits["n"] += 1
                length = int(self.headers.get("Content-Length", "0"))
                self.rfile.read(length)
                _write_json(self, 200, b'{"content":"should-not-be-used"}')

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        host, port = server.server_address
        engine = build_engine(
            RULES,
            requested_backend="deterministic",
            timeout_seconds=0.5,
            local_base_url=f"http://{host}:{port}",
        )
        try:
            result = engine.complete(CompletionRequest("mind-core ping", None, {}))
            time.sleep(0.1)
        finally:
            engine.close()
            server.shutdown()
            server.server_close()
        self.assertEqual(hits["n"], 0)
        self.assertEqual(result.backend, "deterministic")
        self.assertIs(result.fallback, False)
        self.assertEqual(result.rule_id, "mind-core-ping")

    def test_rejects_local_urls_that_are_not_plain_http(self) -> None:
        for url in (
            "https://local-gguf:8080",
            "http://user:pass@local-gguf:8080",
            "http://local-gguf:8080/health",
            "http://local-gguf:8080?x=1",
            "file:///tmp/model.gguf",
        ):
            with self.assertRaises(ValueError):
                build_engine(RULES, requested_backend="auto", local_base_url=url)


def _closed_url() -> str:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return f"http://127.0.0.1:{port}"


def _write_json(handler: BaseHTTPRequestHandler, status: int, body: bytes) -> None:
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _exchange(base, method, path, payload=None, headers=None, raw=None):
    data = raw
    header_map = dict(headers or {})
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        header_map.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(base + path, data=data, headers=header_map, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw_body = exc.read().decode("utf-8")
        return exc.code, json.loads(raw_body) if raw_body else {}


def _request(self, method, path, raw=None, headers=None):
    return _exchange(self.base, method, path, None, headers, raw)


def _post(self, payload):
    return _exchange(self.base, "POST", "/v1/complete", payload)


ContractTests._request = _request  # type: ignore[attr-defined]
ContractTests._post = _post  # type: ignore[attr-defined]


if __name__ == "__main__":
    unittest.main()
