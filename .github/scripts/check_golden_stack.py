#!/usr/bin/env python3
"""Fail if the default Compose footprint drifts.

With no profile, service names, static IPs, and published host ports must
match the checked-in golden files. mind-core, echo-chamber, oracle-booth,
and later AI labs stay behind the ``ai`` profile and must not appear in
that default set.

With ``--profile ai``, mind-core, echo-chamber, oracle-booth, and marionette
must all be present. Services beyond the default set are allowed when their
Compose profile includes ``ai``, their IPv4 on the ``websploit`` network is
in 10.6.6.50–10.6.6.59, and every published host port is in 5030–5039.
Those services must not change a default service's name, IP, or host
port. mind-core, echo-chamber, and oracle-booth stay on ``websploit``
only. The labs depend on mind-core with ``condition: service_healthy``.

marionette is the only service allowed on ``websploit-isolated`` and must
join both networks. Its golden IPv4 is the ``websploit`` address. The
declaration must stay 10.7.7.0/24, gateway 10.7.7.1, internal: true.
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
REQUIRED_AI = ("mind-core", "echo-chamber", "oracle-booth", "marionette")
AI_PORT_MIN = 5030
AI_PORT_MAX = 5039


def main() -> int:
    default = compose_config(None)
    profiled = compose_config("ai")
    compare("services", service_names(default), read_lines(GOLDEN / "services.txt"))
    compare("endpoints", endpoints(default), read_lines(GOLDEN / "endpoints.txt"))
    assert_default_has_no_ai_track(default)
    require_ai_additions(default, profiled)
    require_isolated_source()
    require_isolated(default)
    require_isolated(profiled)
    print("golden stack ok")
    return 0


def compose_config(profile: str | None) -> dict:
    # --all-resources keeps websploit-isolated visible. Compose otherwise
    # drops networks that no enabled service references.
    # --profile is a global flag and must come before the subcommand.
    completed = _run_compose(profile, all_resources=True)
    if completed.returncode != 0 and _missing_all_resources(completed.stderr):
        completed = _run_compose(profile, all_resources=False)
    if completed.returncode != 0:
        sys.stderr.write(completed.stderr)
        raise SystemExit(f"docker compose config failed ({completed.returncode})")
    return json.loads(completed.stdout)


def _run_compose(profile: str | None, all_resources: bool) -> subprocess.CompletedProcess[str]:
    command = ["docker", "compose"]
    if profile:
        command.extend(["--profile", profile])
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
    for name in REQUIRED_AI:
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
    missing_ai = [name for name in REQUIRED_AI if name not in extras]
    if missing_ai:
        raise SystemExit(f"profile ai must include {', '.join(REQUIRED_AI)}; missing {missing_ai}")
    _reject_isolated(profiled, profiled_names - {"marionette"}, "only marionette may join it")

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
    puppet_networks = sorted(puppet.get("networks") or {})
    if puppet_networks != ["websploit", "websploit-isolated"]:
        raise SystemExit(f"marionette networks are {puppet_networks}; it must join websploit and websploit-isolated")
    require_healthy_dependency(puppet, "marionette", "mind-core")


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
