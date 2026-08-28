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
  const held = (left.held_constant || []).map(escapeHtml).join(", ");
  const differs = formatDiff(left.differs || right.differs || {});
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
  <p class="fineprint">Held constant: ${held || "—"}. Differs: ${differs}. Matching distance ${p.matching_distance == null ? "—" : fmt.auc(p.matching_distance)}.</p>
  <p class="fineprint">${escapeHtml(p.limitation || "")} ${escapeHtml(p.why || "")}</p>`;
}

function formatDiff(diff) {
  if (!diff || typeof diff !== "object") return "—";
  if (Array.isArray(diff.features)) return diff.features.map(escapeHtml).join(", ") || "—";
  return Object.keys(diff)
    .map((k) => {
      const v = diff[k];
      if (v && typeof v === "object" && "left" in v) return `${escapeHtml(k)} (${v.left} → ${v.right})`;
      return escapeHtml(k);
    })
    .join("; ") || "—";
}
