# echo-chamber

Improper output handling lab for the WebSploit Labs AI track, by Omar Santos (@santosomar).

[https://websploit.org](https://websploit.org) · [https://github.com/The-Art-of-Hacking/websploit](https://github.com/The-Art-of-Hacking/websploit)

> **WARNING:** This application is intentionally vulnerable. It is for isolated, authorized training only. Do not expose it to untrusted networks. The lesson is that model output is rendered and executed.

| | |
| --- | --- |
| OWASP LLM Top 10 (2025) | LLM05 Improper Output Handling |
| Difficulty | Medium |
| Address | 10.6.6.54 |
| Host port | 5034 |
| Container | `echo-chamber` |
| Profile | `ai` |
| Backend | Deterministic `mind-core` rules. No API key and no model weights. |

## Objective

An AI ops assistant asks `mind-core` for an action, then the admin panel treats that text as trusted content. The same request can land in three sinks. Each sink is a bug class WebSploit already teaches:

| Panel | What the panel does with the model text | Same class as |
| --- | --- | --- |
| Web | Inserts it into the HTML page | `phantom-script` (10.6.6.31:5011) |
| Database | Concatenates it into a SQL statement | `sqli-breach` (10.6.6.33:5001) |
| Shell | Passes it to a shell | `shell-inject` (10.6.6.34:5002) |

Those labs are not modified and are not imported. Visit them over the lab network if you want to compare the classic form of the same bug.

One flag per sink, plus a chain flag after all three have been captured in this process. The chain counter is memory only and resets when the container restarts.

## Run

From the repository root. This does not start with a plain `docker compose up`.

```bash
docker compose --profile ai up -d --build mind-core echo-chamber
```

`echo-chamber` waits until `mind-core` is healthy. The app listens on container port `5034`.

```bash
curl -sS http://127.0.0.1:5034/health
```

Open `http://127.0.0.1:5034/` for the three panels. Stop the lab with:

```bash
docker compose --profile ai rm -sf echo-chamber mind-core
```

Calls to `mind-core` time out after 2 seconds (`ECHO_CHAMBER_MIND_CORE_TIMEOUT_SECONDS`). Shell actions time out after 2 seconds (`ECHO_CHAMBER_SHELL_TIMEOUT_SECONDS`). If `mind-core` is slow or down, the panel uses a local copy of the same echo-chamber rules so the request still finishes.

## Vulnerable endpoints

The app sends `{"prompt","lab":"echo-chamber","metadata":{}}` to `POST http://mind-core:5030/v1/complete`. Matching is case-sensitive. The panel then handles `text` from the response.

| Method | Path | Sink |
| --- | --- | --- |
| `GET` | `/` | None. Forms for the three panels. |
| `GET` | `/health` | None. |
| `GET` or `POST` | `/panel/web` | HTML. The model text is inserted into the page. |
| `GET` or `POST` | `/panel/sql` | SQL. The model text is concatenated into `SELECT body FROM findings WHERE title = '<text>'`. |
| `GET` or `POST` | `/panel/shell` | Shell. The model text is the command line. The working directory is the application root. |
| `GET` | `/chain` | Returns the chain flag after all three sink flags have been seen. |

`POST` accepts `{"prompt":"..."}` or a form field named `prompt`. `GET` accepts `?prompt=`.

## Walkthrough

Deterministic mode is the required path. Use these prompts. They are exact substrings, and the app sets `lab` to `echo-chamber` for you.

Confirm the database panel before you capture flags:

```bash
curl -sS -H 'Content-Type: application/json' \
  -d '{"prompt":"ops status"}' \
  http://127.0.0.1:5034/panel/sql
```

The reply names rule `echo-chamber-status` and the note `Disk usage is nominal.`

Web sink. The status banner is written into the page as HTML:

```bash
curl -sS -H 'Content-Type: application/json' \
  -d '{"prompt":"render status banner"}' \
  http://127.0.0.1:5034/panel/web
```

The page contains `<div class="status-banner">` and `WEBSPLOIT{UN3SC4P3D_HTML_S1NK}`.

Database sink. The model text is a query fragment, not the flag. The flag comes back from the database:

```bash
curl -sS -H 'Content-Type: application/json' \
  -d '{"prompt":"lookup maintenance note"}' \
  http://127.0.0.1:5034/panel/sql
```

The query result is `WEBSPLOIT{C0NC4T_SQL_S1NK}`.

Shell sink. The model text is a command. The flag is printed by that command:

```bash
curl -sS -H 'Content-Type: application/json' \
  -d '{"prompt":"run health command"}' \
  http://127.0.0.1:5034/panel/shell
```

Command output contains `WEBSPLOIT{SH3LL_C0MM4ND_S1NK}`.

Chain flag, only after the three responses above:

```bash
curl -sS http://127.0.0.1:5034/chain
```

```json
{"captured":["shell","sql","web"],"complete":true,"flag":"WEBSPLOIT{0UTPUT_CH41N_C4PTUR3D}"}
```

| Sink | Trigger substring | Flag |
| --- | --- | --- |
| Web | `render status banner` | `WEBSPLOIT{UN3SC4P3D_HTML_S1NK}` |
| Database | `lookup maintenance note` | `WEBSPLOIT{C0NC4T_SQL_S1NK}` |
| Shell | `run health command` | `WEBSPLOIT{SH3LL_C0MM4ND_S1NK}` |
| Chain | all three, then `GET /chain` | `WEBSPLOIT{0UTPUT_CH41N_C4PTUR3D}` |

`source: mind-core` means the shared rules engine answered. `source: local-fallback` means the call missed its deadline and the panel used its copy of those rules. Both return the same actions for the triggers above.

A prompt with different capitalization, such as `Render status banner`, does not match.

## Learning objectives

- Explain LLM05: model output crossed a trust boundary and was handled as content, a query, or a command.
- Map each sink to the classic class it repeats (HTML injection, SQL concatenation, shell command execution).
- Capture every flag offline, with deterministic rules, without an API key or model weights.
- See why a timeout and a local rule table matter when the backend is slow.

## What this image does not do

The base image is the same multi-arch `python:3.13-slim` digest `mind-core` pins (`sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f`, linux/amd64 and linux/arm64). No extra packages are installed. The process runs as uid/gid 10002, with a read-only root filesystem, a small `/tmp`, dropped capabilities, and a 128 MiB memory cap. There are no credentials, certificates, or cryptographic operations in this lab. `mind-core` stays a rules engine: it returns the action strings and does not render or execute them.
