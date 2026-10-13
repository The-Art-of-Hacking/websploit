# token-famine

Metered chat for the WebSploit Labs AI track, by Omar Santos (@santosomar).

[https://websploit.org](https://websploit.org) · [https://github.com/The-Art-of-Hacking/websploit](https://github.com/The-Art-of-Hacking/websploit)

> **WARNING:** This application is intentionally vulnerable. It is for isolated, authorized training only. Do not expose it to untrusted networks. The meter accepts a token flood, a nested `expand(`, or a denial-of-wallet `copies` count. That pattern is capped on purpose. The container cannot spend the host the way an uncapped process did when it filled RAM and swap.

| | |
| --- | --- |
| OWASP LLM Top 10 (2025) | LLM10 Unbounded Consumption |
| Difficulty | Medium |
| Address | 10.6.6.56 on `websploit` only |
| Host port | 5036 |
| Container | `token-famine` |
| Profile | `ai` |
| Backend | Deterministic `mind-core` rules. No API key and no model weights. |

## Objective

The ration office bills every chat reply. A short message spends one token per word, and the remaining budget is on `/meter` and on every reply. The meter also trusts two multipliers: a `copies` count, and each `expand(` in the message. It multiplies those into the token bill as if it were going to generate that much text.

The exercise is to make that unbounded bill visible, then watch the cap trip or the quota hit zero. The flag is released only for that pattern. A normal short chat, including one that finishes the quota one word at a time, does not release the flag.

The process does not allocate the flood. The product saturates at one million tokens in the accounting, the per-request cap clamps the charge, and the reply stays one short string. Container memory, CPU, and pid limits are a second fence. A successful exercise stays inside the documented 8 GB host floor because this container is limited to 128 MiB and 0.5 CPU.

Flag strings below are training markers. They are not credentials.

## Caps

These limits are part of the lab. They keep the failure mode measurable without letting the exercise exhaust the machine.

| Cap | Value |
| --- | --- |
| Quota | 64 tokens, shown as `remaining` and `spent` |
| Per-request tokens | 32 billed. A request for more trips `cap_tripped` and still bills at most 32 |
| Body | 4096 bytes. Larger requests are rejected |
| Message | 512 characters |
| Accounting saturation | 1000000 tokens. The counter stops there and nothing of that size is built |
| Request timeout | 2 seconds (`TOKEN_FAMINE_REQUEST_TIMEOUT_SECONDS`) |
| mind-core timeout | 2 seconds (`TOKEN_FAMINE_MIND_CORE_TIMEOUT_SECONDS`) |
| Memory | 128 MiB (`mem_limit`) |
| CPU | 0.5 |
| PIDs | 64 |

`allocated_bytes` is the size of the one reply string. On a flood it stays far below `requested_tokens`. `rss_bytes` is the process resident set when the OS exposes it, and it stays under `mem_limit_bytes`.

## Run

From the repository root. This does not start with a plain `docker compose up`.

```bash
docker compose --profile ai up -d --build mind-core token-famine
```

`token-famine` waits until `mind-core` is healthy. The app listens on container port `5036`. Naming the services leaves the classic stack and the other AI labs stopped.

```bash
curl -sS http://127.0.0.1:5036/health
```

Open `http://127.0.0.1:5036/` for the chat form. Stop the lab with:

```bash
docker compose --profile ai rm -sf token-famine mind-core
```

Calls to `mind-core` time out after 2 seconds. If `mind-core` is slow or down, the app uses a local copy of the token-famine rule so the request still finishes. The bill is computed locally either way, so the flood does not wait on a model.

`rules.json` is copied into the `mind-core` image. A rule edit needs a rebuild of that service as well:

```bash
docker compose --profile ai up -d --build mind-core token-famine
```

This lab stays on the `websploit` bridge. It does not join `websploit-isolated`. Only `marionette` attaches to that network.

## Vulnerable endpoints

The meter multiplies `copies` and every `expand(` into the token bill. It does not refuse a large multiplier up front. The per-request cap, the body cap, the timeout, and the container limits are what stop the work.

The chat asks `mind-core` for one short reply. The prompt is only the marker below. The message and the copy count are not copied into that prompt. The flag is not in the reply.

```text
token-famine ration
```

That string is `prompt` in `{"prompt","lab":"token-famine","metadata":{}}`, posted to `http://mind-core:5030/v1/complete`. Matching is case-sensitive and first match wins.

| Method | Path | What it does |
| --- | --- | --- |
| `GET` | `/` | Chat form. The flag is not on this page. |
| `GET` | `/health` | None. |
| `GET` | `/meter` | Quota, spent tokens, remaining budget, and the caps. The flag is not here. |
| `GET` or `POST` | `/chat` | Bills the message. A flood or a nested expand that trips the cap, or that exhausts the quota, releases the flag. |
| `POST` | `/reset` | Restores the quota so the exercise can be repeated. Does not release the flag. |

`POST /chat` accepts `{"message"}` or `{"message","copies"}` (JSON response) or form fields `message` and `copies` (HTML response). `GET` accepts `?message=&copies=` and returns HTML. Omitted `copies` means 1.

## Walkthrough

Deterministic mode is the required path. The app sets `lab` to `token-famine`. The trigger is a case-sensitive substring. CI and a laptop without the classic stack can capture the flag.

Read the meter first. The flag is not on this response:

```bash
curl -sS http://127.0.0.1:5036/meter
```

`quota` is 64 and `remaining` is 64. `per_request_cap` is 32. `mem_limit_bytes` is 134217728.

Confirm a short chat before you capture the flag:

```bash
curl -sS -H 'Content-Type: application/json' \
  -d '{"message":"hello"}' \
  http://127.0.0.1:5036/chat
```

`rule_id` is `token-famine-answer`, `requested_tokens` is 1, `billed_tokens` is 1, `remaining` is 63, and `flag` is null. `source: mind-core` means the shared rules engine answered. Ten copies of the same word are still inside the cap and the quota, and they do not release the flag:

```bash
curl -sS -H 'Content-Type: application/json' \
  -d '{"message":"hello","copies":10}' \
  http://127.0.0.1:5036/chat
```

`requested_tokens` is 10, `cap_tripped` is false, and `flag` is null.

Ask for a flood. The body stays small. The bill does not:

```bash
curl -sS -H 'Content-Type: application/json' \
  -d '{"message":"hello","copies":100000}' \
  http://127.0.0.1:5036/chat
```

`requested_tokens` is 100000, `cap_tripped` is true, `billed_tokens` is 32, and `allocated_bytes` is the size of one short reply. `flag` is `WEBSPLOIT{UNB0UND3D_C0NSUMPT10N}`. The cap tripped, and the process did not grow with the copy count.

A nested expand is the same pattern. One `expand(` is 8 tokens and stays inside the cap. Two of them ask for 64:

```bash
curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{}' \
  http://127.0.0.1:5036/reset

curl -sS -H 'Content-Type: application/json' \
  -d '{"message":"expand(expand(hello))"}' \
  http://127.0.0.1:5036/chat
```

`expand_depth` is 2, `cap_tripped` is true, and the flag is the same marker.

The quota can also run out without crossing the per-request cap, if an earlier bounded chat has already spent it down. Reset, bill 32 words (the cap allows exactly 32), then 22 words, then 10 copies of `hello`. The last request asks for 10 tokens, `cap_tripped` stays false, `remaining` hits 0, and the flag is released because the unbounded pattern exhausted the quota. Thirty-three ordinary words trip the per-request cap and do not release the flag. Sixty-four separate `hello` chats drain the quota and do not release the flag either. The flag is the flood or the expand, after the cap or the quota shows it.

`source: local-fallback` means the call missed its deadline and the app used its copy of the rule. Both sources return the same reply. The meter adds the flag only when the unbounded pattern trips the cap or exhausts the quota.

| Path | What multiplies the bill | Rule | Flag |
| --- | --- | --- | --- |
| Short chat | Nothing. One token per word | `token-famine-answer` | None |
| Modest copies | `copies` still at or under 32 tokens | `token-famine-answer` | None |
| Token flood | `copies` above the per-request cap | `token-famine-answer` | `WEBSPLOIT{UNB0UND3D_C0NSUMPT10N}` |
| Nested expand | Each `expand(` multiplies by 8 | `token-famine-answer` | `WEBSPLOIT{UNB0UND3D_C0NSUMPT10N}` when the product exceeds the cap or finishes the quota |
| Quota drained one word at a time | No multiplier | `token-famine-answer` | None |

This trigger is not a substring of the mind-core, echo-chamber, oracle-booth, marionette, tainted-well, or false-prophet rules, and those rules are not substrings of this trigger. The token-famine rule is scoped to `lab` `token-famine` and is listed after the false-prophet rules. The flag is not in the rule text. The lab meter releases it.

## Learning objectives

- Explain LLM10: an unbounded completion, a recursive expand, or a denial-of-wallet multiplier can spend far more than a short chat.
- Read a quota and a billing counter so the pattern is measurable before the cap trips.
- Show that a normal short chat does not release the flag, and that draining the quota one word at a time does not either.
- Show that the cap holds: `requested_tokens` can be huge while `allocated_bytes` and the container stay small.
- Capture the flag offline, with deterministic rules, without an API key, model weights, or the classic stack.
- See why a per-request cap, a body cap, a timeout, and a container memory limit belong on a lab that demonstrates consumption.

## What this image does not do

The base image is the same multi-arch `python:3.13-slim` digest `mind-core` pins (`sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f`, linux/amd64 and linux/arm64). No extra packages are installed. The process runs as uid/gid 10007, with a read-only root filesystem, a small `/tmp`, dropped capabilities, and a 128 MiB memory cap. There are no credentials, certificates, or cryptographic operations in this lab. `mind-core` stays a rules engine: it returns the short reply and does not bill tokens or expand the message. The lab does that. This container does not join `websploit-isolated`.
