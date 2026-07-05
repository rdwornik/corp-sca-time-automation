/* Tenrox in-page console uploader  (static, reviewed-once artifact)
 * ---------------------------------------------------------------------------
 * WHY THIS EXISTS
 *   The Tenrox timesheet handler cannot be driven from standalone Python (the
 *   ASPX pageKey is single-use and REST is dead under SSO federation - see
 *   docs/audits/2026-07-05-tenrox-aspx-pivot.md). This snippet runs INSIDE the
 *   operator's live, authenticated timesheet tab, where the page mints valid
 *   pageKeys itself, and posts the pipeline-generated payload from there.
 *
 * STRICT CODE/DATA SPLIT
 *   This file is STATIC and reviewed once. It contains NO per-week data. The
 *   per-week payload is pure JSON built by `run.py export-tenrox --week ...`
 *   and handed to `.load(...)`. Never paste generated code.
 *
 * SAFETY CONTRACT (mirrors the mission stop-gates)
 *   - Default action is RECON: it only READS/inspects; it never writes.
 *   - `.post()` requires an explicit confirm() and only posts entries the
 *     payload marked `postable:true` (overhead now; sales held until the
 *     note-save mechanism is wired).
 *   - Amendment-1 idempotency: identity = (entry_date, assignment_attribute_uid,
 *     category, opportunity_id). Identical hours -> skip. Different hours ->
 *     REPORT and SKIP (never overwrite). Never touches Adjustments / submit.
 *
 * STEP-5 VALIDATION (read before first write)
 *   The exact way the page exposes a fresh pageKey + its populated-grid entry
 *   shape were not observable from an empty timesheet. So the FIRST thing to
 *   run in-browser is `TenroxUploader.recon()` (write-free). Paste its output
 *   back so the read/post plumbing below can be finalized before any POST.
 *
 * USAGE (see docs/tenrox-console-uploader.md)
 *   1. Open the target timesheet week in Tenrox.
 *   2. F12 -> Console. (Edge/Chrome may require typing "allow pasting" once.)
 *   3. Paste this whole file.
 *   4. TenroxUploader.recon();                       // safe: reports context
 *   5. TenroxUploader.load(<paste the week JSON>);   // loads the payload
 *   6. await TenroxUploader.dryRun();                // read + idempotency, no writes
 *   7. await TenroxUploader.post();                  // confirm() then post postable entries
 */
