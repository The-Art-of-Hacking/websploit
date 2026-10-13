#!/usr/bin/env python3
"""Fail if the default Compose footprint drifts.

With no profile, service names, static IPs, and published host ports must
match the checked-in golden files. mind-core, echo-chamber, oracle-booth,
and later AI labs stay behind the ``ai`` profile and must not appear in
that default set.

With ``--profile ai``, mind-core, echo-chamber, oracle-booth,
marionette, tainted-well, false-prophet, and token-famine must all be
present. Services beyond the default set are allowed when their Compose
profile includes ``ai``, their IPv4 on the ``websploit`` network is in
10.6.6.50–10.6.6.59, and every published host port is in 5030–5039.
Those services must not change a default service's name, IP, or host
port. mind-core, echo-chamber, oracle-booth, tainted-well,
false-prophet, and token-famine stay on ``websploit`` only.
echo-chamber, oracle-booth, marionette, tainted-well, false-prophet,
and token-famine depend on mind-core with ``condition: service_healthy``.
token-famine must not join ``websploit-isolated``.

marionette also attaches to ``websploit-isolated``. The golden IPv4 is
the ``websploit`` address. Every other service is rejected if it joins
``websploit-isolated``. The declaration must stay 10.7.7.0/24, gateway
10.7.7.1, internal: true.

``--synthetic`` checks that attachment from the Compose file and from
in-memory service maps. It does not run Docker.

Profile ``ai-model`` adds ``model-fetch`` and ``local-gguf``. Those
services stay out of the default stack and out of profile ``ai``.
They are allowed only when profile ``ai`` is enabled as well, because
they depend on ``mind-core``.
"""

from __future__ import annotations

import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / ".github" / "golden-stack"
MIND_CORE_ENDPOINT = "mind-core 10.6.6.50 5030:5030/tcp"
ECHO_CHAMBER_ENDPOINT = "echo-chamber 10.6.6.54 5034:5034/tcp"
ORACLE_BOOTH_ENDPOINT = "oracle-booth 10.6.6.51 5031:5031/tcp"
MARIONETTE_ENDPOINT = "marionette 10.6.6.52 5032:5032/tcp"
TAINTED_WELL_ENDPOINT = "tainted-well 10.6.6.53 5033:5033/tcp"
FALSE_PROPHET_ENDPOINT = "false-prophet 10.6.6.55 5035:5035/tcp"
TOKEN_FAMINE_ENDPOINT = "token-famine 10.6.6.56 5036:5036/tcp"
LLAMA_IMAGE = (
    "ghcr.io/ggml-org/llama.cpp:server"
    "@sha256:c789283572ba78c2699b8945a96e654c850f938a717883f2e6187a14adac698f"
)
LOCAL_GGUF_ADDRESS = "10.6.6.57"
MODEL_FETCH_ADDRESS = "10.6.6.58"
LOCAL_GGUF_MEMORY = 1536 * 1024 * 1024
MODEL_FETCH_MEMORY = 256 * 1024 * 1024
MODEL_SERVICES = ("local-gguf", "model-fetch")
MARIONETTE_ISOLATED_IP = "10.7.7.52"
ISOLATED_GATEWAY = "10.7.7.1"
AI_PORT_MIN = 5030
AI_PORT_MAX = 5039


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--synthetic":
        return synthetic_check()
    if len(sys.argv) != 1:
        raise SystemExit("usage: check_golden_stack.py [--synthetic]")
    require_ai_model_source()
    default = compose_config(None)
    profiled = compose_config("ai")
    compare("services", service_names(default), read_lines(GOLDEN / "services.txt"))
    compare("endpoints", endpoints(default), read_lines(GOLDEN / "endpoints.txt"))
    assert_default_has_no_ai_track(default)
    require_ai_additions(default, profiled)
    require_isolated_source()
    require_isolated(default)
    require_isolated(profiled)
    assert_model_absent(profiled)
    modeled = compose_config(["ai", "ai-model"])
    require_isolated(modeled)
    require_model_tier(default, profiled, modeled)
    require_model_profile_needs_ai()
    print("golden stack ok")
    return 0


