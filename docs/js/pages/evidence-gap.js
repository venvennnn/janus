import { escapeHtml, fmt } from "../format.js";
import { state } from "../state.js";

export function renderEvidenceGap() {
  const ev = ((state.findings || {}).battery || {}).evidence_recourse || {};
  const el = document.getElementById("evidence-root");
  if (!el) return;
  if (ev.skipped) {
    el.innerHTML = `<p class="skipped">${escapeHtml(ev.reason || "Skipped — no evidence pair")}</p>`;
    return;
  }
  el.innerHTML = `
    <div class="evidence">
      <article class="card"><h3>Cross-cutoff rate</h3><p class="big">${fmt.pct1(ev.cross_rate_full_documentation)}</p><p class="meaning">Declined informal rows that cross after documenting existing income.</p></article>
      <article class="card"><h3>Crossers' default</h3><p class="big">${fmt.pct1(ev.cross_default_rate)}</p><p class="meaning">Portfolio default ${fmt.pct1(ev.portfolio_default_rate)}.</p></article>
      <article class="card"><h3>Recorded vs true DTI</h3><p class="big">${fmt.dti(ev.median_recorded_dti)} → ${fmt.dti(ev.median_true_dti)}</p><p class="meaning">Cost $0. Never fabricated.</p></article>
    </div>
    <p class="fineprint">Route C requires a recorded-versus-verified pair. On real data this is directional until the gap is estimated from cash-flow.</p>
  `;
}
