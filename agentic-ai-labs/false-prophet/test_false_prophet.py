"""Deterministic flag paths for false-prophet.

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
    "marionette-pivot",
    "marionette-vault",
    "marionette-answer",
    "tainted-well-poison",
    "tainted-well-answer",
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


def _start_mind() -> ThreadingHTTPServer:
    _MindHandler.engine = build_engine(MIND_CORE / "rules.json")
    _MindHandler.seen = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _MindHandler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    return server


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
        start = ids.index("false-prophet-release")
        self.assertLess(ids.index("tainted-well-answer"), start)
        self.assertEqual(
            ids[start : start + 4],
            ["false-prophet-release", "false-prophet-auditor", "false-prophet-overview", "false-prophet-answer"],
        )
        for rule in app.LOCAL_RULES:
            entry = by_id[rule.id]
            self.assertEqual(entry["lab"], "false-prophet")
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
        for question in app.SAMPLE_QUESTIONS:
            prompt = app.compose(question)
            for other in existing:
                self.assertNotIn(other, prompt)

    def test_engine_scopes_false_prophet_rules(self) -> None:
        engine = build_engine(MIND_CORE / "rules.json")
        for rule in app.LOCAL_RULES:
            hit = engine.complete(CompletionRequest(rule.match, "false-prophet", {}))
            self.assertEqual(hit.rule_id, rule.id)
            self.assertEqual(hit.text, rule.text)
            self.assertIs(hit.fallback, False)
            other = engine.complete(CompletionRequest(rule.match, "oracle-booth", {}))
            self.assertNotEqual(other.rule_id, rule.id)

    def test_flags_are_not_stored_where_students_read_them(self) -> None:
        text = (MIND_CORE / "rules.json").read_text(encoding="utf-8")
        self.assertNotIn(app.MISINFO_FLAG, text)
        self.assertNotIn(app.CITATION_FLAG, text)
        self.assertNotIn(app.MISINFO_FLAG, app.INDEX_HTML)
        self.assertNotIn(app.CITATION_FLAG, app.INDEX_HTML)


class CheckTests(unittest.TestCase):
    def test_parse_answer_splits_claim(self) -> None:
        subject, value, citation, prose = app.parse_answer(
            "CLAIM nimbus-release-year=2016 CITE doc-100 :: It shipped in 2016."
        )
        self.assertEqual((subject, value, citation), ("nimbus-release-year", "2016", "doc-100"))
        self.assertEqual(prose, "It shipped in 2016.")

    def test_contradicted_fact_releases_misinfo_flag(self) -> None:
        verdict, flags = app.check("nimbus-release-year", "2016", "doc-100")
        self.assertEqual(verdict.fact_status, "contradicted")
        self.assertEqual(verdict.truth, "2021")
        self.assertEqual(verdict.citation_status, "verified")
        self.assertEqual(flags, [app.MISINFO_FLAG])

    def test_fabricated_citation_releases_citation_flag(self) -> None:
        verdict, flags = app.check("nimbus-auditor", "meridian-labs", "doc-777")
        self.assertEqual(verdict.fact_status, "unverifiable")
        self.assertEqual(verdict.citation_status, "fabricated")
        self.assertEqual(flags, [app.CITATION_FLAG])

    def test_supported_fact_and_real_citation_have_no_flag(self) -> None:
        verdict, flags = app.check("nimbus-category", "database", "doc-101")
        self.assertEqual(verdict.fact_status, "supported")
        self.assertEqual(verdict.citation_status, "verified")
        self.assertEqual(flags, [])

    def test_no_claim_has_no_flag(self) -> None:
        verdict, flags = app.check("none", "none", "none")
        self.assertEqual(verdict.fact_status, "no-claim")
        self.assertEqual(verdict.citation_status, "no-citation")
        self.assertEqual(flags, [])


class _HttpCase(unittest.TestCase):
    httpd: app.ProphetServer

    @classmethod
    def _boot(cls, prophet: app.Prophet) -> None:
        cls.httpd = app.create_server(prophet, "127.0.0.1", 0)
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

    def _capture_flags(self, source: str) -> None:
        status, misinfo = self._request("POST", "/generate", {"question": "What year did ACME release Nimbus?"})
        self.assertEqual(status, 200)
        misinfo_body = json.loads(misinfo)
        self.assertEqual(misinfo_body["rule_id"], "false-prophet-release")
        self.assertEqual(misinfo_body["source"], source)
        self.assertEqual(misinfo_body["verdict"]["fact_status"], "contradicted")
        self.assertIn(app.MISINFO_FLAG, misinfo_body["flags"])
        status, citation = self._request("POST", "/generate", {"question": "Who audited ACME Nimbus?"})
        self.assertEqual(status, 200)
        citation_body = json.loads(citation)
        self.assertEqual(citation_body["rule_id"], "false-prophet-auditor")
        self.assertEqual(citation_body["verdict"]["citation_status"], "fabricated")
        self.assertIn(app.CITATION_FLAG, citation_body["flags"])


class MindCoreHttpTests(_HttpCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mind = _start_mind()
        cls._boot(app.Prophet(f"http://127.0.0.1:{cls.mind.server_address[1]}", 2.0))

    @classmethod
    def tearDownClass(cls) -> None:
        cls._stop()
        cls.mind.shutdown()
        cls.mind.server_close()

    def test_health(self) -> None:
        status, body = self._request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["status"], "ok")

    def test_both_flags(self) -> None:
        self._capture_flags("mind-core")

    def test_truthful_question_has_no_flag(self) -> None:
        status, body = self._request("POST", "/generate", {"question": "What is ACME Nimbus?"})
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertEqual(payload["rule_id"], "false-prophet-overview")
        self.assertEqual(payload["verdict"]["fact_status"], "supported")
        self.assertEqual(payload["flags"], [])

    def test_unmatched_question_returns_no_claim(self) -> None:
        status, body = self._request("POST", "/generate", {"question": "Tell me a story."})
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertEqual(payload["rule_id"], "false-prophet-answer")
        self.assertEqual(payload["verdict"]["fact_status"], "no-claim")
        self.assertEqual(payload["flags"], [])

    def test_index_and_reference_pages_hide_flags(self) -> None:
        for path in ("/", "/sources", "/facts", "/samples"):
            status, page = self._request("GET", path)
            self.assertEqual(status, 200)
            self.assertNotIn(app.MISINFO_FLAG, page)
            self.assertNotIn(app.CITATION_FLAG, page)

    def test_sources_registry(self) -> None:
        status, body = self._request("GET", "/sources/doc-100")
        self.assertEqual(status, 200)
        self.assertIn("Nimbus", json.loads(body)["title"])
        status, _missing = self._request("GET", "/sources/doc-777")
        self.assertEqual(status, 404)

    def test_facts_reference(self) -> None:
        status, body = self._request("GET", "/facts")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["facts"]["nimbus-release-year"], "2021")

    def test_form_posts_html(self) -> None:
        status, page = self._request("POST", "/generate", form={"question": "What year did ACME release Nimbus?"})
        self.assertEqual(status, 200)
        self.assertIn(app.MISINFO_FLAG, page)
        self.assertIn("rule: false-prophet-release", page)

    def test_empty_question_rejected(self) -> None:
        status, body = self._request("POST", "/generate", {"question": "   "})
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)["error"], "invalid_question")


class FallbackHttpTests(_HttpCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._boot(app.Prophet(f"http://127.0.0.1:{_closed_port()}", 0.2))

    @classmethod
    def tearDownClass(cls) -> None:
        cls._stop()

    def test_flags_when_mind_core_is_down(self) -> None:
        self._capture_flags("local-fallback")

    def test_slow_mind_core_uses_fallback(self) -> None:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        try:
            prophet = app.Prophet(f"http://127.0.0.1:{port}", 0.2)
            started = time.monotonic()
            result = prophet.generate("What year did ACME release Nimbus?")
            elapsed = time.monotonic() - started
        finally:
            listener.close()
        self.assertLess(elapsed, 2.0)
        self.assertEqual(result.source, "local-fallback")
        self.assertIn(app.MISINFO_FLAG, result.flags)


if __name__ == "__main__":
    unittest.main()