def compose_config(profile: str | list[str] | None) -> dict:
    # --all-resources keeps websploit-isolated visible. Compose otherwise
    # drops networks that no enabled service references.
    # --profile is a global flag and must come before the subcommand.
    profiles = _profile_list(profile)
    completed = _run_compose(profiles, all_resources=True)
    if completed.returncode != 0 and _missing_all_resources(completed.stderr):
        completed = _run_compose(profiles, all_resources=False)
    if completed.returncode != 0:
        sys.stderr.write(completed.stderr)
        raise SystemExit(f"docker compose config failed ({completed.returncode})")
    return json.loads(completed.stdout)


def _profile_list(profile: str | list[str] | None) -> list[str]:
    if profile is None:
        return []
    if isinstance(profile, str):
        return [profile]
    return list(profile)


def _run_compose(profiles: list[str], all_resources: bool) -> subprocess.CompletedProcess[str]:
    command = ["docker", "compose"]
    for name in profiles:
        command.extend(["--profile", name])
    if all_resources:
        command.append("--all-resources")
    command.extend(["config", "--format", "json"])
    return subprocess.run(command, cwd=ROOT, check=False, capture_output=True, text=True)


def _missing_all_resources(stderr: str) -> bool:
    lowered = stderr.lower()
    return "all-resources" in lowered and "unknown flag" in lowered


def service_names(config: dict) -> list[str]:
    return sorted(config.get("services", {}))


def endpoints(config: dict, only: set[str] | None = None) -> list[str]:
    lines: list[str] = []
    services = config.get("services") or {}
    selected = sorted(services if only is None else only)
    for name in selected:
        service = services.get(name)
        if not isinstance(service, dict):
            continue
        address = websploit_ipv4(name, service)
        ports = service.get("ports") or []
        if not ports:
            lines.append(f"{name} {address} -")
            continue
        for port in ports:
            lines.append(f"{name} {address} {normalize_port(port)}")
    return sorted(lines)


def websploit_ipv4(name: str, service: dict) -> str:
    """Return the static address on the websploit bridge.

    A service may also be attached to websploit-isolated. The golden
    address is the websploit one, not whichever attachment happens to
    be the only one.
    """

    networks = service.get("networks") or {}
    if not isinstance(networks, dict):
        raise SystemExit(f"{name} is missing a static ipv4_address on websploit")
    attachment = networks.get("websploit")
    if not isinstance(attachment, dict):
        raise SystemExit(f"{name} is missing a static ipv4_address on websploit")
    address = attachment.get("ipv4_address")
    if not address:
        raise SystemExit(f"{name} is missing a static ipv4_address on websploit")
    return str(address)


def normalize_port(port: object) -> str:
    if isinstance(port, str):
        text = port.strip()
        if "/" not in text:
            text = f"{text}/tcp"
        return text
    if not isinstance(port, dict):
        raise SystemExit(f"unrecognized port entry: {port!r}")
    published = port.get("published")
    target = port.get("target")
    protocol = port.get("protocol") or "tcp"
    if published is None or target is None:
        raise SystemExit(f"unrecognized port entry: {port!r}")
    return f"{published}:{target}/{protocol}"


def assert_default_has_no_ai_track(config: dict) -> None:
    services = config.get("services") or {}
    for name in (
        "mind-core",
        "echo-chamber",
        "oracle-booth",
        "marionette",
        "tainted-well",
        "false-prophet",
        "token-famine",
        "local-gguf",
        "model-fetch",
    ):
        if name in services:
            raise SystemExit(f"{name} is part of the default stack; it must stay behind the ai profile")
    for line in endpoints(config):
        name, address, port = line.split(" ", 2)
        if _ai_address(address):
            raise SystemExit(f"{name} uses AI-track address {address} without the ai profile")
        if port != "-" and _host_port(port) in _ai_ports():
            raise SystemExit(f"{name} publishes an AI-track host port without the ai profile")


