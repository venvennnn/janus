import { $, $$, fmt, bind as bindData, escapeHtml } from "./format.js";
import { apiUrl, apiDetail, pingApi, fetchJSON } from "./api.js";
import { state, setState } from "./state.js";
import { initRouter } from "./router.js";
import { renderOverview } from "./pages/overview.js";
import { renderHealth } from "./pages/model-health.js";
import { renderEvidenceCards } from "./pages/attack-lab.js";
import { renderTwins } from "./pages/decision-twins.js";
import { renderEvidenceGap } from "./pages/evidence-gap.js";
import { renderRemediation } from "./pages/remediation.js";
import { renderWatch } from "./pages/integrity-watch.js";
import { renderRoom, exportJSON, exportHTML } from "./pages/evidence-room.js";

initRouter();

let routes = {};
let cutoff;
let pStart;
let uploadJob = null;
const progressTimers = new WeakMap();

function toast(message) {
  const el = $("#toast");
  if (!el) return;
  el.textContent = message;
  el.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => {
    el.hidden = true;
  }, 2200);
}

function paintHeader() {
  $("#hdr-run").textContent = state.runName;
  $("#hdr-mode").textContent = state.mode === "reference" ? "Reference" : "Live audit";
  $("#hdr-model").textContent = state.modelVersion;
  $("#hdr-status").textContent = state.runStatus;
}

function renderAll() {
  paintHeader();
  bindData(document, state.findings || {});
  renderOverview();
  renderHealth();
  renderEvidenceCards();
  fillDesk();
  renderTwins();
  renderEvidenceGap();
  renderRemediation();
  renderWatch();
  renderRoom();
}

function fillDesk() {
  const J = state.findings || {};
  const d = J.demo_applicant || {};
  const menu = J.recourse_menu || {};
  cutoff = J.model?.cutoff;
  pStart = menu.p_start;
  routes = {
    a: menu.route_a_fake_it || {},
    b: menu.route_b_earn_it || {},
    c: menu.route_c_document_it || {},
  };
  const story = $("#demo-story");
  if (story) {
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
    story.textContent = bits.join(" ") || "A declined applicant from this holdout.";
  }
  const def = $("#demo-default");
  if (def) def.textContent = d.default == null ? "—" : d.default ? "defaulted" : "did not default";
  if ($("#cost-a")) {
    $("#cost-a").textContent = routes.a.cost_jpy == null ? "—" : fmt.usd(routes.a.cost_jpy);
    $("#time-a").textContent = routes.a.days == null ? "low effort" : fmt.days(routes.a.days);
    $("#p-a").textContent = routes.a.p_final == null ? "—" : `${fmt.p(routes.a.p_start ?? pStart)} → ${fmt.p(routes.a.p_final)}`;
    const feats = (routes.a.features || []).join(", ");
    $("#steps-a").textContent = feats
      ? `Model owner only: presentation-sensitive levers on ${feats}. Not applicant guidance.`
      : "Model owner only.";
    $("#cost-b").textContent = routes.b.cost_jpy == null ? "—" : fmt.usd(routes.b.cost_jpy);
    $("#time-b").textContent = routes.b.days == null ? "durable change" : fmt.days(routes.b.days);
    $("#p-b").textContent = routes.b.p_final == null ? "—" : `${fmt.p(routes.b.p_start ?? pStart)} → ${fmt.p(routes.b.p_final)}`;
    const btnC = $("[data-apply=c]");
    if (routes.c.skipped || routes.c.p_final == null) {
      $("#cost-c").textContent = "Not available";
      $("#time-c").textContent = "Not available for this dataset";
      $("#p-c").textContent = routes.c.ask || "Route C needs a recorded/true income gap.";
      if (btnC) {
        btnC.disabled = true;
        btnC.classList.add("is-disabled");
      }
    } else {
      $("#cost-c").textContent = routes.c.cost_jpy == null ? "$0" : fmt.usd(routes.c.cost_jpy);
      $("#time-c").textContent = routes.c.documentation_months
        ? `${routes.c.documentation_months} months of statements`
        : "documentation only";
      $("#p-c").textContent = `${fmt.p(routes.c.p_start ?? pStart)} → ${fmt.p(routes.c.p_final)}`;
      if (btnC) {
        btnC.disabled = false;
        btnC.classList.remove("is-disabled");
      }
    }
  }
  setP(pStart);
  resetRoutes();
}

function setP(p) {
  if (p == null || cutoff == null || !$("#p-now")) return;
  const approved = p <= cutoff;
  $("#p-now").textContent = fmt.p(p);
  if ($("#p-now-dup")) $("#p-now-dup").textContent = fmt.p(p);
  $("#p-decision").textContent = approved ? "WOULD CROSS CUTOFF" : "DECLINED";
  $("#p-decision").classList.toggle("is-ok", approved);
  $("#p-decision").classList.toggle("is-bad", !approved);
  const max = Math.max(0.6, cutoff * 1.4, p * 1.15);
  $("#p-needle").style.left = `${Math.max(0, Math.min(100, (p / max) * 100))}%`;
  $("#p-cutoff-tick").style.left = `${Math.max(0, Math.min(100, (cutoff / max) * 100))}%`;
}

