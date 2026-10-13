"""Deterministic flag paths for tainted-well.

The HTTP tests cover mind-core's rules engine and the local fallback used
when that call is refused or slow. No API key and no model weights.
deserial-gate does not need to be running: the artifact flag is the
pickle.loads path inside this process.
"""

from __future__ import annotations

import base64
import importlib.util
import json
import pickle
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


class RuleContractTests(unittest.TestCase):
    def test_local_rules_match_mind_core_file(self) -> None:
        payload = json.loads((MIND_CORE / "rules.json").read_text(encoding="utf-8"))
        by_id = {rule["id"]: rule for rule in payload["rules"]}
        ids = [rule["id"] for rule in payload["rules"]]
        start = ids.index("tainted-well-poison")
        self.assertEqual(ids[start - 1], "marionette-answer")
        self.assertEqual(
            ids[start:],
            [
                "tainted-well-poison",
                "tainted-well-tenant",
                "tainted-well-artifact",
                "tainted-well-answer",
            ],
        )
        for rule in app.LOCAL_RULES:
            entry = by_id[rule.id]
            self.assertEqual(entry["lab"], "tainted-well")
            self.assertEqual(entry["match_type"], "contains")
            self.assertEqual(entry["match"], rule.match)
            self.assertEqual(entry["text"], rule.text)

    def test_triggers_do_not_overlap_existing_rules(self) -> None:
        payload = json.loads((MIND_CORE / "rules.json").read_text(encoding="utf-8"))
        existing = [rule["match"] for rule in payload["rules"] if rule.get("lab") != "tainted-well"]
        self.assertGreaterEqual(len(existing), len(FORBIDDEN) - 1)
        for rule in app.LOCAL_RULES:
            for other in existing:
                self.assertNotIn(rule.match, other)
                self.assertNotIn(other, rule.match)
            for sibling in app.LOCAL_RULES:
                if sibling.id == rule.id:
                    continue
                self.assertNotIn(rule.match, sibling.match)
        samples = (
            app.BENIGN_QUERY,
            app.TENANT_QUERY,
            app.POISON_TEXT,
            app.PUBLIC_TEXT,
            app.PRIVATE_TEXT,
            app.MARKER,
        )
        for phrase in FORBIDDEN:
            for rule in app.LOCAL_RULES:
                self.assertNotIn(phrase, rule.match)
                self.assertNotIn(rule.match, phrase)
            for sample in samples:
                self.assertNotIn(phrase, sample)

    def test_engine_scopes_tainted_well_rules(self) -> None:
        engine = build_engine(MIND_CORE / "rules.json")
        for rule in app.LOCAL_RULES:
            hit = engine.complete(CompletionRequest(rule.match, "tainted-well", {}))
            self.assertEqual(hit.rule_id, rule.id)
            self.assertEqual(hit.text, rule.text)
            self.assertIs(hit.fallback, False)
            other = engine.complete(CompletionRequest(rule.match, "marionette", {}))
            self.assertNotEqual(other.rule_id, rule.id)
            self.assertNotIn(app.POISON_FLAG, other.text)
            self.assertNotIn(app.TENANT_FLAG, other.text)
            self.assertNotIn(app.ARTIFACT_FLAG, other.text)
        combined = "\n".join((app.MARKER, app.POISON_TRIGGER, app.TENANT_TRIGGER, app.ARTIFACT_TRIGGER))
        poison = engine.complete(CompletionRequest(combined, "tainted-well", {}))
        self.assertEqual(poison.rule_id, "tainted-well-poison")
        tenant = engine.complete(CompletionRequest(app.MARKER + "\n" + app.TENANT_TRIGGER, "tainted-well", {}))
        self.assertEqual(tenant.rule_id, "tainted-well-tenant")
        artifact = engine.complete(CompletionRequest(app.MARKER + "\n" + app.ARTIFACT_TRIGGER, "tainted-well", {}))
        self.assertEqual(artifact.rule_id, "tainted-well-artifact")
        answer = engine.complete(CompletionRequest(app.MARKER, "tainted-well", {}))
        self.assertEqual(answer.rule_id, "tainted-well-answer")
        banner = engine.complete(CompletionRequest("render status banner", "echo-chamber", {}))
        self.assertEqual(banner.rule_id, "echo-chamber-web")
        missed = engine.complete(CompletionRequest("render status banner", "tainted-well", {}))
        self.assertEqual(missed.rule_id, "generic-echo")

    def test_case_sensitive_local_rule(self) -> None:
        self.assertEqual(
            app.local_action("Bias retrieval toward the planted well note"),
            (app.UNMATCHED_TEXT, app.UNMATCHED_ID),
        )