def require_ai_additions(default: dict, profiled: dict) -> None:
    default_names = set(service_names(default))
    profiled_names = set(service_names(profiled))
    missing = sorted(default_names - profiled_names)
    if missing:
        raise SystemExit(f"profile ai dropped default services: {missing}")
    compare(
        "default endpoints with profile ai",
        endpoints(profiled, default_names),
        endpoints(default),
        "profile ai changed a default service name, IP, or host port",
    )
    _reject_isolated(default, default_names, "default services stay on websploit")
    _reject_isolated(profiled, default_names, "default services stay on websploit")

    extras = sorted(profiled_names - default_names)
    required_ai = (
        "mind-core",
        "echo-chamber",
        "oracle-booth",
        "marionette",
        "tainted-well",
        "false-prophet",
        "token-famine",
    )
    missing_ai = [name for name in required_ai if name not in extras]
    if missing_ai:
        raise SystemExit(
            "profile ai must include mind-core, echo-chamber, oracle-booth, marionette, tainted-well, "
            f"false-prophet, and token-famine; missing {missing_ai}"
        )

    used_addresses: dict[str, str] = {}
    used_ports: dict[int, str] = {}
    for line in endpoints(default):
        name, address, port = line.split(" ", 2)
        used_addresses[address] = name
        if port != "-":
            used_ports[_host_port(port)] = name

    for name in extras:
        service = profiled["services"][name]
        if "ai" not in _profiles(name, service):
            raise SystemExit(
                f"{name} is enabled with --profile ai but its Compose profile does not include ai"
            )
        address = websploit_ipv4(name, service)
        if not _ai_address(address):
            raise SystemExit(f"{name} websploit address {address} is outside 10.6.6.50-10.6.6.59")
        owner = used_addresses.get(address)
        if owner is not None:
            raise SystemExit(f"{name} reuses websploit address {address} already used by {owner}")
        used_addresses[address] = name
        ports = service.get("ports") or []
        if not isinstance(ports, list):
            raise SystemExit(f"{name} has an unrecognized ports entry")
        for port in ports:
            host = _host_port(normalize_port(port))
            if host not in _ai_ports():
                raise SystemExit(f"{name} publishes host port {host}, outside 5030-5039")
            port_owner = used_ports.get(host)
            if port_owner is not None:
                raise SystemExit(f"{name} reuses host port {host} already used by {port_owner}")
            used_ports[host] = name

    mind = profiled["services"]["mind-core"]
    mind_lines = endpoints(profiled, {"mind-core"})
    if mind_lines != [MIND_CORE_ENDPOINT]:
        raise SystemExit(f"mind-core endpoint is {mind_lines}, expected {[MIND_CORE_ENDPOINT]}")
    require_limits(mind, "mind-core")
    _require_websploit_only(mind, "mind-core")

    chamber = profiled["services"]["echo-chamber"]
    chamber_lines = endpoints(profiled, {"echo-chamber"})
    if chamber_lines != [ECHO_CHAMBER_ENDPOINT]:
        raise SystemExit(f"echo-chamber endpoint is {chamber_lines}, expected {[ECHO_CHAMBER_ENDPOINT]}")
    require_limits(chamber, "echo-chamber")
    _require_websploit_only(chamber, "echo-chamber")
    require_healthy_dependency(chamber, "echo-chamber", "mind-core")

    booth = profiled["services"]["oracle-booth"]
    booth_lines = endpoints(profiled, {"oracle-booth"})
    if booth_lines != [ORACLE_BOOTH_ENDPOINT]:
        raise SystemExit(f"oracle-booth endpoint is {booth_lines}, expected {[ORACLE_BOOTH_ENDPOINT]}")
    require_limits(booth, "oracle-booth")
    _require_websploit_only(booth, "oracle-booth")
    require_healthy_dependency(booth, "oracle-booth", "mind-core")

    puppet = profiled["services"]["marionette"]
    puppet_lines = endpoints(profiled, {"marionette"})
    if puppet_lines != [MARIONETTE_ENDPOINT]:
        raise SystemExit(f"marionette endpoint is {puppet_lines}, expected {[MARIONETTE_ENDPOINT]}")
    require_limits(puppet, "marionette")
    require_marionette_networks(puppet)
    require_healthy_dependency(puppet, "marionette", "mind-core")

    well = profiled["services"]["tainted-well"]
    well_lines = endpoints(profiled, {"tainted-well"})
    if well_lines != [TAINTED_WELL_ENDPOINT]:
        raise SystemExit(f"tainted-well endpoint is {well_lines}, expected {[TAINTED_WELL_ENDPOINT]}")
    require_limits(well, "tainted-well")
    _require_websploit_only(well, "tainted-well")
    require_healthy_dependency(well, "tainted-well", "mind-core")

    prophet = profiled["services"]["false-prophet"]
    prophet_lines = endpoints(profiled, {"false-prophet"})
    if prophet_lines != [FALSE_PROPHET_ENDPOINT]:
        raise SystemExit(f"false-prophet endpoint is {prophet_lines}, expected {[FALSE_PROPHET_ENDPOINT]}")
    require_limits(prophet, "false-prophet")
    _require_websploit_only(prophet, "false-prophet")
    require_healthy_dependency(prophet, "false-prophet", "mind-core")

    famine = profiled["services"]["token-famine"]
    famine_lines = endpoints(profiled, {"token-famine"})
    if famine_lines != [TOKEN_FAMINE_ENDPOINT]:
        raise SystemExit(f"token-famine endpoint is {famine_lines}, expected {[TOKEN_FAMINE_ENDPOINT]}")
    require_limits(famine, "token-famine")
    _require_websploit_only(famine, "token-famine")
    require_healthy_dependency(famine, "token-famine", "mind-core")
    if famine.get("pids_limit") != 64:
        raise SystemExit(f"token-famine pids_limit is {famine.get('pids_limit')}, expected 64")
    assert_isolated_attachments(default.get("services") or {})
    assert_isolated_attachments(profiled.get("services") or {})


