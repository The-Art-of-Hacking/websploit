# Agentic AI labs

Opt-in track for WebSploit Labs by Omar Santos (@santosomar). Classic web labs stay in [`additional-labs/`](../additional-labs/). This directory is separate so `docker compose up` and `install.sh` keep today's footprint unless you ask for the `ai` profile.

More about WebSploit Labs: [https://websploit.org](https://websploit.org). Source: [https://github.com/The-Art-of-Hacking/websploit](https://github.com/The-Art-of-Hacking/websploit).

> **WARNING:** These applications are intentionally vulnerable. They are for isolated, authorized training only. Do not expose them to untrusted networks. `mind-core` is the exception: it is shared infrastructure, not a challenge.

## Opt in

From the repository root:

```bash
docker compose --profile ai up -d --build
```

That builds every service in the `ai` profile. Today that is `mind-core` and `echo-chamber`. To start the backend without the lab:

```bash
docker compose --profile ai up -d --build mind-core
```

To start the backend and the improper-output-handling lab:

```bash
docker compose --profile ai up -d --build mind-core echo-chamber
```

`docker compose up` without `--profile ai` does not create or start `mind-core` or `echo-chamber`.

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
| oracle-booth | 10.6.6.51 | 5031 | Reserved, not created |
| marionette | 10.6.6.52 | 5032 | Reserved, not created |
| tainted-well | 10.6.6.53 | 5033 | Reserved, not created |
| echo-chamber | 10.6.6.54 | 5034 | Deployed with profile `ai` |
| false-prophet | 10.6.6.55 | 5035 | Reserved, not created |
| token-famine | 10.6.6.56 | 5036 | Reserved, not created |
| (unassigned) | 10.6.6.57–10.6.6.59 | 5037–5039 | Unused |

## Directory map

| Directory | Container | Role |
| --- | --- | --- |
| `mind-core/` | `mind-core` | Shared completion API. Not a vulnerable lab. |
| `echo-chamber/` | `echo-chamber` | LLM05 improper output handling. Intentionally vulnerable. |

Labs added later should live in `agentic-ai-labs/<lab>/` and use build path `./agentic-ai-labs/<dir>`, profile `ai`, a healthcheck, and memory and CPU limits. The track maps onto the OWASP Top 10 for LLM Applications (2025). `echo-chamber` is documented in [echo-chamber/README.md](echo-chamber/README.md). `marionette` is still the later agentic exercise.

## Isolated network

`websploit-isolated` is defined in the root `docker-compose.yml`:

| Property | Value |
| --- | --- |
| Subnet | 10.7.7.0/24 |
| Gateway | 10.7.7.1 |
| Internal | yes (no internet egress) |
| Attached containers | none |

`containers.sh` already prints this subnet. The network is declared in Compose so that reference has a definition to match. Compose v2 does not create a network until a service references it, unless you pass `--all-resources`, so `10.7.7.1` will not show up on the host until `marionette` attaches. The golden-stack check reads the declaration with `--all-resources` and fails if any service attaches before that guard is updated.

## Calling mind-core

From another container on the `websploit` network, use `http://mind-core:5030` or `http://10.6.6.50:5030`. From the host, use `http://127.0.0.1:5030`. The request and response contract is in [mind-core/README.md](mind-core/README.md).
