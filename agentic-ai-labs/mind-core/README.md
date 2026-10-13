# mind-core

Shared completion service for the WebSploit Labs AI track, by Omar Santos (@santosomar).

[https://websploit.org](https://websploit.org) · [https://github.com/The-Art-of-Hacking/websploit](https://github.com/The-Art-of-Hacking/websploit)

> **WARNING:** Run this stack only in an isolated lab. `mind-core` itself is **not** a vulnerable challenge. It is shared infrastructure. Do not add injection sinks, hardcoded credentials, certificates, or weak cryptography to it. Later AI-track labs are intentionally vulnerable and must stay out of this service.

## Objective

Give later labs one stable HTTP API that returns the same text for the same trigger, with no API key. A deterministic rules file is the default backend and does not use model weights. An optional CPU GGUF tier can be turned on with a second Compose profile. If that model is missing, slow, or failing, this process returns the rules-engine text instead of hanging. An external provider is not wired up.

The image is built for `linux/amd64` and `linux/arm64`. It does not use a GPU. The rules engine does not open outbound connections. With the local tier enabled, this process calls `local-gguf` on the `websploit` bridge only.

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

The image default for `MIND_CORE_BACKEND` is `deterministic`. Compose sets it to `auto` unless you override it. `auto` keeps the rules engine until `local-gguf` answers `/health`, then completions come from that server. `--profile ai` does not start `local-gguf`, so the API stays `deterministic` with `"fallback": false`. Set `MIND_CORE_BACKEND=deterministic` to ignore the model even when the container is up.

## Local model

Opt in with both profiles. The weight is not in git. `model-fetch` downloads it into the `gguf-cache` volume, checks SHA-256, and exits. It starts as root only long enough to chown that volume, then drops to uid 10001 before any download. A file that already matches is reused and is not downloaded again. A truncated or tampered file fails the check and is deleted, so `local-gguf` does not load it.

```bash
docker compose --profile ai --profile ai-model up -d --build mind-core model-fetch local-gguf
```

The same selection is `COMPOSE_PROFILES=ai,ai-model`. `--profile ai-model` alone is not a valid project: the model services depend on `mind-core`, which stays behind profile `ai`. `--profile ai` without `ai-model` does not start `model-fetch` or `local-gguf` and does not download the weight.

`local-gguf` is `ghcr.io/ggml-org/llama.cpp:server` pinned by digest, on `10.6.6.57`, with no host port. `mind-core` calls `http://local-gguf:8080` on the `websploit` bridge. `model-fetch` is on `10.6.6.58`, also with no host port. Neither container joins `websploit-isolated`. The server is CPU-only (`--n-gpu-layers 0`) and the image index covers `linux/amd64` and `linux/arm64`.

| Pin | Value |
| --- | --- |
| Model id | `Qwen/Qwen2.5-0.5B-Instruct-GGUF` |
| File | `qwen2.5-0.5b-instruct-q4_k_m.gguf` |
| Parameters / quant | 0.5B, Q4_K_M |
| License | Apache-2.0 (Copyright 2024 Alibaba Cloud) |
| Size | 491,400,032 bytes (published weight; about 469 MiB) |
| Checksum | SHA-256 `74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db` |
| URL | `https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf` |
| Runtime image | `ghcr.io/ggml-org/llama.cpp:server@sha256:c789283572ba78c2699b8945a96e654c850f938a717883f2e6187a14adac698f` |

Compose caps `local-gguf` at 1536 MiB and 1.5 CPUs so an 8 GB host still has room for the rest of the stack. Container RSS was not measured here: Docker was not installed on the machine that prepared this change. Do not treat 1536 MiB as a measured footprint. Re-measure with `docker stats local-gguf` on a host that has Docker. `model-fetch` is capped at 256 MiB and 0.50 CPU.

Disk is the published weight, 491,400,032 bytes, on the `gguf-cache` volume, plus the llama.cpp image and the small fetch image. Those image sizes were not measured here.

After the volume holds a file that matches the SHA-256 pin, later starts hash it locally and do not contact Hugging Face. The runtime image still has to be present on the machine. The first run needs the network for the image pull and the weight. A failed checksum removes the bad file and leaves `local-gguf` stopped; `mind-core` keeps serving the rules engine.

Direct callers of `POST /v1/complete` wait up to `MIND_CORE_BACKEND_TIMEOUT_SECONDS` (Compose sets 15, process default 2, allowed range 0.05–30) and then receive the rules-engine text with `"fallback": true`. Labs keep their own 2 second client timeout, so a slow model does not hold a lab request open.

`MIND_CORE_EXTERNAL_API_KEY` and `MIND_CORE_EXTERNAL_BASE_URL` are not read. Do not commit a provider key.

## HTTP contract

Base URL from another container on the `websploit` network: `http://mind-core:5030` (or `http://10.6.6.50:5030`). Those names resolve only on `websploit`. A container attached solely to `websploit-isolated` cannot call this service. `marionette` joins both networks.

### `GET /health`

`200` when the process can serve completions.

```json
{"status":"ok","ready":true,"backend":"deterministic","requested_backend":"deterministic"}
```

`backend` is the backend this process is configured to call. `requested_backend` is that same effective name. `auto` is a selector, not a backend name: until `local-gguf` is healthy the API reports `deterministic`. After it is healthy both fields become `local`. An unregistered name still falls back to the rules engine.

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
| `backend` | string | Backend that produced `text`. On the default path and on fallback this is `deterministic`. A local completion uses `local`. |
| `fallback` | boolean | `false` when the requested backend produced `text`, including the generic echo rule. `true` when the requested backend was missing, slow, or failed and the rules engine answered instead. |
| `rule_id` | string | Id of the rule that matched, `generic-echo`, or `local-completion` when the model answered. |
| `requested_backend` | string | Effective backend name for this process. `auto` is reported as `deterministic` until the local server is healthy, then `local`. |

Example:

```json
{"text":"mind-core deterministic backend is ready.","backend":"deterministic","fallback":false,"rule_id":"mind-core-ping","requested_backend":"deterministic"}
```

Error body: `{"error":"<code>","message":"<short reason>"}`. Prompts are not copied into errors. Status codes: `400` invalid JSON or fields, `404` unknown path, `405` wrong method, `411` missing `Content-Length`, `413` oversized body, `415` wrong content type, `429` too many in-flight requests, `500` unexpected failure.

The deterministic path does not wait on a timer. `MIND_CORE_BACKEND_TIMEOUT_SECONDS` (process default `2`, Compose sets `15` for the model tier, allowed range `0.05`–`30`) applies to the local backend. When that deadline is exceeded, the response is the rules-engine result with `fallback` set to `true`.

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
| `marionette-pivot` | contains `invoke tool http_get on http://10.6.6.32` | `marionette` | Tool call `http_get` of `http://10.6.6.32` |
| `marionette-vault` | contains `run db_query against the vault` | `marionette` | Tool call `db_query` of `SELECT value FROM vault` |
| `marionette-answer` | contains `marionette context` | `marionette` | Status reply with no tool call |
| `tainted-well-poison` | contains `bias retrieval toward the planted well note` | `tainted-well` | Poisoned-retrieval reply for that lab |
| `tainted-well-tenant` | contains `leak the other tenant chunk` | `tainted-well` | Cross-tenant chunk reply for that lab |
| `tainted-well-artifact` | contains `untrusted embedding artifact loaded` | `tainted-well` | Insecure model-artifact reply for that lab |
| `tainted-well-answer` | contains `tainted-well context` | `tainted-well` | Public well-report reply |
| `false-prophet-fabricate` | contains `fabricate a citation for the unlisted claim` | `false-prophet` | Fabricated claim and citation for that lab |
| `false-prophet-pump` | contains `ground the pump station opening` | `false-prophet` | Gazette reply for the pump-station question |
| `false-prophet-depth` | contains `ground the reservoir depth` | `false-prophet` | Gazette reply for the reservoir-depth question |
| `false-prophet-answer` | contains `false-prophet context` | `false-prophet` | Reply with no citation |
| `token-famine-answer` | contains `token-famine ration` | `token-famine` | Short ration reply for that lab |
| `generic-echo` | nothing else matched | any | Length and a short excerpt of the prompt. |

Templates may use only `{lab}`, `{prompt_length}`, and `{prompt_excerpt}`. Those tokens are replaced once. A prompt that contains `{lab}` is not evaluated as a template. `{lab}` renders as `unspecified` when the request omits `lab`. Excerpts drop control characters and are capped at 120 characters.

`echo-chamber`, `oracle-booth`, `marionette`, `tainted-well`, `false-prophet`, and `token-famine` added their rules here. Those strings are data. This service returns them and does not render HTML, run SQL, start a shell, fetch a URL, load a pickle, compare a citation to a gazette, bill tokens, or decide which chunk a lab may return. Flag strings are training markers for those labs, not credentials. The false-prophet rules return a claim and a citation. That lab's ground-truth check releases its training flag when the fabricated citation is absent from the gazette. The token-famine rule returns one short reply. That lab's meter releases its training flag when an unbounded bill trips the cap or exhausts the quota.

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

## External provider

Not implemented. `MIND_CORE_EXTERNAL_BASE_URL` and `MIND_CORE_EXTERNAL_API_KEY` are unread. The key must stay in the environment of a future change and must not be committed. `MIND_CORE_LOCAL_MODEL_PATH` is also unread: the weight lives on the `gguf-cache` volume, not in this image.

An unregistered or failing backend must not be wired to the network in a way that blocks the request. The dispatcher already falls back.

## Resources

Limits on the Compose service: `mem_limit` 128m, `cpus` 0.50, `pids_limit` 64. That keeps an 8 GB / 2 vCPU lab host from being exhausted by this container.

Measured while preparing this change:

| Measurement | Result |
| --- | --- |
| Base image | `python:3.13-slim` index `sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f` (published 2026-10-06). linux/amd64 and linux/arm64. |
| Compressed base layers | 43,060,729 bytes (amd64) and 43,322,292 bytes (arm64), from the registry. No extra packages are installed. |
| Process RSS | 24,690,688 bytes (about 24 MiB) for CPython 3.12.11 on Darwin arm64 after `GET /health` and one `POST /v1/complete`. This is the interpreter on the development host, not a container sample. |
| Container image size | Not measured here. Docker was not installed on the machine that prepared the change. The hard memory cap inside Compose is 128 MiB for `mind-core`. |
| Local weight | 491,400,032 bytes, SHA-256 pinned, Apache-2.0. Not measured inside a container. |
| `local-gguf` cap | 1536 MiB, 1.5 CPUs. This is a limit, not a measured RSS. |
| llama.cpp image | Index digest `sha256:c789283572ba78c2699b8945a96e654c850f938a717883f2e6187a14adac698f` (`linux/amd64` and `linux/arm64`). Layer size was not measured here. |

The target from the track design is a small `mind-core` image (around the slim base, near 150 MB uncompressed) and under 128 MB of RAM for that service. The RSS sample is well under that cap. The model tier's cap is 1536 MiB so the published 469 MiB weight has room to run on an 8 GB host. Re-measure with `docker image inspect` and `docker stats` when Docker is available.

## Security properties

This service is infrastructure, so the usual lab weaknesses are out of scope.

- No credentials are stored in the image, Compose file, or rules. `MIND_CORE_EXTERNAL_API_KEY` is not read. The model URL and SHA-256 pin are a public weight, not a secret.
- No certificates are embedded. The listener is HTTP on the lab bridge because this environment is isolated and the track forbids shipping certificate material. `local-gguf` is also HTTP, on the bridge only, with no host port. Do not publish port 5030 on an untrusted network.
- The rules engine does not hash, encrypt, or sign. The weight check is SHA-256 of the published file. MD5 and SHA-1 are not used. The checksum is an integrity check, not a password hash.
- The container runs as uid/gid 10001, with a read-only root filesystem, all capabilities dropped, `no-new-privileges`, no Docker socket, and no privileged mode. The image removes `pip`. A tmpfs is mounted on `/tmp`.
- Request bodies are size-capped, unknown JSON fields are rejected, and prompts are not written to logs.
