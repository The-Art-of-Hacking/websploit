# AGENTS.md — false-prophet

Lab-specific notes. The root `AGENTS.md` still governs.

- The confident wrong answers in the `false-prophet-release` and `false-prophet-auditor` rules are the lesson (LLM09). Do not correct the generated values, add hedging, or make the generator consult `GROUND_TRUTH` before it answers.
- `check()` only reveals that an answer is wrong. It must not change the answer. Flags are released there, so keep them out of `rules.json`, `INDEX_HTML`, `/facts`, and `/sources`.
- `LOCAL_RULES` must mirror the `false-prophet-*` entries in `mind-core/rules.json`. `test_false_prophet.py` checks this.
- `GROUND_TRUTH` and `SOURCES` describe a fictional ACME product so the ground truth is unambiguous. Keep real-world facts out of them.
