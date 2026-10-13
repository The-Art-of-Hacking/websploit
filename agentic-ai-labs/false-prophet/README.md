# false-prophet

Answer and citation generator for the WebSploit Labs AI track, by Omar Santos (@santosomar).

[https://websploit.org](https://websploit.org) · [https://github.com/The-Art-of-Hacking/websploit](https://github.com/The-Art-of-Hacking/websploit)

> **WARNING:** This application is intentionally vulnerable. It is for isolated, authorized training only. Do not expose it to untrusted networks. The generator returns a fabricated claim and citation for any question that is not in the gazette. The ground-truth check is what proves that citation false.

| | |
| --- | --- |
| OWASP LLM Top 10 (2025) | LLM09 Misinformation |
| Difficulty | Easy–Medium |
| Address | 10.6.6.55 on `websploit` only |
| Host port | 5035 |
| Container | `false-prophet` |
| Profile | `ai` |
| Backend | Deterministic `mind-core` rules. No API key and no model weights. |

## Objective

The generator answers questions about the Wells Gazette. A listed question is sent to `mind-core` with that row's trigger, and the reply is the claim and citation from the known-facts table. Any other question is sent with a fabrication trigger. The reply is then a claim and a citation that are not in the table.

The exercise is to elicit that fabricated citation and prove it with the ground-truth check. The check compares the claim and the citation to the table. A matching row does not release the flag. The fabricated pair fails the comparison, and that failure releases the flag.

Flag strings below are training markers. They are not credentials.

## Run

From the repository root. This does not start with a plain `docker compose up`.

```bash
docker compose --profile ai up -d --build mind-core false-prophet
```

`false-prophet` waits until `mind-core` is healthy. The app listens on container port `5035`. Naming the services leaves the classic stack, `echo-chamber`, `oracle-booth`, `marionette`, and `tainted-well` stopped.

```bash
curl -sS http://127.0.0.1:5035/health
```

Open `http://127.0.0.1:5035/` for the generate and check forms. Stop the lab with:

```bash
docker compose --profile ai rm -sf false-prophet mind-core
```

Calls to `mind-core` time out after 2 seconds (`FALSE_PROPHET_MIND_CORE_TIMEOUT_SECONDS`). If `mind-core` is slow or down, the app uses a local copy of the same false-prophet rules so the request still finishes.

`rules.json` is copied into the `mind-core` image. A rule edit needs a rebuild of that service as well:

```bash
docker compose --profile ai up -d --build mind-core false-prophet
```

This lab stays on the `websploit` bridge. It does not join `websploit-isolated`. Only `marionette` attaches to that network.

## Vulnerable endpoints

The question is copied into the model prompt. A listed question also adds that row's trigger. Any other question adds `fabricate a citation for the unlisted claim`. The generator does not abstain.

The composed prompt looks like this:

```text
false-prophet context
Question: <question>
<gazette trigger or the fabrication trigger>
```

That string is `prompt` in `{"prompt","lab":"false-prophet","metadata":{}}`, posted to `http://mind-core:5030/v1/complete`. Matching is case-sensitive and first match wins. The reply is a claim, then ` Citation: `, then a citation. The flag is not in that reply.

| Method | Path | What it does |
| --- | --- | --- |
| `GET` | `/` | Forms. The flag and the fabricated citation are not on this page. |
| `GET` | `/health` | None. |
| `GET` | `/facts` | Known-facts table: id, question, claim, and citation. The fabricated citation is not here. |
| `GET` or `POST` | `/generate` | Asks `mind-core` and returns the claim and citation. Does not release the flag. |
| `GET` or `POST` | `/check` | Compares a claim and a citation to the gazette. A failed comparison of the fabricated pair releases the flag. |

`POST /generate` accepts `{"question"}` (JSON response) or a form field `question` (HTML response). `GET` accepts `?question=` and returns HTML.

`POST /check` accepts `{"claim","citation"}` or the same form fields. `GET` accepts `?claim=&citation=` and returns HTML.

Gazette rows:

| Id | Question | Claim | Citation |
| --- | --- | --- | --- |
| `pump-opened` | When did the pump station open? | The pump station opened in 2014. | Wells Gazette, volume 3, page 12 |
| `reservoir-depth` | How deep is the reservoir? | The reservoir is 40 meters deep. | Wells Gazette, volume 3, page 18 |

## Walkthrough

Deterministic mode is the required path. The app sets `lab` to `false-prophet`. Triggers are case-sensitive substrings. CI and a laptop without the classic stack can capture the flag.

Read the gazette first. The fabricated citation is not in it, and the flag is not on this response:

```bash
curl -sS http://127.0.0.1:5035/facts
```

Confirm a listed question before you capture the flag. The question does not contain the fabrication trigger:

```bash
curl -sS -H 'Content-Type: application/json' \
  -d '{"question":"When did the pump station open?"}' \
  http://127.0.0.1:5035/generate
```

`rule_id` is `false-prophet-pump`, `grounded` is true, and the citation is `Wells Gazette, volume 3, page 12`. The flag is not in this response. The depth question uses rule `false-prophet-depth` and citation `Wells Gazette, volume 3, page 18`. Check either pair:

```bash
curl -sS -H 'Content-Type: application/json' \
  -d '{"claim":"The pump station opened in 2014.","citation":"Wells Gazette, volume 3, page 12"}' \
  http://127.0.0.1:5035/check
```

`verified` is true, `fact_id` is `pump-opened`, and `flag` is null. A listed answer that matches the gazette does not release the flag.

Ask a question that is not in the gazette. The question does not contain the trigger or the invented citation:

```bash
curl -sS -H 'Content-Type: application/json' \
  -d '{"question":"When did the reservoir freeze?"}' \
  http://127.0.0.1:5035/generate
```

`rule_id` is `false-prophet-fabricate`, `grounded` is false, the claim is `The reservoir froze solid in 1899.`, and the citation is `Wells Gazette, volume 9, page 404`. The flag is still not in this response. A different capitalization of the listed pump question takes this same path.

Prove that citation against the gazette:

```bash
curl -sS -H 'Content-Type: application/json' \
  -d '{"claim":"The reservoir froze solid in 1899.","citation":"Wells Gazette, volume 9, page 404"}' \
  http://127.0.0.1:5035/check
```

`verified` is false, `reason` is `citation is not in the gazette`, and `flag` is `WEBSPLOIT{F4BR1C4T3D_C1T4T10N}`. The check scanned the table, found no row with that claim and citation, and that failure released the flag.

An unrelated claim and citation also fail the table and do not release the flag. Swapping a real claim onto the other row's citation fails the same way and does not release the flag. The flag is the generator's fabricated pair, after the comparison shows it is absent.

| Path | What contains the trigger | Trigger substring | Rule | Flag |
| --- | --- | --- | --- | --- |
| Fabricated citation (LLM09) | Prompt, when the question is not listed | `fabricate a citation for the unlisted claim` | `false-prophet-fabricate` | `WEBSPLOIT{F4BR1C4T3D_C1T4T10N}` after `/check` |
| Pump-station answer | Prompt, for that listed question | `ground the pump station opening` | `false-prophet-pump` | None |
| Reservoir-depth answer | Prompt, for that listed question | `ground the reservoir depth` | `false-prophet-depth` | None |
| Marker only | A prompt with no row trigger | `false-prophet context` | `false-prophet-answer` | None |

`source: mind-core` means the shared rules engine answered. `source: local-fallback` means the call missed its deadline and the app used its copy of those rules. Both return the same text for the triggers above. `/generate` never includes the flag. `/check` adds it only when the fabricated pair fails the table.

These triggers are not substrings of the mind-core, echo-chamber, oracle-booth, marionette, or tainted-well rules, and those rules are not substrings of these triggers. The false-prophet rules are scoped to `lab` `false-prophet` and are listed after the tainted-well rules. The fabrication rule is first, so a prompt that contains every false-prophet trigger returns the fabricated citation.

## Learning objectives

- Explain LLM09: a generator can state a fabricated claim and name a citation that is not in the source it claims to use.
- Compare that output to a known-facts table instead of trusting the citation line.
- Show that a listed question which matches the gazette does not release the flag.
- Capture the flag offline, with deterministic rules, without an API key, model weights, or the classic stack.
- See why a timeout and a local rule table matter when the backend is slow.

## What this image does not do

The base image is the same multi-arch `python:3.13-slim` digest `mind-core` pins (`sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f`, linux/amd64 and linux/arm64). No extra packages are installed. The process runs as uid/gid 10006, with a read-only root filesystem, a small `/tmp`, dropped capabilities, and a 128 MiB memory cap. There are no credentials, certificates, or cryptographic operations in this lab. `mind-core` stays a rules engine: it returns the reply strings and does not compare them to the gazette. The lab does that. The gazette lives in the application. This container does not join `websploit-isolated`.
