import { escapeHtml, usdText } from "../format.js";
import { state } from "../state.js";

export function renderRoom() {
  const items = ((state.findings || {}).investigation || {}).findings || [];
  const el = document.getElementById("findings-list");
  if (!el) return;
  el.innerHTML = items
    .map(
      (f) => `<li>
        <p class="title"><label><input type="checkbox" class="finding-box" data-id="${escapeHtml(f.id)}" checked> ${escapeHtml(f.title)}</label>
        <span class="sev sev-${escapeHtml(f.severity)}">${escapeHtml(f.severity)}</span></p>
        <p class="subtitle">${escapeHtml(usdText(f.claim || f.description || ""))} <span class="run">${escapeHtml(f.run_id || "")}</span></p>
        <p class="fineprint">Limitation: engine evidence, not proof of fraud or causality. Owner and due date are recorded at approval.</p>
      </li>`
    )
    .join("");
}

export function exportJSON() {
  const blob = new Blob(
    [
      JSON.stringify(
        {
          mode: state.mode,
          run: state.runId,
          health: state.health,
          findings: state.findings,
          twins: state.twins,
          remediation: state.remediation,
          watch: state.watch,
          policy: state.policy,
        },
        null,
        2
      ),
    ],
    { type: "application/json" }
  );
  download(blob, `janus-${state.runId}.json`);
}

export function exportHTML() {
  const html = document.documentElement.outerHTML;
  download(new Blob([html], { type: "text/html" }), `janus-${state.runId}.html`);
}

function download(blob, name) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
}
