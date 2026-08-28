import { escapeHtml, fmt } from "../format.js";
import { state } from "../state.js";

export function renderRemediation() {
  const scenarios = (state.remediation || {}).scenarios || [];
  const el = document.getElementById("remediation-root");
  if (!el) return;
  if (!scenarios.length) {
    el.innerHTML = `<p class="skipped">No remediation scenarios in this run.</p>`;
    return;
  }
  const rows = scenarios
    .map((s, i) => {
      const d = s.delta_from_baseline || {};
      const c = s.core_metrics || {};
      return `<tr>
        <td>${escapeHtml(s.name)}</td>
        <td class="mono">${fmt.auc(c.roc_auc)} (${sign(d.roc_auc)})</td>
        <td class="mono">${fmt.auc(c.brier)} (${sign(d.brier)})</td>
        <td class="mono">${fmt.pct1(c.acceptance_rate)} (${sign(d.acceptance_rate, true)})</td>
        <td class="mono">${fmt.pct1(c.approved_default_rate)} (${sign(d.approved_default_rate, true)})</td>
        <td>${escapeHtml(s.reviewer_status || "needs review")}</td>
      </tr><tr><td colspan="6" class="fineprint">${escapeHtml((s.notes || []).join(" "))}</td></tr>`;
    })
    .join("");
  el.innerHTML = `
    <p class="note">These are input or policy sensitivity tests. The estimator was not retrained.</p>
    <div class="table-wrap"><table class="grid">
      <thead><tr><th>Scenario</th><th>AUC (Δ)</th><th>Brier (Δ)</th><th>Acceptance (Δ)</th><th>Approved default (Δ)</th><th>Status</th></tr></thead>
      <tbody>${rows}</tbody>
    </table></div>
  `;
}

function sign(v, pct) {
  if (v == null || Number.isNaN(Number(v))) return "—";
  const n = Number(v);
  const txt = pct ? `${n >= 0 ? "+" : ""}${(n * 100).toFixed(1)}pp` : `${n >= 0 ? "+" : ""}${n.toFixed(3)}`;
  return txt;
}
