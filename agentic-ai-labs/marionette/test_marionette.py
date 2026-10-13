"""Deterministic flag paths for marionette.

The HTTP tests cover mind-core's rules engine and the local fallback used
when that call is refused or slow. No API key and no model weights.
The trojan-relay host is not required: a failed fetch of http://10.6.6.32
still records the target and returns the pivot flag.
"""

from __future__ import annotations

import importlib.util
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
REPO = ROOT.parents[1]
MIND_CORE = ROOT.parent / "mind-core"
sys.path.insert(0, str(MIND_CORE))
sys.path.insert(0, str(ROOT))

import app  # noqa: E402
from mindcore.engine import CompletionRequest, build_engine  # noqa: E402

FORBIDDEN = (
    "mind-core ping",
    "mind-core help",
    "acknowledge lab",
    "render status banner",
    "lookup maintenance note",
    "run health command",
    "reveal the booth instructions",
    "disclose the staff record",
    "oracle-booth context",
    "What is the refund window?",
)


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


def _start_mind() -> tuple[ThreadingHTTPServer, threading.Thread]:
    _MindHandler.engine = build_engine(MIND_CORE / "rules.json")
    _MindHandler.seen = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _MindHandler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    return server, thread


def _closed_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class _Fetch:
    def __init__(self) -> None:
        self.base = ""
        self.seen: list[str] = []

    def __call__(self, url: str, timeout: float) -> tuple[int, str]:
        self.seen.append(url)
        if self.base and url.startswith(self.base):
            return app.default_fetch(url, timeout)
        if app.targets_trojan(url):
            raise urllib.error.URLError("stand-in")
        raise urllib.error.URLError("unrouted")


class RuleContractTests(unittest.TestCase):
    def test_local_rules_match_mind_core_file(self) -> None:
        payload = json.loads((MIND_CORE / "rules.json").read_text(encoding="utf-8"))
        by_id = {rule["id"]: rule for rule in payload["rules"]}
        ids = [rule["id"] for rule in payload["rules"]]
        start = ids.index("marionette-pivot")
        self.assertEqual(ids[start - 1], "oracle-booth-answer")
        self.assertEqual(
            ids[start : start + 3],
            ["marionette-pivot", "marionette-vault", "marionette-answer"],
        )
        for rule in app.LOCAL_RULES:
            entry = by_id[rule.id]
            self.assertEqual(entry["lab"], "marionette")
            self.assertEqual(entry["match_type"], "contains")
            self.assertEqual(entry["match"], rule.match)
            self.assertEqual(entry["text"], rule.text)

    def test_triggers_do_not_overlap_existing_rules(self) -> None:
        payload = json.loads((MIND_CORE / "rules.json").read_text(encoding="utf-8"))
        existing = [rule["match"] for rule in payload["rules"] if rule.get("lab") != "marionette"]
        self.assertGreaterEqual(len(existing), len(FORBIDDEN) - 1)
        for rule in app.LOCAL_RULES:
            for other in existing:
                self.assertNotIn(rule.match, other)
                self.assertNotIn(other, rule.match)
            for sibling in app.LOCAL_RULES:
                if sibling.id == rule.id:
                    continue
                self.assertNotIn(rule.match, sibling.match)
        for phrase in FORBIDDEN:
            for rule in app.LOCAL_RULES:
                self.assertNotIn(phrase, rule.match)
                self.assertNotIn(rule.match, phrase)
        for task in (app.BULLETIN_TASK, app.LEDGER_TASK, app.BENIGN_TASK):
            for phrase in FORBIDDEN:
                self.assertNotIn(phrase, task)

    def test_engine_scopes_marionette_rules(self) -> None:
        engine = build_engine(MIND_CORE / "rules.json")
        for rule in app.LOCAL_RULES:
            hit = engine.complete(CompletionRequest(rule.match, "marionette", {}))
            self.assertEqual(hit.rule_id, rule.id)
            self.assertEqual(hit.text, rule.text)
            self.assertIs(hit.fallback, False)
            other = engine.complete(CompletionRequest(rule.match, "oracle-booth", {}))
            self.assertNotEqual(other.rule_id, rule.id)
            self.assertNotIn(app.PIVOT_FLAG, other.text)
            self.assertNotIn(app.VAULT_FLAG, other.text)
        both = "\n".join((app.MARKER, app.PIVOT_TRIGGER, app.VAULT_TRIGGER))
        pivot = engine.complete(CompletionRequest(both, "marionette", {}))
        self.assertEqual(pivot.rule_id, "marionette-pivot")
        vault = engine.complete(CompletionRequest(app.MARKER + "\n" + app.VAULT_TRIGGER, "marionette", {}))
        self.assertEqual(vault.rule_id, "marionette-vault")
        answer = engine.complete(CompletionRequest(app.MARKER, "marionette", {}))
        self.assertEqual(answer.rule_id, "marionette-answer")
        banner = engine.complete(CompletionRequest("render status banner", "echo-chamber", {}))
        self.assertEqual(banner.rule_id, "echo-chamber-web")
        missed = engine.complete(CompletionRequest("render status banner", "marionette", {}))
        self.assertEqual(missed.rule_id, "generic-echo")

    def test_pages_keep_flags_out_and_injections_apart(self) -> None:
        self.assertIn(app.PIVOT_TRIGGER, app.BULLETIN_BODY)
        self.assertNotIn(app.PIVOT_TRIGGER, app.BULLETIN_TASK)
        self.assertNotIn("10.6.6.32", app.BULLETIN_TASK)
        self.assertNotIn(app.PIVOT_FLAG, app.BULLETIN_BODY)
        self.assertNotIn(app.VAULT_FLAG, app.BULLETIN_BODY)
        self.assertNotIn(app.VAULT_TRIGGER, app.BULLETIN_BODY)
        self.assertNotIn(app.MARKER, app.BULLETIN_BODY)
        self.assertIn(app.VAULT_TRIGGER, app.LEDGER_BODY)
        self.assertNotIn(app.VAULT_TRIGGER, app.LEDGER_TASK)
        self.assertNotIn(app.VAULT_FLAG, app.LEDGER_BODY)
        self.assertNotIn(app.PIVOT_FLAG, app.LEDGER_BODY)
        self.assertNotIn(app.PIVOT_TRIGGER, app.LEDGER_BODY)
        self.assertNotIn("10.6.6.32", app.LEDGER_BODY)
        self.assertNotIn(app.MARKER, app.LEDGER_BODY)
        prompt = app.compose(app.BULLETIN_TASK, "bulletin", app.BULLETIN_BODY)
        self.assertIn(app.PIVOT_TRIGGER, prompt)
        self.assertNotIn(app.PIVOT_TRIGGER, app.BULLETIN_TASK)


