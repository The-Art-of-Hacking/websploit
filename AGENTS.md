# AGENTS.md

Guidance for AI coding agents working in this repository.

## What this repo is

WebSploit Labs is an **intentionally vulnerable** training environment by Omar Santos. It bundles classic OWASP apps (WebGoat, Juice Shop, DVWA), several CTF challenges, and a set of custom Flask-based labs that each demonstrate a specific web vulnerability class. Everything is orchestrated via Docker Compose on a bridge network (`10.6.6.0/24`). An opt-in AI track lives behind the Compose profile `ai`. `mind-core` listens on that bridge. A second, internal network (`websploit-isolated`, `10.7.7.0/24`) has no route to the internet. `marionette` is the only container attached to it.

The intended deployment target is a Kali or Parrot VM (see `Vagrantfile` and `install.sh`). The host running these containers is expected to be isolated.

## Critical rule: this code is intentionally vulnerable

The custom labs under `additional-labs/` contain **deliberate vulnerabilities** (SQLi, XSS, SSRF, XXE, command injection, path traversal, SSTI, insecure deserialization, JWT flaws, prototype pollution, GraphQL introspection/IDOR, etc.). These vulnerabilities are the product. Do not "fix" them.

When working in this repo:

- **Do not remove or harden the intentional vulnerabilities** in any lab application code (the Python/JS/HTML inside `additional-labs/<lab>/`). The educational value depends on them being exploitable.
- **Do not** add input sanitization, parameterized queries, output encoding, secure XML parsing, JWT signature verification, etc. to the lab apps unless the user explicitly asks you to add a "secure mode" or a separate hardened endpoint.
- The workspace-level `codeguard-*` security rules describe best practices that **apply to tooling, infrastructure, CI, and any non-vulnerable code** (e.g., `install.sh`, `docker-compose.yml`, helper scripts, READMEs). Treat the lab application source files as out of scope for those rules unless the user says otherwise.
- If you spot a vulnerability in a lab and are unsure whether it is intentional, ask before changing it. Default assumption: it is intentional.
- Hardcoded weak credentials, default secrets, and insecure crypto inside lab apps are intentional teaching artifacts. The "no hardcoded credentials" rule still applies to anything outside the lab apps (install scripts, compose files, infra, READMEs).
- `agentic-ai-labs/mind-core/` is shared infrastructure for the opt-in AI track. Keep it non-vulnerable: non-root, no intentional injection sinks, no hardcoded credentials, no certificates, and no weak cryptography. Later lab apps under `agentic-ai-labs/<lab>/` (everything except `mind-core`) are intentionally vulnerable once they exist; do not "fix" those either.

What you **should** improve when asked:

- `install.sh`, `containers.sh`, `vulnhub.sh`, `Vagrantfile`, `docker-compose.yml`, top-level `README.md`, lab `README.md` files (instructions, exercises, hints).
- Dockerfile hygiene (pinned base images, non-root users, healthchecks) **as long as** the vulnerabilities the lab is built around remain exploitable from outside the container.
- New labs, new exercises, new walkthroughs, fixing typos, improving documentation.

## Repo layout

```
websploit/
├── README.md                       # Top-level overview, container table, network diagram
├── docker-compose.yml              # Single source of truth for all containers + the websploit network
├── install.sh                      # Kali/Parrot installer (root); installs tools + brings up compose
├── containers.sh                   # Helper to print container info on the host
├── vulnhub.sh                      # Helper for VulnHub-style targets
├── Vagrantfile                     # Kali VM that curls install.sh from websploit.org
├── pyproject.toml / uv.lock        # Top-level Python project metadata (mostly placeholder; flask dep)
├── main.py                         # Placeholder entry point ("Hello from websploit!")
├── .python-version                 # pinned Python for uv
├── websploit-containers.drawio     # Network diagram source
├── additional-labs/                # Custom Flask labs, each built by docker-compose
    ├── README.md                   # Directory-name → container-name → vuln type mapping
    ├── Command_Injection/          → shell-inject       (10.6.6.34, host port 5002)
    ├── deserial-gate/              → deserial-gate      (10.6.6.42, host port 5022)
    ├── GraphQL/                    → graphql-galaxy     (10.6.6.44, host port 5023)
    ├── Multi-Vulnerability-Gauntlet/ → hydra-nexus      (10.6.6.30, host port 5010)
    ├── Path_Traversal/             → maze-walker        (10.6.6.35, host port 5003)
    ├── Prototype_Pollution/        → proto-pollute      (10.6.6.45, host port 5004)
    ├── render-reign/               → render-reign       (10.6.6.41, host port 5021)  # SSTI
    ├── SQLi/                       → sqli-breach        (10.6.6.33, host port 5001)
    ├── SSRF/                       → trojan-relay       (10.6.6.32, host port 5012)
    ├── token-tower/                → token-tower        (10.6.6.40, host port 5020)  # JWT
    ├── XSS/                        → phantom-script     (10.6.6.31, host port 5011)
    └── XXE/                        → entity-smuggler    (10.6.6.36, host port 5013)
└── agentic-ai-labs/              # Opt-in AI track (Compose profile `ai`)
    ├── README.md                 # Track overview, reserved addresses, opt-in command
    ├── mind-core/                → mind-core          (10.6.6.50, host port 5030)
    ├── oracle-booth/             → oracle-booth       (10.6.6.51, host port 5031)
    ├── marionette/               → marionette         (10.6.6.52, host port 5032; isolated 10.7.7.52)
    ├── tainted-well/             → tainted-well       (10.6.6.53, host port 5033)
    └── echo-chamber/             → echo-chamber       (10.6.6.54, host port 5034)
```

