import { escapeHtml, fmt } from "../format.js";
import { state } from "../state.js";

export function renderTwins() {
  const t = state.twins || {};
  const root = document.getElementById("twins-engine");
  if (!root) return;
  const cf = t.counterfactual;
  const matched = t.matched_observation || {};
  let html = "";
  if (cf) {
    html += pair(cf);
  }
  if (matched.skipped) {
    html += `<p class="skipped">${escapeHtml(matched.reason)}</p>`;
  } else {
    (matched.pairs || []).forEach((p) => {
      html += pair(p);
    });
  }
  const conceptual = t.capital_injection_example || {};
  html += `<p class="note">${escapeHtml(conceptual.note || "")}</p>`;
  root.innerHTML = html;
}

function pair(p) {
  const left = p.left || {};
  const right = p.right || {};
  return `<div class="twins">
    <article>
      <p class="eyebrow">${escapeHtml(p.mode || "")}</p>
      <h3>${escapeHtml(left.title || "Left")}</h3>
      <p class="mono">${escapeHtml(left.applicant_id || "")}</p>
      <p>p = <span class="mono">${fmt.p(left.p)}</span> · ${escapeHtml(left.decision || "")}</p>
      <p>Outcome: ${left.default == null ? "—" : left.default ? "defaulted" : "did not default"}</p>
    </article>
    <article>
      <h3>${escapeHtml(right.title || "Right")}</h3>
      <p class="mono">${escapeHtml(right.applicant_id || "")}</p>
      <p>p = <span class="mono">${fmt.p(right.p)}</span> · ${escapeHtml(right.decision || "")}</p>
      <p>Outcome: ${right.default == null ? "—" : right.default ? "defaulted" : "did not default"}</p>
    </article>
  </div>
  <p class="fineprint">${escapeHtml(p.limitation || "")} ${escapeHtml(p.why || "")}</p>`;
}
