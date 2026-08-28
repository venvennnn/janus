(() => {
  const recorded = window.JANUS_FINDINGS;
  if (!recorded) {
    document.body.insertAdjacentHTML(
      "afterbegin",
      "<p style='padding:2rem;font-family:sans-serif'>Findings failed to load. Run <code>python -m janus.run_audit</code>.</p>"
    );
    return;
  }

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
  const escape = (s) =>
    String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");

  let J = recorded;
  let routes = {};
  let cutoff = recorded.model?.cutoff;
  let pStart = recorded.recourse_menu?.p_start;
  let uploadJob = null;
  const progressTimers = new WeakMap();

  const get = (path, obj = J) =>
    path.split(".").reduce((acc, key) => (acc == null ? acc : acc[key]), obj);

  const fmt = {
    auc: (v) => (v == null || Number.isNaN(Number(v)) ? "—" : Number(v).toFixed(3)),
    p: (v) => (v == null || Number.isNaN(Number(v)) ? "—" : Number(v).toFixed(3)),
    pct: (v) => (v == null || Number.isNaN(Number(v)) ? "—" : `${Math.round(Number(v) * 100)}%`),
    pct1: (v) => (v == null || Number.isNaN(Number(v)) ? "—" : `${(Number(v) * 100).toFixed(1)}%`),
    pp: (v) => (v == null || Number.isNaN(Number(v)) ? "—" : `${Number(v).toFixed(1)}pp`),
    yen: (v) => (v == null || Number.isNaN(Number(v)) ? "—" : `¥${Math.round(Number(v)).toLocaleString("en-US")}`),
    int: (v) => (v == null || Number.isNaN(Number(v)) ? "—" : Math.round(Number(v)).toLocaleString("en-US")),
    dti: (v) => (v == null || Number.isNaN(Number(v)) ? "—" : Number(v).toFixed(2)),
    times: (v) => (v == null || Number.isNaN(Number(v)) ? "—" : `${Math.round(Number(v))}×`),
    days: (v) => {
      if (v == null || Number.isNaN(Number(v))) return "—";
      const n = Math.round(Number(v));
      return n === 1 ? "1 day" : `${n} days`;
    },
    raw: (v) => String(v ?? "—"),
  };

  function bind(root = document) {
    $$("[data-bind]", root).forEach((el) => {
      const value = get(el.dataset.bind);
      const kind = el.dataset.fmt || "raw";
      el.textContent = value == null ? "—" : (fmt[kind] || fmt.raw)(value);
    });
  }

  function toast(message) {
    const el = $("#toast");
    el.textContent = message;
    el.hidden = false;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => {
      el.hidden = true;
    }, 2200);
  }

  function apiUrl(path) {
    const base = (window.JANUS_API || "").replace(/\/$/, "");
    return `${base}${path}`;
  }

  function apiDetail(body, fallback) {
    const detail = body && body.detail;
    if (typeof detail === "string" && detail) return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => item.msg || item.detail || (typeof item === "string" ? item : JSON.stringify(item)))
        .join("; ");
    }
    if (detail && typeof detail === "object") return JSON.stringify(detail);
    return fallback;
  }

  function setNav() {
    const ids = $$(".nav a").map((a) => a.getAttribute("href")).filter(Boolean);
    const fromHash = (location.hash || "").split("/")[0];
    let active = ids.includes(fromHash) ? fromHash : "";
    if (!active) {
      const y = window.scrollY + 90;
      for (const href of ids) {
        const el = document.querySelector(href);
        if (el && el.offsetTop <= y) active = href;
      }
    }
    $$(".nav a").forEach((a) => {
      a.setAttribute("aria-current", a.getAttribute("href") === active ? "page" : "false");
    });
  }

  function fillSource() {
    const banner = $("#source-banner");
    if (J.source === "upload") {
      banner.hidden = false;
      banner.textContent =
        "Live upload review is bound on this page. Scroll the same sections below. The holdout was dropped from memory after the run.";
    } else {
      banner.hidden = true;
    }
  }

  function fillStory() {
    const d = J.demo_applicant || {};
    const el = $("#demo-story");
    if (!el) return;
    const bits = [];
    if (d.age != null) bits.push(`Age ${d.age}.`);
    if (d.is_informal) bits.push("Informal income.");
    if (d.recorded_dti != null) {
      bits.push(
        d.true_dti != null
          ? `Recorded DTI ${fmt.dti(d.recorded_dti)} against a true DTI of ${fmt.dti(d.true_dti)}.`
          : `Recorded DTI ${fmt.dti(d.recorded_dti)}.`
      );
    }
    bits.push("Declined.");
    if (d.default === 0) bits.push("Did not default.");
    if (d.default === 1) bits.push("Defaulted.");
    if (J.source === "upload" && bits.length <= 1) {
      el.textContent = `${d.applicant_id || "A declined holdout row"}. The routes are what this model responds to.`;
    } else {
      el.textContent = bits.join(" ") || "A declined applicant from this holdout.";
    }
    const def = $("#demo-default");
    if (def) def.textContent = d.default == null ? "—" : d.default ? "defaulted" : "did not default";
  }

  function fillRoutes() {
    const menu = J.recourse_menu || {};
    cutoff = J.model?.cutoff;
    pStart = menu.p_start;
    routes = {
      a: menu.route_a_fake_it || {},
      b: menu.route_b_earn_it || {},
      c: menu.route_c_document_it || {},
    };
    $("#cost-a").textContent = routes.a.cost_jpy == null ? "—" : fmt.yen(routes.a.cost_jpy);
    $("#time-a").textContent = routes.a.days == null ? "low effort" : fmt.days(routes.a.days);
    $("#p-a").textContent = routes.a.p_final == null ? "—" : `${fmt.p(routes.a.p_start ?? pStart)} → ${fmt.p(routes.a.p_final)}`;
    const feats = (routes.a.features || []).join(", ");
    $("#steps-a").textContent = feats
      ? `Model owner only: presentation-sensitive levers on ${feats}. Not applicant guidance.`
      : "Model owner only. Not applicant guidance.";
    $("#cost-b").textContent = routes.b.cost_jpy == null ? "—" : fmt.yen(routes.b.cost_jpy);
    $("#time-b").textContent = routes.b.days == null ? "durable change" : fmt.days(routes.b.days);
    $("#p-b").textContent = routes.b.p_final == null ? "—" : `${fmt.p(routes.b.p_start ?? pStart)} → ${fmt.p(routes.b.p_final)}`;
    const btnC = $("[data-apply=c]");
    if (routes.c.skipped || routes.c.p_final == null) {
      $("#cost-c").textContent = "Not available";
      $("#time-c").textContent = "Not available for this dataset";
      $("#p-c").textContent = routes.c.ask || "Route C needs a recorded/true income gap.";
      btnC.disabled = true;
      btnC.classList.add("is-disabled");
    } else {
      $("#cost-c").textContent = routes.c.cost_jpy == null ? "¥0" : fmt.yen(routes.c.cost_jpy);
      $("#time-c").textContent = routes.c.documentation_months
        ? `${routes.c.documentation_months} months of statements`
        : (routes.c.days == null ? "documentation only" : fmt.days(routes.c.days));
      const dti =
        routes.c.dti_start != null && routes.c.dti_final != null
          ? ` · DTI ${fmt.dti(routes.c.dti_start)} → ${fmt.dti(routes.c.dti_final)}`
          : "";
      $("#p-c").textContent = `${fmt.p(routes.c.p_start ?? pStart)} → ${fmt.p(routes.c.p_final)}${dti}`;
      btnC.disabled = false;
      btnC.classList.remove("is-disabled");
    }
    setP(pStart);
  }

  function setP(p) {
    if (p == null || cutoff == null) return;
    const approved = p < cutoff;
    $("#p-now").textContent = fmt.p(p);
    $("#p-now-dup").textContent = fmt.p(p);
    $("#p-decision").textContent = approved ? "WOULD CROSS CUTOFF" : "DECLINED";
    $("#p-decision").classList.toggle("is-ok", approved);
    $("#p-decision").classList.toggle("is-bad", !approved);
    const max = Math.max(0.6, cutoff * 1.4, p * 1.15);
    const left = Math.max(0, Math.min(100, (p / max) * 100));
    const cut = Math.max(0, Math.min(100, (cutoff / max) * 100));
    $("#p-needle").style.left = `${left}%`;
    $("#p-cutoff-tick").style.left = `${cut}%`;
    const track = $("#p-track");
    if (track) {
      track.setAttribute(
        "aria-label",
        `Predicted default ${fmt.p(p)} versus cutoff ${fmt.p(cutoff)}. ${approved ? "Would cross cutoff." : "Declined."}`
      );
    }
  }

  function resetRoutes() {
    $$(".route").forEach((card) => card.classList.remove("is-live"));
    $$("[data-apply]").forEach((b) => {
      b.textContent = `Apply route ${b.dataset.apply.toUpperCase()}`;
    });
    setP(pStart);
    $("#route-reveal").hidden = true;
  }

  function applyRoute(key) {
    const rec = routes[key];
    if (!rec || rec.skipped || rec.p_final == null) {
      toast("This route is not available on this book.");
      return;
    }
    $$(".route").forEach((card) => card.classList.toggle("is-live", card.dataset.route === key));
    $$("[data-apply]").forEach((b) => {
      b.textContent = b.dataset.apply === key ? "Applied" : `Apply route ${b.dataset.apply.toUpperCase()}`;
    });
    setP(rec.p_final);
    const reveal = $("#route-reveal");
    const lines = {
      a: "The decision changed, but the applicant’s underlying repayment capacity did not. This is an integrity vulnerability.",
      b: "The decision moved because the financial position actually changed. That is genuine improvement, not presentation.",
      c: "Documentation alone moved the decision. Nothing economic changed. The exclusion was measurement error.",
    };
    reveal.textContent = lines[key] || "";
    reveal.hidden = false;
    toast(key === "a" ? "Route A applied — model owner only" : `Route ${key.toUpperCase()} applied`);
  }

  function cardHTML(item) {
    if (item.skipped) {
      return `<article class="card">
        <h3>${escape(item.name)}</h3>
        <p class="big">skipped</p>
        <p class="meaning">${escape(item.reason || "This audit was skipped for this dataset.")}</p>
        <p class="meta-row"><span class="kind-tag">Observed engine result</span><span class="run">${escape(item.run)}</span></p>
        <details>
          <summary>How this was measured</summary>
          <p>${escape(item.how || item.reason || "Skipped.")}</p>
        </details>
      </article>`;
    }
    return `<article class="card">
      <h3>${escape(item.name)}</h3>
      <p class="big">${escape(item.value)}</p>
      <p class="meaning">${escape(item.meaning)}</p>
      <p class="meta-row">
        <span class="sev sev-${escape(item.severity)}">${escape(item.severity)}</span>
        <span class="kind-tag">${escape(item.kind)}</span>
        <span class="run">${escape(item.run)}</span>
      </p>
      <details>
        <summary>How this was measured</summary>
        <p>${escape(item.how)}</p>
      </details>
    </article>`;
  }

  function fillEvidence() {
    const b = J.battery || {};
    const atk = b.attack_surface || {};
    const proxy = b.proxy_audit || {};
    const excl = b.unexplained_exclusion || {};
    const segs = b.broken_segments || {};
    const gap = b.integrity_gap || {};
    const ev = b.evidence_recourse || {};
    const young = segs.young_self_employed || {};
    const items = [
      {
        name: "Attack-surface flip rate",
        skipped: Boolean(atk.skipped),
        reason: atk.reason,
        value: atk.flip_rate == null ? "—" : fmt.pct1(atk.flip_rate),
        meaning: "Share of sampled declines that cross the cutoff on presentation-sensitive change.",
        severity: (atk.flip_rate || 0) >= 0.35 ? "high" : "medium",
        kind: "Observed engine result",
        run: atk.run_id || "run.attack_surface",
        how: atk.skipped
          ? atk.reason
          : `Greedy search on n=${atk.n_sampled} declined rows, ${fmt.yen(atk.budget_jpy)} attack budget. Flipped default ${fmt.pct1(atk.flipped_default_rate)} vs baseline ${fmt.pct1(atk.baseline_default_rate)}.`,
      },
      {
        name: "Median attack effort",
        skipped: Boolean(atk.skipped),
        reason: atk.reason,
        value: atk.median_cost_jpy == null ? "—" : fmt.yen(atk.median_cost_jpy),
        meaning: "Median cost of the cheapest successful presentation path among flipped declines.",
        severity: "medium",
        kind: "Observed engine result",
        run: atk.run_id || "run.attack_surface",
        how: "Not interchangeable with the integrity-gap attack median. Different sample.",
      },
      {
        name: "Integrity gap",
        skipped: Boolean(gap.skipped),
        reason: gap.reason,
        value: gap.median_gap_ratio == null ? "—" : fmt.times(gap.median_gap_ratio),
        meaning: "Median of per-applicant (genuine effort / cosmetic effort) ratios.",
        severity: (gap.median_gap_ratio || 0) >= 20 ? "high" : "medium",
        kind: "Assumption requiring human confirmation",
        run: gap.run_id || "run.integrity_gap",
        how: gap.skipped
          ? gap.reason
          : `Fake it ${fmt.yen(gap.median_attack_cost_jpy)}; earn it ${fmt.yen(gap.median_genuine_cost_jpy)} / ${fmt.days(gap.median_genuine_days)}. Only as credible as the signed mutability table.`,
      },
      {
        name: "Proxy reconstruction",
        skipped: Boolean(proxy.skipped),
        reason: proxy.reason,
        value: proxy.probe_auc == null ? "—" : fmt.auc(proxy.probe_auc),
        meaning: proxy.chief_carrier
          ? `Rural residence recovered from model-visible features, chiefly ${proxy.chief_carrier}.`
          : "Sensitive attribute recovered from model-visible features.",
        severity: (proxy.probe_auc || 0) >= 0.95 ? "high" : "medium",
        kind: "Observed engine result",
        run: proxy.run_id || "run.proxy_audit",
        how: proxy.skipped ? proxy.reason : "A probe model is fit on scorecard features to recover a label the scorecard was never given.",
      },
      {
        name: "Unexplained exclusion",
        skipped: Boolean(excl.skipped),
        reason: excl.reason,
        value: excl.approval_gap_pp == null ? "—" : fmt.pp(excl.approval_gap_pp),
        meaning: excl.skipped
          ? excl.reason
          : `Informal-income approval gap. Default ${fmt.pct1(excl.default_informal)} vs ${fmt.pct1(excl.default_formal)}.`,
        severity: (excl.approval_gap_pp || 0) >= 15 ? "high" : "medium",
        kind: "Interpretation",
        run: excl.run_id || "run.unexplained_exclusion",
        how: excl.skipped
          ? excl.reason
          : "Approval and realised default compared across informal vs formal labels the model was not trained on.",
      },
      {
        name: "Broken segments",
        skipped: Boolean(segs.skipped),
        reason: segs.reason,
        value: young.n
          ? `${fmt.pct1(young.predicted_default)} pred`
          : segs.worst_understated
            ? fmt.pp(segs.worst_understated.gap_pp)
            : "calibrated",
        meaning: young.n
          ? `Young self-employed actual ${fmt.pct1(young.actual_default)} · n=${young.n}.`
          : segs.worst_understated
            ? `Worst understated leaf n=${segs.worst_understated.n}.`
            : "No large residual leaf on this book.",
        severity: "medium",
        kind: "Observed engine result",
        run: segs.run_id || "run.discover_segments",
        how: segs.skipped ? segs.reason : "A shallow tree on residual default risk finds leaves where predicted and realised default diverge.",
      },
      {
        name: "Evidence / documentation recourse",
        skipped: Boolean(ev.skipped),
        reason: ev.reason,
        value: ev.cross_rate_full_documentation == null ? "—" : fmt.pct1(ev.cross_rate_full_documentation),
        meaning: ev.skipped
          ? ev.reason
          : `Declined informal-income rows that cross on documentation alone. Those who cross default at ${fmt.pct1(ev.cross_default_rate)} vs ${fmt.pct1(ev.portfolio_default_rate)} book.`,
        severity: (ev.cross_rate_full_documentation || 0) >= 0.2 ? "high" : "medium",
        kind: "Observed engine result",
        run: ev.run_id || "run.evidence_recourse",
        how: ev.skipped
          ? ev.reason
          : "Recorded DTI is recomputed after documenting the recorded/true income gap. Cost ¥0. Directional on real data until the gap is estimated from cash-flow.",
      },
    ];
    $("#evidence-grid").innerHTML = items.map(cardHTML).join("");
  }

  function fillGap() {
    const gap = (J.battery && J.battery.integrity_gap) || {};
    const block = $("#integrity-gap");
    const value = $("#gap-value");
    const attack = $("#gap-attack");
    const genuine = $("#gap-genuine");
    const note = $("#gap-note");
    if (!block || !value) return;
    block.classList.toggle("is-skipped", Boolean(gap.skipped));
    if (gap.skipped) {
      value.textContent = "skipped";
      if (attack) attack.textContent = "—";
      if (genuine) genuine.textContent = "—";
      if (note) note.textContent = gap.reason || "Integrity gap was skipped for this dataset.";
      return;
    }
    value.textContent = gap.median_gap_ratio == null ? "—" : fmt.times(gap.median_gap_ratio);
    if (attack) attack.textContent = gap.median_attack_cost_jpy == null ? "—" : fmt.yen(gap.median_attack_cost_jpy);
    if (genuine) {
      const cost = gap.median_genuine_cost_jpy == null ? "—" : fmt.yen(gap.median_genuine_cost_jpy);
      const days = gap.median_genuine_days == null ? "" : ` · ${fmt.days(gap.median_genuine_days)}`;
      genuine.textContent = `${cost}${days}`;
    }
    if (note) {
      note.textContent =
        "This is the median of per-applicant ratios — not the ratio of medians. Not interchangeable with attack-surface median cost. Observed engine result, not proof of fraud. The ratio is only as credible as the lender-approved mutability and effort assumptions.";
    }
  }

  function fillFindings() {
    const items = (J.investigation && J.investigation.findings) || [];
    $("#findings-list").innerHTML = items
      .map(
        (f) => `<li>
          <p class="title"><label><input type="checkbox" class="finding-box" data-id="${escape(f.id)}" checked> ${escape(f.title)}</label>
          <span class="sev sev-${escape(f.severity)}">${escape(f.severity)}</span></p>
          <p class="subtitle">${escape(f.claim)}${f.reading ? " " + escape(f.reading) : ""} <span class="run">${escape(f.run_id)}</span></p>
        </li>`
      )
      .join("");
    updateSign();
  }

  function updateSign() {
    const boxes = $$(".finding-box");
    const accepted = boxes.filter((b) => b.checked).length;
    const gated = $("#gate-findings").checked;
    $("#sign-status").textContent = gated
      ? `Package signed. ${accepted} of ${boxes.length} findings accepted.`
      : `Package unsigned. ${accepted} of ${boxes.length} findings checked.`;
  }

  function boot(findings) {
    J = findings;
    window.JANUS_FINDINGS = findings;
    bind();
    fillSource();
    fillStory();
    fillRoutes();
    fillEvidence();
    fillGap();
    fillFindings();
    resetRoutes();
  }

  function proposalRows(proposal) {
    if (Array.isArray(proposal)) return proposal;
    if (proposal && Array.isArray(proposal.levers)) return proposal.levers;
    return [];
  }

  function fillProposeTable(rows) {
    $("#propose-table tbody").innerHTML = rows
      .map((row) => {
        const payload = encodeURIComponent(JSON.stringify(row));
        const kinds = ["cosmetic", "genuine", "mixed", "immutable", "documentation"]
          .map((k) => `<option${k === row.kind ? " selected" : ""}>${k}</option>`)
          .join("");
        const dirs = ["up", "down"].map((d) => `<option${d === row.direction ? " selected" : ""}>${d}</option>`).join("");
        return `<tr data-row="${payload}">
          <td><code>${escape(row.feature)}</code></td>
          <td><select name="kind" aria-label="Kind for ${escape(row.feature)}">${kinds}</select></td>
          <td><select name="direction" aria-label="Direction for ${escape(row.feature)}">${dirs}</select></td>
          <td><input name="attack" type="number" step="1" value="${row.attack_cost_jpy ?? ""}" placeholder="—" aria-label="Attack cost for ${escape(row.feature)}"></td>
          <td><input name="attack_days" type="number" step="0.1" value="${row.attack_days ?? ""}" placeholder="—" aria-label="Attack time for ${escape(row.feature)}"></td>
          <td><input name="genuine" type="number" step="1" value="${row.genuine_cost_jpy ?? ""}" placeholder="—" aria-label="Genuine cost for ${escape(row.feature)}"></td>
          <td><input name="genuine_days" type="number" step="0.1" value="${row.genuine_days ?? ""}" placeholder="—" aria-label="Genuine time for ${escape(row.feature)}"></td>
          <td><input name="rationale" type="text" value="${escape(row.rationale || "")}" aria-label="Rationale for ${escape(row.feature)}"></td>
        </tr>`;
      })
      .join("");
  }

  function collectLevers() {
    return $$("#propose-table tbody tr").map((tr) => {
      const row = JSON.parse(decodeURIComponent(tr.dataset.row));
      const num = (name) => {
        const v = tr.querySelector(`[name=${name}]`).value;
        return v === "" ? null : Number(v);
      };
      return {
        ...row,
        kind: tr.querySelector("[name=kind]").value,
        direction: tr.querySelector("[name=direction]").value,
        attack_cost_jpy: num("attack"),
        attack_days: num("attack_days"),
        genuine_cost_jpy: num("genuine"),
        genuine_days: num("genuine_days"),
        rationale: tr.querySelector("[name=rationale]").value,
      };
    });
  }

  function setStatus(el, text) {
    el.textContent = text;
  }

  function stopProgress(el) {
    const id = progressTimers.get(el);
    if (id) clearInterval(id);
    progressTimers.delete(el);
  }

  function startProgress(el, labels) {
    stopProgress(el);
    let i = 0;
    el.textContent = labels[0];
    const id = setInterval(() => {
      i = (i + 1) % labels.length;
      el.textContent = labels[i];
    }, 1600);
    progressTimers.set(el, id);
  }

  function syncRunGate() {
    const btn = $("#btn-run-upload");
    const gate = $("#gate-upload-mutability");
    if (!btn || !gate) return;
    btn.disabled = !gate.checked;
    btn.classList.toggle("is-disabled", !gate.checked);
  }

  async function pingApi() {
    const status = $("#api-status");
    const zip = $("#sample-zip");
    try {
      const res = await fetch(apiUrl("/health"), { cache: "no-store" });
      if (!res.ok) throw new Error(res.statusText);
      const body = await res.json();
      const llm = body.llm === "anthropic" ? `Agent on (${body.model || "anthropic"}).` : "Heuristic fallback (no LLM key).";
      status.textContent = `Review service up (${body.version || "JANUS"}). ${llm} Free-tier hosts sleep; the first call may wait.`;
      zip.href = apiUrl("/sample.zip");
    } catch {
      status.textContent =
        "Review service is asleep or not configured. The reference audit still works. Set docs/js/config.js to your Render URL, or start uvicorn locally.";
    }
  }

  function wireAudit() {
    $("#btn-use-book")?.addEventListener("click", () => {
      boot(recorded);
      document.querySelector("#break")?.scrollIntoView({ behavior: "smooth", block: "start" });
      toast("Reference audit reloaded");
    });

    $("#gate-upload-mutability")?.addEventListener("change", syncRunGate);
    syncRunGate();

    $("#audit-form")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const status = $("#propose-status");
      const model = $("#input-model").files[0];
      const holdout = $("#input-holdout").files[0];
      if (!model || !holdout) {
        setStatus(status, "A model file and a holdout CSV are required.");
        $("#input-model").setAttribute("aria-invalid", model ? "false" : "true");
        $("#input-holdout").setAttribute("aria-invalid", holdout ? "false" : "true");
        return;
      }
      $("#input-model").setAttribute("aria-invalid", "false");
      $("#input-holdout").setAttribute("aria-invalid", "false");
      const data = new FormData();
      data.append("model", model);
      data.append("holdout", holdout);
      data.append("cutoff", $("#input-cutoff").value);
      data.append("dictionary_text", $("#input-dictionary-text").value || "");
      data.append("context", $("#input-context").value || "");
      const dictFile = $("#input-dictionary").files[0];
      if (dictFile) data.append("dictionary", dictFile);
      startProgress(status, ["Inspecting model", "Reading feature definitions"]);
      try {
        const res = await fetch(apiUrl("/propose"), { method: "POST", body: data });
        const body = await res.json().catch(() => ({}));
        stopProgress(status);
        if (!res.ok) throw new Error(apiDetail(body, res.statusText));
        uploadJob = body;
        const rows = proposalRows(body.proposal);
        fillProposeTable(rows);
        $("#propose-stage").hidden = false;
        $("#gate-upload-mutability").checked = false;
        syncRunGate();
        const who = body.agent && body.agent.llm === "anthropic" ? "Agent proposed this table" : "Heuristic table (no API key)";
        const auc = body.model?.auc_holdout == null ? "—" : fmt.auc(body.model.auc_holdout);
        setStatus(
          status,
          `Awaiting human confirmation. ${who}. ${body.model?.n_features ?? "—"} features · AUC ${auc} · ${fmt.int(body.model?.n_holdout)} rows.`
        );
        $("#propose-stage").scrollIntoView({ behavior: "smooth", block: "start" });
      } catch (err) {
        stopProgress(status);
        setStatus(status, String(err.message || err));
      }
    });

    $("#btn-run-upload")?.addEventListener("click", async () => {
      const status = $("#run-status");
      if (!$("#gate-upload-mutability").checked) {
        setStatus(status, "Confirm the mutability table before search runs.");
        toast("Confirm the mutability table before search runs.");
        return;
      }
      if (!uploadJob) {
        setStatus(status, "Propose first.");
        return;
      }
      startProgress(status, ["Searching decision boundary", "Testing segments", "Building evidence package"]);
      try {
        const res = await fetch(apiUrl("/run"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            job_id: uploadJob.job_id,
            confirmed: true,
            levers: collectLevers(),
          }),
        });
        const body = await res.json().catch(() => ({}));
        stopProgress(status);
        if (!res.ok) throw new Error(apiDetail(body, res.statusText));
        boot(body);
        uploadJob = null;
        setStatus(
          status,
          "Review ready on this page. The holdout was dropped from memory. The sections above now show this model’s findings."
        );
        document.querySelector("#break")?.scrollIntoView({ behavior: "smooth", block: "start" });
        toast("Upload review bound on this page");
      } catch (err) {
        stopProgress(status);
        setStatus(status, String(err.message || err));
      }
    });
  }

  $$("[data-apply]").forEach((btn) => {
    btn.addEventListener("click", () => applyRoute(btn.dataset.apply));
  });
  $("#btn-reset-p")?.addEventListener("click", resetRoutes);

  document.addEventListener("change", (e) => {
    if (e.target.classList.contains("finding-box") || e.target.id === "gate-findings") updateSign();
  });

  document.addEventListener("keydown", (e) => {
    if (["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName)) return;
    if (e.key === "1" || e.key === "2" || e.key === "3") applyRoute(["a", "b", "c"][Number(e.key) - 1]);
    if (e.key === "r" || e.key === "R") resetRoutes();
  });

  document.addEventListener("click", (e) => {
    const el = e.target.closest("[data-run]");
    if (el?.dataset.run) toast(`Provenance ${el.dataset.run}`);
  });

  window.addEventListener("hashchange", setNav);
  window.addEventListener("scroll", setNav, { passive: true });
  boot(recorded);
  setNav();
  wireAudit();
  pingApi();
})();
