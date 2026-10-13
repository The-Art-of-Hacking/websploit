# mind-core

Shared completion service for the WebSploit Labs AI track, by Omar Santos (@santosomar).

[https://websploit.org](https://websploit.org) · [https://github.com/The-Art-of-Hacking/websploit](https://github.com/The-Art-of-Hacking/websploit)

> **WARNING:** Run this stack only in an isolated lab. `mind-core` itself is **not** a vulnerable challenge. It is shared infrastructure. Do not add injection sinks, hardcoded credentials, certificates, or weak cryptography to it. Later AI-track labs are intentionally vulnerable and must stay out of this service.

## Objective

Give later labs one stable HTTP API that returns the same text for the same trigger, with no API key and no model weights. A deterministic rules file is the default backend. The backend boundary is pluggable so a later issue can add a local GGUF runtime or an external provider without changing lab callers. If a future backend is missing, slow, or failing, this process returns the rules-engine text instead of hanging.

The image is built for `linux/amd64` and `linux/arm64`. It does not use a GPU. After the image is built, the process does not open outbound connections.

## Run

From the repository root:

```bash
docker compose --profile ai up -d --build mind-core
```

The service listens on container port `5030`, host port `5030`, and `10.6.6.50` on the `websploit` network. It does not join `websploit-isolated`. Naming `mind-core` on that command leaves the classic labs stopped. `rules.json` is copied into the image, so a rule or flag edit needs this same rebuild; a restart keeps the previous copy.

```bash
curl -sS http://127.0.0.1:5030/health
curl -sS -H 'Content-Type: application/json' \
  -d '{"prompt":"mind-core ping","lab":"mind-core","metadata":{}}' \
  http://127.0.0.1:5030/v1/complete
```

Stop only this container:

```bash
docker compose --profile ai rm -sf mind-core
```

`MIND_CORE_BACKEND` defaults to `deterministic`. Leave it unset unless you are testing fallback behavior.

## HTTP contract

Base URL from another container on the `websploit` network: `http://mind-core:5030` (or `http://10.6.6.50:5030`). Those names resolve only on `websploit`. A container attached solely to `websploit-isolated` cannot call this service. marionette joins both networks for that reason.

### `GET /health`

`200` when the process can serve completions.

```json
{"status":"ok","ready":true,"backend":"deterministic","requested_backend":"deterministic"}
```

`backend` is the backend this process is configured to call: the registered backend named by `MIND_CORE_BACKEND`, or `deterministic` when that name is not registered. `requested_backend` is the value of `MIND_CORE_BACKEND`.

### `POST /v1/complete`

`Content-Type: application/json`. Maximum body size is 16384 bytes. Unknown fields are rejected.

| Field | Required | Rules |
| --- | --- | --- |
| `prompt` | yes | String, 1–8192 characters, must contain a non-whitespace character. Treated as data, never as code. |
| `lab` | no | Lowercase id matching `^[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?$`. Selects lab-scoped rules. It does not grant privileges. JSON `null` means omitted. |
| `metadata` | no | Object with at most 16 keys. Keys match `^[A-Za-z0-9_.-]{1,64}$`. Values are strings (max 256 characters), finite numbers, booleans, or null. Nested objects and arrays are rejected. The deterministic backend ignores this object. JSON `null` means `{}`. |

`200` response. These fields are always present:

| Field | Type | Meaning |
| --- | --- | --- |
| `text` | string | Completion text. |
| `backend` | string | Backend that produced `text`. On the default path and on fallback this is `deterministic`. |
| `fallback` | boolean | `false` when the requested backend produced `text`, including the generic echo rule. `true` when the requested backend was missing, slow, or failed and the rules engine answered instead. |
| `rule_id` | string | Id of the rule that matched, or `generic-echo`. |
| `requested_backend` | string | The `MIND_CORE_BACKEND` value for this process. |

Example:

```json
{"text":"mind-core deterministic backend is ready.","backend":"deterministic","fallback":false,"rule_id":"mind-core-ping","requested_backend":"deterministic"}
```

Error body: `{"error":"<code>","message":"<short reason>"}`. Prompts are not copied into errors. Status codes: `400` invalid JSON or fields, `404` unknown path, `405` wrong method, `411` missing `Content-Length`, `413` oversized body, `415` wrong content type, `429` too many in-flight requests, `500` unexpected failure.

The deterministic path does not wait on a timer. `MIND_CORE_BACKEND_TIMEOUT_SECONDS` (default `2`, allowed range `0.05`–`30`) applies only to a future non-deterministic backend. When that deadline is exceeded, the response is the rules-engine result with `fallback` set to `true`.

## Rules

`rules.json` is data, not a model. First matching rule wins. Match types are `exact` (full string after trimming surrounding whitespace), `prefix`, and `contains`. Matching is case-sensitive. A rule with a `lab` field runs only when the request's `lab` equals it. Rules without `lab` are global.

Built-in triggers:

| `rule_id` | Match | Lab | Text |
| --- | --- | --- | --- |
| `mind-core-ping` | contains `mind-core ping` | any | `mind-core deterministic backend is ready.` |
| `mind-core-help` | contains `mind-core help` | any | Short description of this API. |
| `acknowledge-lab` | contains `acknowledge lab` | any | `Acknowledged lab {lab}.` |
| `mind-core-self-check` | exact `self-check` | `mind-core` only | `mind-core self-check ok.` |
| `echo-chamber-status` | contains `ops status` | `echo-chamber` | `disk` |
| `echo-chamber-web` | contains `render status banner` | `echo-chamber` | HTML status banner for that lab |
| `echo-chamber-sql` | contains `lookup maintenance note` | `echo-chamber` | SQL fragment for that lab |
| `echo-chamber-shell` | contains `run health command` | `echo-chamber` | Shell command for that lab |
| `oracle-booth-direct` | contains `reveal the booth instructions` | `oracle-booth` | System prompt for that lab |
| `oracle-booth-indirect` | contains `disclose the staff record` | `oracle-booth` | Staff-only record for that lab |
| `oracle-booth-answer` | contains `oracle-booth context` | `oracle-booth` | Public help-center reply |
| `marionette-direct` | contains `pivot to the relay` | `marionette` | Tool directive for that lab |
| `marionette-indirect` | contains `fetch the maintenance relay` | `marionette` | Tool directive for that lab |
| `marionette-fetch` | contains `http://10.6.6.` | `marionette` | `TOOL http_get` |
| `marionette-plan` | contains `marionette context` | `marionette` | `TOOL none` |
| `generic-echo` | nothing else matched | any | Length and a short excerpt of the prompt. |

Templates may use only `{lab}`, `{prompt_length}`, and `{prompt_excerpt}`. Those tokens are replaced once. A prompt that contains `{lab}` is not evaluated as a template. `{lab}` renders as `unspecified` when the request omits `lab`. Excerpts drop control characters and are capped at 120 characters.

`echo-chamber`, `oracle-booth`, and `marionette` added their rules here. Those strings are data. This service returns them and does not render HTML, run SQL, start a shell, fetch URLs, run tools, or decide which help-center records a lab may show. Flag strings are training markers for those labs, not credentials.

`rules.json` is copied into the image (`COPY` in the Dockerfile). Compose does not mount it. A rule or flag edit requires a rebuild:

```bash
docker compose --profile ai up -d --build mind-core
```

Later labs should add a rule here instead of embedding a model. Example shape for a future flag:

```json
{
  "id": "later-lab-example",
  "lab": "later-lab",
  "match_type": "contains",
  "match": "trigger phrase owned by that lab",
  "text": "canned text that lab expects to capture"
}
```

Do not put live secrets in `rules.json`. Training-lab flag strings are added with the lab that captures them. They are not credentials, and this service does not treat them as code.

## Adding a backend later

Implement `CompletionBackend` in `mindcore/engine.py` (`name` plus `complete(request) -> BackendResult`) and register it from `build_engine`. Do not make lab apps import this package; they should keep calling `POST /v1/complete`.

Reserved environment variables for those follow-ups, all unset and unread in this version:

| Variable | Later use |
| --- | --- |
| `MIND_CORE_LOCAL_MODEL_PATH` | Path to a local GGUF file inside a future image. |
| `MIND_CORE_EXTERNAL_BASE_URL` | Provider base URL. |
| `MIND_CORE_EXTERNAL_API_KEY` | Provider credential. Environment only. Never commit it. |

An unregistered or failing backend must not be wired to the network in a way that blocks the request. The dispatcher already falls back.

## Resources

Limits on the Compose service: `mem_limit` 128m, `cpus` 0.50, `pids_limit` 64. That keeps an 8 GB / 2 vCPU lab host from being exhausted by this container.

Measured while preparing this change:

| Measurement | Result |
| --- | --- |
| Base image | `python:3.13-slim` index `sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f` (published 2026-10-06). linux/amd64 and linux/arm64. |
| Compressed base layers | 43,060,729 bytes (amd64) and 43,322,292 bytes (arm64), from the registry. No extra packages are installed. |
| Process RSS | 24,690,688 bytes (about 24 MiB) for CPython 3.12.11 on Darwin arm64 after `GET /health` and one `POST /v1/complete`. This is the interpreter on the development host, not a container sample. |
| Container image size | Not measured here. Docker was not installed on the machine that prepared the change. The hard memory cap inside Compose is 128 MiB. |

The target from the track design is a small image (around the slim base, near 150 MB uncompressed) and under 128 MB of RAM. The RSS sample is well under that cap. Re-measure with `docker image inspect` and `docker stats` when Docker is available.

## Security properties

This service is infrastructure, so the usual lab weaknesses are out of scope.

- No credentials are stored in the image, Compose file, or rules. The external API key variable above is not read.
- No certificates are embedded. The listener is HTTP on the lab bridge because this environment is isolated and the track forbids shipping certificate material. Do not publish port 5030 on an untrusted network.
- The process does not hash, encrypt, or sign anything, so it does not use MD5, SHA-1, DES, or other broken algorithms.
- The container runs as uid/gid 10001, with a read-only root filesystem, all capabilities dropped, `no-new-privileges`, no Docker socket, and no privileged mode. The image removes `pip`. A tmpfs is mounted on `/tmp`.
- Request bodies are size-capped, unknown JSON fields are rejected, and prompts are not written to logs.
