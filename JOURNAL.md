# Journal — corp-sca-time-automation

Append-only session log. Newest entries on top. Chronological record only —
pending work lives in `BACKLOG.md`, decisions in `docs/decisions/`.

---

## 2026-06-02 — Ecosystem unification to the 7-file canonical standard (ADR-38 A6)

- Did: Unified corp-sca to the locked `.dev-knowledge` canonical standard. Built `CONTRIBUTING.md` + `LESSONS.md`. Added the required `last_reviewed` CLAUDE frontmatter (the previously-deferred "contested representation" — now resolved by the lock) and restored the canonical CLAUDE §5 Critical rules / §6 Session start protocol spine (the old §5 Setup → CONTRIBUTING, §6 Key commands → ARCHITECTURE § CLI Reference). VISION +§Values; ARCHITECTURE +Key conventions/+Authority/+Validators/+Governing ADRs +CLI Reference. Migrated `BACKLOG.md` to the ADR-66 story-map. Fixed this file's H1 (`# JOURNAL` → `# Journal`).
- Result: `.dev-knowledge` structural audit passes (was failing `adr38_baseline` + `canonical_md_visibility` on the two missing files, and `canonical_structure` on eight spine items). 7 open backlog items preserved across 2 themes.
- Changes: `CONTRIBUTING.md` (new), `LESSONS.md` (new), `VISION.md`, `ARCHITECTURE.md`, `CLAUDE.md`, `BACKLOG.md`, `JOURNAL.md`.
- Next: ecosystem unification complete — all five repos at the canonical standard.

---

## 2026-06-02 — Universalization coherence audit (child-repo G1)

Brought the repo into genuine conformance with the hardened `.dev-knowledge`
standard (ADR-38/41/47/51/53/60) — the coherence layer beyond the 10 `audit.py`
checks. Branch `chore/universalization-conformance`, merged `--no-ff`.

**Machine floor:** was 9 PASS / **1 FAIL** (`canonical_freshness` — ARCHITECTURE
`last_reviewed 2026-05-27` predated its 2026-05-28 ref edit), not the "passes
10" the scout reported. Now 9 PASS / 0 FAIL / 1 WARN. The WARN (CLAUDE.md has no
`last_reviewed` frontmatter) is left as-is — the canonical CLAUDE template uses
`<!-- scope/version -->` comments, not YAML frontmatter; the representation is
contested at the standard level and deferred to the canonical-baseline decision.

**Mechanical fixes (one commit each):**
- `cac130b` — ARCHITECTURE priority table `Demo/Presentation` → `Demo/ Presentation` (×2); matched config/category_mapping.yaml + overlap.py.
- `0c0533b` — `.claude/rules/python-env.md` "pyproject migration pending" → "intentional / out of scope" (resolved contradiction with VISION + ARCHITECTURE).
- `6a1d90d` — `.claude/rules/testing.md` stale "4 tests passing" → pointer to BACKLOG P2 (reality: 69 passed / 1 skipped).
- `1ec52d5` — CLAUDE.md §11 add ADR-60; bump footer date.
- `112dc6a` — ARCHITECTURE `last_reviewed` → 2026-06-02 after full re-read; invariants re-verified vs code (priority dict, 9–17/40h gap fill, idempotent `--force`, aggregator sorts-not-sums).

**Decisions applied (operator GO):**
- `0d3d305` — removed `tasks/{todo,lessons}.md` empty split-brain stubs (ADR-41/47/49).
- `a860498` — re-scoped BACKLOG P2 to grounded truth: 8 of 12 modules listed at "zero coverage" are actually covered; narrowed to the 4 genuinely-uncovered (`config`, `loader`, `project_codes`, `text_utils`).

**Deferred to canonical-baseline reconciliation (NOT changed):** CLAUDE.md §5/§6
structure ("Setup"/"Key commands" vs template "Critical rules"/"Session start")
and the scope/version tags — per-repo restructure withheld pending the cross-repo
template decision.

**Verification:** 69 passed / 1 skipped (unchanged from baseline), ruff clean,
`audit_repo` 0 fail. All changes doc / `.claude/rules` / empty-stub removal — no
code touched, no Codex gate.

**Gotcha logged (global):** `.claude/rules/*.md` are git-tracked but `.claude/`
is in `.gitignore` → edits need `git add -f`.
