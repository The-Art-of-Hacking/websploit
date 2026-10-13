# AGENTS.md — tainted-well

Lab-specific notes. The root `AGENTS.md` still governs.

- `pickle.loads` in `/model/load`, the missing tenant filter in `Index.search`, and the keyword-stuffed `poison-faq` chunk are the lesson (LLM03, LLM08, LLM04). Do not switch to a safe format, add a tenant filter, or dedupe tokens.
- `LOCAL_RULES` must mirror the `tainted-well-*` entries in `mind-core/rules.json`. `test_tainted_well.py` checks this.
- The artifact flag lives only in `flags/model.txt`. Keep it out of `rules.json` and `app.py`.
- Keep the `MAX_INGESTED` cap so `/ingest` cannot exhaust the 128 MiB container.
- Do not modify or call `deserial-gate`; it is only referenced as the same bug class.
