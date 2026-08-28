import { escapeHtml, fmt } from "../format.js?v=032";
import { state } from "../state.js?v=032";

export function renderEvidenceCards() {
  const J = state.findings || {};
  const b = J.battery || {};
  const atk = b.attack_surface || {};
  const gap = b.integrity_gap || {};
  const ev = b.evidence_recourse || (state.evidenceGap || {}).result || {};
  const grid = document.getElementById("attack-evidence");
  if (!grid) return;
  const items = [
    ["Attack flip rate", atk.skipped ? "skipped" : fmt.pct1(atk.flip_rate), atk.skipped ? atk.reason : `${fmt.int(atk.n_flipped)} of ${fmt.int(atk.n_sampled)} eligible declines. Presentation-sensitive change only.`, atk.run_id],
    ["Cosmetic vs genuine flip", gap.skipped ? "skipped" : `${fmt.pct1(gap.attack_flip_rate)} / ${fmt.pct1(gap.genuine_flip_rate)}`, "Route A versus Route B flip rates. Formula: cosmetic ÷ genuine, with numerator and denominator returned.", gap.run_id],
    ["Median attack effort", atk.skipped ? "skipped" : fmt.usd(atk.median_cost_jpy), "Median configured effort among successful attacks.", atk.run_id],
    ["Integrity gap (cost)", gap.skipped ? "skipped" : fmt.times(gap.median_gap_ratio), `Cosmetic ${fmt.usd(gap.median_attack_cost_jpy)} vs genuine ${fmt.usd(gap.median_genuine_cost_jpy)}. Human-confirmed assumptions required.`, gap.run_id],
    ["Flipped-record default", atk.skipped ? "—" : fmt.pct1(atk.flipped_default_rate), `Baseline ${fmt.pct1(atk.baseline_default_rate)}. A flip is a decision change, not better performance.`, atk.run_id],
    ["Evidence cross rate", ev.skipped ? "skipped" : fmt.pct1(ev.cross_rate_full_documentation ?? ev.cross_rate), ev.skipped || !ev.cross_rate_full_documentation && !ev.cross_rate ? (ev.reason || "Skipped — no evidence pair") : "Cutoff crosses after documented or verified values. Route C only when a pair exists.", ev.run_id],
  ];
  const cards = items
    .map(
      ([name, value, meaning, run]) => `<article class="card"><h3>${escapeHtml(name)}</h3><p class="big">${escapeHtml(value)}</p><p class="meaning">${escapeHtml(meaning)}</p><p class="run">${escapeHtml(run || "")}</p></article>`
    )
    .join("");
  const ids = (atk.flipped_applicant_ids || []).slice(0, 12).map((id) => escapeHtml(id)).join(", ");
  const limits = `<p class="note">Limitations: bounds come from confirmed assumptions. Immutable features are not modified. Successful attacks are not proof of fraud. Masked record IDs: ${ids || "none listed"}.</p>`;
  grid.innerHTML = cards + limits;
}
