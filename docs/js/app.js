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

  let J = recorded;
  let routes = {};
  let cutoff = recorded.model.cutoff;
  let pStart = recorded.recourse_menu.p_start;
  let uploadJob = null;

  const get = (path) =>
    path.split(".").reduce((acc, key) => (acc == null ? acc : acc[key]), J);

  const fmt = {
    auc: (v) => Number(v).toFixed(3),
    p: (v) => Number(v).toFixed(3),
    pct: (v) => `${Math.round(Number(v) * 100)}%`,
    pct1: (v) => `${(Number(v) * 100).toFixed(1)}%`,
    pp: (v) => `${Number(v).toFixed(1)}pp`,
    yen: (v) => `¥${Math.round(Number(v)).toLocaleString("en-US")}`,
    int: (v) => Math.round(Number(v)).toLocaleString("en-US"),
    dti: (v) => Number(v).toFixed(2),
    times: (v) => `${Math.round(Number(v))}×`,
    days: (v) => `${Math.round(Number(v))} days`,
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

  const views = $$(".view");
  const dock = $("#applicant-dock");

  function showView(name) {
    views.forEach((view) => {
      const on = view.dataset.view === name;
      view.hidden = !on;
    });
    $$(".nav a").forEach((a) => {
      a.setAttribute("aria-current", a.getAttribute("href") === `#${name}` ? "page" : "false");
    });
    dock.hidden = !(name === "investigate" || name === "routes");
    if (name === "investigate") $("#stage")?.focus({ preventScroll: true });
  }

  let step = 0;
  const panels = $$("[data-panel]");
  const stepButtons = $$("[data-step]");

  function setStep(next) {
    step = Math.max(0, Math.min(panels.length - 1, next));
    panels.forEach((panel) => {
      panel.hidden = Number(panel.dataset.panel) !== step;
    });
    stepButtons.forEach((btn) => {
      btn.classList.toggle("is-active", Number(btn.dataset.step) === step);
    });
    if (location.hash.startsWith("#investigate")) {
      history.replaceState(null, "", `#investigate/${step}`);
    }
  }

  function parseHash() {
    const hash = (location.hash || "#brief").slice(1);
    const [view, extra] = hash.split("/");
    const known = ["brief", "audit", "investigate", "routes", "memo", "method"];
    const name = known.includes(view) ? view : "brief";
    showView(name);
    if (name === "investigate") setStep(Number(extra || 0) || 0);
  }

  function fillDock() {
    const d = J.demo_applicant || {};
    const bits = [];
    if (d.age != null) bits.push(`age ${d.age}`);
    if (d.is_informal === 1) bits.push("informal income");
    if (d.is_rural === 1) bits.push("rural");
    $("#dock-who").textContent = bits.join(", ") || "holdout row";
  }

  function fillMutability() {
    const body = $("#mutability-table tbody");
    const rows = (J.mutability_model || []).filter((row) => row.kind !== "immutable");
    body.innerHTML = rows
      .map((row) => {
        const fake = row.attack_cost_jpy == null ? "—" : `¥${row.attack_cost_jpy} / step`;
        const earn = row.genuine_cost_jpy == null ? "—" : `¥${row.genuine_cost_jpy} / step`;
        return `<tr>
          <td><code>${row.feature}</code></td>
          <td><span class="kind">${row.kind}</span></td>
          <td>${fake}</td>
          <td>${earn}</td>
          <td>${row.rationale}</td>
        </tr>`;
      })
      .join("");
  }

  function tile(run, k, v, s) {
    return { run, k, v, s };
  }

  function fillBattery() {
    const b = J.battery || {};
    const tiles = [];
    const atk = b.attack_surface || {};
    tiles.push(
      atk.skipped
        ? tile(atk.run_id, "Gaming surface", "skipped", atk.reason)
        : tile(atk.run_id, "Gaming surface", fmt.pct1(atk.flip_rate), `median ${fmt.yen(atk.median_cost_jpy)} · n=${atk.n_sampled}`)
    );
    const proxy = b.proxy_audit || {};
    tiles.push(
      proxy.skipped
        ? tile(proxy.run_id, "Proxy reconstruction", "skipped", proxy.reason)
        : tile(proxy.run_id, "Proxy reconstruction", fmt.auc(proxy.probe_auc), `rural via ${proxy.chief_carrier}`)
    );
    const excl = b.unexplained_exclusion || {};
    tiles.push(
      excl.skipped
        ? tile(excl.run_id, "Unexplained exclusion", "skipped", excl.reason)
        : tile(excl.run_id, "Unexplained exclusion", fmt.pp(excl.approval_gap_pp), `default ${fmt.pct1(excl.default_informal)} vs ${fmt.pct1(excl.default_formal)}`)
    );
    const segs = (b.broken_segments || {}).young_self_employed || {};
    const broken = b.broken_segments || {};
    if (broken.skipped) {
      tiles.push(tile(broken.run_id, "Broken segments", "skipped", broken.reason));
    } else if (segs.n) {
      tiles.push(tile("run.discover_segments", "Young self-employed", `${fmt.pct1(segs.predicted_default)} pred`, `actual ${fmt.pct1(segs.actual_default)} · n=${segs.n}`));
    } else {
      const worst = broken.worst_understated;
      tiles.push(
        worst
          ? tile(broken.run_id, "Broken segments", fmt.pp(worst.gap_pp), `leaf n=${worst.n}`)
          : tile(broken.run_id, "Broken segments", "calibrated", "no large residual leaf")
      );
    }
    $("#battery-tiles").innerHTML = tiles
      .map(
        (t, i) => `<li title="${t.run || ""}">
          <span class="num">№ ${String(i + 1).padStart(2, "0")}</span>
          <span class="title">${t.k}</span>
          <span class="date">${t.v}</span>
          <span class="subtitle">${t.s || ""}</span>
        </li>`
      )
      .join("");
  }

  function fillCurve() {
    const ev = J.battery.evidence_recourse || {};
    const host = $("#doc-curve");
    if (ev.skipped) {
      host.innerHTML = `<li><span class="num">№ 01</span><span class="title">Route C skipped</span><span class="subtitle">${ev.reason}</span></li>`;
      return;
    }
    const curve = ev.documentation_curve || [];
    host.innerHTML = curve
      .map(
        (c, i) => `<li>
          <span class="num">№ ${String(i + 1).padStart(2, "0")}</span>
          <span class="title">${Math.round(c.documented_share * 100)}% documented</span>
          <span class="date">${fmt.pct1(c.cross_rate)}</span>
          <span class="subtitle">cross the cutoff</span>
        </li>`
      )
      .join("");
  }

  function fillStory() {
    const d = J.demo_applicant || {};
    const el = $("#demo-story");
    if (!el) return;
    if (J.source === "upload") {
      const dti = d.recorded_dti != null ? `Recorded DTI ${Number(d.recorded_dti).toFixed(2)}` : "A declined holdout row";
      const trueDti = d.true_dti != null ? ` against a true DTI of ${Number(d.true_dti).toFixed(2)}` : "";
      el.textContent = `${d.applicant_id}. ${dti}${trueDti}. The routes below are what this model responds to.`;
    } else {
      el.textContent =
        "Age 21. Undocumented income. Recorded DTI 1.07 against a true DTI of 0.50. Declined. Did not default. The model asked the wrong question of a person whose finances were already sound.";
    }
  }

  function fillRoutes() {
    const menu = J.recourse_menu;
    cutoff = J.model.cutoff;
    pStart = menu.p_start;
    routes = {
      a: menu.route_a_fake_it,
      b: menu.route_b_earn_it,
      c: menu.route_c_document_it,
    };
    $("#cost-a").textContent = fmt.yen(routes.a.cost_jpy);
    $("#time-a").textContent = "one afternoon";
    $("#p-a").textContent = `${fmt.p(routes.a.p_start)} → ${fmt.p(routes.a.p_final)}`;
    $("#cost-b").textContent = fmt.yen(routes.b.cost_jpy);
    $("#time-b").textContent = fmt.days(routes.b.days);
    $("#p-b").textContent = `${fmt.p(routes.b.p_start)} → ${fmt.p(routes.b.p_final)}`;
    if (routes.c.skipped) {
      $("#cost-c").textContent = "—";
      $("#time-c").textContent = "needs a recorded/true income gap";
      $("#p-c").textContent = routes.c.ask || "";
    } else {
      $("#cost-c").textContent = "¥0";
      $("#time-c").textContent = `${routes.c.documentation_months} months of statements`;
      $("#p-c").textContent = `${fmt.p(routes.c.p_start)} → ${fmt.p(routes.c.p_final)} · DTI ${fmt.dti(routes.c.dti_start)} → ${fmt.dti(routes.c.dti_final)}`;
    }
    setP(pStart);
  }

  function setP(p) {
    $("#p-now").textContent = fmt.p(p);
    const approved = p < cutoff;
    $("#p-decision").textContent = approved ? "APPROVED" : "DECLINED";
    $("#p-decision").classList.toggle("is-ok", approved);
    $("#p-decision").classList.toggle("is-bad", !approved);
    $("#dock-decision").textContent = approved ? "would cross cutoff" : "declined";
  }

  function fillFindings() {
    const list = $("#findings-list");
    const items = J.investigation.findings || [];
    list.innerHTML = items
      .map(
        (f, i) => `<li>
          <span class="num">№ ${String(i + 1).padStart(2, "0")}</span>
          <span class="title"><label><input type="checkbox" class="finding-box" data-id="${f.id}" checked> ${f.title}</label></span>
          <span class="date">${f.severity}</span>
          <span class="subtitle">${f.claim}${f.reading ? " " + f.reading : ""} <span class="run">${f.run_id}</span></span>
        </li>`
      )
      .join("");
    const home = $("#home-findings");
    if (home) {
      home.innerHTML = items
        .map(
          (f, i) => `<li>
            <span class="num">№ ${String(i + 1).padStart(2, "0")}</span>
            <span class="title">${f.title}</span>
            <span class="date">${f.severity}</span>
            <span class="subtitle">${f.claim}${f.reading ? " " + f.reading : ""}</span>
          </li>`
        )
        .join("");
    }
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
    fillDock();
    fillMutability();
    fillBattery();
    fillCurve();
    fillStory();
    fillRoutes();
    fillFindings();
  }

  function apiUrl(path) {
    const base = (window.JANUS_API || "").replace(/\/$/, "");
    return `${base}${path}`;
  }

  async function pingApi() {
    const status = $("#api-status");
    const zip = $("#sample-zip");
    try {
      const res = await fetch(apiUrl("/health"), { cache: "no-store" });
      if (!res.ok) throw new Error(res.statusText);
      const body = await res.json();
      const llm =
        body.llm === "anthropic"
          ? `Claude is on (${body.model || "anthropic"}).`
          : "Claude is off — add ANTHROPIC_API_KEY on Render.";
      status.textContent = `Review service up (${body.version || "JANUS"}). ${llm} Free-tier hosts sleep; the first call may wait.`;
      status.classList.toggle("is-ok", body.llm === "anthropic");
      status.classList.toggle("is-bad", body.llm !== "anthropic");
      zip.href = apiUrl("/sample.zip");
    } catch {
      status.textContent =
        "Review service is asleep or not configured. Use the JANUS book, or set docs/js/config.js to your Render URL and start uvicorn locally.";
      status.classList.add("is-bad");
    }
  }

  function fillProposeTable(rows) {
    const body = $("#propose-table tbody");
    body.innerHTML = rows
      .map((row) => {
        const payload = JSON.stringify(row).replace(/'/g, "&#39;");
        return `<tr data-row='${payload}'>
          <td><code>${row.feature}</code></td>
          <td><select name="kind">
            ${["cosmetic", "genuine", "mixed", "immutable", "documentation"].map((k) => `<option${k === row.kind ? " selected" : ""}>${k}</option>`).join("")}
          </select></td>
          <td><select name="direction">
            ${["up", "down"].map((d) => `<option${d === row.direction ? " selected" : ""}>${d}</option>`).join("")}
          </select></td>
          <td><input name="attack" type="number" step="1" value="${row.attack_cost_jpy ?? ""}" placeholder="—"></td>
          <td><input name="genuine" type="number" step="1" value="${row.genuine_cost_jpy ?? ""}" placeholder="—"></td>
          <td><input name="rationale" type="text" value="${(row.rationale || "").replace(/"/g, "&quot;")}"></td>
        </tr>`;
      })
      .join("");
  }

  function collectLevers() {
    return $$("#propose-table tbody tr").map((tr) => {
      const row = JSON.parse(tr.dataset.row);
      const attack = tr.querySelector("[name=attack]").value;
      const genuine = tr.querySelector("[name=genuine]").value;
      return {
        ...row,
        kind: tr.querySelector("[name=kind]").value,
        direction: tr.querySelector("[name=direction]").value,
        attack_cost_jpy: attack === "" ? null : Number(attack),
        genuine_cost_jpy: genuine === "" ? null : Number(genuine),
        rationale: tr.querySelector("[name=rationale]").value,
      };
    });
  }

  function wireAudit() {
    $("#btn-use-book")?.addEventListener("click", () => {
      boot(recorded);
      location.hash = "#investigate";
      toast("Recorded JANUS book loaded");
    });

    $("#audit-form")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const status = $("#propose-status");
      const model = $("#input-model").files[0];
      const holdout = $("#input-holdout").files[0];
      if (!model || !holdout) {
        status.textContent = "A model file and a holdout CSV are required.";
        return;
      }
      const data = new FormData();
      data.append("model", model);
      data.append("holdout", holdout);
      data.append("cutoff", $("#input-cutoff").value);
      data.append("dictionary_text", $("#input-dictionary-text").value || "");
      data.append("context", $("#input-context").value || "");
      const dictFile = $("#input-dictionary").files[0];
      if (dictFile) data.append("dictionary", dictFile);
      status.textContent = "Claude is reading the dictionary. Search has not started.";
      try {
        const res = await fetch(apiUrl("/propose"), { method: "POST", body: data });
        const body = await res.json();
        if (!res.ok) throw new Error(body.detail || res.statusText);
        uploadJob = body;
        fillProposeTable(body.proposal);
        $("#propose-stage").hidden = false;
        const who = body.agent && body.agent.llm === "anthropic" ? "Claude proposed this table" : "Heuristic table (no API key)";
        status.textContent = `${who}. ${body.model.n_features} features · AUC ${body.model.auc_holdout} · ${body.model.n_holdout} rows. Confirm, then run.`;
      } catch (err) {
        status.textContent = String(err.message || err);
      }
    });

    $("#btn-run-upload")?.addEventListener("click", async () => {
      const status = $("#run-status");
      if (!$("#gate-upload-mutability").checked) {
        status.textContent = "Confirm the mutability model to run the battery.";
        toast("Confirm the mutability model to run the battery.");
        return;
      }
      if (!uploadJob) {
        status.textContent = "Propose first.";
        return;
      }
      status.textContent = "Engine is running the battery. Claude will read the figures next.";
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
        const body = await res.json();
        if (!res.ok) throw new Error(body.detail || res.statusText);
        boot(body);
        uploadJob = null;
        status.textContent = "Review ready. The holdout was dropped from memory.";
        location.hash = "#investigate";
        toast("Upload review ready");
      } catch (err) {
        status.textContent = String(err.message || err);
      }
    });
  }

  stepButtons.forEach((btn) => btn.addEventListener("click", () => setStep(Number(btn.dataset.step))));
  $("#btn-next")?.addEventListener("click", () => {
    if (step === 0 && !$("#gate-mutability").checked) {
      toast("Confirm the mutability model to run the battery.");
      return;
    }
    if (step === panels.length - 1) {
      location.hash = "#routes";
      return;
    }
    setStep(step + 1);
  });
  $("#btn-prev")?.addEventListener("click", () => setStep(step - 1));

  let playing = false;
  $("#btn-play")?.addEventListener("click", () => {
    playing = !playing;
    $("#btn-play").textContent = playing ? "pause" : "play";
    if (playing) tick();
  });
  function tick() {
    if (!playing) return;
    if (step === 0 && !$("#gate-mutability").checked) {
      $("#gate-mutability").checked = true;
    }
    if (step >= panels.length - 1) {
      playing = false;
      $("#btn-play").textContent = "play";
      return;
    }
    setStep(step + 1);
    setTimeout(tick, 1600);
  }

  $("#btn-reset-p")?.addEventListener("click", () => {
    $$(".route").forEach((card) => card.classList.remove("is-live"));
    $$("[data-apply]").forEach((b) => {
      b.textContent = "apply →";
    });
    setP(pStart);
    $("#route-reveal").hidden = true;
  });

  $$("[data-apply]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const key = btn.dataset.apply;
      if (!routes[key] || routes[key].skipped) {
        toast("This route was skipped on this book.");
        return;
      }
      $$(".route").forEach((card) => card.classList.toggle("is-live", card.dataset.route === key));
      $$("[data-apply]").forEach((b) => {
        b.textContent = b.dataset.apply === key ? "applied" : "apply →";
      });
      setP(routes[key].p_final);
      $("#route-reveal").hidden = key !== "c";
      toast(key === "a" ? "Route A applied — owner desk only" : `Route ${key.toUpperCase()} applied on the desk`);
    });
  });

  document.addEventListener("click", (e) => {
    const el = e.target.closest("[data-run]");
    if (el?.dataset.run) toast(`Provenance ${el.dataset.run}`);
  });

  $("#gate-findings")?.addEventListener("change", updateSign);
  document.addEventListener("change", (e) => {
    if (e.target.classList.contains("finding-box")) updateSign();
  });

  document.addEventListener("keydown", (e) => {
    if (["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName)) return;
    if (e.key === "ArrowRight" || e.key === "j") {
      if (!$("#investigate").hidden) $("#btn-next").click();
    }
    if (e.key === "ArrowLeft" || e.key === "k") {
      if (!$("#investigate").hidden) $("#btn-prev").click();
    }
    if (e.key === "1" || e.key === "2" || e.key === "3") {
      if (!$("#routes").hidden) $(`[data-apply="${["a", "b", "c"][Number(e.key) - 1]}"]`).click();
    }
  });

  window.addEventListener("hashchange", parseHash);
  boot(recorded);
  if (!location.hash) location.hash = "#brief";
  else parseHash();
  wireAudit();
  pingApi();
})();