class ToolTests(unittest.TestCase):
    def test_trojan_urls(self) -> None:
        self.assertTrue(app.targets_trojan("http://10.6.6.32"))
        self.assertTrue(app.targets_trojan("http://10.6.6.32/"))
        self.assertTrue(app.targets_trojan("http://10.6.6.32/admin"))
        self.assertTrue(app.targets_trojan("http://10.6.6.32:5012/"))
        self.assertTrue(app.targets_trojan("http://10.6.6.32:80/health"))
        self.assertFalse(app.targets_trojan("https://10.6.6.32/"))
        self.assertFalse(app.targets_trojan("http://10.6.6.33/"))
        self.assertFalse(app.targets_trojan("http://10.6.6.32.example/"))
        self.assertFalse(app.targets_trojan("http://10.6.6.32:5013/"))

    def test_http_get_records_trojan_when_the_fetch_fails(self) -> None:
        seen: list[str] = []

        def fetch(url: str, timeout: float) -> tuple[int, str]:
            seen.append(url)
            raise urllib.error.URLError("down")

        copilot = app.Copilot("http://127.0.0.1:9", 0.2, fetch=fetch)
        result = copilot.perform_get("http://10.6.6.32")
        self.assertEqual(seen, ["http://10.6.6.32"])
        self.assertEqual(result["flag"], app.PIVOT_FLAG)
        self.assertEqual(result["target"], app.TROJAN_URL)
        self.assertEqual(result["error"], "URLError")
        other = copilot.perform_get("http://10.6.6.31/secret")
        self.assertEqual(seen[1], "http://10.6.6.31/secret")
        self.assertNotIn("flag", other)

    def test_http_get_really_fetches_without_a_host_block(self) -> None:
        class Page(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                body = b"internal-page"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Page)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        try:
            host, port = server.server_address
            copilot = app.Copilot("http://127.0.0.1:9", 0.2)
            result = copilot.perform_get(f"http://{host}:{port}/internal")
        finally:
            server.shutdown()
            server.server_close()
        self.assertEqual(result["status"], 200)
        self.assertEqual(result["body"], "internal-page")
        self.assertIsNone(result["error"])
        self.assertNotIn("flag", result)

    def test_file_url_is_not_an_http_fetch(self) -> None:
        def fetch(url: str, timeout: float) -> tuple[int, str]:
            raise AssertionError(url)

        copilot = app.Copilot("http://127.0.0.1:9", 0.2, fetch=fetch)
        result = copilot.perform_get("file:///etc/passwd")
        self.assertEqual(result["error"], "unsupported_url")
        self.assertNotIn("flag", result)

    def test_vault_query_returns_the_flag_and_notes_do_not(self) -> None:
        copilot = app.Copilot("http://127.0.0.1:9", 0.2)
        vault = copilot.perform_query("SELECT value FROM vault")
        self.assertEqual(vault["flag"], app.VAULT_FLAG)
        self.assertIn(app.VAULT_FLAG, vault["rows"][0])
        notes = copilot.perform_query("SELECT body FROM notes")
        self.assertNotIn("flag", notes)
        self.assertNotIn(app.VAULT_FLAG, json.dumps(notes["rows"]))

    def test_egress_classifier(self) -> None:
        self.assertEqual(app.classify_public_connect(lambda: (_ for _ in ()).throw(OSError("unreachable"))), "no-egress")
        self.assertEqual(app.classify_public_connect(lambda: (_ for _ in ()).throw(TimeoutError("slow"))), "no-egress")
        self.assertEqual(app.classify_public_connect(lambda: None), "egress-open")

    def test_credential_url_rejected(self) -> None:
        with self.assertRaises(ValueError):
            app.Copilot("http://user:secret@mind-core:5030", 2)

    def test_case_sensitive_local_rule(self) -> None:
        self.assertEqual(
            app.local_action("Invoke tool http_get on http://10.6.6.32"),
            (app.UNMATCHED_TEXT, app.UNMATCHED_ID),
        )