def assert_model_absent(config: dict) -> None:
    services = config.get("services") or {}
    present = [name for name in MODEL_SERVICES if name in services]
    if present:
        raise SystemExit(f"{present} must stay behind profile ai-model")


def require_model_tier(default: dict, profiled: dict, modeled: dict) -> None:
    """Allow the GGUF services only in the combined ai,ai-model config."""

    profiled_names = set(service_names(profiled))
    modeled_names = set(service_names(modeled))
    if not profiled_names <= modeled_names:
        missing = sorted(profiled_names - modeled_names)
        raise SystemExit(f"profile ai,ai-model dropped services: {missing}")
    added = sorted(modeled_names - profiled_names)
    if added != sorted(MODEL_SERVICES):
        raise SystemExit(f"profile ai-model added {added}, expected {list(MODEL_SERVICES)}")
    compare(
        "ai endpoints with ai-model",
        endpoints(modeled, profiled_names),
        endpoints(profiled),
        "profile ai-model changed an ai-profile service name, IP, or host port",
    )
    compare(
        "default endpoints with ai and ai-model",
        endpoints(modeled, set(service_names(default))),
        endpoints(default),
        "profile ai-model changed a default service name, IP, or host port",
    )
    assert_isolated_attachments(modeled.get("services") or {})
    services = modeled["services"]
    seen_addresses: dict[str, str] = {}
    for name in sorted(services):
        service = services[name]
        if not isinstance(service, dict):
            continue
        networks = service.get("networks") or {}
        if not isinstance(networks, dict) or "websploit" not in networks:
            continue
        address = websploit_ipv4(name, service)
        owner = seen_addresses.get(address)
        if owner is not None:
            raise SystemExit(f"{name} reuses websploit address {address} already used by {owner}")
        seen_addresses[address] = name
    _require_model_service(
        services["local-gguf"],
        "local-gguf",
        LOCAL_GGUF_ADDRESS,
        LOCAL_GGUF_MEMORY,
        1.5,
    )
    fetch = services["model-fetch"]
    _require_model_service(fetch, "model-fetch", MODEL_FETCH_ADDRESS, MODEL_FETCH_MEMORY, 0.5)
    llama = services["local-gguf"]
    if llama.get("image") != LLAMA_IMAGE:
        raise SystemExit(f"local-gguf image is {llama.get('image')}, expected the pinned digest")
    health = llama.get("healthcheck") or {}
    rendered = health.get("test")
    text = " ".join(rendered) if isinstance(rendered, list) else str(rendered)
    if "8080/health" not in text:
        raise SystemExit("local-gguf healthcheck must call /health on port 8080")
    require_dependency(llama, "local-gguf", "mind-core", "service_healthy")
    require_dependency(llama, "local-gguf", "model-fetch", "service_completed_successfully")
    require_dependency(fetch, "model-fetch", "mind-core", "service_healthy")
    build = fetch.get("build")
    dockerfile = build.get("dockerfile") if isinstance(build, dict) else ""
    if dockerfile != "fetch.Dockerfile":
        raise SystemExit(f"model-fetch dockerfile is {dockerfile!r}")