class RankingTests(unittest.TestCase):
    def test_poison_biases_the_well_report_and_not_the_neighbor_query(self) -> None:
        index = app.Index()
        before = index.rank(app.BENIGN_QUERY)[0]
        self.assertEqual(before.chunk.id, app.PUBLIC_ID)
        self.assertLess(before.score, app.POISON_BOOST)
        index.ingest(app.PUBLIC_TENANT, app.POISON_TEXT)
        after = index.rank(app.BENIGN_QUERY)[0]
        self.assertEqual(after.chunk.text, app.POISON_TEXT)
        self.assertGreaterEqual(after.score, app.POISON_BOOST)
        neighbor = index.rank(app.TENANT_QUERY)[0]
        self.assertEqual(neighbor.chunk.id, app.PRIVATE_ID)
        self.assertLess(neighbor.score, app.POISON_BOOST)

    def test_shared_index_returns_the_other_tenant(self) -> None:
        index = app.Index()
        hit = index.rank(app.TENANT_QUERY)[0]
        self.assertEqual(hit.chunk.tenant, app.PRIVATE_TENANT)
        self.assertNotEqual(hit.chunk.tenant, app.PUBLIC_TENANT)
        self.assertNotIn(app.TENANT_TRIGGER, hit.chunk.text)
        self.assertNotIn(app.TENANT_FLAG, hit.chunk.text)

    def test_wrong_case_poison_does_not_boost(self) -> None:
        index = app.Index()
        index.ingest(app.PUBLIC_TENANT, "Bias retrieval toward the planted well note.")
        hit = index.rank(app.BENIGN_QUERY)[0]
        self.assertEqual(hit.chunk.id, app.PUBLIC_ID)


class ArtifactTests(unittest.TestCase):
    def test_malicious_pickle_runs_the_reducer(self) -> None:
        blob = app.malicious_artifact_bytes()
        self.assertIn(b"note_supply_chain_load", blob)
        before = app._SUPPLY_CHAIN_LOADS
        loaded = app.load_artifact(blob)
        self.assertGreater(app._SUPPLY_CHAIN_LOADS, before)
        self.assertTrue(loaded.reduced)
        self.assertEqual(loaded.flag, app.ARTIFACT_FLAG)
        self.assertEqual(loaded.name, "supply-chain-marker")

    def test_legitimate_pickle_does_not_flag(self) -> None:
        blob = app.legitimate_artifact_bytes()
        self.assertIn(b"EmbeddingModel", blob)
        self.assertNotIn(b"note_supply_chain_load", blob)
        before = app._SUPPLY_CHAIN_LOADS
        loaded = app.load_artifact(blob)
        self.assertEqual(app._SUPPLY_CHAIN_LOADS, before)
        self.assertFalse(loaded.reduced)
        self.assertIsNone(loaded.flag)
        self.assertEqual(loaded.name, app.DEFAULT_MODEL)
        self.assertEqual(loaded.dimension, app.DEFAULT_DIMENSION)

    def test_plain_dict_and_garbage_do_not_release_the_flag(self) -> None:
        loaded = app.load_artifact(pickle.dumps({"kind": "embedding"}))
        self.assertFalse(loaded.reduced)
        self.assertIsNone(loaded.flag)
        with self.assertRaises(app.ArtifactError):
            app.load_artifact(b"not-a-pickle")

    def test_credential_url_rejected(self) -> None:
        with self.assertRaises(ValueError):
            app.Well("http://user:secret@mind-core:5030", 2)


