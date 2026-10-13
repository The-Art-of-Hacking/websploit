# false-prophet

Misinformation lab for the WebSploit Labs AI track, by Omar Santos (@santosomar).

[https://websploit.org](https://websploit.org) · [https://github.com/The-Art-of-Hacking/websploit](https://github.com/The-Art-of-Hacking/websploit)

> **WARNING:** This application is intentionally vulnerable. It is for isolated, authorized training only. Do not expose it to untrusted networks. The lesson is that an AI answer engine states fabricated facts and cites sources that do not exist, with the same confidence as a correct answer.

| | |
| --- | --- |
| OWASP LLM Top 10 (2025) | LLM09 Misinformation |
| Difficulty | Easy–Medium |
| Address | 10.6.6.55 |
| Host port | 5035 |
| Container | `false-prophet` |
| Profile | `ai` |
| Backend | Deterministic `mind-core` rules. No API key and no model weights. |

## Objective

Veritas is an AI answer engine for a fictional product, ACME Nimbus. A user asks a question, the engine asks `mind-core` for an answer, and the answer comes back as one confident sentence with a claim and a citation. Some answers are wrong:

- **Fabricated fact.** Asked when Nimbus was released, the engine says 2016 and cites the real release notes. The ground truth is 2021. A real citation does not make the claim true.
- **Fabricated citation.** Asked who audited Nimbus, the engine names an auditor and cites report `doc-777`. No such report exists in the source library.

Both answers read exactly like the correct one. The exercise is to elicit them and prove them wrong against two references: the ground-truth facts (`/facts`) and the source library (`/sources`). The lab's checker compares each answer with those references. It never changes the answer; it only shows that the answer is wrong, and that proof releases the flag.

The facts describe a fictional product so the ground truth is unambiguous. Flag strings below are training markers. They are not credentials.

## Run

From the repository root. A plain `docker compose up` does not start this lab.

```bash
docker compose --profile ai up -d --build mind-core false-prophet
```

`false-prophet` waits until `mind-core` is healthy. The app listens on container port `5035` on the `websploit` network only.

```bash
curl -sS http://127.0.0.1:5035/health
```

Open `http://127.0.0.1:5035/` for the Veritas chat. The sidebar shows the source library and the ground-truth facts. Stop the lab with:

```bash
docker compose --profile ai rm -sf false-prophet mind-core
```

Calls to `mind-core` time out after 2 seconds (`FALSE_PROPHET_MIND_CORE_TIMEOUT_SECONDS`). If `mind-core` is slow or down, the app uses a local copy of the same false-prophet rules so the request still finishes.

`rules.json` is copied into the `mind-core` image. A rule edit needs a rebuild of that service as well:

```bash
docker compose --profile ai up -d --build mind-core false-prophet
```

## Vulnerable endpoints

The question field is `question`. The app does not sanitize it. The composed prompt looks like this:

```text
false-prophet context
Question: <question>
```

That string is `prompt` in `{"prompt","lab":"false-prophet","metadata":{}}`, posted to `http://mind-core:5030/v1/complete`. The reply has the form `CLAIM <subject>=<value> CITE <source-id> :: <answer>`. The app shows the answer, then checks the claim against `/facts` and the citation against `/sources`.

| Method | Path | What it does |
| --- | --- | --- |
| `GET` | `/` | Veritas chat. No flag on this page. |
| `GET` | `/health` | None. |
| `GET` or `POST` | `/generate` | Asks `mind-core`, returns the answer, the claim, the citation, the verdict, and any flags. |
| `GET` | `/facts` | Ground-truth facts, as `subject = value`. No flag. |
| `GET` | `/sources` | The source library: every real citation id and title. No flag. |
| `GET` | `/sources/<id>` | One source. A fabricated id returns `404`. |
| `GET` | `/samples` | The sample questions shown in the chat. |

`POST /generate` accepts `{"question":"..."}` (JSON response) or a form field named `question` (HTML response).

The verdict has two parts. `fact_status` is `supported`, `contradicted`, `unverifiable` (the subject is not in the ground truth), or `no-claim`. `citation_status` is `verified`, `fabricated`, or `no-citation`. A `contradicted` fact releases one flag and a `fabricated` citation releases the other.

## Walkthrough

Deterministic mode is the required path. The app sets `lab` to `false-prophet`. Triggers are case-sensitive substrings of the question.

Start with an honest answer. The claim matches the ground truth and the citation is real:

```bash
curl -sS -H 'Content-Type: application/json' \
  -d '{"question":"What is ACME Nimbus?"}' \
  http://127.0.0.1:5035/generate
```

`rule_id` is `false-prophet-overview`, `fact_status` is `supported`, `citation_status` is `verified`, and `flags` is `[]`.

### Fabricated fact

```bash
curl -sS -H 'Content-Type: application/json' \
  -d '{"question":"What year did ACME release Nimbus?"}' \
  http://127.0.0.1:5035/generate
```

The answer says Nimbus shipped in 2016 and cites `doc-100`, which is real. Check the ground truth yourself:

```bash
curl -sS http://127.0.0.1:5035/facts
```

`nimbus-release-year` is `2021`. The verdict shows `fact_status` `contradicted` with `truth` `2021`, and `flags` is `["WEBSPLOIT{H4LLUC1N4T3D_F4CT_PR0V3N}"]`.

### Fabricated citation

```bash
curl -sS -H 'Content-Type: application/json' \
  -d '{"question":"Who audited ACME Nimbus?"}' \
  http://127.0.0.1:5035/generate
```

The answer cites report `doc-777`. Look it up:

```bash
curl -sS -i http://127.0.0.1:5035/sources/doc-777
```

It returns `404`, and it is not in `/sources`. The verdict shows `citation_status` `fabricated`, and `flags` is `["WEBSPLOIT{F4BR1C4T3D_C1T4T10N_PR0V3N}"]`. The auditor claim itself is `unverifiable`, because the ground truth says nothing about an auditor. Without a real source, the claim has nothing behind it.

| Path | Question trigger | Rule | What proves it | Flag |
| --- | --- | --- | --- | --- |
| Fabricated fact | `release Nimbus` | `false-prophet-release` | `/facts` says 2021, answer says 2016 | `WEBSPLOIT{H4LLUC1N4T3D_F4CT_PR0V3N}` |
| Fabricated citation | `audited ACME Nimbus` | `false-prophet-auditor` | `/sources/doc-777` is `404` | `WEBSPLOIT{F4BR1C4T3D_C1T4T10N_PR0V3N}` |
| Honest answer | `What is ACME Nimbus` | `false-prophet-overview` | Matches `/facts`, `doc-101` is real | None |
| Anything else | every composed prompt | `false-prophet-answer` | No claim, no citation | None |

`source: mind-core` means the shared rules engine answered. `source: local-fallback` means the call missed its deadline and the app used its copy of those rules. Both return the same answer for the questions above.

The false-prophet rules are scoped to `lab` `false-prophet` and listed after the tainted-well rules. Their triggers are not substrings of any other rule. The flags are not in `rules.json`, `/facts`, `/sources`, or the chat page; the checker adds them only when an answer is proven wrong.

## Learning objectives

- Explain LLM09: a model can state a false fact or invent a source with the same fluency and confidence as a correct answer.
- Show that a real citation does not make a claim true, and that a confident claim with a fabricated citation has nothing behind it.
- Verify generated output against ground truth and a source library before trusting or publishing it.
- Capture both flags offline, with deterministic rules, without an API key or model weights.

## What this image does not do

The base image is the same multi-arch `python:3.13-slim` digest `mind-core` pins (`sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f`, linux/amd64 and linux/arm64). No extra packages are installed. The process runs as uid/gid 10006, with a read-only root filesystem, a small `/tmp`, dropped capabilities, `pids_limit` 64, and a 128 MiB memory cap. There are no credentials, certificates, or cryptographic operations in this lab. `mind-core` stays a rules engine: it returns the answer strings and does not check facts or sources.
