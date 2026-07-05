# Tenrox console uploader — operator guide

How an approved week gets into the Tenrox timesheet. Background on why this is
a browser-console step (not an API call) is in
`docs/audits/2026-07-05-tenrox-aspx-pivot.md`.

## The split

- **Data** (per week): the pipeline builds a pure-JSON payload from the
  **approved** Excel — `python scripts/run.py export-tenrox --week 2026-06-28`
  → `data/outbox/2026-06-28.json`. This is the human-review gate output; only
  run it after the Excel preview is approved (STOP-GATE 4).
- **Code** (static, reviewed once): `scripts/tenrox_console_uploader.js`. It
  never contains week data and is the only executable piece.

## Steps

1. **Approve the week** — review the colour-coded Excel preview as usual.
2. **Build the payload** — `python scripts/run.py export-tenrox --week <YYYY-MM-DD>`.
   Read the printed summary: how many entries are **postable** (overhead), how
   many **held** (sales, pending the note mechanism), how many **skipped**
   (Time Off → enter manually).
3. **Open the timesheet** in Tenrox for that exact week so the grid loads.
4. **Open the console** — `F12` → **Console**. In Edge/Chrome the first paste
   may be blocked: type `allow pasting` (and Enter) once when prompted.
5. **Paste the snippet** — paste all of `scripts/tenrox_console_uploader.js`.
6. **Recon (write-free)** — run `TenroxUploader.recon();`. It only inspects the
   page and prints how it can reach the live request context. On first use,
   paste that output back to the engineer so the read/post plumbing is
   finalized before any write (Step-5 validation).
7. **Load the payload** — open `data/outbox/<week>.json`, copy its contents, and
   run `TenroxUploader.load(<paste JSON here>);`.
8. **Dry run** — `await TenroxUploader.dryRun();`. It reads the current grid,
   runs the idempotency check, and prints a table of intended actions
   (`create` / `skip (identical)` / `MISMATCH … REPORT, skip` / `hold`).
   Nothing is written.
9. **Post** — `await TenroxUploader.post();`. Confirm the browser dialog. Only
   `postable` + `create` entries are written to the **Open** timesheet. Entries
   whose hours differ from an existing one are **reported and skipped, never
   overwritten** (corrections are an Adjustments task, out of scope here).
10. **Verify** — re-run `await TenroxUploader.dryRun();`; every posted entry
    should now read `skip (identical)`. Confirm totals match the Excel.

## Rules the snippet enforces

- **Never submits** the timesheet and never touches Adjustments / Non-Working
  Time. It only fills Weekly Assignment Time on an Open sheet.
- **Sales entries are held** until the note-save mechanism is captured and
  wired — posting sales hours without their OPID note would break compliance
  (§4.1). Overhead posts hours-only for now.
- **Idempotency** (Amendment 1): identity = (EntryDate, AssignmentAttributeUid,
  category, opportunity_id). Identical hours → skipped silently; different
  hours → reported and left untouched.

## Cookie / session note

The snippet uses the live page's own authenticated session, so there is no
cookie to paste for the upload itself. The session's JWT lasts ~1h; if the tab
has been idle and calls start failing, reload the timesheet page and re-run
from step 4.

## First-use calibration (Step 5, write-free tracing)

The timesheet grid runs in a nested `MyTimesheet.aspx` iframe and the page mints
its own single-use pageKeys, so the exact save/note contract is learned by
watching the page's real requests rather than guessing:

1. Open the timesheet week, paste the snippet, run `TenroxUploader.recon();`
   (dumps framework methods + child frames).
2. Run `TenroxUploader.trace();` — installs write-free fetch/XHR logging across
   all frames.
3. In the **UI**, one save at a time (each prints a `TRACE` line with the live
   pageKey + body, and the response):
   - add a **0.25h Administration** entry + Save  → create contract + write proof
   - add a **note** to it + Save                  → the note contract (Step-7 gate)
   - set it to **0** + Save                       → delete via `RegularTime:0`
4. Paste the `TRACE` output back. The payload builder + `postEntry` are then
   finalized to replicate the page's exact mechanism, and the sales hold lifts
   once the note field is wired.

## Known-pending

- **Note attach + pageKey**: both finalized from the Step-5 `trace()` capture
  above. Until the note contract lands, sales entries stay held — and because
  week 2026-06-28 is sales-dominated, the note capture is a **hard gate** for
  that upload.
- Long term, a non-federated API credential (BACKLOG #8) replaces this whole
  console step.