def _require_model_service(service: dict, name: str, address: str, memory: int, cpus: float) -> None:
    if _profiles_from_source(name) != ["ai-model"]:
        raise SystemExit(f"{name} profile is {_profiles_from_source(name)}, expected ['ai-model']")
    _require_websploit_only(service, name)
    actual = websploit_ipv4(name, service)
    if actual != address:
        raise SystemExit(f"{name} websploit address is {actual}, expected {address}")
    if service.get("ports"):
        raise SystemExit(f"{name} must not publish a host port")
    limit = memory_limit_bytes(service)
    if limit != memory:
        raise SystemExit(f"{name} mem_limit is {limit}, expected {memory}")
    cpu = cpu_limit(service)
    if cpu is None or abs(cpu - cpus) > 0.001:
        raise SystemExit(f"{name} cpus is {cpu}, expected {cpus}")


def require_dependency(service: dict, name: str, dependency: str, condition: str) -> None:
    depends = service.get("depends_on") or {}
    spec = depends.get(dependency) if isinstance(depends, dict) else None
    actual = spec.get("condition") if isinstance(spec, dict) else None
    if actual != condition:
        raise SystemExit(f"{name} must depend on {dependency} with condition {condition}")


def require_model_profile_needs_ai() -> None:
    """``--profile ai-model`` alone must not render the model tier."""

    completed = _run_compose(["ai-model"], all_resources=True)
    if completed.returncode != 0 and _missing_all_resources(completed.stderr):
        completed = _run_compose(["ai-model"], all_resources=False)
    if completed.returncode == 0:
        raise SystemExit("profile ai-model rendered without profile ai")
    if "mind-core" not in completed.stderr:
        sys.stderr.write(completed.stderr)
        raise SystemExit("profile ai-model failed without requiring mind-core")


def require_ai_model_source() -> None:
    """Check the model tier from the Compose file. Docker is not required."""

    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    if LLAMA_IMAGE not in text:
        raise SystemExit("local-gguf image is not digest-pinned")
    if f"ipv4_address: {LOCAL_GGUF_ADDRESS}" not in text:
        raise SystemExit("local-gguf address missing")
    if f"ipv4_address: {MODEL_FETCH_ADDRESS}" not in text:
        raise SystemExit("model-fetch address missing")
    if text.count('profiles: ["ai-model"]') != 2:
        raise SystemExit("profile ai-model must be set only on local-gguf and model-fetch")
    if "MIND_CORE_EXTERNAL_API_KEY" in text:
        raise SystemExit("compose file must not reference an external API key")
    if "qwen2.5-0.5b-instruct-q4_k_m.gguf" not in text:
        raise SystemExit("pinned GGUF filename missing from compose")
    if "gguf-cache:" not in text:
        raise SystemExit("gguf cache volume missing")
    for name in MODEL_SERVICES:
        block = _service_block(name)
        if "websploit-isolated" in block or "\n    ports:" in block:
            raise SystemExit(f"{name} must stay on websploit and must not publish a host port")
    mind = _service_block("mind-core")
    if 'profiles: ["ai"]' not in mind or "ai-model" in mind:
        raise SystemExit("mind-core must stay on profile ai only")
    if "${MIND_CORE_BACKEND:-auto}" not in mind or "http://local-gguf:8080" not in mind:
        raise SystemExit("mind-core must select the local server only when it is healthy")


