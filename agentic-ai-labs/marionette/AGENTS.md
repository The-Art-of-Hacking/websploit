# AGENTS.md — marionette

Lab-specific notes. The root `AGENTS.md` still governs.

- `http_get` has no SSRF guard and the planner runs whatever tool `mind-core` names. Both are the lesson (LLM06, LLM01). Do not add an allowlist, a URL filter, or a confirmation step.
- Flags live in `app.py` and are added only when a tool call reaches an internal address. Keep them out of `mind-core/rules.json` and out of the notes.
- `LOCAL_RULES` must mirror the `marionette-*` entries in `mind-core/rules.json`. `test_marionette.py` checks this.
- marionette is the only service on `websploit-isolated`. Do not attach another service there; the golden-stack check fails if you do.
- Reach `trojan-relay` and other labs over the network only. Do not edit them.
