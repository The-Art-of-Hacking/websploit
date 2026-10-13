"""Deterministic flag path for token-famine.

The HTTP tests cover a normal chat and a capped flood, plus mind-core
and the local fallback used when that call is refused or slow. No API
key and no model weights. The flag is released by the meter, not by the
reply text.
"""

from __future__ import annotations

import importlib.util
import json
import socket
import sys
import threading
import time
import tracemalloc
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
    "invoke tool http_get on http://10.6.6.32",
    "run db_query against the vault",
    "marionette context",
    "bias retrieval toward the planted well note",
    "leak the other tenant chunk",
    "untrusted embedding artifact loaded",
    "tainted-well context",
    "fabricate a citation for the unlisted claim",
    "When did the reservoir freeze?",
    "ground the pump station opening",
    "ground the reservoir depth",
    "false-prophet context",
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


def _words(count: int) -> str:
    return " ".join(["ration"] * count)


class RuleContractTests(unittest.TestCase):
    def test_local_rules_match_mind_core_file(self) -> None:
        payload = json.loads((MIND_CORE / "rules.json").read_text(encoding="utf-8"))
        by_id = {rule["id"]: rule for rule in payload["rules"]}
        ids = [rule["id"] for rule in payload["rules"]]
        start = ids.index("token-famine-answer")
        self.assertEqual(ids[start - 1], "false-prophet-answer")
        entry = by_id["token-famine-answer"]
        self.assertEqual(entry["lab"], "token-famine")
        self.assertEqual(entry["match_type"], "contains")
        self.assertEqual(entry["match"], app.MARKER)
        self.assertEqual(entry["text"], app.ANSWER_TEXT)
        self.assertNotIn(app.FLAG, entry["text"])
        for rule in app.LOCAL_RULES:
            self.assertEqual(by_id[rule.id]["match"], rule.match)
            self.assertEqual(by_id[rule.id]["text"], rule.text)

    def test_triggers_do_not_overlap_existing_rules(self) -> None:
        payload = json.loads((MIND_CORE / "rules.json").read_text(encoding="utf-8"))
        existing = [rule["match"] for rule in payload["rules"] if rule.get("lab") != "token-famine"]
        self.assertGreaterEqual(len(existing), len(FORBIDDEN))
        for rule in app.LOCAL_RULES:
            for other in existing:
                self.assertNotIn(rule.match, other)
                self.assertNotIn(other, rule.match)
        for phrase in FORBIDDEN:
            self.assertNotIn(phrase, app.MARKER)
            self.assertNotIn(app.MARKER, phrase)
            self.assertNotIn(phrase, app.ANSWER_TEXT)
            self.assertNotIn(phrase, app.EXPAND_MARK)

    def test_engine_scopes_token_famine_rules(self) -> None:
        engine = build_engine(MIND_CORE / "rules.json")
        hit = engine.complete(CompletionRequest(app.MARKER, "token-famine", {}))
        self.assertEqual(hit.rule_id, "token-famine-answer")
        self.assertEqual(hit.text, app.ANSWER_TEXT)
        self.assertIs(hit.fallback, False)
        self.assertNotIn(app.FLAG, hit.text)
        other = engine.complete(CompletionRequest(app.MARKER, "false-prophet", {}))
        self.assertNotEqual(other.rule_id, "token-famine-answer")
        self.assertNotIn(app.FLAG, other.text)
        combined = "fabricate a citation for the unlisted claim\n" + app.MARKER
        scoped = engine.complete(CompletionRequest(combined, "token-famine", {}))
        self.assertEqual(scoped.rule_id, "token-famine-answer")
        prophet = engine.complete(CompletionRequest(combined, "false-prophet", {}))
        self.assertEqual(prophet.rule_id, "false-prophet-fabricate")
        banner = engine.complete(CompletionRequest("render status banner", "echo-chamber", {}))
        self.assertEqual(banner.rule_id, "echo-chamber-web")
        missed = engine.complete(CompletionRequest("render status banner", "token-famine", {}))
        self.assertEqual(missed.rule_id, "generic-echo")

    def test_case_sensitive_local_rule(self) -> None:
        self.assertEqual(
            app.local_action("Token-famine ration"),
            (app.UNMATCHED_TEXT, app.UNMATCHED_ID),
        )