function resetRoutes() {
  $$(".route").forEach((card) => card.classList.remove("is-live"));
  $$("[data-apply]").forEach((b) => {
    b.textContent = `Apply route ${b.dataset.apply.toUpperCase()}`;
  });
  setP(pStart);
  if ($("#route-reveal")) $("#route-reveal").hidden = true;
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
  if (reveal) {
    reveal.textContent = lines[key] || "";
    reveal.hidden = false;
  }
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
        <td><code>${escapeHtml(row.feature)}</code></td>
        <td><select name="kind">${kinds}</select></td>
        <td><select name="direction">${dirs}</select></td>
        <td><input name="attack" type="number" step="1" value="${row.attack_cost_jpy ?? ""}"></td>
        <td><input name="attack_days" type="number" step="0.1" value="${row.attack_days ?? ""}"></td>
        <td><input name="genuine" type="number" step="1" value="${row.genuine_cost_jpy ?? ""}"></td>
        <td><input name="genuine_days" type="number" step="0.1" value="${row.genuine_days ?? ""}"></td>
        <td><input name="rationale" type="text" value="${escapeHtml(row.rationale || "")}"></td>
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

function startProgress(el, labels) {
  stopProgress(el);
  let i = 0;
  el.textContent = labels[0];
  progressTimers.set(
    el,
    setInterval(() => {
      i = (i + 1) % labels.length;
      el.textContent = labels[i];
    }, 1600)
  );
}

function stopProgress(el) {
  const id = progressTimers.get(el);
  if (id) clearInterval(id);
  progressTimers.delete(el);
}

function wire() {
  $$("[data-apply]").forEach((btn) => btn.addEventListener("click", () => applyRoute(btn.dataset.apply)));
  $("#btn-reset-p")?.addEventListener("click", resetRoutes);
  $("#btn-export-json")?.addEventListener("click", exportJSON);
  $("#btn-export-html")?.addEventListener("click", exportHTML);
  $("#btn-new-audit")?.addEventListener("click", () => {
    location.hash = "#audit";
  });
  $("#btn-use-book")?.addEventListener("click", async () => {
    await loadReference();
    toast("Reference case reloaded");
    location.hash = "#overview";
  });
  document.addEventListener("keydown", (e) => {
    if (["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName)) return;
    if (e.key === "1" || e.key === "2" || e.key === "3") applyRoute(["a", "b", "c"][Number(e.key) - 1]);
    if (e.key === "r" || e.key === "R") resetRoutes();
  });
  $("#gate-upload-mutability")?.addEventListener("change", () => {
    const btn = $("#btn-run-upload");
    if (btn) btn.disabled = !$("#gate-upload-mutability").checked;
  });
  $("#audit-form")?.addEventListener("submit", onPropose);
  $("#btn-run-upload")?.addEventListener("click", onRun);
  pingApi()
    .then((body) => {
      const llm = body.llm === "anthropic" ? `Agent on (${body.model || "anthropic"}).` : "Heuristic fallback (no LLM key).";
      $("#api-status").textContent = `Review service up (${body.version}). ${llm}`;
      if ($("#sample-zip")) $("#sample-zip").href = apiUrl("/sample.zip");
    })
    .catch(() => {
      $("#api-status").textContent =
        "Review service is asleep or not configured. GitHub Pages still serves this reference case without a backend.";
    });
}

async function onPropose(e) {
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
  startProgress(status, ["Inspecting model", "Reading feature definitions"]);
  try {
    const res = await fetch(apiUrl("/propose"), { method: "POST", body: data });
    const body = await res.json().catch(() => ({}));
    stopProgress(status);
    if (!res.ok) throw new Error(apiDetail(body, res.statusText));
    uploadJob = body;
    fillProposeTable(Array.isArray(body.proposal) ? body.proposal : []);
    $("#propose-stage").hidden = false;
    $("#gate-upload-mutability").checked = false;
    $("#btn-run-upload").disabled = true;
    status.textContent = `Awaiting human confirmation. ${body.model?.n_features} features · AUC ${fmt.auc(body.model?.auc_holdout)}.`;
  } catch (err) {
    stopProgress(status);
    status.textContent = String(err.message || err);
  }
}

async function onRun() {
  const status = $("#run-status");
  if (!$("#gate-upload-mutability").checked) {
    status.textContent = "Confirm the mutability table before search runs.";
    return;
  }
  if (!uploadJob) {
    status.textContent = "Propose first.";
    return;
  }
  startProgress(status, ["Searching decision boundary", "Testing segments", "Building evidence package"]);
  try {
    const res = await fetch(apiUrl("/run"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: uploadJob.job_id, confirmed: true, levers: collectLevers() }),
    });
    const body = await res.json().catch(() => ({}));
    stopProgress(status);
    if (!res.ok) throw new Error(apiDetail(body, res.statusText));
    setState({
      mode: "live",
      runId: body.run_id || uploadJob.job_id,
      runName: "Live audit",
      runStatus: "Integrity tests complete",
      modelVersion: "uploaded",
      findings: body,
    });
    renderAll();
    status.textContent = "Live results are bound on this page. Raw holdout was dropped from memory.";
    location.hash = "#overview";
  } catch (err) {
    stopProgress(status);
    status.textContent = String(err.message || err);
  }
}

async function loadReference() {
  const findings = window.JANUS_FINDINGS || (await fetchJSON("./data/findings.json"));
  const [health, twins, remediation, watch, policy] = await Promise.all([
    fetchJSON("./data/model_health.json").catch(() => null),
    fetchJSON("./data/twins.json").catch(() => null),
    fetchJSON("./data/remediation.json").catch(() => null),
    fetchJSON("./data/watch.json").catch(() => null),
    fetchJSON("./data/policy.json").catch(() => null),
  ]);
  setState({
    mode: "reference",
    runId: "reference",
    runName: "Synthetic reference case",
    runStatus: health?.conclusion || "Recorded",
    modelVersion: (health?.metadata || {}).model_version || "reference-scorecard",
    findings,
    health,
    twins,
    remediation,
    watch,
    policy,
  });
  renderAll();
}

loadReference().catch((err) => {
  document.body.insertAdjacentHTML("afterbegin", `<p style="padding:2rem">Reference data failed to load. ${escapeHtml(err.message)}</p>`);
});
wire();
