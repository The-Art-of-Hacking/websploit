"""Checksum tests for the optional GGUF pin. These tests do not download it."""

from __future__ import annotations

import hashlib
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from fetch_model import download_to, install_weight
from model_pin import (
    FILENAME,
    LICENSE,
    MODEL_ID,
    MODEL_URL,
    PARAMETERS,
    QUANTIZATION,
    SHA256,
    SIZE_BYTES,
    ChecksumError,
    ModelPin,
    shipped_pin,
    verify_file,
)

ROOT = Path(__file__).resolve().parent


class ModelPinTests(unittest.TestCase):
    def test_shipped_pin(self) -> None:
        pin = shipped_pin()
        self.assertEqual(pin.model_id, MODEL_ID)
        self.assertEqual(pin.model_id, "Qwen/Qwen2.5-0.5B-Instruct-GGUF")
        self.assertEqual(pin.filename, FILENAME)
        self.assertEqual(pin.filename, "qwen2.5-0.5b-instruct-q4_k_m.gguf")
        self.assertEqual(pin.url, MODEL_URL)
        self.assertTrue(pin.url.startswith("https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/"))
        self.assertEqual(pin.sha256, SHA256)
        self.assertEqual(pin.sha256, "74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db")
        self.assertEqual(pin.size_bytes, SIZE_BYTES)
        self.assertEqual(pin.size_bytes, 491400032)
        self.assertEqual(pin.license, LICENSE)
        self.assertEqual(pin.license, "Apache-2.0")
        self.assertEqual(pin.quantization, QUANTIZATION)
        self.assertEqual(pin.quantization, "Q4_K_M")
        self.assertEqual(pin.parameters, PARAMETERS)
        self.assertEqual(pin.parameters, "0.5B")

    def test_checksum_source_uses_sha256(self) -> None:
        for name in ("model_pin.py", "fetch_model.py"):
            text = (ROOT / name).read_text(encoding="utf-8").lower()
            self.assertNotIn("md5", text, name)
            self.assertNotIn("sha1", text, name)
            self.assertNotIn("mind_core_external_api_key", text, name)
        pin_source = (ROOT / "model_pin.py").read_text(encoding="utf-8").lower()
        self.assertIn("sha256", pin_source)

    def test_verify_accepts_exact_bytes_and_rejects_truncation_or_tamper(self) -> None:
        payload = b"gguf-fixture-not-a-real-weight"
        digest = hashlib.sha256(payload).hexdigest()
        path = Path(self._tmp()) / "good.gguf"
        path.write_bytes(payload)
        verify_file(path, len(payload), digest)

        truncated = Path(self._tmp()) / "short.gguf"
        truncated.write_bytes(payload[:-1])
        with self.assertRaises(ChecksumError):
            verify_file(truncated, len(payload), digest)

        tampered = bytearray(payload)
        tampered[0] ^= 0xFF
        bad = Path(self._tmp()) / "bad.gguf"
        bad.write_bytes(bytes(tampered))
        with self.assertRaises(ChecksumError):
            verify_file(bad, len(payload), digest)

        missing = Path(self._tmp()) / "missing.gguf"
        with self.assertRaises(ChecksumError):
            verify_file(missing, len(payload), digest)

    def test_install_is_idempotent_and_does_not_fetch_a_matching_file(self) -> None:
        payload = b"cached-weight"
        pin = _pin(payload, "http://127.0.0.1:9/should-not-be-called")
        directory = Path(self._tmp())
        destination = directory / pin.filename
        destination.write_bytes(payload)

        def fetch(url: str, dest: Path) -> None:
            raise AssertionError(url)

        install_weight(pin, destination, fetch=fetch, attempts=1, pause=lambda _seconds: None)
        self.assertEqual(destination.read_bytes(), payload)

    def test_failed_download_leaves_no_file(self) -> None:
        payload = b"expected-weight"
        pin = _pin(payload, "http://127.0.0.1:9/model.gguf")
        destination = Path(self._tmp()) / pin.filename
        destination.write_bytes(b"tampered")

        def fetch(url: str, dest: Path) -> None:
            dest.write_bytes(b"truncated")

        with self.assertRaises(ChecksumError):
            install_weight(pin, destination, fetch=fetch, attempts=2, pause=lambda _seconds: None)
        self.assertFalse(destination.exists())
        self.assertFalse(destination.with_name(destination.name + ".partial").exists())

    def test_retry_then_installs_once(self) -> None:
        payload = b"retry-weight"
        pin = _pin(payload, "http://127.0.0.1:9/model.gguf")
        destination = Path(self._tmp()) / pin.filename
        calls = {"n": 0}

        def fetch(url: str, dest: Path) -> None:
            calls["n"] += 1
            if calls["n"] < 3:
                raise ChecksumError("temporary")
            dest.write_bytes(payload)

        install_weight(pin, destination, fetch=fetch, attempts=4, pause=lambda _seconds: None)
        self.assertEqual(calls["n"], 3)
        self.assertEqual(destination.read_bytes(), payload)
        self.assertEqual(destination.stat().st_mode & 0o777, 0o444)

    def test_download_rejects_a_truncated_response_and_a_non_http_url(self) -> None:
        payload = b"http-fixture-weight"
        served = {"path": "/good", "body": payload}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt: str, *args: object) -> None:
                return

            def do_GET(self) -> None:  # noqa: N802
                body = served["body"] if self.path == "/good" else served["body"][:-1]
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        host, port = server.server_address
        directory = Path(self._tmp())
        try:
            good = _pin(payload, f"http://{host}:{port}/good")
            destination = directory / good.filename
            install_weight(good, destination, attempts=1, pause=lambda _seconds: None)
            self.assertEqual(destination.read_bytes(), payload)
            install_weight(good, destination, attempts=1, pause=lambda _seconds: None)

            bad = _pin(payload, f"http://{host}:{port}/bad")
            rejected = directory / "rejected.gguf"
            with self.assertRaises(ChecksumError):
                install_weight(bad, rejected, attempts=1, pause=lambda _seconds: None)
            self.assertFalse(rejected.exists())
            self.assertFalse(rejected.with_name(rejected.name + ".partial").exists())
        finally:
            server.shutdown()
            server.server_close()

        with self.assertRaises(ChecksumError):
            download_to("file:///tmp/model.gguf", directory / "file-url.gguf")
        self.assertFalse((directory / "file-url.gguf").exists())

    def _tmp(self) -> str:
        import tempfile

        path = tempfile.mkdtemp(prefix="mind-core-pin-")
        self.addCleanup(lambda: _rmtree(Path(path)))
        return path


def _pin(payload: bytes, url: str) -> ModelPin:
    return ModelPin(
        model_id="fixture",
        filename="fixture.gguf",
        url=url,
        sha256=hashlib.sha256(payload).hexdigest(),
        size_bytes=len(payload),
        license="Apache-2.0",
        quantization="Q4_K_M",
        parameters="0.5B",
    )


def _rmtree(path: Path) -> None:
    if not path.exists():
        return
    for child in path.iterdir():
        if child.is_file() or child.is_symlink():
            child.chmod(0o644)
            child.unlink()
        else:
            _rmtree(child)
    path.rmdir()


if __name__ == "__main__":
    unittest.main()