def _service_block(name: str) -> str:
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if line == f"  {name}:"), None)
    if start is None:
        raise SystemExit(f"{name} is not declared in docker-compose.yml")
    block = [lines[start]]
    for line in lines[start + 1 :]:
        if line.startswith("  ") and not line.startswith("   ") and not line.startswith("  #"):
            break
        if line and not line.startswith((" ", "#")):
            break
        block.append(line)
    return "\n".join(block)


def require_marionette_networks(service: dict) -> None:
    """marionette joins both bridges. The isolated address is not the gateway."""

    networks = service.get("networks") or {}
    if not isinstance(networks, dict):
        raise SystemExit("marionette networks are not a mapping")
    names = sorted(networks)
    if names != ["websploit", "websploit-isolated"]:
        raise SystemExit(
            f"marionette networks are {names}; it must join websploit and websploit-isolated"
        )
    isolated = networks["websploit-isolated"]
    address = isolated.get("ipv4_address") if isinstance(isolated, dict) else None
    if address != MARIONETTE_ISOLATED_IP:
        raise SystemExit(f"marionette isolated address is {address}, expected {MARIONETTE_ISOLATED_IP}")
    if address in {ISOLATED_GATEWAY, "10.7.7.0", "10.7.7.255"}:
        raise SystemExit("marionette isolated address collides with the gateway or network address")
    websploit = networks["websploit"]
    websploit_address = websploit.get("ipv4_address") if isinstance(websploit, dict) else None
    if websploit_address != "10.6.6.52":
        raise SystemExit(f"marionette websploit address is {websploit_address}, expected 10.6.6.52")


def assert_isolated_attachments(services: dict) -> None:
    """Reject every service except marionette on websploit-isolated."""

    for name in sorted(services):
        service = services.get(name) or {}
        if not isinstance(service, dict):
            continue
        networks = service.get("networks") or {}
        if isinstance(networks, dict):
            attached = "websploit-isolated" in networks
        elif isinstance(networks, list):
            attached = "websploit-isolated" in networks
        else:
            attached = False
        if not attached:
            continue
        if name != "marionette":
            raise SystemExit(f"{name} joined websploit-isolated; only marionette may attach")
        require_marionette_networks(service)


