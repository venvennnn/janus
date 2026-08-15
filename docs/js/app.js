(() => {
  const J = window.JANUS_FINDINGS;
  if (!J) {
    document.body.insertAdjacentHTML(
      "afterbegin",
      "<p style='padding:2rem;font-family:sans-serif'>Findings failed to load. Run <code>python -m janus.run_audit</code>.</p>"
    );
    return;
  }

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

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
      if (el.dataset.run) {
        el.classList.add("mono");
        el.title = el.dataset.run;
        el.tabIndex = 0;
        el.addEventListener("click", () => toast(`Provenance ${el.dataset.run}`));
        el.addEventListener("keydown", (e) => {
          if (e.key === "Enter") toast(`Provenance ${el.dataset.run}`);
        });
      }
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
    const known = ["brief", "investigate", "routes", "memo", "method"];
    const name = known.includes(view) ? view : "brief";
    showView(name);
    if (name === "investigate") setStep(Number(extra || 0) || 0);
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
    $("#btn-play").textContent = playing ? "Pause" : "Play";
    if (playing) tick();
  });
  function tick() {
    if (!playing) return;
    if (step === 0 && !$("#gate-mutability").checked) {
      $("#gate-mutability").checked = true;
    }
    if (step >= panels.length - 1) {
      playing = false;
      $("#btn-play").textContent = "Play";
      return;
    }
    setStep(step + 1);
    setTimeout(tick, 1600);
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

  function fillBattery() {
    const atk = J.battery.attack_surface;
    const proxy = J.battery.proxy_audit;
    const excl = J.battery.unexplained_exclusion;
    const segs = J.battery.broken_segments.young_self_employed;
    const tiles = [
      { run: atk.run_id, k: "Gaming surface", v: fmt.pct1(atk.flip_rate), s: `median ${fmt.yen(atk.median_cost_jpy)} · n=${atk.n_sampled}` },
      { run: proxy.run_id, k: "Proxy reconstruction", v: fmt.auc(proxy.probe_auc), s: `rural via ${proxy.chief_carrier}` },
      { run: excl.run_id, k: "Unexplained exclusion", v: fmt.pp(excl.approval_gap_pp), s: `default ${fmt.pct1(excl.default_informal)} vs ${fmt.pct1(excl.default_formal)}` },
      { run: "run.discover_segments", k: "Young self-employed", v: `${fmt.pct1(segs.predicted_default)} pred`, s: `actual ${fmt.pct1(segs.actual_default)} · n=${segs.n}` },
    ];
    $("#battery-tiles").innerHTML = tiles
      .map(
        (t) => `<article>
          <p class="label">${t.k}</p>
          <p class="big" title="${t.run}">${t.v}</p>
          <p class="sub">${t.s}</p>
        </article>`
      )
      .join("");
  }

  function fillCurve() {
    const curve = J.battery.evidence_recourse.documentation_curve || [];
    $("#doc-curve").innerHTML = curve
      .map(
        (c) => `<div class="bar">
          <span class="label">${Math.round(c.documented_share * 100)}% documented</span>
          <b>${fmt.pct1(c.cross_rate)}</b>
          <span class="sub">cross the cutoff</span>
        </div>`
      )
      .join("");
  }

  const menu = J.recourse_menu;
  const cutoff = J.model.cutoff;
  const pStart = menu.p_start;
  const routes = {
    a: menu.route_a_fake_it,
    b: menu.route_b_earn_it,
    c: menu.route_c_document_it,
  };

  function fillRoutes() {
    $("#cost-a").textContent = fmt.yen(routes.a.cost_jpy);
    $("#time-a").textContent = "one afternoon";
    $("#p-a").textContent = `${fmt.p(routes.a.p_start)} → ${fmt.p(routes.a.p_final)}`;
    $("#cost-b").textContent = fmt.yen(routes.b.cost_jpy);
    $("#time-b").textContent = fmt.days(routes.b.days);
    $("#p-b").textContent = `${fmt.p(routes.b.p_start)} → ${fmt.p(routes.b.p_final)}`;
    $("#time-c").textContent = `${routes.c.documentation_months} months of statements`;
    $("#p-c").textContent = `${fmt.p(routes.c.p_start)} → ${fmt.p(routes.c.p_final)} · DTI ${fmt.dti(routes.c.dti_start)} → ${fmt.dti(routes.c.dti_final)}`;
    setP(pStart);
    const cutPct = Math.min(98, Math.max(2, (cutoff / 0.8) * 100));
    $("#p-cutoff-tick").style.left = `${cutPct}%`;
  }

  function setP(p) {
    const pct = Math.min(98, Math.max(2, (p / 0.8) * 100));
    $("#p-needle").style.left = `${pct}%`;
    $("#p-now").textContent = fmt.p(p);
    const approved = p < cutoff;
    $("#p-decision").textContent = approved ? "APPROVED" : "DECLINED";
    $("#p-decision").style.color = approved ? "#9ad4be" : "#f0a396";
    $("#dock-decision").textContent = approved ? "would cross cutoff" : "declined";
  }

  $("#btn-reset-p")?.addEventListener("click", () => {
    $$(".route").forEach((card) => card.classList.remove("is-live"));
    $$("[data-apply]").forEach((b) => {
      b.textContent = "Apply on desk";
    });
    setP(pStart);
    $("#route-reveal").hidden = true;
  });

  $$("[data-apply]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const key = btn.dataset.apply;
      $$(".route").forEach((card) => card.classList.toggle("is-live", card.dataset.route === key));
      $$("[data-apply]").forEach((b) => {
        const applied = b.dataset.apply === key;
        b.textContent = applied ? "Applied on desk" : b.dataset.apply === "c" ? "Apply on desk" : "Apply on desk";
      });
      setP(routes[key].p_final);
      const reveal = $("#route-reveal");
      if (key === "c") {
        reveal.hidden = false;
      }
      toast(key === "a" ? "Route A applied — owner desk only" : `Route ${key.toUpperCase()} applied on the desk`);
    });
  });

  function fillFindings() {
    const list = $("#findings-list");
    list.innerHTML = J.investigation.findings
      .map(
        (f) => `<li>
          <label>
            <input type="checkbox" class="finding-box" data-id="${f.id}" checked>
            <span>
              <strong>${f.id} · ${f.title}</strong>
              <span class="run"> ${f.run_id} · ${f.severity}</span>
              <br>${f.claim}
            </span>
          </label>
        </li>`
      )
      .join("");
  }

  function updateSign() {
    const boxes = $$(".finding-box");
    const accepted = boxes.filter((b) => b.checked).length;
    const gated = $("#gate-findings").checked;
    $("#sign-status").textContent = gated
      ? `Package signed. ${accepted} of ${boxes.length} findings accepted.`
      : `Package unsigned. ${accepted} of ${boxes.length} findings checked.`;
  }

  function routeHash() {
    window.addEventListener("hashchange", parseHash);
    if (!location.hash) location.hash = "#brief";
    else parseHash();
  }

  document.addEventListener("keydown", (e) => {
    if (["INPUT", "TEXTAREA"].includes(e.target.tagName)) return;
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

  bind();
  fillMutability();
  fillBattery();
  fillCurve();
  fillRoutes();
  fillFindings();
  $("#gate-findings")?.addEventListener("change", updateSign);
  document.addEventListener("change", (e) => {
    if (e.target.classList.contains("finding-box")) updateSign();
  });
  updateSign();
  routeHash();
})();
