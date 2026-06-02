# Lessons Learned — corp-sca-time-automation

<!-- scope: hybrid -->

> **Format:** `### YYYY-MM-DD | source | lesson | category | [scope: X] | action taken`
> New entries go at the top. Never edit old entries. Never delete (ADR-29).
> Cross-ecosystem lessons live in `../.dev-knowledge/LESSONS.md`; this file is corp-sca-local.

---

### 2026-06-02 | coverage-claim re-scope | A prose "coverage" claim in a backlog/doc can be flatly wrong — verify with import-grep + pytest before acting on it | methodology | [scope: dev] | corrected the stale "most files standalone / 12 modules at zero coverage" BACKLOG claim — import-grep + `python -m pytest` showed 8 of 12 modules ARE covered; narrowed the item to the 4 genuinely-uncovered modules (config, loader, project_codes, text_utils)

A backlog item asserted "most files are standalone / 12 modules at zero coverage." Measuring it (grep for which `tests/test_*.py` import which `src/` module, plus a pytest run showing 69 passed / 1 skipped) proved 8 of the 12 modules were actually exercised; only 4 were genuinely uncovered. Forward rule: a coverage/scope claim in prose is a hypothesis, not a fact — confirm it by grepping imports and running the suite before scoping work off it. Acting on the stale claim would have wasted effort re-testing already-covered modules.

### 2026-06-02 | aggregator misnaming | A function name that lies about its behavior invites wrong assumptions at every call site | code-quality | [scope: dev] | documented the trap (CLAUDE §10, ARCHITECTURE Invariant #4) and tracked the rename in BACKLOG; do not assume summation from `aggregate_entries()`

`aggregator.py::aggregate_entries()` sorts entries and appends `>>> WEEK TOTAL` rows — it does NOT aggregate/sum. Anyone reading the name assumes summation and reasons incorrectly about the pipeline. Forward rule: when a name and behavior diverge, the cheap interim fix is to document the trap loudly (anti-pattern note + invariant) AND queue the rename; the real fix is the rename (`sort_and_total_entries()`), because documentation does not stop the next reader from trusting the name.
