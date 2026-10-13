"""Deterministic flag paths for marionette.

The HTTP tests cover mind-core's rules engine and the local fallback used
when that call is refused or slow. No API key and no model weights.
"""

from __future__ import annotations

import json
import socket
import sys
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MIND_CORE = ROOT.parent / "mind-core"
sys.path.insert(0, str(MIND_CORE))
sys.path.insert(0, str(ROOT))

import app  # noqa: E402
from mindcore.engine import CompletionRequest, build_engine  # noqa: E402

EXISTING_RULE_IDS = (
    "mind-core-ping",
    "mind-core-help",
    "acknowledge-lab",
    "mind-core-self-check",
    "echo-chamber-status",
    "echo-chamber-web",
    "echo-chamber-sql",
    "echo-chamber-shell",
    "oracle-booth-direct",
    "oracle-booth-indirect",
    "oracle-booth-answer",
)
UNROUTABLE_SOURCE = "10.7.7.10"


class _MindHandler(BaseHTTPRequestHandler):
    engine = None
    seen: list[dict] = []

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        self.seen.append(payload)
        result = self.engine.complete(
            CompletionRequest(payload["prompt"], payload.get("lab"), payload.get("metadata") or {})
        )
        body = json.dumps(
            {
                "text": result.text,
                "backend": result.backend,
                "fallback": result.fallback,
                "rule_id": result.rule_id,
                "requested_backend": result.requested_backend,
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


class _RelayHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = b"<title>SecretCorp Diagnostics Suite</title>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def _serve(handler: type[BaseHTTPRequestHandler]) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    return server


def _start_mind() -> ThreadingHTTPServer:
    _MindHandler.engine = build_engine(MIND_CORE / "rules.json")
    _MindHandler.seen = []
    return _serve(_MindHandler)


def _closed_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _copilot(mind_port: int, mind_timeout: float = 2.0) -> app.Copilot:
    return app.Copilot(f"http://127.0.0.1:{mind_port}", mind_timeout, 0.3, UNROUTABLE_SOURCE)


class RuleContractTests(unittest.TestCase):
    def test_local_rules_match_mind_core_file(self) -> None:
        payload = json.loads((MIND_CORE / "rules.json").read_text(encoding="utf-8"))
        by_id = {rule["id"]: rule for rule in payload["rules"]}
        ids = [rule["id"] for rule in payload["rules"]]
        start = ids.index("marionette-direct")
        self.assertLess(ids.index("oracle-booth-answer"), start)
        self.assertEqual(
            ids[start : start + 3],
            ["marionette-direct", "marionette-indirect", "marionette-plan"],
        )
        for rule in app.LOCAL_RULES:
            entry = by_id[rule.id]
            self.assertEqual(entry["lab"], "marionette")
            self.assertEqual(entry["match_type"], "contains")
            self.assertEqual(entry["match"], rule.match)
            self.assertEqual(entry["text"], rule.text)
        for rule_id in EXISTING_RULE_IDS:
            self.assertIn(rule_id, by_id)

    def test_triggers_do_not_overlap_existing_rules(self) -> None:
        payload = json.loads((MIND_CORE / "rules.json").read_text(encoding="utf-8"))
        own = {item.id for item in app.LOCAL_RULES}
        existing = [rule["match"] for rule in payload["rules"] if rule["id"] not in own]
        self.assertEqual(len(existing), len(EXISTING_RULE_IDS))
        for rule in app.LOCAL_RULES:
            for other in existing:
                self.assertNotIn(rule.match, other)
                self.assertNotIn(other, rule.match)
        for task in (app.DIRECT_TASK, app.INDIRECT_TASK, app.BENIGN_TASK):
            prompt = app.compose(task, app.retrieve(task))
            for other in existing:
                self.assertNotIn(other, prompt)

    def test_engine_scopes_marionette_rules(self) -> None:
        engine = build_engine(MIND_CORE / "rules.json")
        for rule in app.LOCAL_RULES:
            hit = engine.complete(CompletionRequest(rule.match, "marionette", {}))
            self.assertEqual(hit.rule_id, rule.id)
            self.assertEqual(hit.text, rule.text)
            self.assertIs(hit.fallback, False)
            other = engine.complete(CompletionRequest(rule.match, "oracle-booth", {}))
            self.assertNotEqual(other.rule_id, rule.id)
        both = "\n".join((app.MARKER, app.DIRECT_TRIGGER, app.INDIRECT_TRIGGER))
        self.assertEqual(engine.complete(CompletionRequest(both, "marionette", {})).rule_id, "marionette-direct")
        indirect = app.MARKER + "\n" + app.INDIRECT_TRIGGER
        self.assertEqual(engine.complete(CompletionRequest(indirect, "marionette", {})).rule_id, "marionette-indirect")
        self.assertEqual(engine.complete(CompletionRequest(app.MARKER, "marionette", {})).rule_id, "marionette-plan")

    def test_flags_are_not_in_rules_or_notes(self) -> None:
        text = (MIND_CORE / "rules.json").read_text(encoding="utf-8")
        self.assertNotIn(app.SSRF_FLAG, text)
        self.assertNotIn(app.HIJACK_FLAG, text)
        for document in app.DOCUMENTS:
            self.assertNotIn(app.SSRF_FLAG, document.body)
            self.assertNotIn(app.HIJACK_FLAG, document.body)
            self.assertNotIn(app.DIRECT_TRIGGER, document.body)
            self.assertNotIn(app.MARKER, document.body)
        self.assertIn(app.INDIRECT_TRIGGER, app.DOCUMENTS_BY_ID["relay-notes"].body)
        self.assertNotIn(app.INDIRECT_TRIGGER, app.DOCUMENTS_BY_ID["onboarding"].body)


class PlanningTests(unittest.TestCase):
    def test_tasks_use_different_paths(self) -> None:
        self.assertIn(app.DIRECT_TRIGGER, app.DIRECT_TASK)
        self.assertNotIn(app.INDIRECT_TRIGGER, app.INDIRECT_TASK)
        self.assertNotIn(app.DIRECT_TRIGGER, app.INDIRECT_TASK)
        notes = app.retrieve(app.INDIRECT_TASK)
        self.assertEqual(tuple(note.id for note in notes), ("relay-notes",))
        self.assertIn(app.INDIRECT_TRIGGER, app.compose(app.INDIRECT_TASK, notes))
        benign = app.retrieve(app.BENIGN_TASK)
        self.assertEqual(tuple(note.id for note in benign), ("onboarding",))

    def test_parse_directive(self) -> None:
        self.assertEqual(app.parse_directive(app.RELAY_DIRECTIVE), ("http_get", app.RELAY_URL))
        self.assertEqual(app.parse_directive(app.PLAN_DIRECTIVE), ("none", ""))
        self.assertEqual(app.parse_directive("hello"), ("none", ""))

    def test_internal_classification(self) -> None:
        self.assertTrue(app._is_internal("10.6.6.32"))
        self.assertTrue(app._is_internal("127.0.0.1"))
        self.assertTrue(app._is_internal("trojan-relay"))
        self.assertFalse(app._is_internal("203.0.113.9"))
        self.assertFalse(app._is_internal("example.com"))

    def test_credential_url_rejected(self) -> None:
        with self.assertRaises(ValueError):
            app.Copilot("http://user:secret@mind-core:5030", 2, 1, UNROUTABLE_SOURCE)


class ToolTests(unittest.TestCase):
    def test_http_get_reaches_an_internal_relay(self) -> None:
        relay = _serve(_RelayHandler)
        try:
            host, port = relay.server_address
            tool = _copilot(_closed_port()).http_get(f"http://{host}:{port}/")
        finally:
            relay.shutdown()
            relay.server_close()
        self.assertTrue(tool.internal)
        self.assertEqual(tool.status, 200)
        self.assertIn("SecretCorp Diagnostics Suite", tool.body_excerpt)
        self.assertEqual(tool.flag, app.SSRF_FLAG)

    def test_http_get_external_target_has_no_flag(self) -> None:
        tool = _copilot(_closed_port()).http_get("http://203.0.113.9/")
        self.assertFalse(tool.internal)
        self.assertIsNone(tool.flag)

    def test_http_get_rejects_non_http(self) -> None:
        with self.assertRaises(app.ApiError):
            _copilot(_closed_port()).http_get("file:///etc/passwd")

    def test_sandbox_egress_fails_from_isolated_source(self) -> None:
        report = _copilot(_closed_port()).sandbox_egress("203.0.113.9", 80)
        self.assertIs(report["egress"], False)
        self.assertEqual(report["source"], UNROUTABLE_SOURCE)
        self.assertTrue(report["detail"])

    def test_sandbox_probe_reports_a_reachable_route(self) -> None:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        try:
            copilot = app.Copilot(f"http://127.0.0.1:{_closed_port()}", 1, 0.5, "127.0.0.1")
            report = copilot.sandbox_egress("127.0.0.1", port)
        finally:
            listener.close()
        self.assertIs(report["egress"], True)


class _HttpCase(unittest.TestCase):
    httpd: app.CopilotServer

    def setUp(self) -> None:
        _MindHandler.seen.clear()

    @classmethod
    def _boot(cls, copilot: app.Copilot) -> None:
        cls.httpd = app.create_server(copilot, "127.0.0.1", 0)
        threading.Thread(target=cls.httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
        host, port = cls.httpd.server_address
        cls.base = f"http://{host}:{port}"

    @classmethod
    def _stop(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _request(self, method: str, path: str, payload: dict | None = None, form: dict | None = None) -> tuple[int, str]:
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif form is not None:
            data = urllib.parse.urlencode(form).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8")

    def _capture_both(self, source: str) -> None:
        status, direct = self._request("POST", "/agent", {"task": app.DIRECT_TASK})
        self.assertEqual(status, 200)
        direct_body = json.loads(direct)
        self.assertEqual(direct_body["rule_id"], "marionette-direct")
        self.assertEqual(direct_body["source"], source)
        self.assertEqual(direct_body["tool"]["target"], app.RELAY_URL)
        self.assertIs(direct_body["tool"]["internal"], True)
        self.assertEqual(direct_body["flags"], [app.SSRF_FLAG])
        status, indirect = self._request("POST", "/agent", {"task": app.INDIRECT_TASK})
        self.assertEqual(status, 200)
        indirect_body = json.loads(indirect)
        self.assertEqual(indirect_body["rule_id"], "marionette-indirect")
        self.assertEqual(indirect_body["source"], source)
        self.assertEqual(indirect_body["documents"], ["relay-notes"])
        self.assertEqual(indirect_body["tool"]["target"], app.RELAY_URL)
        self.assertEqual(indirect_body["flags"], [app.SSRF_FLAG, app.HIJACK_FLAG])


class MindCoreHttpTests(_HttpCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mind = _start_mind()
        cls._boot(_copilot(cls.mind.server_address[1]))

    @classmethod
    def tearDownClass(cls) -> None:
        cls._stop()
        cls.mind.shutdown()
        cls.mind.server_close()

    def test_health_index_and_notes_hide_flags(self) -> None:
        status, body = self._request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["status"], "ok")
        for path in ("/", "/notes", "/notes/relay-notes"):
            status, page = self._request("GET", path)
            self.assertEqual(status, 200)
            self.assertNotIn(app.SSRF_FLAG, page)
            self.assertNotIn(app.HIJACK_FLAG, page)
        status, note = self._request("GET", "/notes/relay-notes")
        self.assertIn(app.INDIRECT_TRIGGER, json.loads(note)["body"])
        status, _missing = self._request("GET", "/notes/secrets")
        self.assertEqual(status, 404)

    def test_both_flags(self) -> None:
        self._capture_both("mind-core")

    def test_indirect_trigger_comes_from_the_note(self) -> None:
        self._request("POST", "/agent", {"task": app.INDIRECT_TASK})
        sent = _MindHandler.seen[-1]
        self.assertEqual(sent["lab"], "marionette")
        self.assertNotIn(app.INDIRECT_TRIGGER, app.INDIRECT_TASK)
        self.assertIn(app.INDIRECT_TRIGGER, sent["prompt"])
        self.assertIn("[relay-notes]", sent["prompt"])

    def test_benign_task_calls_no_tool(self) -> None:
        status, body = self._request("POST", "/agent", {"task": app.BENIGN_TASK})
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertEqual(payload["rule_id"], "marionette-plan")
        self.assertIsNone(payload["tool"])
        self.assertEqual(payload["flags"], [])

    def test_tool_endpoint_ssrf(self) -> None:
        status, body = self._request("POST", "/tools/http_get", {"url": app.RELAY_URL})
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertIs(payload["internal"], True)
        self.assertEqual(payload["flag"], app.SSRF_FLAG)

    def test_db_query_tool(self) -> None:
        status, body = self._request("POST", "/tools/db_query", {"query": "SELECT * FROM tickets"})
        self.assertEqual(status, 200)
        self.assertIn("ticket-104", json.loads(body)["body_excerpt"])

    def test_sandbox_egress_endpoint(self) -> None:
        status, body = self._request("GET", "/sandbox/egress")
        self.assertEqual(status, 200)
        self.assertIs(json.loads(body)["egress"], False)

    def test_form_posts_html(self) -> None:
        status, page = self._request("POST", "/agent", form={"task": app.INDIRECT_TASK})
        self.assertEqual(status, 200)
        self.assertIn(app.HIJACK_FLAG, page)
        self.assertIn("rule: marionette-indirect", page)

    def test_empty_task_rejected(self) -> None:
        status, body = self._request("POST", "/agent", {"task": "   "})
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)["error"], "invalid_task")


class FallbackHttpTests(_HttpCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._boot(_copilot(_closed_port(), 0.2))

    @classmethod
    def tearDownClass(cls) -> None:
        cls._stop()

    def test_flags_when_mind_core_is_down(self) -> None:
        self._capture_both("local-fallback")

    def test_slow_mind_core_uses_fallback(self) -> None:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        try:
            started = time.monotonic()
            run = _copilot(port, 0.2).run(app.DIRECT_TASK)
            elapsed = time.monotonic() - started
        finally:
            listener.close()
        self.assertLess(elapsed, 2.0)
        self.assertEqual(run.source, "local-fallback")
        self.assertEqual(run.rule_id, "marionette-direct")
        self.assertIn(app.SSRF_FLAG, run.flags)


if __name__ == "__main__":
    unittest.main()
