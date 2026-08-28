import { escapeHtml, fmt } from "../format.js";
import { state } from "../state.js";

export function renderEvidenceCards() {
  const J = state.findings || {};
  const b = J.battery || {};
  const atk = b.attack_surface || {};
  const gap = b.integrity_gap || {};
  const ev = b.evidence_recourse || {};
  const grid = document.getElementById("attack-evidence");
  if (!grid) return;
  const items = [
    ["Attack flip rate", atk.skipped ? "skipped" : fmt.pct1(atk.flip_rate), atk.skipped ? atk.reason : "Eligible declines that cross after presentation-sensitive change.", atk.run_id],
    ["Median attack effort", atk.skipped ? "skipped" : fmt.usd(atk.median_cost_jpy), "Median configured effort among successful attacks.", atk.run_id],
    ["Integrity gap", gap.skipped ? "skipped" : fmt.times(gap.median_gap_ratio), `Cosmetic ${fmt.usd(gap.median_attack_cost_jpy)} vs genuine ${fmt.usd(gap.median_genuine_cost_jpy)}. Human-confirmed assumptions required.`, gap.run_id],
    ["Flipped-record default", atk.skipped ? "—" : fmt.pct1(atk.flipped_default_rate), `Baseline ${fmt.pct1(atk.baseline_default_rate)}. A flip is a decision change, not better performance.`, atk.run_id],
    ["Evidence cross rate", ev.skipped ? "skipped" : fmt.pct1(ev.cross_rate_full_documentation), ev.skipped ? ev.reason : "Cutoff crosses after documented income. Route C only when a recorded/verified pair exists.", ev.run_id],
  ];
  grid.innerHTML = items
    .map(
      ([name, value, meaning, run]) => `<article class="card"><h3>${escapeHtml(name)}</h3><p class="big">${escapeHtml(value)}</p><p class="meaning">${escapeHtml(meaning)}</p><p class="run">${escapeHtml(run || "")}</p></article>`
    )
    .join("");
}
