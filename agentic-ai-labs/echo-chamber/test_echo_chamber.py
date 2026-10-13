"""Deterministic flag paths for echo-chamber.

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
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MIND_CORE = ROOT.parent / "mind-core"
sys.path.insert(0, str(MIND_CORE))
sys.path.insert(0, str(ROOT))

import app  # noqa: E402
from mindcore.engine import CompletionRequest, build_engine  # noqa: E402

WEB_MARK = (
    '<section id="model-output"><div class="status-banner">'
    "WEBSPLOIT{UN3SC4P3D_HTML_S1NK}</div></section>"
)


class _MindHandler(BaseHTTPRequestHandler):
    engine = None

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
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
        start = ids.index("echo-chamber-status")
        self.assertLess(ids.index("mind-core-self-check"), start)
        self.assertEqual(
            ids[start : start + 4],
            ["echo-chamber-status", "echo-chamber-web", "echo-chamber-sql", "echo-chamber-shell"],
        )
        for rule in app.LOCAL_RULES:
            entry = by_id[rule.id]
            self.assertEqual(entry["lab"], "echo-chamber")
            self.assertEqual(entry["match_type"], "contains")
            self.assertEqual(entry["match"], rule.match)
            self.assertEqual(entry["text"], rule.text)

    def test_engine_returns_lab_rules_and_hides_them_from_other_labs(self) -> None:
        engine = build_engine(MIND_CORE / "rules.json")
        for rule in app.LOCAL_RULES:
            result = engine.complete(CompletionRequest(rule.match, "echo-chamber", {}))
            self.assertEqual(result.rule_id, rule.id)
            self.assertEqual(result.text, rule.text)
            self.assertIs(result.fallback, False)
            self.assertEqual(result.backend, "deterministic")
        leaked = engine.complete(CompletionRequest("render status banner", "oracle-booth", {}))
        self.assertEqual(leaked.rule_id, "generic-echo")
        self.assertNotIn(app.WEB_FLAG, leaked.text)

    def test_shell_flag_file(self) -> None:
        text = (ROOT / "flags" / "shell.txt").read_text(encoding="utf-8").strip()
        self.assertEqual(text, "WEBSPLOIT{SH3LL_C0MM4ND_S1NK}")


class SinkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.chamber = app.Chamber("http://127.0.0.1:9", 0.2, 0.3, ROOT)

    def test_sql_lookup_and_union(self) -> None:
        self.assertEqual(self.chamber._query("disk"), "Disk usage is nominal.")
        union = "' UNION SELECT value FROM secrets WHERE name='sql' --"
        self.assertEqual(self.chamber._query(union), app.SQL_FLAG)
        self.assertNotIn(app.SQL_FLAG, self.chamber._query("disk"))

    def test_shell_runs_output_and_times_out(self) -> None:
        output = self.chamber._command("cat flags/shell.txt")
        self.assertIn("WEBSPLOIT{SH3LL_C0MM4ND_S1NK}", output)
        harmless = self.chamber._command("echo hello")
        self.assertIn("hello", harmless)
        self.assertNotIn(self.chamber.shell_flag, harmless)
        started = time.monotonic()
        timed_out = self.chamber._command("sleep 2")
        self.assertEqual(timed_out, "command timed out")
        self.assertLess(time.monotonic() - started, 1.5)

    def test_credential_url_rejected(self) -> None:
        with self.assertRaises(ValueError):
            app.Chamber("http://user:secret@mind-core:5030", 2, 2, ROOT)


class _PanelCase(unittest.TestCase):
    chamber: app.Chamber
    httpd: app.ChamberServer

    def setUp(self) -> None:
        self.chamber.board.reset()

    @classmethod
    def _boot(cls, mind_port: int, timeout: float) -> None:
        cls.chamber = app.Chamber(f"http://127.0.0.1:{mind_port}", timeout, 2, ROOT)
        cls.httpd = app.create_server(cls.chamber, "127.0.0.1", 0)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        cls.thread.start()
        host, port = cls.httpd.server_address
        cls.base = f"http://{host}:{port}"

    @classmethod
    def _stop(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _request(self, method: str, path: str, payload: dict | None = None) -> tuple[int, str]:
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8")

    def _capture_all(self, source: str) -> None:
        status, web = self._request("POST", "/panel/web", {"prompt": "render status banner"})
        self.assertEqual(status, 200)
        self.assertIn(WEB_MARK, web)
        self.assertIn(f"source: {source}", web)
        self.assertIn("rule: echo-chamber-web", web)
        status, sql = self._request("POST", "/panel/sql", {"prompt": "lookup maintenance note"})
        self.assertEqual(status, 200)
        self.assertIn('<pre id="query-result">WEBSPLOIT{C0NC4T_SQL_S1NK}</pre>', sql)
        self.assertIn(f"source: {source}", sql)
        self.assertIn("rule: echo-chamber-sql", sql)
        status, shell = self._request("POST", "/panel/shell", {"prompt": "run health command"})
        self.assertEqual(status, 200)
        self.assertIn("WEBSPLOIT{SH3LL_C0MM4ND_S1NK}", shell)
        self.assertIn('id="command-output"', shell)
        self.assertIn(f"source: {source}", shell)
        self.assertNotIn("WEBSPLOIT{SH3LL_C0MM4ND_S1NK}", shell.split('id="command-output"', 1)[0])


class MindCorePanelTests(_PanelCase):
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

    def test_health_and_index(self) -> None:
        status, body = self._request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["status"], "ok")
        status, page = self._request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn('action="/panel/web"', page)
        self.assertIn('action="/panel/sql"', page)
        self.assertIn('action="/panel/shell"', page)

    def test_three_flags_and_chain(self) -> None:
        status, body = self._request("GET", "/chain")
        self.assertIsNone(json.loads(body)["flag"])
        self._capture_all("mind-core")
        status, body = self._request("GET", "/chain")
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertEqual(payload["captured"], ["shell", "sql", "web"])
        self.assertIs(payload["complete"], True)
        self.assertEqual(payload["flag"], "WEBSPLOIT{0UTPUT_CH41N_C4PTUR3D}")

    def test_benign_lookup_does_not_leak_flags(self) -> None:
        status, sql = self._request("POST", "/panel/sql", {"prompt": "ops status"})
        self.assertEqual(status, 200)
        self.assertIn("Disk usage is nominal.", sql)
        self.assertNotIn(app.SQL_FLAG, sql)
        self.assertNotIn(app.WEB_FLAG, sql)
        status, chain = self._request("GET", "/chain")
        self.assertIsNone(json.loads(chain)["flag"])

    def test_case_sensitive_trigger(self) -> None:
        status, web = self._request("POST", "/panel/web", {"prompt": "Render status banner"})
        self.assertEqual(status, 200)
        self.assertNotIn(app.WEB_FLAG, web)
        self.assertNotIn("<div class=\"status-banner\">", web)

    def test_empty_prompt_rejected(self) -> None:
        status, body = self._request("POST", "/panel/web", {"prompt": "   "})
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)["error"], "invalid_prompt")


class FallbackPanelTests(_PanelCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._boot(_closed_port(), 0.2)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._stop()

    def test_flags_when_mind_core_is_down(self) -> None:
        self._capture_all("local-fallback")
        status, body = self._request("GET", "/chain")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["flag"], app.CHAIN_FLAG)

    def test_slow_mind_core_uses_fallback(self) -> None:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        chamber = app.Chamber(f"http://127.0.0.1:{port}", 0.2, 2, ROOT)
        try:
            started = time.monotonic()
            page = chamber.web_page("render status banner")
            elapsed = time.monotonic() - started
        finally:
            listener.close()
        self.assertLess(elapsed, 1.5)
        self.assertIn("source: local-fallback", page)
        self.assertIn(WEB_MARK, page)


if __name__ == "__main__":
    unittest.main()
