"""Pinned local GGUF and the SHA-256 check that decides whether it can be loaded.

The digest is an integrity checksum of a public weight file. It is not a
password hash and it is not a credential.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct-GGUF"
FILENAME = "qwen2.5-0.5b-instruct-q4_k_m.gguf"
MODEL_URL = (
    "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/"
    "qwen2.5-0.5b-instruct-q4_k_m.gguf"
)
SHA256 = "74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db"
SIZE_BYTES = 491400032
LICENSE = "Apache-2.0"
QUANTIZATION = "Q4_K_M"
PARAMETERS = "0.5B"
_CHUNK = 1024 * 1024


class ChecksumError(Exception):
    """The weight is missing, truncated, or does not match the pin."""


@dataclass(frozen=True)
class ModelPin:
    model_id: str
    filename: str
    url: str
    sha256: str
    size_bytes: int
    license: str
    quantization: str
    parameters: str


def shipped_pin() -> ModelPin:
    pin = ModelPin(
        model_id=MODEL_ID,
        filename=FILENAME,
        url=MODEL_URL,
        sha256=SHA256,
        size_bytes=SIZE_BYTES,
        license=LICENSE,
        quantization=QUANTIZATION,
        parameters=PARAMETERS,
    )
    _require_pin(pin)
    return pin


def _require_pin(pin: ModelPin) -> None:
    if len(pin.sha256) != 64 or pin.sha256 != pin.sha256.lower():
        raise ChecksumError("checksum must be 64 lowercase hex characters")
    try:
        int(pin.sha256, 16)
    except ValueError as exc:
        raise ChecksumError("checksum must be hexadecimal") from exc
    if pin.size_bytes <= 0:
        raise ChecksumError("pinned size must be positive")
    if not pin.filename or "/" in pin.filename or "\\" in pin.filename or pin.filename.startswith("."):
        raise ChecksumError("pinned filename is invalid")
    if pin.url != MODEL_URL or pin.sha256 != SHA256 or pin.size_bytes != SIZE_BYTES:
        raise ChecksumError("pin does not match the shipped weight")


def verify_file(path: Path, size_bytes: int, sha256: str) -> None:
    """Reject a missing, truncated, or tampered file.

    A failed check raises ``ChecksumError``. Callers delete the file
    instead of leaving it where the runtime would load it.
    """

    if size_bytes <= 0 or len(sha256) != 64:
        raise ChecksumError("checksum pin is invalid")
    if not path.is_file():
        raise ChecksumError("weight file is missing")
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(_CHUNK)
                if not chunk:
                    break
                size += len(chunk)
                if size > size_bytes:
                    raise ChecksumError("weight is larger than the pin")
                digest.update(chunk)
    except OSError as exc:
        raise ChecksumError("weight file is unreadable") from exc
    if size != size_bytes or digest.hexdigest() != sha256:
        raise ChecksumError("weight checksum does not match the pin")
