import { escapeHtml, fmt, statusLabel } from "../format.js";
import { rocChart, prChart, calibrationChart, bandChart } from "../charts.js";
import { state } from "../state.js";

export function renderHealth() {
  const h = state.health;
  const el = document.getElementById("health-root");
  if (!h) {
    el.innerHTML = `<p class="skipped">Model Health has not been run.</p>`;
    return;
  }
  const m = h.metadata || {};
  const c = h.core_metrics || {};
  const s = h.secondary_metrics || {};
  const cards = [
    ["ROC AUC", fmt.auc(c.roc_auc), "Ranking quality for default vs non-default."],
    ["Gini", fmt.auc(c.gini), "2 × AUC − 1."],
    ["KS", fmt.auc(c.ks), "Maximum separation of score CDFs."],
    ["PR-AUC", fmt.auc(c.pr_auc), "Average precision for defaults."],
    ["Brier", fmt.auc(c.brier), "Mean squared error of probabilities."],
    ["Acceptance", fmt.pct1(c.acceptance_rate), "Share with p(default) ≤ cutoff."],
    ["Approved default", fmt.pct1(c.approved_default_rate), "Realised default among approved."],
    ["Approved loss", c.approved_loss_rate == null ? "Skipped" : fmt.pct1(c.approved_loss_rate), "Needs a confirmed exposure column."],
  ];
  const segs = (h.segment_exceptions || [])
    .map(
      (r) => `<tr><td>${escapeHtml(r.segment_field)}</td><td>${escapeHtml(r.segment_value)}</td><td class="mono">${r.count}</td>
      <td class="mono">${fmt.pct1(r.default_rate)}</td><td class="mono">${fmt.pct1(r.approval_rate)}</td>
      <td class="mono">${fmt.auc(r.auc)}</td><td class="mono">${fmt.auc(r.calibration_error)}</td>
      <td class="mono">${fmt.auc(r.difference_from_overall)}</td><td>${escapeHtml(r.status)}</td></tr>`
    )
    .join("");
  const healthStrip = (h.data_health || [])
    .map((d) => `<li><strong>${escapeHtml(statusLabel(d.status))}</strong> ${escapeHtml(d.id.replace(/_/g, " "))} — ${escapeHtml(typeof d.detail === "string" ? d.detail : JSON.stringify(d.detail))}</li>`)
    .join("");
  const rolling = h.rolling || {};
  const curveToggle = `<p class="hero-actions"><button type="button" class="btn btn-ghost" data-curve="roc">ROC</button><button type="button" class="btn btn-ghost" data-curve="pr">Precision-Recall</button></p>
    <div id="health-curve">${rocChart((h.curves || {}).roc)}</div>`;
  el.innerHTML = `
    <div class="desk">
      <dl class="mini">
        <div><dt>Model</dt><dd>${escapeHtml(m.model_name || "—")}</dd></div>
        <div><dt>Target</dt><dd class="mono">${escapeHtml(m.target_column || "—")} = ${escapeHtml(String(m.positive_class ?? 1))}</dd></div>
        <div><dt>n / defaults</dt><dd class="mono">${fmt.int(m.n)} / ${fmt.int(m.n_defaults)}</dd></div>
        <div><dt>Default rate</dt><dd class="mono">${fmt.pct1(m.default_rate)}</dd></div>
        <div><dt>Cutoff</dt><dd class="mono">${fmt.p(m.cutoff)}</dd></div>
        <div><dt>Period</dt><dd>${escapeHtml(m.evaluation_period || "Not dated")}</dd></div>
      </dl>
      <div>
        <p class="badge-amber">Policy ${escapeHtml(h.policy_id || "")}</p>
        <p class="display" style="font-size:40px">${escapeHtml(h.conclusion || "—")}</p>
        <p class="fineprint">${escapeHtml(h.policy_label || "")}</p>
        <p class="fineprint">${escapeHtml(h.conclusion_rule || "")}</p>
      </div>
    </div>
    <div class="evidence">${cards.map(([n, v, t]) => `<article class="card"><h3>${n}</h3><p class="big">${v}</p><p class="meaning">${t}</p></article>`).join("")}</div>
    <details class="card" style="margin:20px 0"><summary>Optional secondary metrics</summary>
      <p>Log loss ${fmt.auc(s.log_loss)} · Accuracy ${fmt.pct1(s.accuracy)} · Precision ${fmt.pct1(s.precision)} · Recall ${fmt.pct1(s.recall)} · Specificity ${fmt.pct1(s.specificity)} · F1 ${fmt.pct1(s.f1)}</p>
    </details>
    <h3 class="subhead">Charts</h3>
    ${curveToggle}
    <div class="twins">
      <article><h3>Calibration</h3>${calibrationChart((h.calibration || {}).bins)}<p class="fineprint">ECE ${fmt.auc((h.calibration || {}).ece)}</p></article>
      <article><h3>Score bands</h3>${bandChart(h.score_bands)}</article>
    </div>
    <article class="card" style="margin-top:16px"><h3>Rolling stability</h3>
      ${rolling.skipped ? `<p class="skipped">${escapeHtml(rolling.reason || "Skipped")}</p>` : `<p>PSI ${fmt.auc(h.psi)}. Periods: ${(rolling.periods || []).length}.</p>`}
    </article>
    <h3 class="subhead">Data health</h3>
    <ul class="rules">${healthStrip}</ul>
    <h3 class="subhead">Segment exceptions</h3>
    ${segs ? `<div class="table-wrap"><table class="grid"><thead><tr><th>Field</th><th>Value</th><th>n</th><th>Default</th><th>Approval</th><th>AUC</th><th>ECE</th><th>Δ</th><th>Status</th></tr></thead><tbody>${segs}</tbody></table></div>` : `<p class="skipped">No segment exceptions above the policy minimum.</p>`}
    <p class="pull" style="max-width:40ch">The model predicts. Now test whether its decisions survive the real world.</p>
    <p><a class="btn" href="#attack">Start Integrity Red Team</a></p>
  `;
  el.querySelectorAll("[data-curve]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const box = document.getElementById("health-curve");
      box.innerHTML = btn.dataset.curve === "pr" ? prChart((h.curves || {}).pr) : rocChart((h.curves || {}).roc);
    });
  });
}