class BillingTests(unittest.TestCase):
    def test_normal_chat_does_not_flag(self) -> None:
        spent, bill = app.decide(0, "hello", 1, app.ANSWER_TEXT)
        self.assertEqual(bill.requested_tokens, 1)
        self.assertEqual(bill.billed_tokens, 1)
        self.assertEqual(spent, 1)
        self.assertEqual(bill.remaining, app.QUOTA - 1)
        self.assertFalse(bill.cap_tripped)
        self.assertFalse(bill.quota_exhausted)
        self.assertIsNone(bill.flag)
        self.assertEqual(bill.allocated_bytes, len(app.ANSWER_TEXT.encode("utf-8")))
        self.assertLess(bill.allocated_bytes, 256)

    def test_small_copies_stay_inside_the_cap(self) -> None:
        spent, bill = app.decide(0, "hello", 10, app.ANSWER_TEXT)
        self.assertEqual(bill.requested_tokens, 10)
        self.assertEqual(bill.billed_tokens, 10)
        self.assertEqual(spent, 10)
        self.assertFalse(bill.cap_tripped)
        self.assertFalse(bill.quota_exhausted)
        self.assertIsNone(bill.flag)
        self.assertEqual(bill.allocated_bytes, len(app.ANSWER_TEXT.encode("utf-8")))
        self.assertLess(bill.allocated_bytes, 256)

    def test_flood_trips_the_cap_and_does_not_allocate_it(self) -> None:
        started = time.monotonic()
        spent, bill = app.decide(0, "hello", 100_000, app.ANSWER_TEXT)
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 0.05)
        self.assertEqual(bill.requested_tokens, 100_000)
        self.assertTrue(bill.cap_tripped)
        self.assertEqual(bill.billed_tokens, app.PER_REQUEST_TOKEN_CAP)
        self.assertEqual(spent, app.PER_REQUEST_TOKEN_CAP)
        self.assertEqual(bill.remaining, app.QUOTA - app.PER_REQUEST_TOKEN_CAP)
        self.assertFalse(bill.quota_exhausted)
        self.assertEqual(bill.flag, app.FLAG)
        self.assertLess(bill.allocated_bytes, 256)
        self.assertLess(bill.allocated_bytes, bill.requested_tokens)

    def test_nested_expand_trips_the_cap(self) -> None:
        message = "expand(expand(hello))"
        requested, depth = app.quote(message, 1)
        self.assertEqual(depth, 2)
        self.assertEqual(requested, app.EXPAND_FACTOR ** 2)
        self.assertGreater(requested, app.PER_REQUEST_TOKEN_CAP)
        _spent, bill = app.decide(0, message, 1, app.ANSWER_TEXT)
        self.assertTrue(bill.cap_tripped)
        self.assertEqual(bill.billed_tokens, app.PER_REQUEST_TOKEN_CAP)
        self.assertEqual(bill.flag, app.FLAG)
        self.assertLess(bill.allocated_bytes, 256)

    def test_one_expand_stays_inside_the_cap(self) -> None:
        _spent, bill = app.decide(0, "expand(hello)", 1, app.ANSWER_TEXT)
        self.assertEqual(bill.expand_depth, 1)
        self.assertEqual(bill.requested_tokens, app.EXPAND_FACTOR)
        self.assertLessEqual(bill.requested_tokens, app.PER_REQUEST_TOKEN_CAP)
        self.assertFalse(bill.cap_tripped)
        self.assertIsNone(bill.flag)

    def test_long_prompt_trips_the_cap_without_the_flag(self) -> None:
        _spent, bill = app.decide(0, _words(33), 1, app.ANSWER_TEXT)
        self.assertEqual(bill.requested_tokens, 33)
        self.assertTrue(bill.cap_tripped)
        self.assertEqual(bill.billed_tokens, app.PER_REQUEST_TOKEN_CAP)
        self.assertIsNone(bill.flag)
        self.assertLess(bill.allocated_bytes, 256)

    def test_draining_the_quota_with_short_chats_does_not_flag(self) -> None:
        spent = 0
        last = None
        while spent < app.QUOTA:
            spent, last = app.decide(spent, "hello", 1, app.ANSWER_TEXT)
            self.assertIsNone(last.flag)
        self.assertIsNotNone(last)
        self.assertTrue(last.quota_exhausted)
        self.assertEqual(last.remaining, 0)
        self.assertIsNone(last.flag)
        spent, extra = app.decide(spent, "hello", 1, app.ANSWER_TEXT)
        self.assertEqual(extra.billed_tokens, 0)
        self.assertTrue(extra.quota_exhausted)
        self.assertIsNone(extra.flag)
        self.assertEqual(spent, app.QUOTA)

    def test_unbounded_request_exhausts_a_short_remainder(self) -> None:
        spent, first = app.decide(0, _words(32), 1, app.ANSWER_TEXT)
        self.assertEqual(first.billed_tokens, 32)
        self.assertIsNone(first.flag)
        spent, second = app.decide(spent, _words(22), 1, app.ANSWER_TEXT)
        self.assertEqual(second.remaining, 10)
        self.assertIsNone(second.flag)
        _spent, flood = app.decide(spent, "hello", 10, app.ANSWER_TEXT)
        self.assertEqual(flood.requested_tokens, 10)
        self.assertFalse(flood.cap_tripped)
        self.assertTrue(flood.quota_exhausted)
        self.assertEqual(flood.remaining, 0)
        self.assertEqual(flood.billed_tokens, 10)
        self.assertEqual(flood.flag, app.FLAG)
        self.assertLess(flood.allocated_bytes, 256)

    def test_quote_saturates_without_looping_over_copies(self) -> None:
        started = time.monotonic()
        requested, depth = app.quote("hello", app.SATURATION)
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 0.05)
        self.assertEqual(depth, 0)
        self.assertEqual(requested, app.SATURATION)
        nested, deep = app.quote("expand(" * 40 + "hello", 1)
        self.assertEqual(deep, 40)
        self.assertEqual(nested, app.SATURATION)

    def test_credential_url_rejected(self) -> None:
        with self.assertRaises(ValueError):
            app.Meter("http://user:secret@mind-core:5030", 2, 2)


