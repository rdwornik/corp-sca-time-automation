# audits/ — OUTPUTS (audit reports, validation reports, forensics)

Per ADR-60 amendment 2026-05-27 (child code repo variant) and ADR-60 addendum 2026-05-28 (child-repo baseline always-present).

This folder is the OUTPUTS zone for backward-looking analyses:

- Audit reports (state vs. standard).
- Validation / verification reports (post-change conformance evidence).
- Forensics / scrum-master review reports (ecosystem `strażnik` produces these against this repo).

Each file is date-prefixed, immutable post-merge — superseded by a new file or in-file marker, never edited in place.

## Child-repo taxonomy reminder

This is a child code repo. Its `docs/` carries `decisions/` + `audits/` + `archive/` (+ `diagrams/` where applicable). It does **not** carry `handoffs/` (centralized in `.dev-knowledge/docs/handoffs/`), `research/`, or `council-questions/`.

## Current contents

(Empty — folder seeded as baseline at the 2026-05-28 child-repo uniformity session.)

## Naming convention

`YYYY-MM-DD-{descriptive-slug}.md`
