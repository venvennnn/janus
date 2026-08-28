import { escapeHtml, fmt, statusLabel } from "../format.js";
import { state } from "../state.js";

export function renderOverview() {
  const h = state.health || {};
  const domains = h.domain_statuses || {};
  const findings = ((state.findings || {}).investigation || {}).findings || [];
  const top = findings.slice(0, 5);
  const core = h.core_metrics || {};
  const atk = ((state.findings || {}).battery || {}).attack_surface || {};
  document.getElementById("ov-health-status").textContent = h.conclusion || "—";
  document.getElementById("ov-integrity-status").textContent = atk.skipped
    ? atk.reason || "Skipped"
    : `Attack flip ${fmt.pct1(atk.flip_rate)}`;
  document.getElementById("ov-findings").innerHTML = top
    .map(
      (f) => `<li><strong>${escapeHtml(f.title)}</strong> · ${escapeHtml(f.severity)} · ${escapeHtml(usd(f.claim))}</li>`
    )
    .join("") || "<li>No findings in this run.</li>";
  document.getElementById("ov-auc").textContent = fmt.auc(core.roc_auc);
  const steps = ["Intake", "Model Health", "Assumptions", "Integrity Tests", "Remediation", "Review"];
  document.getElementById("ov-workflow").innerHTML = steps.map((s) => `<li>${s}</li>`).join("");
  const grid = document.getElementById("ov-domains");
  if (grid) {
    grid.innerHTML = Object.entries(domains)
      .map(([k, v]) => `<div class="mini"><dt>${escapeHtml(k.replace(/_/g, " "))}</dt><dd>${escapeHtml(statusLabel(v))}</dd></div>`)
      .join("");
  }
}

function usd(s) {
  return String(s || "")
    .replace(/\u00a5/g, "$")
    .replace(/¥/g, "$");
}
