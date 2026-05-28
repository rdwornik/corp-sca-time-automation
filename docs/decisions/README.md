# decisions/ — OUTPUTS (ADRs + Council transcripts)

Per ADR-60 amendment 2026-05-27 (child code repo variant) and ADR-60 addendum 2026-05-28 (child-repo baseline always-present).

This folder is the OUTPUTS zone for architectural decisions:

- `ADR-NNN-{topic}.md` — ratified architectural decisions in Michael Nygard form.
- `transcripts/` — AI Council debate outputs routed here automatically when a debate sets `target-project: corp-sca-time-automation` (per ADR-43 in `.dev-knowledge`).

## Child-repo taxonomy reminder

This is a child code repo. Its `docs/` carries `decisions/` + `audits/` + `archive/` (+ `diagrams/` where applicable). It does **not** carry `handoffs/` (centralized in `.dev-knowledge/docs/handoffs/`), `research/`, or `council-questions/`.

## Current contents

(Empty — folder seeded as baseline at the 2026-05-28 child-repo uniformity session.)

## Naming convention

- `ADR-NNN-{kebab-topic}.md` for ADRs (zero-padded sequence).
- `council-out-YYYYMMDD-HHMMSS-{topic}.md` for Council transcripts (ADR-43 router writes this).