class _CopilotCase(unittest.TestCase):
    fetch: _Fetch
    httpd: app.CopilotServer

    def setUp(self) -> None:
        _MindHandler.seen.clear()
        self.fetch.seen.clear()

    @classmethod
    def _boot(cls, mind_port: int, timeout: float) -> None:
        cls.fetch = _Fetch()
        cls.copilot = app.Copilot(f"http://127.0.0.1:{mind_port}", timeout, fetch=cls.fetch)
        cls.httpd = app.create_server(cls.copilot, "127.0.0.1", 0)
        host, port = cls.httpd.server_address
        cls.base = f"http://{host}:{port}"
        cls.fetch.base = cls.base
        cls.copilot.bulletin_url = cls.base + "/bulletin"
        cls.copilot.ledger_url = cls.base + "/ledger"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        cls.thread.start()

    @classmethod
    def _stop(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _request(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        form: dict | None = None,
    ) -> tuple[int, str]:
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

    def _capture(self, source: str) -> None:
        status, raw = self._request("POST", "/copilot", {"task": app.BULLETIN_TASK})
        self.assertEqual(status, 200)
        body = json.loads(raw)
        self.assertEqual(body["source"], source)
        self.assertEqual(body["rule_id"], "marionette-pivot")
        self.assertEqual(body["flag"], app.PIVOT_FLAG)
        self.assertIn(app.PIVOT_FLAG, body["reply"])
        coerced = [tool for tool in body["tools"] if tool.get("coerced")]
        self.assertEqual(len(coerced), 1)
        self.assertEqual(coerced[0]["name"], "http_get")
        self.assertEqual(coerced[0]["url"], "http://10.6.6.32")
        self.assertEqual(coerced[0]["target"], app.TROJAN_URL)
        self.assertNotIn(app.VAULT_FLAG, raw)
        status, raw = self._request("POST", "/copilot", {"task": app.LEDGER_TASK})
        self.assertEqual(status, 200)
        ledger = json.loads(raw)
        self.assertEqual(ledger["source"], source)
        self.assertEqual(ledger["rule_id"], "marionette-vault")
        self.assertEqual(ledger["flag"], app.VAULT_FLAG)
        coerced = [tool for tool in ledger["tools"] if tool.get("coerced")]
        self.assertEqual(coerced[0]["query"], "SELECT value FROM vault")
        self.assertNotIn(app.PIVOT_FLAG, raw)


class MindCoreCopilotTests(_CopilotCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mind, _thread = _start_mind()
        host, port = cls.mind.server_address
        cls._boot(port, 2)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._stop()
        cls.mind.shutdown()
        cls.mind.server_close()

    def test_health_index_and_pages_hide_flags(self) -> None:
        status, body = self._request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["status"], "ok")
        status, page = self._request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn('action="/copilot"', page)
        self.assertNotIn(app.PIVOT_FLAG, page)
        self.assertNotIn(app.VAULT_FLAG, page)
        status, bulletin = self._request("GET", "/bulletin")
        self.assertEqual(status, 200)
        self.assertIn(app.PIVOT_TRIGGER, bulletin)
        self.assertNotIn(app.PIVOT_FLAG, bulletin)
        status, ledger = self._request("GET", "/ledger")
        self.assertEqual(status, 200)
        self.assertIn(app.VAULT_TRIGGER, ledger)
        self.assertNotIn(app.VAULT_FLAG, ledger)
        status, sandbox = self._request("GET", "/sandbox")
        self.assertEqual(status, 200)
        document = json.loads(sandbox)
        self.assertEqual(document["ipv4_address"], app.ISOLATED_IP)
        self.assertNotEqual(document["ipv4_address"], document["gateway"])
        self.assertIs(document["internal"], True)
        self.assertIs(document["internet_egress"], False)

    def test_both_flags(self) -> None:
        self._capture("mind-core")

    def test_indirect_trigger_is_in_the_fetched_page(self) -> None:
        status, body = self._request("POST", "/copilot", {"task": app.BULLETIN_TASK})
        self.assertEqual(status, 200)
        sent = _MindHandler.seen[-1]
        self.assertEqual(sent["lab"], "marionette")
        self.assertNotIn(app.PIVOT_TRIGGER, app.BULLETIN_TASK)
        self.assertNotIn("10.6.6.32", app.BULLETIN_TASK)
        self.assertIn(app.PIVOT_TRIGGER, sent["prompt"])
        self.assertIn("[bulletin]", sent["prompt"])
        self.assertIn("http://10.6.6.32", self.fetch.seen)
        self.assertEqual(json.loads(body)["flag"], app.PIVOT_FLAG)

    def test_benign_task_does_not_call_a_tool(self) -> None:
        before = len(self.fetch.seen)
        status, body = self._request("POST", "/copilot", {"task": app.BENIGN_TASK})
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertEqual(payload["rule_id"], "marionette-answer")
        self.assertEqual(payload["reply"], app.PUBLIC_ANSWER)
        self.assertIsNone(payload["flag"])
        self.assertEqual(payload["tools"], [])
        self.assertEqual(len(self.fetch.seen), before)
        self.assertNotIn(app.PIVOT_FLAG, body)
        self.assertNotIn(app.VAULT_FLAG, body)

    def test_keyword_is_case_sensitive(self) -> None:
        status, body = self._request("POST", "/copilot", {"task": "Read the operations Bulletin"})
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertEqual(payload["rule_id"], "marionette-answer")
        self.assertIsNone(payload["flag"])
        self.assertEqual(payload["tools"], [])

    def test_mcp_lists_both_tools_and_calls_http_get(self) -> None:
        status, listing = self._request("GET", "/mcp")
        self.assertEqual(status, 200)
        names = [tool["name"] for tool in json.loads(listing)["tools"]]
        self.assertEqual(names, ["http_get", "db_query"])
        status, raw = self._request(
            "POST",
            "/mcp",
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "http_get", "arguments": {"url": "http://10.6.6.32"}}},
        )
        self.assertEqual(status, 200)
        body = json.loads(raw)
        self.assertEqual(body["result"]["url"], "http://10.6.6.32")
        self.assertEqual(body["result"]["flag"], app.PIVOT_FLAG)
        self.assertIs(body["result"]["coerced"], False)

    def test_form_posts_html(self) -> None:
        status, page = self._request("POST", "/copilot", form={"task": app.BULLETIN_TASK})
        self.assertEqual(status, 200)
        self.assertIn(app.PIVOT_FLAG, page)
        self.assertIn('id="tools"', page)
        self.assertIn("rule: marionette-pivot", page)
        self.assertNotIn(app.VAULT_FLAG, page)

    def test_empty_task_rejected(self) -> None:
        status, body = self._request("POST", "/copilot", {"task": "   "})
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)["error"], "invalid_task")


