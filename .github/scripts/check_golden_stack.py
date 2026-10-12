#!/usr/bin/env python3
"""Fail if the default Compose footprint drifts.

With no profile, service names, static IPs, and published host ports must
match the checked-in golden files. mind-core is allowed only with --profile ai.

The websploit-isolated network must exist and stay internal. No service
joins it in this issue. The marionette lab has to update this guard when
it attaches to that network.
"""

from __future__ import annotations

import difflib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / ".github" / "golden-stack"
MIND_CORE_ENDPOINT = "mind-core 10.6.6.50 5030:5030/tcp"


def main() -> int:
    default = compose_config(None)
    profiled = compose_config("ai")
    compare("services", service_names(default), read_lines(GOLDEN / "services.txt"))
    compare("endpoints", endpoints(default), read_lines(GOLDEN / "endpoints.txt"))
    if "mind-core" in default.get("services", {}):
        raise SystemExit("mind-core is part of the default stack; it must stay behind the ai profile")
    if "5030:5030/tcp" in "\n".join(endpoints(default)):
        raise SystemExit("host port 5030 is published without the ai profile")

    names = service_names(profiled)
    expected = service_names(default) + ["mind-core"]
    if names != sorted(expected):
        raise SystemExit("profile ai must add mind-core and keep every default service")
    mind_core_lines = [line for line in endpoints(profiled) if line.startswith("mind-core ")]
    if mind_core_lines != [MIND_CORE_ENDPOINT]:
        raise SystemExit(f"mind-core endpoint is {mind_core_lines}, expected {MIND_CORE_ENDPOINT}")
    require_limits(profiled["services"]["mind-core"])
    mind_core_networks = sorted((profiled["services"]["mind-core"].get("networks") or {}))
    if mind_core_networks != ["websploit"]:
        raise SystemExit(f"mind-core networks are {mind_core_networks}; it must stay on websploit only")
    require_isolated_source()
    require_isolated(default)
    require_isolated(profiled)
    require_unattached(default)
    require_unattached(profiled)
    print("golden stack ok")
    return 0


def compose_config(profile: str | None) -> dict:
    # --all-resources keeps websploit-isolated visible. Compose otherwise
    # drops networks that no enabled service references, and no service
    # joins that network until the marionette lab.
    # --profile is a global flag and must come before the subcommand.
    command = ["docker", "compose", "--all-resources", "config", "--format", "json"]
    if profile:
        command[2:2] = ["--profile", profile]
    completed = subprocess.run(command, cwd=ROOT, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        sys.stderr.write(completed.stderr)
        raise SystemExit(f"docker compose config failed ({completed.returncode})")
    return json.loads(completed.stdout)


def service_names(config: dict) -> list[str]:
    return sorted(config.get("services", {}))


def endpoints(config: dict) -> list[str]:
    lines: list[str] = []
    for name, service in config.get("services", {}).items():
        address = ipv4_address(name, service)
        ports = service.get("ports") or []
        if not ports:
            lines.append(f"{name} {address} -")
            continue
        for port in ports:
            lines.append(f"{name} {address} {normalize_port(port)}")
    return sorted(lines)


def ipv4_address(name: str, service: dict) -> str:
    networks = service.get("networks") or {}
    if not isinstance(networks, dict):
        raise SystemExit(f"{name} is missing a static ipv4_address")
    found = [
        cfg.get("ipv4_address")
        for cfg in networks.values()
        if isinstance(cfg, dict) and cfg.get("ipv4_address")
    ]
    if len(found) != 1:
        raise SystemExit(f"{name} should have one static ipv4_address, found {found}")
    return str(found[0])


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


def require_limits(service: dict) -> None:
    memory = memory_limit_bytes(service)
    cpus = cpu_limit(service)
    if memory != 128 * 1024 * 1024:
        raise SystemExit(f"mind-core mem_limit is {memory}, expected 134217728")
    if cpus is None or abs(cpus - 0.5) > 0.001:
        raise SystemExit(f"mind-core cpus is {cpus}, expected 0.5")


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
    """Compose omits a network from `config` until a service references it.

    The declaration in docker-compose.yml is still the contract. marionette
    has to attach before `docker compose up` will create the bridge.
    """

    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    if ISOLATED_BLOCK not in text:
        raise SystemExit("docker-compose.yml is missing the websploit-isolated declaration")
    for line in text.splitlines():
        if "websploit-isolated" not in line or line.strip().startswith("#"):
            continue
        if line.startswith("  websploit-isolated:"):
            continue
        raise SystemExit(f"unexpected websploit-isolated reference: {line}")


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


def require_unattached(config: dict) -> None:
    for name, service in config.get("services", {}).items():
        networks = service.get("networks") or {}
        if isinstance(networks, dict) and "websploit-isolated" in networks:
            raise SystemExit(f"{name} joined websploit-isolated; only a later marionette change should do that")


def read_lines(path: Path) -> list[str]:
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def compare(label: str, actual: list[str], expected: list[str]) -> None:
    if actual == expected:
        return
    diff = difflib.unified_diff(
        [line + "\n" for line in expected],
        [line + "\n" for line in actual],
        fromfile=f"golden {label}",
        tofile=f"compose {label}",
    )
    sys.stderr.writelines(diff)
    raise SystemExit(f"default stack {label} drifted")


if __name__ == "__main__":
    raise SystemExit(main())
