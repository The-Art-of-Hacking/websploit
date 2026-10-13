# Agentic AI labs

Opt-in track for WebSploit Labs by Omar Santos (@santosomar). Classic web labs stay in [`additional-labs/`](../additional-labs/). This directory is separate so `docker compose up` and `install.sh` keep today's footprint unless you ask for the `ai` profile.

More about WebSploit Labs: [https://websploit.org](https://websploit.org). Source: [https://github.com/The-Art-of-Hacking/websploit](https://github.com/The-Art-of-Hacking/websploit).

> **WARNING:** These applications are intentionally vulnerable. They are for isolated, authorized training only. Do not expose them to untrusted networks. `mind-core` is the exception: it is shared infrastructure, not a challenge.

## Opt in

From the repository root, a plain Compose up leaves the AI track off:

```bash
docker compose up -d
```

Start just the shared backend by activating the profile and naming the service:

```bash
docker compose --profile ai up -d --build mind-core
```

Start the backend and one lab the same way:

```bash
docker compose --profile ai up -d --build mind-core echo-chamber
docker compose --profile ai up -d --build mind-core oracle-booth
docker compose --profile ai up -d --build mind-core trojan-relay marionette
```

`docker compose --profile ai up -d --build` with no service names starts the classic stack and every service in the `ai` profile (`mind-core`, `oracle-booth`, `marionette`, and `echo-chamber`). Naming the services is how you avoid booting every classic lab. `marionette` pivots to `trojan-relay`, so name that classic lab too if you want a live target.

`docker compose up` without `--profile ai` does not create or start `mind-core`, `oracle-booth`, `marionette`, or `echo-chamber`.

## Backend tiers

| Tier | Status | What it does |
| --- | --- | --- |
| Deterministic rules | This track, default | Canned and templated replies from `mind-core/rules.json`. No API key and no model weights. |
| Local GGUF model | Follow-up issue | A later change may add a local runtime behind the same HTTP API. Not in this image. |
| External provider | Follow-up issue | A later change may call a provider with environment variables only, unset by default. Not implemented, and no key is read today. |

`MIND_CORE_BACKEND` selects the tier. The only registered name today is `deterministic`. Any other syntactically valid name returns the rules-engine text with `"fallback": true` instead of hanging.

## Reserved addresses

The AI track uses `10.6.6.50`–`10.6.6.59` and host ports `5030`–`5039` on the `websploit` bridge (`10.6.6.0/24`, gateway `10.6.6.1`). `10.6.6.46`–`10.6.6.49` stay unused as a buffer above the classic labs.

| Name | Address | Host port | Status |
| --- | --- | --- | --- |
| mind-core | 10.6.6.50 | 5030 | Deployed with profile `ai` |
| oracle-booth | 10.6.6.51 | 5031 | Deployed with profile `ai` |
| marionette | 10.6.6.52 (and 10.7.7.10 on `websploit-isolated`) | 5032 | Deployed with profile `ai` |
| tainted-well | 10.6.6.53 | 5033 | Reserved, not created |
| echo-chamber | 10.6.6.54 | 5034 | Deployed with profile `ai` |
| false-prophet | 10.6.6.55 | 5035 | Reserved, not created |
| token-famine | 10.6.6.56 | 5036 | Reserved, not created |
| (unassigned) | 10.6.6.57–10.6.6.59 | 5037–5039 | Unused |

## Directory map

| Directory | Container | Role |
| --- | --- | --- |
| `mind-core/` | `mind-core` | Shared completion API. Not a vulnerable lab. |
| `oracle-booth/` | `oracle-booth` | LLM01 prompt injection, LLM02 sensitive disclosure, LLM07 system prompt leakage. Intentionally vulnerable. |
| `echo-chamber/` | `echo-chamber` | LLM05 improper output handling. Intentionally vulnerable. |
| `marionette/` | `marionette` | LLM06 excessive agency, LLM01 indirect prompt injection (secondary: Agentic ASI01 goal hijack). Intentionally vulnerable. |

Labs added later should live in `agentic-ai-labs/<lab>/` and use build path `./agentic-ai-labs/<dir>`, profile `ai`, a healthcheck, and memory and CPU limits. The track maps onto the OWASP Top 10 for LLM Applications (2025). `oracle-booth` is documented in [oracle-booth/README.md](oracle-booth/README.md). `echo-chamber` is documented in [echo-chamber/README.md](echo-chamber/README.md). `marionette` is documented in [marionette/README.md](marionette/README.md).

## Isolated network

`websploit-isolated` is defined in the root `docker-compose.yml`:

| Property | Value |
| --- | --- |
| Subnet | 10.7.7.0/24 |
| Gateway | 10.7.7.1 |
| Internal | yes (no internet egress) |
| Attached containers | `marionette` (10.7.7.10) only |

`containers.sh` already prints this subnet. Compose v2 does not create a network until a service references it, unless you pass `--all-resources`, so `10.7.7.1` shows up on the host once `marionette` starts. `mind-core`, `echo-chamber`, and `oracle-booth` stay on `websploit` and do not join this network. The golden-stack check requires this declaration (`10.7.7.0/24`, gateway `10.7.7.1`, `internal: true`) and fails if any service other than `marionette` joins it. marionette also joins `websploit`, because mind-core is not on `websploit-isolated`.

## Calling mind-core

`http://mind-core:5030` and `http://10.6.6.50:5030` resolve only on the `websploit` network. A container attached solely to `websploit-isolated` cannot call the backend. marionette joins both networks for that reason. From the host, use `http://127.0.0.1:5030`. The request and response contract is in [mind-core/README.md](mind-core/README.md).