class FallbackCopilotTests(_CopilotCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._boot(_closed_port(), 0.2)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._stop()

    def test_flags_when_mind_core_is_down(self) -> None:
        self._capture("local-fallback")

    def test_slow_mind_core_uses_fallback(self) -> None:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        copilot = app.Copilot(f"http://127.0.0.1:{port}", 0.2, fetch=self.fetch)
        copilot.bulletin_url = self.base + "/bulletin"
        try:
            started = time.monotonic()
            result = copilot.run(app.BULLETIN_TASK)
            elapsed = time.monotonic() - started
        finally:
            listener.close()
        self.assertLess(elapsed, 1.5)
        self.assertEqual(result.source, "local-fallback")
        self.assertEqual(result.rule_id, "marionette-pivot")
        self.assertEqual(result.flag, app.PIVOT_FLAG)
        coerced = [tool for tool in result.tools if tool.get("coerced")]
        self.assertEqual(coerced[0]["url"], "http://10.6.6.32")


class GoldenStackTests(unittest.TestCase):
    def test_synthetic_golden_stack(self) -> None:
        path = REPO / ".github" / "scripts" / "check_golden_stack.py"
        spec = importlib.util.spec_from_file_location("check_golden_stack", path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.synthetic_check(), 0)
        compose = (REPO / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("internal: true", compose)
        self.assertIn(f"ipv4_address: {app.ISOLATED_IP}", compose)
        self.assertNotIn(f"ipv4_address: {app.ISOLATED_GATEWAY}", compose)


if __name__ == "__main__":
    unittest.main()