def synthetic_check() -> int:
    """Validate the isolated attachment without Docker."""

    require_isolated_source()
    require_ai_model_source()
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    attachments = text.count("\n      websploit-isolated:\n")
    if attachments != 1:
        raise SystemExit(f"websploit-isolated service attachments: {attachments}, expected 1")
    if f"ipv4_address: {MARIONETTE_ISOLATED_IP}" not in text:
        raise SystemExit("marionette isolated address missing")
    if "ipv4_address: 10.6.6.52" not in text:
        raise SystemExit("marionette websploit address missing")
    if "ipv4_address: 10.6.6.53" not in text:
        raise SystemExit("tainted-well websploit address missing")
    if "ipv4_address: 10.6.6.55" not in text:
        raise SystemExit("false-prophet websploit address missing")
    if "ipv4_address: 10.6.6.56" not in text:
        raise SystemExit("token-famine websploit address missing")
    if text.count("10.7.7.1") != 1:
        raise SystemExit("websploit-isolated gateway must appear once and not as a service address")
    if f"ipv4_address: {ISOLATED_GATEWAY}" in text:
        raise SystemExit("isolated gateway is assigned to a service")
    good = {
        "marionette": {
            "networks": {
                "websploit": {"ipv4_address": "10.6.6.52"},
                "websploit-isolated": {"ipv4_address": MARIONETTE_ISOLATED_IP},
            }
        },
        "oracle-booth": {"networks": {"websploit": {"ipv4_address": "10.6.6.51"}}},
        "tainted-well": {"networks": {"websploit": {"ipv4_address": "10.6.6.53"}}},
        "false-prophet": {"networks": {"websploit": {"ipv4_address": "10.6.6.55"}}},
        "token-famine": {"networks": {"websploit": {"ipv4_address": "10.6.6.56"}}},
    }
    assert_isolated_attachments(good)
    require_marionette_networks(good["marionette"])
    bad = {
        "marionette": good["marionette"],
        "tainted-well": {
            "networks": {
                "websploit": {"ipv4_address": "10.6.6.53"},
                "websploit-isolated": {"ipv4_address": "10.7.7.53"},
            }
        },
    }
    try:
        assert_isolated_attachments(bad)
    except SystemExit as exc:
        if "tainted-well" not in str(exc):
            raise
    else:
        raise SystemExit("non-marionette isolated attachment was accepted")
    bad_prophet = {
        "marionette": good["marionette"],
        "false-prophet": {
            "networks": {
                "websploit": {"ipv4_address": "10.6.6.55"},
                "websploit-isolated": {"ipv4_address": "10.7.7.55"},
            }
        },
    }
    try:
        assert_isolated_attachments(bad_prophet)
    except SystemExit as exc:
        if "false-prophet" not in str(exc):
            raise
    else:
        raise SystemExit("false-prophet isolated attachment was accepted")
    bad_famine = {
        "marionette": good["marionette"],
        "token-famine": {
            "networks": {
                "websploit": {"ipv4_address": "10.6.6.56"},
                "websploit-isolated": {"ipv4_address": "10.7.7.56"},
            }
        },
    }
    try:
        assert_isolated_attachments(bad_famine)
    except SystemExit as exc:
        if "token-famine" not in str(exc):
            raise
    else:
        raise SystemExit("token-famine isolated attachment was accepted")
    bad_model = {
        "marionette": good["marionette"],
        "local-gguf": {
            "networks": {
                "websploit": {"ipv4_address": LOCAL_GGUF_ADDRESS},
                "websploit-isolated": {"ipv4_address": "10.7.7.57"},
            }
        },
    }
    try:
        assert_isolated_attachments(bad_model)
    except SystemExit as exc:
        if "local-gguf" not in str(exc):
            raise
    else:
        raise SystemExit("local-gguf isolated attachment was accepted")
    print("synthetic golden stack ok")
    return 0


def _reject_isolated(config: dict, names: set[str], reason: str) -> None:
    services = config.get("services") or {}
    for name in sorted(names):
        service = services.get(name) or {}
        networks = service.get("networks") or {}
        if isinstance(networks, dict) and "websploit-isolated" in networks:
            raise SystemExit(f"{name} joined websploit-isolated; {reason}")


def _profiles(name: str, service: dict) -> list[str]:
    raw = service.get("profiles")
    if isinstance(raw, str) and raw:
        return [raw]
    if isinstance(raw, list) and raw and all(isinstance(item, str) and item for item in raw):
        return list(raw)
    return _profiles_from_source(name)


def _profiles_from_source(name: str) -> list[str]:
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if line == f"  {name}:"), None)
    if start is None:
        raise SystemExit(f"{name} is not declared in docker-compose.yml")
    block: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("  ") and not line.startswith("   ") and not line.startswith("  #"):
            break
        if line and not line.startswith((" ", "#")):
            break
        block.append(line)
    for index, line in enumerate(block):
        inline = re.fullmatch(r"    profiles:\s*\[(.*)]\s*", line)
        if inline:
            return [item.strip().strip("\"'") for item in inline.group(1).split(",") if item.strip()]
        if re.fullmatch(r"    profiles:\s*", line):
            found: list[str] = []
            for follower in block[index + 1 :]:
                match = re.fullmatch(r"      - [\"']?([A-Za-z0-9_.-]+)[\"']?", follower)
                if match is None:
                    break
                found.append(match.group(1))
            return found
    return []


def _ai_address(address: str) -> bool:
    parts = address.split(".")
    if len(parts) != 4 or parts[:3] != ["10", "6", "6"]:
        return False
    last = parts[3]
    if not last.isdigit() or (len(last) > 1 and last.startswith("0")):
        return False
    return 50 <= int(last) <= 59


