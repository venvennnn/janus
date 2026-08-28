import { escapeHtml, fmt } from "../format.js";
import { state } from "../state.js";
import { fetchJSON, postJSON, apiUrl } from "../api.js";

export function renderWatch() {
  const w = state.watch || {};
  const el = document.getElementById("watch-root");
  if (!el) return;
  el.innerHTML = `
    ${w.skipped ? `<p class="skipped">${escapeHtml(w.reason || "Need a second run.")}</p>` : renderDeltas(w)}
    <p>Integrity Watch compares Model Health and integrity metrics across two runs. Policy and assumption changes are shown so a definition change is not mistaken for a model change.</p>
    <p class="fineprint" id="watch-live"></p>
  `;
  if (state.mode === "live") {
    fetchJSON(apiUrl("/api/v1/runs"))
      .then((body) => {
        const runs = body.runs || [];
        const note = document.getElementById("watch-live");
        if (!note) return;
        if (runs.length < 2) {
          note.textContent = `${runs.length} run(s) in memory. Compare after a second live audit.`;
          return;
        }
        note.innerHTML = `<label>Baseline <select id="watch-a">${runs.map(opt).join("")}</select></label>
          <label>Comparison <select id="watch-b">${runs.map(opt).join("")}</select></label>
          <button type="button" class="btn btn-ghost" id="btn-watch">Compare</button>
          <div id="watch-out"></div>`;
        document.getElementById("btn-watch")?.addEventListener("click", async () => {
          const out = document.getElementById("watch-out");
          try {
            const res = await postJSON("/api/v1/comparisons", {
              baseline_run_id: document.getElementById("watch-a").value,
              comparison_run_id: document.getElementById("watch-b").value,
            });
            out.innerHTML = renderDeltas(res);
          } catch (err) {
            out.textContent = String(err.message || err);
          }
        });
      })
      .catch(() => {});
  }
}

function opt(r) {
  return `<option value="${escapeHtml(r.id)}">${escapeHtml(r.name || r.id)} · ${escapeHtml(r.status || "")}</option>`;
}

function renderDeltas(w) {
  const d = w.metric_deltas || {};
  const keys = Object.keys(d);
  if (!keys.length) return `<p class="skipped">No comparable metrics yet.</p>`;
  return `<div class="table-wrap"><table class="grid"><thead><tr><th>Metric</th><th>Δ comparison − baseline</th></tr></thead><tbody>
    ${keys.map((k) => `<tr><td>${escapeHtml(k)}</td><td class="mono">${fmt.auc(d[k])}</td></tr>`).join("")}
  </tbody></table></div>
  <p class="fineprint">${escapeHtml(w.assumption_policy_note || "Compare policy_id and assumption hashes before treating a delta as a model change.")}</p>`;
}