OWASP/classic apps and CTFs (`webgoat`, `juice-shop`, `dvwa`, `galactic-archives`, `gravemind`, `y-wing`, `redis-rogue`) are **pulled as prebuilt images** (mostly under `santosomar/*` on Docker Hub) and have no source in this repo.

## Container conventions

- Network: every service joins the `websploit` bridge network with subnet `10.6.6.0/24`, gateway `10.6.6.1`, and a static `ipv4_address`.
- Naming: each service sets an explicit `container_name` (the codename, e.g., `phantom-script`).
- Restart policy: `restart: unless-stopped`.
- Custom labs use `build: ./additional-labs/<dir>` and expose ports on the host.
- Prebuilt amd64 images set `platform: linux/amd64` (important for Apple Silicon hosts).
- Host port → container port mapping is intentional and documented in `README.md`. Do not change a port without also updating the top-level README, the track README (`additional-labs/README.md` or `agentic-ai-labs/README.md`), and the lab's own README.
- AI-track services set `profiles: ["ai"]` so a plain `docker compose up` leaves them off. `docker compose --profile ai up -d --build` starts the classic stack and the AI services. Naming the service (`docker compose --profile ai up -d --build mind-core`) starts the backend alone.
- `mind-core` stays on `websploit` only. `http://mind-core:5030` and `http://10.6.6.50:5030` resolve only on that bridge. A container attached solely to `websploit-isolated` cannot call the backend. `marionette` joins both networks. The golden-stack guard requires mind-core, echo-chamber, oracle-booth, marionette, and tainted-well by name when profile `ai` is set. Only marionette may join `websploit-isolated`. A later lab inside the reserved block (`10.6.6.50`–`10.6.6.59`, host ports `5030`–`5039`) can exist without another change to `.github/scripts/check_golden_stack.py` as long as it stays on `websploit` alone. Compose creates `websploit-isolated` when marionette attaches.

When adding a classic lab:

1. Create `additional-labs/<NewLab>/` with a `Dockerfile`, app source, `requirements.txt`, and a `README.md` (objective, vulnerable endpoints, exploitation hints, learning objectives).
2. Add a service block in `docker-compose.yml` following the existing pattern (build path `./additional-labs/<dir>`, container_name, static IP in `10.6.6.0/24`, host port mapping, `restart: unless-stopped`).
3. Pick a free static IP and a non-conflicting host port outside the reserved ranges below. Update the top-level README, `additional-labs/README.md`, and the network diagram.
4. Keep the lab app intentionally vulnerable to its target class; document the intended exploit path in the lab README.
5. Leave `10.6.6.46`–`10.6.6.49` unused (buffer) and do not take `10.6.6.50`–`10.6.6.59` or host ports `5030`–`5039` (AI track).

When adding an AI-track lab:

1. Create `agentic-ai-labs/<lab>/` with a `Dockerfile`, app source, `requirements.txt`, and a `README.md` (objective, vulnerable endpoints, exploitation hints, learning objectives, isolated-lab disclaimer).
2. Add a service block in the existing `docker-compose.yml` with build path `./agentic-ai-labs/<dir>`, `profiles: ["ai"]`, `container_name`, `restart: unless-stopped`, a healthcheck, `mem_limit`, and `cpus`.
3. Use the reserved block only: `10.6.6.50`–`10.6.6.59` and host ports `5030`–`5039`. `mind-core` already owns `10.6.6.50` / `5030`. `oracle-booth` already owns `10.6.6.51` / `5031`. `marionette` already owns `10.6.6.52` / `5032` and `10.7.7.52` on `websploit-isolated`. `echo-chamber` already owns `10.6.6.54` / `5034`. `tainted-well` already owns `10.6.6.53` / `5033` and stays on `websploit` only. The names still reserved in issue #89 are false-prophet `.55:5035` and token-famine `.56:5036`. `.57`–`.59` and ports `5037`–`5039` stay unused until a later issue assigns them.
4. Call `mind-core` at `http://mind-core:5030` (or `http://10.6.6.50:5030`) using the contract in `agentic-ai-labs/mind-core/README.md`. Those URLs resolve only on `websploit`. Add flag triggers to `agentic-ai-labs/mind-core/rules.json` instead of putting a model in the lab container. The Dockerfile copies `rules.json` into the image, so a rule or flag edit needs `docker compose --profile ai up -d --build mind-core`.
5. Keep the lab intentionally vulnerable to its target class. Do not add those weaknesses to `mind-core`.
6. `websploit-isolated` (`10.7.7.0/24`, gateway `10.7.7.1`, `internal: true`) is for marionette. Keep that declaration. marionette joins both `websploit` and `websploit-isolated`. The golden-stack guard requires that dual-homed attach, reads the lab's golden IPv4 from `websploit`, and rejects every other service on `websploit-isolated`. Leave mind-core on `websploit` only. Other AI labs stay on `websploit` alone. The isolated network has no internet egress.
7. Update the top-level README, `agentic-ai-labs/README.md`, and the lab README. Leave `additional-labs/` unchanged.

## How to run things

From the repo root:

```bash
docker compose up -d --build      # classic labs; the AI track stays off
docker compose ps                 # list containers
docker compose logs -f <name>     # tail a service
docker compose build --no-cache <name>
docker compose down               # stop everything
docker compose --profile ai up -d --build mind-core   # backend only; name the service so the classic stack stays down
docker compose --profile ai up -d --build mind-core echo-chamber   # backend plus the LLM05 lab
docker compose --profile ai up -d --build mind-core oracle-booth   # backend plus the prompt-injection lab
docker compose --profile ai up -d --build mind-core marionette     # backend plus the excessive-agency lab
```

The `install.sh` script is meant to be run as root on Kali/Parrot. It installs system tooling, clones companion repos into `/root/`, and runs `docker-compose -f docker-compose.yml up -d`. Don't run it on your dev machine.

## Python tooling

- `pyproject.toml` declares Python `>=3.13` and `flask>=3.1.2`. `uv.lock` is checked in, suggesting `uv` for environment management at the top level. Individual labs have their own `requirements.txt` and Python versions baked into their Dockerfiles — treat each lab as its own self-contained environment.
- The top-level `main.py` is a placeholder; the real "apps" are the per-lab Flask apps under `additional-labs/`.

## Documentation conventions

- Top-level `README.md` and `additional-labs/README.md` both contain the classic network topology and container table. **Keep them in sync** when you add, rename, renumber, or remove a classic container. AI-track containers are documented in the top-level README and `agentic-ai-labs/README.md`; do not add them to `additional-labs/`.
- Lab READMEs follow a rough pattern: overview, vulnerable endpoints/parameters, step-by-step exploitation, learning objectives, and sometimes hints. Match that style for new labs.
- The `websploit-containers.drawio` source diagram should ideally be updated alongside topology changes (optional if the user doesn't ask).

## Style and small things

- Bash scripts use `set -e` / `set -u` (see `install.sh`); preserve that. They are interactive and assume root and a Debian-family distro (`apt`, `lsb_release`).
- Markdown tables in READMEs are aligned by content, not by spaces — don't over-format.
- Two header URLs appear repeatedly: `https://websploit.org` and `https://github.com/The-Art-of-Hacking/websploit`. Use them consistently.
- Author/credit line: "Omar Santos" / "@santosomar".

## Disclaimer to repeat in user-facing changes

These containers are intentionally vulnerable and must only run in isolated, non-production environments. Any new lab README should carry a short version of this warning.