def _ai_ports() -> range:
    return range(AI_PORT_MIN, AI_PORT_MAX + 1)


def _host_port(rendered: str) -> int:
    host = rendered.split(":", 1)[0]
    if not host.isdigit():
        raise SystemExit(f"unrecognized published port {rendered}")
    return int(host)


def _require_websploit_only(service: dict, name: str) -> None:
    networks = sorted((service.get("networks") or {}))
    if networks != ["websploit"]:
        raise SystemExit(f"{name} networks are {networks}; it must stay on websploit only")


def require_healthy_dependency(service: dict, name: str, dependency: str) -> None:
    depends = service.get("depends_on") or {}
    spec = depends.get(dependency) if isinstance(depends, dict) else None
    condition = spec.get("condition") if isinstance(spec, dict) else None
    if condition != "service_healthy":
        raise SystemExit(f"{name} must depend on {dependency} with condition service_healthy")


def require_limits(service: dict, name: str) -> None:
    memory = memory_limit_bytes(service)
    cpus = cpu_limit(service)
    if memory != 128 * 1024 * 1024:
        raise SystemExit(f"{name} mem_limit is {memory}, expected 134217728")
    if cpus is None or abs(cpus - 0.5) > 0.001:
        raise SystemExit(f"{name} cpus is {cpus}, expected 0.5")


def memory_limit_bytes(service: dict) -> int | None:
    if "mem_limit" in service:
        return parse_memory(service["mem_limit"])
    limits = ((service.get("deploy") or {}).get("resources") or {}).get("limits") or {}
    if "memory" in limits:
        return parse_memory(limits["memory"])
    return None


def cpu_limit(service: dict) -> float | None:
    if "cpus" in service:
        return float(service["cpus"])
    limits = ((service.get("deploy") or {}).get("resources") or {}).get("limits") or {}
    if "cpus" in limits:
        return float(limits["cpus"])
    return None


def parse_memory(value: object) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().lower()
    if text.endswith("mb"):
        return int(float(text[:-2]) * 1024 * 1024)
    if text.endswith("m"):
        return int(float(text[:-1]) * 1024 * 1024)
    return int(text)


ISOLATED_BLOCK = """\
  websploit-isolated:
    driver: bridge
    internal: true
    ipam:
      config:
        - subnet: 10.7.7.0/24
          gateway: 10.7.7.1
"""


def require_isolated_source() -> None:
    """Require the websploit-isolated declaration in docker-compose.yml.

    A service may name that network. Compose still creates the bridge
    only after a service attaches, unless ``--all-resources`` is set.
    """

    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    require_isolated_text(text)


def require_isolated_text(text: str) -> None:
    if ISOLATED_BLOCK not in text:
        raise SystemExit("docker-compose.yml is missing the websploit-isolated declaration")


def require_isolated(config: dict) -> None:
    network = config.get("networks", {}).get("websploit-isolated")
    if network is None:
        return
    if not isinstance(network, dict) or network.get("internal") is not True:
        raise SystemExit("websploit-isolated must be internal")
    configs = ((network.get("ipam") or {}).get("config") or [])
    subnets = {item.get("subnet"): item.get("gateway") for item in configs if isinstance(item, dict)}
    if "10.7.7.0/24" not in subnets:
        raise SystemExit(f"websploit-isolated subnet/gateway is {subnets}")
    gateway = subnets.get("10.7.7.0/24")
    if gateway not in (None, "10.7.7.1"):
        raise SystemExit(f"websploit-isolated gateway is {gateway}")


def read_lines(path: Path) -> list[str]:
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def compare(label: str, actual: list[str], expected: list[str], message: str | None = None) -> None:
    if actual == expected:
        return
    diff = difflib.unified_diff(
        [line + "\n" for line in expected],
        [line + "\n" for line in actual],
        fromfile=f"golden {label}",
        tofile=f"compose {label}",
    )
    sys.stderr.writelines(diff)
    raise SystemExit(message or f"default stack {label} drifted")


if __name__ == "__main__":
    raise SystemExit(main())
