import { escapeHtml } from "../format.js";
import { state } from "../state.js";

export function renderWatch() {
  const w = state.watch || {};
  const el = document.getElementById("watch-root");
  if (!el) return;
  if (w.skipped) {
    el.innerHTML = `<p class="skipped">${escapeHtml(w.reason || "Need a second run.")}</p>
      <p>Integrity Watch compares Model Health and integrity metrics across two runs. It also shows policy and assumption changes so a definition change is not mistaken for a model change.</p>`;
    return;
  }
  el.innerHTML = `<pre class="mono">${escapeHtml(JSON.stringify(w.metric_deltas || {}, null, 2))}</pre>`;
}
