import { escapeHtml, fmt, statusLabel, usdText } from "../format.js?v=032";
import { state } from "../state.js?v=032";

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
    : atk.flip_rate == null
      ? "Integrity tests not started"
      : `Attack flip ${fmt.pct1(atk.flip_rate)}`;
  document.getElementById("ov-findings").innerHTML = top
    .map(
      (f) => `<li><strong>${escapeHtml(f.title)}</strong> · ${escapeHtml(f.severity)} · ${escapeHtml(usdText(f.claim || f.description || ""))}</li>`
    )
    .join("") || "<li>No findings in this run.</li>";
  document.getElementById("ov-auc").textContent = fmt.auc(core.roc_auc);
  const steps = [
    ["intake", "Intake"],
    ["health", "Model Health"],
    ["assumptions", "Assumptions"],
    ["integrity", "Integrity Tests"],
    ["remediation", "Remediation"],
    ["review", "Review"],
  ];
  const now = state.workflowStep || "review";
  document.getElementById("ov-workflow").innerHTML = steps
    .map(([key, label]) => `<li class="${key === now ? "is-now" : ""}">${label}</li>`)
    .join("");
  const grid = document.getElementById("ov-domains");
  if (grid) {
    grid.innerHTML = Object.entries(domains)
      .map(([k, v]) => `<div><dt>${escapeHtml(k.replace(/_/g, " "))}</dt><dd>${escapeHtml(statusLabel(v))}</dd></div>`)
      .join("");
  }
  const cta = document.querySelector(".hero-actions .text-btn");
  if (cta) {
    if (now === "intake") cta.setAttribute("href", "#audit");
    else if (now === "health" || now === "assumptions") cta.setAttribute("href", "#audit");
    else cta.setAttribute("href", "#attack");
  }
}