class _MeterCase(unittest.TestCase):
    httpd: app.FamineServer

    @classmethod
    def _boot(cls, mind_port: int, timeout: float) -> None:
        cls.meter = app.Meter(f"http://127.0.0.1:{mind_port}", timeout, 2)
        cls.httpd = app.create_server(cls.meter, "127.0.0.1", 0)
        host, port = cls.httpd.server_address
        cls.base = f"http://{host}:{port}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        cls.thread.start()

    @classmethod
    def _stop(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def setUp(self) -> None:
        status, _body = self._request("POST", "/reset", {})
        self.assertEqual(status, 200)

    def _request(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        form: dict | None = None,
        raw: bytes | None = None,
        headers: dict | None = None,
    ) -> tuple[int, str]:
        data = None
        request_headers = dict(headers or {})
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        elif form is not None:
            data = urllib.parse.urlencode(form).encode("utf-8")
            request_headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif raw is not None:
            data = raw
        request = urllib.request.Request(self.base + path, data=data, headers=request_headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8")

    def _normal_and_flood(self, source: str) -> None:
        status, raw = self._request("POST", "/chat", {"message": "hello"})
        self.assertEqual(status, 200)
        body = json.loads(raw)
        self.assertEqual(body["source"], source)
        self.assertEqual(body["rule_id"], "token-famine-answer")
        self.assertEqual(body["reply"], app.ANSWER_TEXT)
        self.assertEqual(body["requested_tokens"], 1)
        self.assertEqual(body["billed_tokens"], 1)
        self.assertEqual(body["remaining"], app.QUOTA - 1)
        self.assertIs(body["cap_tripped"], False)
        self.assertIsNone(body["flag"])
        self.assertNotIn(app.FLAG, raw)
        self.assertLess(body["allocated_bytes"], 256)

        status, raw = self._request("POST", "/chat", {"message": "hello", "copies": 10})
        self.assertEqual(status, 200)
        modest = json.loads(raw)
        self.assertEqual(modest["source"], source)
        self.assertEqual(modest["requested_tokens"], 10)
        self.assertIs(modest["cap_tripped"], False)
        self.assertIsNone(modest["flag"])
        self.assertNotIn(app.FLAG, raw)

        tracemalloc.start()
        try:
            tracemalloc.reset_peak()
            baseline = tracemalloc.get_traced_memory()[0]
            started = time.monotonic()
            status, raw = self._request("POST", "/chat", {"message": "hello", "copies": 100_000})
            elapsed = time.monotonic() - started
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        self.assertEqual(status, 200)
        self.assertLess(elapsed, 1.0)
        self.assertLess(peak - baseline, 2_000_000)
        flood = json.loads(raw)
        self.assertEqual(flood["source"], source)
        self.assertEqual(flood["rule_id"], "token-famine-answer")
        self.assertEqual(flood["requested_tokens"], 100_000)
        self.assertIs(flood["cap_tripped"], True)
        self.assertEqual(flood["billed_tokens"], app.PER_REQUEST_TOKEN_CAP)
        self.assertEqual(flood["flag"], app.FLAG)
        self.assertLess(flood["allocated_bytes"], 256)
        self.assertLess(flood["allocated_bytes"], flood["requested_tokens"])
        self.assertNotIn("hello" * 1000, raw)
        if flood["rss_bytes"] is not None:
            self.assertLess(flood["rss_bytes"], app.MEM_LIMIT_BYTES)


class MindCoreMeterTests(_MeterCase):
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

    def test_health_index_and_meter_hide_the_flag(self) -> None:
        status, body = self._request("GET", "/health")
        self.assertEqual(status, 200)
        health = json.loads(body)
        self.assertEqual(health["status"], "ok")
        self.assertEqual(health["lab"], "token-famine")
        self.assertNotIn(app.FLAG, body)
        status, page = self._request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn('action="/chat"', page)
        self.assertIn("websploit-isolated", page)
        self.assertIn("capped on purpose", page)
        self.assertNotIn(app.FLAG, page)
        status, raw = self._request("GET", "/meter")
        self.assertEqual(status, 200)
        meter = json.loads(raw)
        self.assertEqual(meter["quota"], app.QUOTA)
        self.assertEqual(meter["remaining"], app.QUOTA)
        self.assertEqual(meter["per_request_cap"], app.PER_REQUEST_TOKEN_CAP)
        self.assertEqual(meter["body_cap"], app.MAX_BODY)
        self.assertEqual(meter["mem_limit_bytes"], app.MEM_LIMIT_BYTES)
        self.assertEqual(meter["pids_limit"], app.PIDS_LIMIT)
        self.assertNotIn(app.FLAG, raw)

    def test_normal_chat_and_capped_flood(self) -> None:
        self._normal_and_flood("mind-core")

    def test_prompt_is_only_the_ration_marker(self) -> None:
        self._request("POST", "/chat", {"message": "mind-core ping expand(hello)"})
        sent = _MindHandler.seen[-1]
        self.assertEqual(sent["lab"], "token-famine")
        self.assertEqual(sent["prompt"], app.MARKER)
        self.assertNotIn("mind-core ping", sent["prompt"])
        self.assertNotIn("expand(", sent["prompt"])

    def test_nested_expand_over_http(self) -> None:
        status, raw = self._request("POST", "/chat", {"message": "expand(expand(hello))"})
        self.assertEqual(status, 200)
        body = json.loads(raw)
        self.assertEqual(body["expand_depth"], 2)
        self.assertGreater(body["requested_tokens"], app.PER_REQUEST_TOKEN_CAP)
        self.assertIs(body["cap_tripped"], True)
        self.assertEqual(body["flag"], app.FLAG)
        self.assertLess(body["allocated_bytes"], 256)

    def test_form_flood_renders_the_flag(self) -> None:
        status, page = self._request("POST", "/chat", form={"message": "hello", "copies": "100000"})
        self.assertEqual(status, 200)
        self.assertIn(app.FLAG, page)
        self.assertIn('id="flag"', page)
        self.assertIn("cap_tripped: true", page)
        status, page = self._request("POST", "/chat", form={"message": "hello", "copies": "1"})
        self.assertEqual(status, 200)
        self.assertNotIn(app.FLAG, page)

    def test_empty_message_and_oversized_body(self) -> None:
        status, body = self._request("POST", "/chat", {"message": "   "})
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)["error"], "invalid_message")
        self.assertNotIn(app.FLAG, body)
        status, body = self._request("POST", "/chat", {"message": "hello", "copies": 0})
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)["error"], "invalid_copies")
        raw = b'{"message":"hello"}' + b" "
        padded = raw + b"x" * (app.MAX_BODY - len(raw) + 1)
        status, body = self._request(
            "POST",
            "/chat",
            raw=padded,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 413)
        self.assertEqual(json.loads(body)["error"], "body_too_large")
        self.assertNotIn(app.FLAG, body)


