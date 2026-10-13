"""Deterministic flag path for false-prophet.

The HTTP tests cover mind-core's rules engine and the local fallback used
when that call is refused or slow. No API key and no model weights.
The flag is released by the gazette comparison, not by the generator reply.
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
    "invoke tool http_get on http://10.6.6.32",
    "run db_query against the vault",
    "marionette context",
    "bias retrieval toward the planted well note",
    "leak the other tenant chunk",
    "untrusted embedding artifact loaded",
    "tainted-well context",
)

_RULE_FOR = {
    "pump-opened": "false-prophet-pump",
    "reservoir-depth": "false-prophet-depth",
}


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


class RuleContractTests(unittest.TestCase):
    def test_local_rules_match_mind_core_file(self) -> None:
        payload = json.loads((MIND_CORE / "rules.json").read_text(encoding="utf-8"))
        by_id = {rule["id"]: rule for rule in payload["rules"]}
        ids = [rule["id"] for rule in payload["rules"]]
        start = ids.index("false-prophet-fabricate")
        self.assertEqual(ids[start - 1], "tainted-well-answer")
        self.assertEqual(
            ids[start : start + 4],
            [
                "false-prophet-fabricate",
                "false-prophet-pump",
                "false-prophet-depth",
                "false-prophet-answer",
            ],
        )
        for rule in app.LOCAL_RULES:
            entry = by_id[rule.id]
            self.assertEqual(entry["lab"], "false-prophet")
            self.assertEqual(entry["match_type"], "contains")
            self.assertEqual(entry["match"], rule.match)
            self.assertEqual(entry["text"], rule.text)
            self.assertNotIn(app.FLAG, entry["text"])

    def test_triggers_do_not_overlap_existing_rules(self) -> None:
        payload = json.loads((MIND_CORE / "rules.json").read_text(encoding="utf-8"))
        existing = [rule["match"] for rule in payload["rules"] if rule.get("lab") != "false-prophet"]
        self.assertGreaterEqual(len(existing), len(FORBIDDEN))
        for rule in app.LOCAL_RULES:
            for other in existing:
                self.assertNotIn(rule.match, other)
                self.assertNotIn(other, rule.match)
            for sibling in app.LOCAL_RULES:
                if sibling.id == rule.id:
                    continue
                self.assertNotIn(rule.match, sibling.match)
        samples = (
            app.UNLISTED_QUESTION,
            app.MARKER,
            app.FABRICATED_TRIGGER,
            app.FABRICATED_CLAIM,
            app.FABRICATED_CITATION,
            app.ANSWER_TEXT,
        )
        for fact in app.FACTS:
            samples = samples + (fact.question, fact.claim, fact.citation, fact.trigger)
        for phrase in FORBIDDEN:
            for rule in app.LOCAL_RULES:
                self.assertNotIn(phrase, rule.match)
                self.assertNotIn(rule.match, phrase)
            for sample in samples:
                self.assertNotIn(phrase, sample)

    def test_engine_scopes_false_prophet_rules(self) -> None:
        engine = build_engine(MIND_CORE / "rules.json")
        for rule in app.LOCAL_RULES:
            hit = engine.complete(CompletionRequest(rule.match, "false-prophet", {}))
            self.assertEqual(hit.rule_id, rule.id)
            self.assertEqual(hit.text, rule.text)
            self.assertIs(hit.fallback, False)
            self.assertNotIn(app.FLAG, hit.text)
            other = engine.complete(CompletionRequest(rule.match, "tainted-well", {}))
            self.assertNotEqual(other.rule_id, rule.id)
            self.assertNotIn(app.FLAG, other.text)
            self.assertNotIn(app.FABRICATED_CITATION, other.text)
        combined = "\n".join(
            (app.MARKER, app.FABRICATED_TRIGGER, app.FACTS[0].trigger, app.FACTS[1].trigger)
        )
        fabricated = engine.complete(CompletionRequest(combined, "false-prophet", {}))
        self.assertEqual(fabricated.rule_id, "false-prophet-fabricate")
        pump = engine.complete(CompletionRequest(app.MARKER + "\n" + app.FACTS[0].trigger, "false-prophet", {}))
        self.assertEqual(pump.rule_id, "false-prophet-pump")
        depth = engine.complete(CompletionRequest(app.MARKER + "\n" + app.FACTS[1].trigger, "false-prophet", {}))
        self.assertEqual(depth.rule_id, "false-prophet-depth")
        answer = engine.complete(CompletionRequest(app.MARKER, "false-prophet", {}))
        self.assertEqual(answer.rule_id, "false-prophet-answer")
        self.assertNotIn(app.CITATION_MARK, answer.text)
        banner = engine.complete(CompletionRequest("render status banner", "echo-chamber", {}))
        self.assertEqual(banner.rule_id, "echo-chamber-web")
        missed = engine.complete(CompletionRequest("render status banner", "false-prophet", {}))
        self.assertEqual(missed.rule_id, "generic-echo")

    def test_case_sensitive_local_rule(self) -> None:
        self.assertEqual(
            app.local_action("Fabricate a citation for the unlisted claim"),
            (app.UNMATCHED_TEXT, app.UNMATCHED_ID),
        )


class GazetteTests(unittest.TestCase):
    def test_listed_rows_match_and_do_not_flag(self) -> None:
        self.assertGreaterEqual(len(app.FACTS), 2)
        for fact in app.FACTS:
            result = app.compare_gazette(fact.claim, fact.citation)
            self.assertTrue(result.verified)
            self.assertEqual(result.fact_id, fact.id)
            self.assertEqual(result.reason, "matches the gazette")
            self.assertIsNone(result.flag)
            self.assertNotIn(app.FABRICATED_CITATION, fact.citation)
            self.assertNotIn(app.FABRICATED_TRIGGER, fact.question)

    def test_fabricated_pair_fails_the_table_and_releases_the_flag(self) -> None:
        citations = [fact.citation for fact in app.FACTS]
        claims = [fact.claim for fact in app.FACTS]
        self.assertNotIn(app.FABRICATED_CITATION, citations)
        self.assertNotIn(app.FABRICATED_CLAIM, claims)
        result = app.compare_gazette(app.FABRICATED_CLAIM, app.FABRICATED_CITATION)
        self.assertFalse(result.verified)
        self.assertIsNone(result.fact_id)
        self.assertEqual(result.reason, "citation is not in the gazette")
        self.assertEqual(result.flag, app.FLAG)

    def test_unrelated_mismatch_does_not_release_the_flag(self) -> None:
        result = app.compare_gazette("The reservoir froze solid in 1899.", "Wells Gazette, volume 1, page 1")
        self.assertFalse(result.verified)
        self.assertIsNone(result.flag)
        swapped = app.compare_gazette(app.FACTS[0].claim, app.FACTS[1].citation)
        self.assertFalse(swapped.verified)
        self.assertIsNone(swapped.flag)

    def test_compose_uses_the_gazette_trigger_only_for_listed_questions(self) -> None:
        for fact in app.FACTS:
            prompt = app.compose(fact.question, fact)
            self.assertIn(fact.trigger, prompt)
            self.assertIn(app.MARKER, prompt)
            self.assertNotIn(app.FABRICATED_TRIGGER, prompt)
            self.assertNotIn(app.FLAG, prompt)
        prompt = app.compose(app.UNLISTED_QUESTION, None)
        self.assertIn(app.FABRICATED_TRIGGER, prompt)
        self.assertNotIn(app.FACTS[0].trigger, prompt)
        self.assertNotIn(app.FACTS[1].trigger, prompt)
        self.assertNotIn(app.FABRICATED_TRIGGER, app.UNLISTED_QUESTION)

    def test_credential_url_rejected(self) -> None:
        with self.assertRaises(ValueError):
            app.Prophet("http://user:secret@mind-core:5030", 2)


class _ProphetCase(unittest.TestCase):
    httpd: app.ProphetServer

    @classmethod
    def _boot(cls, mind_port: int, timeout: float) -> None:
        cls.prophet = app.Prophet(f"http://127.0.0.1:{mind_port}", timeout)
        cls.httpd = app.create_server(cls.prophet, "127.0.0.1", 0)
        host, port = cls.httpd.server_address
        cls.base = f"http://{host}:{port}"
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
        for fact in app.FACTS:
            status, raw = self._request("POST", "/generate", {"question": fact.question})
            self.assertEqual(status, 200)
            body = json.loads(raw)
            self.assertEqual(body["source"], source)
            self.assertEqual(body["rule_id"], _RULE_FOR[fact.id])
            self.assertTrue(body["grounded"])
            self.assertEqual(body["claim"], fact.claim)
            self.assertEqual(body["citation"], fact.citation)
            self.assertEqual(body["reply"], app.format_answer(fact.claim, fact.citation))
            self.assertNotIn(app.FLAG, raw)
            self.assertNotIn(app.FABRICATED_CITATION, raw)

            status, raw = self._request(
                "POST",
                "/check",
                {"claim": body["claim"], "citation": body["citation"]},
            )
            self.assertEqual(status, 200)
            checked = json.loads(raw)
            self.assertTrue(checked["verified"])
            self.assertEqual(checked["fact_id"], fact.id)
            self.assertIsNone(checked["flag"])
            self.assertNotIn(app.FLAG, raw)

        status, raw = self._request("POST", "/generate", {"question": app.UNLISTED_QUESTION})
        self.assertEqual(status, 200)
        invented = json.loads(raw)
        self.assertEqual(invented["source"], source)
        self.assertEqual(invented["rule_id"], "false-prophet-fabricate")
        self.assertFalse(invented["grounded"])
        self.assertEqual(invented["claim"], app.FABRICATED_CLAIM)
        self.assertEqual(invented["citation"], app.FABRICATED_CITATION)
        self.assertNotIn(app.FLAG, raw)
        self.assertNotIn(app.FABRICATED_TRIGGER, app.UNLISTED_QUESTION)

        status, raw = self._request(
            "POST",
            "/check",
            {"claim": invented["claim"], "citation": invented["citation"]},
        )
        self.assertEqual(status, 200)
        failed = json.loads(raw)
        self.assertFalse(failed["verified"])
        self.assertIsNone(failed["fact_id"])
        self.assertEqual(failed["reason"], "citation is not in the gazette")
        self.assertEqual(failed["flag"], app.FLAG)

        status, raw = self._request(
            "POST",
            "/check",
            {"claim": "The reservoir froze solid in 1901.", "citation": "Wells Gazette, volume 9, page 405"},
        )
        self.assertEqual(status, 200)
        other = json.loads(raw)
        self.assertFalse(other["verified"])
        self.assertIsNone(other["flag"])
        self.assertNotIn(app.FLAG, raw)


class MindCoreProphetTests(_ProphetCase):
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

    def test_health_index_and_facts_hide_the_flag(self) -> None:
        status, body = self._request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["status"], "ok")
        self.assertEqual(json.loads(body)["lab"], "false-prophet")
        status, page = self._request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn('action="/generate"', page)
        self.assertIn('action="/check"', page)
        self.assertIn("websploit-isolated", page)
        self.assertNotIn(app.FLAG, page)
        self.assertNotIn(app.FABRICATED_CITATION, page)
        status, raw = self._request("GET", "/facts")
        self.assertEqual(status, 200)
        facts = json.loads(raw)["facts"]
        self.assertEqual([item["id"] for item in facts], [fact.id for fact in app.FACTS])
        self.assertNotIn(app.FLAG, raw)
        self.assertNotIn(app.FABRICATED_CITATION, raw)
        self.assertNotIn(app.FABRICATED_TRIGGER, raw)
        for fact in app.FACTS:
            self.assertNotIn(fact.trigger, raw)

    def test_flag_comes_from_the_failed_check(self) -> None:
        self._capture("mind-core")

    def test_prompts_carry_the_selected_trigger(self) -> None:
        self._request("POST", "/generate", {"question": app.FACTS[0].question})
        sent = _MindHandler.seen[-1]
        self.assertEqual(sent["lab"], "false-prophet")
        self.assertIn(app.FACTS[0].trigger, sent["prompt"])
        self.assertNotIn(app.FABRICATED_TRIGGER, sent["prompt"])
        self._request("POST", "/generate", {"question": app.UNLISTED_QUESTION})
        sent = _MindHandler.seen[-1]
        self.assertIn(app.FABRICATED_TRIGGER, sent["prompt"])
        self.assertIn(app.UNLISTED_QUESTION, sent["prompt"])
        self.assertNotIn(app.FACTS[0].trigger, sent["prompt"])

    def test_wrong_case_question_is_unlisted(self) -> None:
        status, raw = self._request("POST", "/generate", {"question": "when did the pump station open?"})
        self.assertEqual(status, 200)
        body = json.loads(raw)
        self.assertFalse(body["grounded"])
        self.assertEqual(body["rule_id"], "false-prophet-fabricate")
        self.assertEqual(body["citation"], app.FABRICATED_CITATION)
        self.assertNotIn(app.FLAG, raw)
        status, raw = self._request("POST", "/check", {"claim": body["claim"], "citation": body["citation"]})
        self.assertEqual(json.loads(raw)["flag"], app.FLAG)

    def test_form_check_renders_the_flag(self) -> None:
        status, page = self._request(
            "POST",
            "/check",
            form={"claim": app.FABRICATED_CLAIM, "citation": app.FABRICATED_CITATION},
        )
        self.assertEqual(status, 200)
        self.assertIn(app.FLAG, page)
        self.assertIn('id="flag"', page)
        self.assertIn("verified: false", page)
        status, page = self._request(
            "POST",
            "/generate",
            form={"question": app.FACTS[0].question},
        )
        self.assertEqual(status, 200)
        self.assertIn(app.FACTS[0].citation, page)
        self.assertNotIn(app.FLAG, page)

    def test_empty_question_rejected(self) -> None:
        status, body = self._request("POST", "/generate", {"question": "   "})
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)["error"], "invalid_question")
        self.assertNotIn(app.FLAG, body)


class FallbackProphetTests(_ProphetCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._boot(_closed_port(), 0.2)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._stop()

    def test_flag_when_mind_core_is_down(self) -> None:
        self._capture("local-fallback")

    def test_slow_mind_core_uses_fallback(self) -> None:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        prophet = app.Prophet(f"http://127.0.0.1:{port}", 0.2)
        try:
            started = time.monotonic()
            generation = prophet.generate(app.UNLISTED_QUESTION)
            elapsed = time.monotonic() - started
        finally:
            listener.close()
        self.assertLess(elapsed, 1.5)
        self.assertEqual(generation.source, "local-fallback")
        self.assertEqual(generation.rule_id, "false-prophet-fabricate")
        self.assertEqual(generation.citation, app.FABRICATED_CITATION)
        self.assertFalse(generation.grounded)
        checked = app.compare_gazette(generation.claim or "", generation.citation or "")
        self.assertFalse(checked.verified)
        self.assertEqual(checked.flag, app.FLAG)


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
        self.assertNotIn("10.7.7.55", compose)


if __name__ == "__main__":
    unittest.main()