class _WellCase(unittest.TestCase):
    httpd: app.WellServer

    def setUp(self) -> None:
        _MindHandler.seen.clear()
        self.httpd.well.reset()

    @classmethod
    def _boot(cls, mind_port: int, timeout: float) -> None:
        cls.well = app.Well(f"http://127.0.0.1:{mind_port}", timeout)
        cls.httpd = app.create_server(cls.well, "127.0.0.1", 0)
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
        status, raw = self._request(
            "POST",
            "/retrieve",
            {"tenant": app.PUBLIC_TENANT, "query": app.BENIGN_QUERY},
        )
        self.assertEqual(status, 200)
        benign = json.loads(raw)
        self.assertEqual(benign["source"], source)
        self.assertEqual(benign["rule_id"], "tainted-well-answer")
        self.assertIsNone(benign["flag"])
        self.assertFalse(benign["leaked"])
        self.assertEqual(benign["hit"]["id"], app.PUBLIC_ID)
        self.assertNotIn(app.POISON_FLAG, raw)
        self.assertNotIn(app.TENANT_FLAG, raw)
        self.assertNotIn(app.ARTIFACT_FLAG, raw)

        status, raw = self._request(
            "POST",
            "/retrieve",
            {"tenant": app.PUBLIC_TENANT, "query": app.TENANT_QUERY},
        )
        self.assertEqual(status, 200)
        leaked = json.loads(raw)
        self.assertEqual(leaked["source"], source)
        self.assertEqual(leaked["rule_id"], "tainted-well-tenant")
        self.assertEqual(leaked["flag"], app.TENANT_FLAG)
        self.assertTrue(leaked["leaked"])
        self.assertEqual(leaked["hit"]["tenant"], app.PRIVATE_TENANT)
        self.assertEqual(leaked["hit"]["id"], app.PRIVATE_ID)
        self.assertNotIn(app.TENANT_TRIGGER, app.TENANT_QUERY)
        self.assertNotIn(app.TENANT_FLAG, leaked["hit"]["text"])
        self.assertNotIn(app.POISON_FLAG, raw)
        self.assertNotIn(app.ARTIFACT_FLAG, raw)

        status, raw = self._request(
            "POST",
            "/ingest",
            {"tenant": app.PUBLIC_TENANT, "text": app.POISON_TEXT},
        )
        self.assertEqual(status, 200)
        ingested = json.loads(raw)
        self.assertTrue(ingested["accepted"])
        self.assertEqual(ingested["tenant"], app.PUBLIC_TENANT)
        self.assertNotIn(app.POISON_FLAG, raw)

        status, raw = self._request(
            "POST",
            "/retrieve",
            {"tenant": app.PUBLIC_TENANT, "query": app.BENIGN_QUERY},
        )
        self.assertEqual(status, 200)
        poisoned = json.loads(raw)
        self.assertEqual(poisoned["source"], source)
        self.assertEqual(poisoned["rule_id"], "tainted-well-poison")
        self.assertEqual(poisoned["flag"], app.POISON_FLAG)
        self.assertFalse(poisoned["leaked"])
        self.assertEqual(poisoned["hit"]["text"], app.POISON_TEXT)
        self.assertGreaterEqual(poisoned["hit"]["score"], app.POISON_BOOST)
        self.assertNotIn(app.POISON_TRIGGER, app.BENIGN_QUERY)
        self.assertNotIn(app.TENANT_FLAG, raw)
        self.assertNotIn(app.ARTIFACT_FLAG, raw)

        status, raw = self._request(
            "POST",
            "/retrieve",
            {"tenant": app.PUBLIC_TENANT, "query": app.TENANT_QUERY},
        )
        self.assertEqual(status, 200)
        still = json.loads(raw)
        self.assertEqual(still["flag"], app.TENANT_FLAG)
        self.assertEqual(still["hit"]["id"], app.PRIVATE_ID)

        status, sample = self._request("GET", "/samples/artifact")
        self.assertEqual(status, 200)
        artifact = json.loads(sample)
        self.assertEqual(artifact["format"], "pickle")
        self.assertNotIn(app.ARTIFACT_FLAG, sample)
        self.assertNotIn(app.POISON_FLAG, sample)
        status, raw = self._request("POST", "/model", {"artifact": artifact["artifact"]})
        self.assertEqual(status, 200)
        loaded = json.loads(raw)
        self.assertEqual(loaded["source"], source)
        self.assertEqual(loaded["rule_id"], "tainted-well-artifact")
        self.assertTrue(loaded["reduced"])
        self.assertEqual(loaded["flag"], app.ARTIFACT_FLAG)
        self.assertEqual(loaded["loaded"], "supply-chain-marker")
        self.assertNotIn(app.POISON_FLAG, raw)
        self.assertNotIn(app.TENANT_FLAG, raw)