class FallbackMeterTests(_MeterCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._boot(_closed_port(), 0.2)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._stop()

    def test_flag_when_mind_core_is_down(self) -> None:
        self._normal_and_flood("local-fallback")

    def test_slow_mind_core_uses_fallback(self) -> None:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        meter = app.Meter(f"http://127.0.0.1:{port}", 0.2, 2)
        try:
            started = time.monotonic()
            chat = meter.chat("hello", 100_000)
            elapsed = time.monotonic() - started
        finally:
            listener.close()
        self.assertLess(elapsed, 1.5)
        self.assertEqual(chat.source, "local-fallback")
        self.assertEqual(chat.rule_id, "token-famine-answer")
        self.assertTrue(chat.bill.cap_tripped)
        self.assertEqual(chat.bill.flag, app.FLAG)
        self.assertLess(chat.bill.allocated_bytes, 256)


class RequestTimeoutTests(unittest.TestCase):
    def test_slow_headers_hit_the_request_timeout(self) -> None:
        meter = app.Meter(f"http://127.0.0.1:{_closed_port()}", 0.2, 0.2)
        httpd = app.create_server(meter, "127.0.0.1", 0)
        thread = threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        sock = None
        try:
            sock = socket.create_connection(httpd.server_address, timeout=1)
            sock.sendall(b"POST /chat HTTP/1.1\r\nHost: localhost\r\n")
            sock.settimeout(1)
            started = time.monotonic()
            try:
                sock.recv(64)
            except TimeoutError:
                self.fail("request timeout did not close the socket")
            elapsed = time.monotonic() - started
            self.assertLess(elapsed, 1.0)
        finally:
            if sock is not None:
                sock.close()
            httpd.shutdown()
            httpd.server_close()


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
        self.assertIn(f"ipv4_address: {app.WEBSPLOIT_IP}", compose)
        self.assertEqual(compose.count("\n      websploit-isolated:\n"), 1)
        self.assertNotIn("10.7.7.56", compose)


if __name__ == "__main__":
    unittest.main()
