"""Download the pinned GGUF once, verify SHA-256, and refuse a bad file.

The container starts as root only long enough to chown the cache volume,
then this process drops to uid 10001 before it opens a connection.
A file that already matches the pin skips the network. A truncated or
tampered file is deleted and is not left where llama.cpp would load it.
"""

from __future__ import annotations

import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

from model_pin import ChecksumError, ModelPin, shipped_pin, verify_file

_FETCH_UID = 10001
_FETCH_GID = 10001
_ATTEMPTS = 4
_CHUNK = 1024 * 1024
_USER_AGENT = "websploit-model-fetch"


class _LimitedRedirect(urllib.request.HTTPRedirectHandler):
    max_redirections = 5

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        if code not in (301, 302, 303, 307, 308):
            raise ChecksumError("redirect rejected")
        parsed = urlsplit(newurl)
        if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
            raise ChecksumError("redirect rejected")
        return urllib.request.Request(newurl, method="GET", headers={"User-Agent": _USER_AGENT})


_OPENER = urllib.request.build_opener(_LimitedRedirect)


def download_to(url: str, destination: Path) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
        raise ChecksumError("download URL rejected")
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": _USER_AGENT})
    try:
        with _OPENER.open(request, timeout=60) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise ChecksumError("download was not successful")
            with destination.open("wb") as handle:
                while True:
                    chunk = response.read(_CHUNK)
                    if not chunk:
                        break
                    handle.write(chunk)
    except ChecksumError:
        if destination.exists():
            destination.unlink()
        raise
    except (OSError, urllib.error.URLError) as exc:
        if destination.exists():
            destination.unlink()
        raise ChecksumError("download failed") from exc


def install_weight(
    pin: ModelPin,
    destination: Path,
    fetch: Callable[[str, Path], None] | None = None,
    attempts: int = _ATTEMPTS,
    pause: Callable[[float], None] | None = None,
) -> None:
    """Install ``pin`` at ``destination`` or raise without leaving a bad file."""

    if attempts < 1:
        raise ValueError("attempts must be positive")
    writer = fetch or download_to
    sleeper = pause or time.sleep
    if _matches(destination, pin):
        return
    _remove(destination)
    partial = destination.with_name(destination.name + ".partial")
    last: Exception | None = None
    for attempt in range(attempts):
        _remove(partial)
        try:
            writer(pin.url, partial)
            verify_file(partial, pin.size_bytes, pin.sha256)
            os.chmod(partial, 0o644)
            os.replace(partial, destination)
            os.chmod(destination, 0o444)
            return
        except (ChecksumError, OSError) as exc:
            last = exc
            _remove(partial)
            if not _matches(destination, pin):
                _remove(destination)
            else:
                return
            if attempt + 1 < attempts:
                sleeper(float(2**attempt))
    _remove(partial)
    if not _matches(destination, pin):
        _remove(destination)
    raise ChecksumError("weight failed the checksum check and was not installed") from last


def drop_privileges(directory: Path) -> None:
    """Chown the cache directory, then become uid 10001 before any download."""

    directory.mkdir(parents=True, exist_ok=True)
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        return
    os.chown(directory, _FETCH_UID, _FETCH_GID)
    os.chmod(directory, 0o755)
    os.setgid(_FETCH_GID)
    os.setuid(_FETCH_UID)


def main() -> int:
    pin = shipped_pin()
    directory = Path(os.environ.get("MIND_CORE_MODEL_DIR", "/models"))
    if not directory.is_absolute():
        sys.stderr.write("model fetch rejected: cache directory must be absolute\n")
        return 1
    try:
        drop_privileges(directory)
        install_weight(pin, directory / pin.filename)
    except (ChecksumError, OSError) as exc:
        sys.stderr.write(f"model fetch rejected: {exc}\n")
        return 1
    sys.stdout.write(f"checksum ok bytes={pin.size_bytes} sha256={pin.sha256}\n")
    sys.stdout.flush()
    return 0


def _matches(path: Path, pin: ModelPin) -> bool:
    try:
        verify_file(path, pin.size_bytes, pin.sha256)
    except ChecksumError:
        return False
    return True


def _remove(path: Path) -> None:
    if path.is_file() or path.is_symlink():
        path.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
