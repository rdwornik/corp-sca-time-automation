# Tenrox loader — ASPX-surface pivot (design note)

**Date:** 2026-07-05 · **Branch:** `feature/tenrox-loader` · Supersedes the REST/OAuth design in the approved plan (decisions 2 & 6).

> **Outcome (2026-07-05):** the ASPX handler cannot be driven from standalone Python either — see "Addendum: neither Python path works" below. Final write path = an **in-page console snippet** run in the operator's live authenticated tab, fed a pipeline-generated JSON payload. Read/idempotency also move in-browser. This note's contract sections remain accurate (they describe the same requests the snippet issues).

## Why the pivot

The approved plan targeted the Upland PSA REST API (`/api/token` password grant, `/api/v2/...`). STOP-GATE 2 proved that surface unusable for this tenant (probes 2026-07-05, secrets redacted):

- Password grant → `400 Invalid credentials` on the confirmed-correct org `JDASoftware` (SSO-federated account has no local password).
- UI session cookie on `/api/*` → `500 "Sequence contains no elements"` inside `TenroxAuthorizeAttribute.OnAuthorization` (API authorize filter cannot build context from the UI cookie).
- `tenant.token` JWT as bearer → `403 Invalid token.`
- Handoff's `/api/v2/users/me` etc. return `404` (routes absent on this tenant).

Operator decision (2026-07-05): pivot the loader to the UI's own async postback surface, cookie-authenticated. REST becomes a future drop-in auth swap if Upland/IT issue a non-federated API credential (BACKLOG escalation item).

## The two ASPX contracts (captured from the live UI)

Both are `POST /TEnterprise/Entry/TimeEntry/MyTimesheet.aspx?r=<rand>&pageKey=<key>`, `content-type: application/x-www-form-urlencoded`, headers `csrftoken: 0` + `origin`/`referer` `https://jda.tenrox.net`, cookie-authenticated + `OrgName` header.

### Read — `pageMethod=GetTimesheetDetails`
Body: `pageMethod=GetTimesheetDetails&IsTenroxAsyncCallback=true&usercontrolid=&requestData=<url-encoded JSON>` where requestData = `{date, userUniqueId, roleObjectType:26, roleObjectUniqueId:-1, comingFrom:"MYTIMESHEET", hasPrevious:false, hasNext:false, pinnedAssignmentAttributeIds:[]}`. `date` selects the period (pass the target week's Sunday). Response carries `main.timesheetId` (per-week), `assignments[]` (task UIDs), `timeEntries`, `notes`, and `currentState` (Open/Submitted). Replaying it IS discovery (`scripts/tenrox_discovery.py`).

### Write — `pageMethod=UpdateTimeEntries`
Body: `...&entries=<url-encoded JSON array>`. Each entry: `UserUid, StartDate/EndDate (week bounds MM-DD-YYYY), EntryDate (MM-DD-YYYY), TimesheetUid, TemplateUid, AssignmentAttributeUid, EntryUid ("-1"=create / real uid=update), RegularTime (SECONDS: 0.25h=900), Overtime/DoubleOvertime/EntryState/IsETC/EtcFlag, AssignmentAttributeData{IsNonWorking, ClientId, ProjectId, WorkTypeId, TeamId, ChargeId}`.

## Binding facts

- **`RegularTime` is in SECONDS.** hours × 3600. Delete = update the entry with `RegularTime: 0` (used for the Step-5 write-probe cleanup; never the Adjustments section).
- **`TimesheetUid` is per-week** — `9022043` (week 2026-06-28) vs `9022044` (week 2026-07-05). Read it from the grid-load for the target week; never reuse across weeks.
- **Assignment rows are user-level and stable** (valid 2015/2020 → 2737); UIDs live in `config/tenrox_mapping.yaml`. The grid-load `AssignmentAttributeData` fields map 1:1 into the SAVE payload (verified: Sales Activities `4823453` → 10957/12226/26882/3/0 matches the SAVE capture).
- **Note attach mechanism not yet captured.** SAVE posted hours with no note field; grid-load shows `notes:[]`. Hours-only posting works (Step 5 unblocked); sales OPID notes (§4.1) need one more capture before Step 7.
- **Cookie lifecycle:** per-run paste, ~1h JWT TTL. On 401/login-HTML mid-run → STOP, ask for a fresh cookie (no retry loop). Same discipline as `GRAPH_ACCESS_TOKEN`.

## STOP-GATE 3 result

Clear. All five required work types have assignment rows in the grid-load: Sales Activities (`4823453`), Administration (`4823451`), Internal Project Support (`4823462`), Learning and Development (`4823452`), Travel Administration (`4823454`); plus Leave Time (`4823450`, non-working, loader-skipped). No manual UI seeding needed. (Assignment UIDs read from the operator-pasted grid-load response — that JSON is the verified READ-contract evidence.)

## Addendum: neither Python path works → in-page snippet

Replaying the ASPX handler from standalone Python fails regardless of key freshness. Evidence (all 2026-07-05, valid cookie, secrets redacted):

| Test | Surface / key | Result |
|---|---|---|
| REST password grant | `/api/token`, org JDASoftware | `400 Invalid credentials` (SSO-federated; no local pw) |
| REST cookie | `/api/*` | `500` in `TenroxAuthorizeAttribute` / bearer `403 Invalid token` |
| App liveness | `GET MainFrame2.aspx` | `200` — session IS authenticated |
| EXP-1a | `GetTimesheetDetails`, aged AJAX key `688c34fa` | `302 → Error.aspx` |
| EXP-1b | `GetTimesheetDetails`, fresh navigation key `cddb788f` | `302 → Error.aspx` |
| EXP-1c | `GetTimesheetDetails`, seconds-fresh AJAX key `4863b559` | `302 → Error.aspx` |
| EXP-2 | cold-navigate `MyTimesheet.aspx`, no key (self-mint) | `→ Error.aspx`, zero mintable keys |

**Diagnosis:** `pageKey` is **single-use** — consumed by the browser's own AJAX call, so any captured key is spent on replay; and no unused key can be minted from Python (EXP-2). The app session is alive (MainFrame2 `200`), so this is not auth expiry — the handler simply is not drivable outside a live browser tab.

**Decision (operator, 2026-07-05): in-page console snippet.**
- **Strict code/data split.** `scripts/tenrox_console_uploader.js` is a static, reviewed-once repo artifact. The per-week payload is pure JSON generated by the pipeline from the **approved Excel only** (`run.py export-tenrox --week <YYYY-MM-DD>` → `data/outbox/<week>.json`). Never generate executable code per week.
- **Snippet flow:** (a) read current grid via the page's own live context + run the Amendment-1 idempotency check in-browser; (b) print a dry-run table; (c) `confirm()` gate; (d) POST via `UpdateTimeEntries` using the page's own live pageKey/session; (e) report per-entry results + posted-vs-payload diff. On idempotency mismatch: report, skip, never overwrite.
- **Notes:** the note-save request is still uncaptured. Hours-only posting works now (overhead OK); **sales entries without a working note must NOT be posted** until the note contract is folded in.
- **`src/tenrox.py`** is therefore a payload BUILDER (DataFrame → entries JSON via `config/tenrox_mapping.yaml`: day-grouping, hours→seconds, note assembly, sales-note guard, idempotency identity keys), not a poster. `scripts/tenrox_discovery.py` is retained as the STOP-GATE-2 probe harness and the future REST path if a non-federated credential lands (BACKLOG #8).
- **Long-term:** BACKLOG #8 (non-federated API credential) is the preferred durable path; full browser automation (Playwright, persistent SSO profile) is a separate future slice.