(function () {
  "use strict";

  const BASE = location.origin + "/TEnterprise";
  const SAVE_URL = BASE + "/Entry/TimeEntry/MyTimesheet.aspx";

  const state = { payload: null, context: null, grid: null };

  function log(...a) { console.log("[tenrox]", ...a); }
  function warn(...a) { console.warn("[tenrox]", ...a); }

  // ---- RECON: write-free discovery of the page's request context -----------
  function recon() {
    const ctx = { url: location.href, inIframe: window.top !== window.self };

    // 1. pageKey candidates: query string of this frame + any 32-hex tokens
    //    the page has stashed in globals.
    const qs = new URLSearchParams(location.search);
    ctx.urlPageKey = qs.get("pageKey") || null;
    const hex32 = /\b[0-9a-f]{32}\b/i;
    ctx.globalPageKeyVars = Object.keys(window).filter(k => {
      try {
        const v = window[k];
        return typeof v === "string" && hex32.test(v) && /page?key/i.test(k);
      } catch (_) { return false; }
    });

    // 2. Tenrox async page-method helpers the page uses for its own AJAX
    //    (reusing one of these means the page mints/consumes its own pageKey).
    const helperNames = Object.keys(window).filter(k =>
      /tenrox|pageMethod|asyncCallback|timesheet/i.test(k));
    ctx.candidateHelpers = helperNames.slice(0, 40).map(k => {
      let t; try { t = typeof window[k]; } catch (_) { t = "?"; }
      return `${k}:${t}`;
    });

    // 3. Any in-page timesheet model already loaded (read for uid + entries).
    ctx.modelGlobals = Object.keys(window).filter(k =>
      /timesheet|assignment|entries/i.test(k)).slice(0, 40);

    // 4. Methods on the framework objects that might BE the page's own save
    //    path (reusing one sidesteps the single-use-pageKey problem entirely).
    function methodsOf(objName) {
      let o; try { o = window[objName]; } catch (_) { return null; }
      if (!o || typeof o !== "object") return null;
      const names = new Set();
      for (let p = o; p && p !== Object.prototype; p = Object.getPrototypeOf(p)) {
        for (const k of Object.getOwnPropertyNames(p)) {
          try { if (typeof o[k] === "function") names.add(k); } catch (_) { /* getter */ }
        }
      }
      return [...names].filter(k => /save|update|post|entry|entries|submit|timesheet|call|method|key/i.test(k)).slice(0, 40);
    }
    ctx.frameworkMethods = {
      Tenrox: methodsOf("Tenrox"), tenrox: methodsOf("tenrox"),
      timesheetObject: methodsOf("timesheetObject"),
    };

    // 5. Same-origin child frames (the grid runs in the MyTimesheet iframe).
    ctx.childFrames = [];
    try {
      for (let i = 0; i < window.frames.length; i++) {
        try { ctx.childFrames.push(window.frames[i].location.pathname); }
        catch (_) { ctx.childFrames.push("<cross-origin>"); }
      }
    } catch (_) { /* noop */ }

    state.context = ctx;
    log("RECON (write-free). Paste this back to finalize the uploader:");
    console.log(JSON.stringify(ctx, null, 2));
    log("Next: TenroxUploader.load(<week JSON>) then TenroxUploader.dryRun()");
    return ctx;
  }

  // ---- payload loading -----------------------------------------------------
  function load(payload) {
    if (typeof payload === "string") payload = JSON.parse(payload);
    if (!payload || !Array.isArray(payload.entries)) {
      throw new Error("payload must be the export-tenrox JSON object");
    }
    state.payload = payload;
    const s = payload.summary || {};
    log(`loaded week ${payload.week_beginning}: ` +
        `${s.postable_count} postable / ${s.held_count} held / ${s.skipped_count} skipped`);
    return payload;
  }

  // ---- live grid read (uses the page's own POST helper once recon confirms) -
  async function readGrid() {
    if (!state.payload) throw new Error("call load(payload) first");
    // Read the current week via the page's own GetTimesheetDetails. The pageKey
    // is resolved from the live page (see resolvePageKey); this is a READ.
    const body = new URLSearchParams({
      pageMethod: "GetTimesheetDetails",
      IsTenroxAsyncCallback: "true",
      usercontrolid: "",
      requestData: JSON.stringify({
        date: state.payload.week_beginning,
        userUniqueId: state.payload.timesheet.user_unique_id,
        roleObjectType: 26, roleObjectUniqueId: -1,
        comingFrom: "MYTIMESHEET", hasPrevious: false, hasNext: false,
        pinnedAssignmentAttributeIds: [],
      }),
    });
    const data = await tenroxPost(body);
    state.grid = data;
    return data;
  }

  // Existing entries keyed by the Amendment-1 identity. Finalized once a
  // populated timesheet's entry shape is confirmed at Step 5 (recon output).
  function indexExisting(grid) {
    const idx = new Map();
    const entries = (grid && (grid.timeEntries || grid.entries)) || [];
    for (const e of entries) {
      const key = [
        e.EntryDate || e.entryDate, e.AssignmentAttributeUid || e.assignmentAttributeUid,
        e.Category || e.category || "", e.OpportunityID || e.opportunity_id || "",
      ].join("|");
      idx.set(key, e);
    }
    return idx;
  }
  function identityOf(entry) {
    return [entry.entry_date, entry.assignment_attribute_uid, entry.category, entry.opportunity_id].join("|");
  }

  // ---- dry run: read + idempotency, NO writes ------------------------------
  async function dryRun() {
    const p = state.payload;
    if (!p) throw new Error("call load(payload) first");
    let grid = null;
    try { grid = await readGrid(); }
    catch (err) { warn("could not read live grid (idempotency degraded):", err.message); }
    const existing = grid ? indexExisting(grid) : new Map();

    const plan = [];
    for (const e of p.entries) {
      if (!e.postable) { plan.push({ ...e, action: "hold", reason: e.hold_reason }); continue; }
      const hit = existing.get(identityOf(e));
      if (!hit) { plan.push({ ...e, action: "create" }); continue; }
      const hitSecs = Number(hit.RegularTime ?? hit.regularTime ?? hit.seconds);
      if (hitSecs === e.seconds) plan.push({ ...e, action: "skip (identical)" });
      else plan.push({ ...e, action: `MISMATCH (existing ${hitSecs}s vs payload ${e.seconds}s) - REPORT, skip` });
    }
    console.table(plan.map(x => ({
      date: x.entry_date, category: x.category, hours: x.hours,
      seconds: x.seconds, action: x.action,
    })));
    state.plan = plan;
    log("dry run only - nothing posted. Run TenroxUploader.post() to write postable creates.");
    return plan;
  }

  // ---- post: confirm() gated, postable creates only ------------------------
  async function post() {
    if (!state.plan) { warn("running dryRun() first"); await dryRun(); }
    const creates = state.plan.filter(x => x.action === "create");
    const mism = state.plan.filter(x => String(x.action).startsWith("MISMATCH"));
    if (mism.length) warn(`${mism.length} idempotency mismatch(es) will be SKIPPED (never overwritten).`);
    if (!creates.length) { log("nothing to create."); return []; }
    if (!confirm(`Post ${creates.length} entries to the OPEN timesheet? (never submits)`)) {
      log("cancelled by operator."); return [];
    }
    const results = [];
    for (const e of creates) {
      try {
        const res = await postEntry(e);
        results.push({ date: e.entry_date, category: e.category, ok: true, res });
      } catch (err) {
        results.push({ date: e.entry_date, category: e.category, ok: false, error: String(err) });
      }
    }
    console.table(results.map(r => ({ date: r.date, category: r.category, ok: r.ok })));
    // posted-vs-payload diff
    const posted = results.filter(r => r.ok).length;
    log(`posted ${posted}/${creates.length}. Re-run dryRun() to confirm the grid matches the payload.`);
    return results;
  }

  function postEntry(e) {
    const p = state.payload;
    const entry = {
      UserUid: p.timesheet.user_unique_id,
      StartDate: p.start_date, EndDate: p.end_date, EntryDate: e.entry_date,
      TemplateUid: p.timesheet.template_uid,
      TimesheetUid: (state.grid && state.grid.main && state.grid.main.timesheetId),
      AssignmentAttributeUid: e.assignment_attribute_uid,
      IsETC: 0, EtcFlag: "", EntryUid: "-1",
      RegularTime: e.seconds, Overtime: 0, DoubleOvertime: 0, EntryState: 0,
      AssignmentAttributeData: {
        IsNonWorking: e.attribute_data.is_non_working,
        ClientId: e.attribute_data.client_id, ProjectId: e.attribute_data.project_id,
        WorkTypeId: e.attribute_data.work_type_id, TeamId: e.attribute_data.team_id,
        ChargeId: e.attribute_data.charge_id,
      },
    };
    if (!entry.TimesheetUid) throw new Error("no live TimesheetUid (read the grid first)");
    const body = new URLSearchParams({
      pageMethod: "UpdateTimeEntries", IsTenroxAsyncCallback: "true",
      usercontrolid: "", entries: JSON.stringify([entry]),
    });
    return tenroxPost(body);
  }

  // ---- low-level POST ------------------------------------------------------
  // Runs same-origin from the live page (cookies auto). resolvePageKey() is the
  // one piece pending Step-5 recon: the live page mints its own pageKeys, so we
  // reuse the page's mechanism rather than replay a spent key.
  function resolvePageKey() {
    const ctx = state.context || {};
    // Preference order, refined by recon output:
    //  1) a page global explicitly holding a live pageKey
    //  2) this frame's ?pageKey= (page-shell key)
    for (const name of (ctx.globalPageKeyVars || [])) {
      try { const v = window[name]; if (v) return v; } catch (_) { /* noop */ }
    }
    const qs = new URLSearchParams(location.search);
    return qs.get("pageKey") || "";
  }

  async function tenroxPost(bodyParams) {
    const pageKey = resolvePageKey();
    const url = SAVE_URL + "?r=" + Math.random() + (pageKey ? "&pageKey=" + pageKey : "");
    const resp = await fetch(url, {
      method: "POST", credentials: "include",
      headers: { "content-type": "application/x-www-form-urlencoded; charset=UTF-8", "csrftoken": "0" },
      body: bodyParams.toString(), redirect: "manual",
    });
    if (resp.type === "opaqueredirect" || resp.status === 302) {
      throw new Error("302 -> Error.aspx (pageKey rejected; run recon() and refine resolvePageKey)");
    }
    const text = await resp.text();
    try { return JSON.parse(text); }
    catch (_) { throw new Error("non-JSON response (status " + resp.status + "): " + text.slice(0, 120)); }
  }

  // ---- TRACE: write-free instrumentation of the page's own save requests ---
  // Wraps fetch + XHR across all same-origin frames and logs every
  // MyTimesheet.aspx pageMethod call (request pageKey + body, and response).
  // It does NOT send anything itself - the operator performs real UI saves and
  // this records the exact live contract (incl. how the page sources pageKey
  // and how a note attaches). Reading only; safe.
  function trace() {
    const seen = [];
    state.trace = seen;
    const isTs = (u) => typeof u === "string" && u.indexOf("MyTimesheet.aspx") !== -1;
    const summarize = (url, body) => {
      let pageKey = "", pageMethod = "";
      try { pageKey = new URL(url, location.origin).searchParams.get("pageKey") || ""; } catch (_) { /* noop */ }
      const m = /pageMethod=([^&]+)/.exec(body || "");
      if (m) pageMethod = decodeURIComponent(m[1]);
      return { pageKey, pageMethod };
    };
    function allFrames() {
      const out = [];
      (function walk(w) {
        try { out.push(w); } catch (_) { return; }
        let n = 0; try { n = w.frames.length; } catch (_) { n = 0; }
        for (let i = 0; i < n; i++) { try { void w.frames[i].location.href; walk(w.frames[i]); } catch (_) { /* cross-origin */ } }
      })(window.top || window);
      return out;
    }
    let hooks = 0;
    for (const w of allFrames()) {
      try {
        if (w.fetch && !w.fetch.__tnx) {
          const of = w.fetch;
          w.fetch = function (input, init) {
            const url = typeof input === "string" ? input : (input && input.url);
            const body = init && init.body ? String(init.body) : "";
            if (isTs(url)) {
              const s = summarize(url, body);
              const rec = { via: "fetch", pageMethod: s.pageMethod, pageKey: s.pageKey, body: body.slice(0, 2000) };
              seen.push(rec);
              log("TRACE fetch", s.pageMethod, "pageKey=" + s.pageKey);
              console.log("  body:", body.slice(0, 500));
              return of.apply(this, arguments).then(async (r) => {
                try { rec.resp = (await r.clone().text()).slice(0, 4000); console.log("  resp:", rec.resp.slice(0, 500)); } catch (_) { /* noop */ }
                return r;
              });
            }
            return of.apply(this, arguments);
          };
          w.fetch.__tnx = true; hooks++;
        }
        const XP = w.XMLHttpRequest && w.XMLHttpRequest.prototype;
        if (XP && !XP.__tnx) {
          const oopen = XP.open, osend = XP.send;
          XP.open = function (m, url) { this.__tnxUrl = url; return oopen.apply(this, arguments); };
          XP.send = function (body) {
            const url = this.__tnxUrl || "";
            if (isTs(url)) {
              const s = summarize(url, String(body || ""));
              const rec = { via: "xhr", pageMethod: s.pageMethod, pageKey: s.pageKey, body: String(body || "").slice(0, 2000) };
              seen.push(rec);
              log("TRACE xhr", s.pageMethod, "pageKey=" + s.pageKey);
              console.log("  body:", String(body || "").slice(0, 500));
              this.addEventListener("load", () => { try { rec.resp = this.responseText.slice(0, 4000); console.log("  resp:", rec.resp.slice(0, 500)); } catch (_) { /* noop */ } });
            }
            return osend.apply(this, arguments);
          };
          XP.__tnx = true; hooks++;
        }
      } catch (_) { /* frame not accessible */ }
    }
    log(`trace installed on ${hooks} hook(s) across frames.`);
    log("Now in the timesheet UI, one action at a time (each logs a TRACE line):");
    log("  1) add a 0.25h Administration entry + Save   (create contract + write proof)");
    log("  2) add a note to it + Save                   (NOTE contract - the Step-7 gate)");
    log("  3) set that entry to 0 + Save                (delete via RegularTime:0)");
    log("Then paste the TRACE lines back. Full records: TenroxUploader._state.trace");
    return true;
  }

  window.TenroxUploader = { recon, trace, load, dryRun, post, _state: state };
  log("loaded. Start with TenroxUploader.recon()  (write-free), then TenroxUploader.trace().");
})();
