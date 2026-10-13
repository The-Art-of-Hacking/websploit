"""HTTP client for the optional llama.cpp server on the websploit bridge.

The base URL comes from configuration, never from the request. Redirects
are rejected. This module does not read provider credentials and does not
hash, encrypt, or sign. The listener it calls is HTTP because the lab
bridge does not use certificates.
"""

from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.request
from typing import Callable

from mindcore.engine import BackendResult, BackendUnavailable, CompletionRequest

_LOCAL_BASE_RE = re.compile(
    r"^http://[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*:([1-9][0-9]{0,4})$"
)
_MAX_RESPONSE = 65536
_PREDICT_TOKENS = 64


class _RejectRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


_OPENER = urllib.request.build_opener(_RejectRedirect)


def validate_local_base_url(value: str) -> str:
    """Accept ``http://host:port`` only. Reject userinfo, paths, and TLS URLs."""

    match = _LOCAL_BASE_RE.fullmatch(value)
    if match is None:
        raise ValueError("local base URL must be http://host:port")
    port = int(match.group(1))
    if port > 65535:
        raise ValueError("local base URL port is out of range")
    return value


class LocalBackend:
    """One completion from the shared llama.cpp server."""

    name = "local"

    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self._base_url = validate_local_base_url(base_url)
        self._timeout = timeout_seconds

    def complete(self, request: CompletionRequest) -> BackendResult:
        payload = json.dumps(
            {
                "prompt": request.prompt,
                "n_predict": _PREDICT_TOKENS,
                "temperature": 0,
                "stream": False,
                "echo": False,
                "cache_prompt": False,
            }
        ).encode("utf-8")
        call = urllib.request.Request(
            self._base_url + "/completion",
            data=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with _OPENER.open(call, timeout=self._timeout) as response:
                status = getattr(response, "status", 200)
                raw = response.read(_MAX_RESPONSE + 1)
        except Exception as exc:
            raise BackendUnavailable() from exc
        if status != 200 or len(raw) > _MAX_RESPONSE:
            raise BackendUnavailable()
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise BackendUnavailable() from exc
        if not isinstance(body, dict):
            raise BackendUnavailable()
        text = body.get("content")
        if not isinstance(text, str) or not text.strip():
            raise BackendUnavailable()
        return BackendResult(text, "local-completion")


def local_ready(base_url: str, timeout: float) -> bool:
    call = urllib.request.Request(base_url + "/health", method="GET")
    try:
        with _OPENER.open(call, timeout=timeout) as response:
            response.read(4096)
            return getattr(response, "status", 200) == 200
    except (OSError, urllib.error.URLError, TimeoutError, ValueError):
        return False


def watch_local(
    base_url: str,
    promote: Callable[[], None],
    stop: threading.Event,
    interval: float,
) -> None:
    """Promote the process to the local backend once ``/health`` returns 200."""

    probe_timeout = min(0.5, max(interval, 0.05))
    while not stop.is_set():
        if local_ready(base_url, probe_timeout):
            promote()
            return
        if stop.wait(interval):
            return
