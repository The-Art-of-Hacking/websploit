"""Deterministic completion engine and the pluggable backend boundary.

Later issues can register a local GGUF backend or an external provider
without changing callers. This module makes no outbound connections and
stores no credentials. The deterministic path does not use a timeout
thread; it returns as soon as the rule table is scanned.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol

MAX_RULES = 64
MAX_TEMPLATE = 2048
MAX_MATCH = 512
MAX_OUTPUT = 8192
EXCERPT_CHARS = 120

_ID_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?$")
_MATCH_TYPES = frozenset({"exact", "prefix", "contains"})
_RULE_KEYS = frozenset({"id", "match_type", "match", "text", "lab"})
_ECHO_KEYS = frozenset({"id", "text"})
_TOP_KEYS = frozenset({"version", "rules", "echo"})
_TOKENS = ("{lab}", "{prompt_length}", "{prompt_excerpt}")


class BackendTimeout(Exception):
    """A non-deterministic backend exceeded its deadline."""


class BackendUnavailable(Exception):
    """A non-deterministic backend failed before producing text."""


@dataclass(frozen=True)
class CompletionRequest:
    prompt: str
    lab: str | None
    metadata: Mapping[str, object]


@dataclass(frozen=True)
class BackendResult:
    text: str
    rule_id: str


@dataclass(frozen=True)
class Completion:
    text: str
    backend: str
    fallback: bool
    rule_id: str
    requested_backend: str


class CompletionBackend(Protocol):
    """Stable hook for a later local-model or external-provider issue.

    Implementations must return on their own. The dispatcher also applies
    ``MIND_CORE_BACKEND_TIMEOUT_SECONDS`` around every backend except
    ``deterministic`` and serves the rules engine when that call fails.
    An external provider must read any API key from the environment at
    call time. Do not hardcode secrets in the backend.
    """

    name: str

    def complete(self, request: CompletionRequest) -> BackendResult:
        """Return completion text or raise BackendUnavailable."""


@dataclass(frozen=True)
class _Rule:
    id: str
    match_type: str
    match: str
    text: str
    lab: str | None


@dataclass(frozen=True)
class RuleTable:
    rules: tuple[_Rule, ...]
    echo_id: str
    echo_text: str

    def respond(self, prompt: str, lab: str | None) -> BackendResult:
        for rule in self.rules:
            if rule.lab is not None and rule.lab != lab:
                continue
            if _matches(rule, prompt):
                return BackendResult(_render(rule.text, prompt, lab), rule.id)
        return BackendResult(_render(self.echo_text, prompt, lab), self.echo_id)


class DeterministicBackend:
    """In-memory rule table. This is the default backend."""

    name = "deterministic"

    def __init__(self, table: RuleTable) -> None:
        self._table = table

    def complete(self, request: CompletionRequest) -> BackendResult:
        return self._table.respond(request.prompt, request.lab)


class Engine:
    """Select a backend and fall back to the rules engine on failure."""

    def __init__(
        self,
        deterministic: DeterministicBackend,
        backends: Mapping[str, CompletionBackend],
        requested_backend: str,
        timeout_seconds: float,
    ) -> None:
        if "deterministic" not in backends:
            raise ValueError("deterministic backend is required")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._deterministic = deterministic
        self._backends = dict(backends)
        self.requested_backend = requested_backend
        self.timeout_seconds = timeout_seconds

    def complete(self, request: CompletionRequest) -> Completion:
        backend = self._backends.get(self.requested_backend)
        if backend is None:
            return self._fallback(request)
        if backend.name == "deterministic":
            result = backend.complete(request)
            return self._completion(result, backend="deterministic", fallback=False)
        try:
            result = _call_with_timeout(backend, request, self.timeout_seconds)
        except (BackendTimeout, BackendUnavailable):
            return self._fallback(request)
        return self._completion(result, backend=backend.name, fallback=False)

    def _fallback(self, request: CompletionRequest) -> Completion:
        result = self._deterministic.complete(request)
        return self._completion(result, backend="deterministic", fallback=True)

    def _completion(self, result: BackendResult, backend: str, fallback: bool) -> Completion:
        text = result.text if len(result.text) <= MAX_OUTPUT else result.text[:MAX_OUTPUT]
        rule_id = result.rule_id if _ID_RE.fullmatch(result.rule_id) else "unspecified"
        return Completion(
            text=text,
            backend=backend,
            fallback=fallback,
            rule_id=rule_id,
            requested_backend=self.requested_backend,
        )


def load_rule_table(path: Path) -> RuleTable:
    import json

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load rules from {path.name}") from exc
    if not isinstance(payload, dict) or set(payload) != _TOP_KEYS:
        raise ValueError("rules file must contain version, rules, and echo")
    if payload["version"] != 1:
        raise ValueError("unsupported rules version")
    echo = payload["echo"]
    if not isinstance(echo, dict) or set(echo) != _ECHO_KEYS:
        raise ValueError("echo must contain id and text")
    echo_id = _require_id(echo["id"], "echo id")
    echo_text = _require_template(echo["text"], "echo text")
    raw_rules = payload["rules"]
    if not isinstance(raw_rules, list) or not raw_rules or len(raw_rules) > MAX_RULES:
        raise ValueError("rules must be a non-empty list of at most 64 entries")
    rules: list[_Rule] = []
    seen: set[str] = {echo_id}
    for entry in raw_rules:
        rule = _parse_rule(entry)
        if rule.id in seen:
            raise ValueError(f"duplicate rule id {rule.id}")
        seen.add(rule.id)
        rules.append(rule)
    return RuleTable(rules=tuple(rules), echo_id=echo_id, echo_text=echo_text)


def build_engine(
    rules_path: Path,
    requested_backend: str = "deterministic",
    timeout_seconds: float = 2.0,
) -> Engine:
    """Build the process engine.

    Only the deterministic backend is registered. A later issue should
    register additional ``CompletionBackend`` objects in this function.
    """

    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", requested_backend):
        raise ValueError("requested backend name is invalid")
    table = load_rule_table(rules_path)
    deterministic = DeterministicBackend(table)
    backends: dict[str, CompletionBackend] = {deterministic.name: deterministic}
    return Engine(deterministic, backends, requested_backend, timeout_seconds)


def _parse_rule(entry: object) -> _Rule:
    if not isinstance(entry, dict) or set(entry) - _RULE_KEYS or set(entry) < {"id", "match_type", "match", "text"}:
        raise ValueError("each rule needs id, match_type, match, and text")
    rule_id = _require_id(entry["id"], "rule id")
    match_type = entry["match_type"]
    if match_type not in _MATCH_TYPES:
        raise ValueError(f"unsupported match_type on {rule_id}")
    match = entry["match"]
    if not isinstance(match, str) or not match.strip() or len(match) > MAX_MATCH:
        raise ValueError(f"invalid match on {rule_id}")
    if match_type == "exact":
        match = match.strip()
    text = _require_template(entry["text"], f"text for {rule_id}")
    lab = entry.get("lab")
    if lab is not None:
        lab = _require_id(lab, f"lab for {rule_id}")
    return _Rule(rule_id, match_type, match, text, lab)


def _require_id(value: object, label: str) -> str:
    if not isinstance(value, str) or _ID_RE.fullmatch(value) is None:
        raise ValueError(f"invalid {label}")
    return value


def _require_template(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_TEMPLATE:
        raise ValueError(f"invalid {label}")
    return value


def _matches(rule: _Rule, prompt: str) -> bool:
    if rule.match_type == "exact":
        return prompt.strip() == rule.match
    if rule.match_type == "prefix":
        return prompt.startswith(rule.match)
    return rule.match in prompt


def _render(template: str, prompt: str, lab: str | None) -> str:
    values = {
        "{lab}": lab or "unspecified",
        "{prompt_length}": str(len(prompt)),
        "{prompt_excerpt}": _excerpt(prompt),
    }
    parts: list[str] = []
    index = 0
    while index < len(template):
        token = next((item for item in _TOKENS if template.startswith(item, index)), None)
        if token is None:
            parts.append(template[index])
            index += 1
            continue
        parts.append(values[token])
        index += len(token)
    rendered = "".join(parts)
    return rendered if len(rendered) <= MAX_OUTPUT else rendered[:MAX_OUTPUT]


def _excerpt(prompt: str) -> str:
    chunk = prompt[:EXCERPT_CHARS]
    cleaned = "".join(ch if ch.isprintable() and ch not in "\r\n\t" else " " for ch in chunk).strip()
    return cleaned or "(empty)"


def _call_with_timeout(
    backend: CompletionBackend,
    request: CompletionRequest,
    timeout_seconds: float,
) -> BackendResult:
    """Bound a future model call.

    ``shutdown(wait=False)`` returns the HTTP response without joining a
    stuck worker. The deterministic backend never takes this path.
    A later model backend should still enforce its own deadline inside
    ``complete`` so the worker thread can exit.
    """

    pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mind-core-backend")
    future = pool.submit(backend.complete, request)
    try:
        result = future.result(timeout=timeout_seconds)
    except FuturesTimeoutError as exc:
        pool.shutdown(wait=False, cancel_futures=True)
        raise BackendTimeout() from exc
    except BackendUnavailable:
        pool.shutdown(wait=True, cancel_futures=True)
        raise
    except Exception as exc:
        pool.shutdown(wait=True, cancel_futures=True)
        raise BackendUnavailable() from exc
    pool.shutdown(wait=True)
    if not isinstance(result, BackendResult) or not isinstance(result.text, str):
        raise BackendUnavailable()
    return result


def default_rules_path() -> Path:
    return Path(__file__).resolve().parent.parent / "rules.json"