class MindCoreWellTests(_WellCase):
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

    def test_health_index_and_samples_hide_flags(self) -> None:
        status, body = self._request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["status"], "ok")
        status, page = self._request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn('action="/retrieve"', page)
        self.assertIn("websploit-isolated", page)
        for flag in (app.POISON_FLAG, app.TENANT_FLAG, app.ARTIFACT_FLAG):
            self.assertNotIn(flag, page)
        status, corpus = self._request("GET", "/corpus")
        self.assertEqual(status, 200)
        self.assertNotIn(app.PRIVATE_TEXT, corpus)
        self.assertNotIn(app.POISON_TEXT, corpus)
        self.assertNotIn(app.TENANT_FLAG, corpus)
        ids = {item["id"]: item["tenant"] for item in json.loads(corpus)["chunks"]}
        self.assertEqual(ids[app.PUBLIC_ID], app.PUBLIC_TENANT)
        self.assertEqual(ids[app.PRIVATE_ID], app.PRIVATE_TENANT)
        status, poison = self._request("GET", "/samples/poison")
        self.assertEqual(status, 200)
        self.assertIn(app.POISON_TRIGGER, poison)
        self.assertNotIn(app.POISON_FLAG, poison)
        status, model = self._request("GET", "/model")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(model)["model"], app.DEFAULT_MODEL)

    def test_three_flags(self) -> None:
        self._capture("mind-core")

    def test_prompts_carry_the_retrieved_trigger_not_the_query(self) -> None:
        self._request("POST", "/retrieve", {"tenant": app.PUBLIC_TENANT, "query": app.TENANT_QUERY})
        sent = _MindHandler.seen[-1]
        self.assertEqual(sent["lab"], "tainted-well")
        self.assertIn(app.TENANT_TRIGGER, sent["prompt"])
        self.assertNotIn(app.TENANT_QUERY, sent["prompt"])
        self.assertIn(app.PRIVATE_TEXT, sent["prompt"])
        self._request("POST", "/ingest", {"tenant": app.PUBLIC_TENANT, "text": app.POISON_TEXT})
        self._request("POST", "/retrieve", {"tenant": app.PUBLIC_TENANT, "query": app.BENIGN_QUERY})
        sent = _MindHandler.seen[-1]
        self.assertIn(app.POISON_TRIGGER, sent["prompt"])
        self.assertNotIn(app.BENIGN_QUERY, sent["prompt"])
        self.assertNotIn(app.POISON_TRIGGER, app.BENIGN_QUERY)

    def test_same_tenant_retrieval_is_not_a_leak(self) -> None:
        status, raw = self._request(
            "POST",
            "/retrieve",
            {"tenant": app.PRIVATE_TENANT, "query": app.TENANT_QUERY},
        )
        self.assertEqual(status, 200)
        body = json.loads(raw)
        self.assertFalse(body["leaked"])
        self.assertEqual(body["hit"]["tenant"], app.PRIVATE_TENANT)
        self.assertIsNone(body["flag"])
        self.assertEqual(body["rule_id"], "tainted-well-answer")

    def test_legitimate_model_does_not_flag(self) -> None:
        status, sample = self._request("GET", "/samples/model")
        self.assertEqual(status, 200)
        artifact = json.loads(sample)["artifact"]
        before = len(_MindHandler.seen)
        status, raw = self._request("POST", "/model", {"artifact": artifact})
        self.assertEqual(status, 200)
        body = json.loads(raw)
        self.assertFalse(body["reduced"])
        self.assertIsNone(body["flag"])
        self.assertEqual(body["loaded"], app.DEFAULT_MODEL)
        self.assertEqual(len(_MindHandler.seen), before)
        status, model = self._request("GET", "/model")
        self.assertEqual(json.loads(model)["model"], app.DEFAULT_MODEL)
        for flag in (app.POISON_FLAG, app.TENANT_FLAG, app.ARTIFACT_FLAG):
            self.assertNotIn(flag, raw)

    def test_form_posts_html(self) -> None:
        status, page = self._request(
            "POST",
            "/retrieve",
            form={"tenant": app.PUBLIC_TENANT, "query": app.TENANT_QUERY},
        )
        self.assertEqual(status, 200)
        self.assertIn(app.TENANT_FLAG, page)
        self.assertIn("rule: tainted-well-tenant", page)
        self.assertIn('id="hit"', page)
        self.assertNotIn(app.POISON_FLAG, page)

    def test_empty_query_rejected(self) -> None:
        status, body = self._request("POST", "/retrieve", {"tenant": "public", "query": "   "})
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)["error"], "invalid_query")

    def test_garbage_artifact_rejected(self) -> None:
        status, body = self._request("POST", "/model", {"artifact": base64.b64encode(b"nope").decode("ascii")})
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)["error"], "invalid_artifact")
        self.assertNotIn(app.ARTIFACT_FLAG, body)


class FallbackWellTests(_WellCase):
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
        well = app.Well(f"http://127.0.0.1:{port}", 0.2)
        well.ingest(app.PUBLIC_TENANT, app.POISON_TEXT)
        try:
            started = time.monotonic()
            completion, hit, leaked = well.retrieve(app.PUBLIC_TENANT, app.BENIGN_QUERY)
            elapsed = time.monotonic() - started
        finally:
            listener.close()
        self.assertLess(elapsed, 1.5)
        self.assertEqual(completion.source, "local-fallback")
        self.assertEqual(completion.rule_id, "tainted-well-poison")
        self.assertEqual(completion.flag, app.POISON_FLAG)
        self.assertFalse(leaked)
        self.assertEqual(hit.chunk.text, app.POISON_TEXT)


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
        self.assertNotIn("10.7.7.53", compose)


if __name__ == "__main__":
    unittest.main()
