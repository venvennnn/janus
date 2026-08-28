import { escapeHtml, usdText } from "../format.js?v=032";
import { state, setState } from "../state.js?v=032";

export function renderRoom() {
  const items = ((state.findings || {}).investigation || {}).findings || [];
  const el = document.getElementById("findings-list");
  if (!el) return;
  el.innerHTML = items
    .map(
      (f, i) => `<li>
        <p class="title"><label><input type="checkbox" class="finding-box" data-id="${escapeHtml(f.id)}" ${f.status === "rejected" ? "" : "checked"}> ${escapeHtml(f.title)}</label>
        <span class="sev sev-${escapeHtml(f.severity || "medium")}">${escapeHtml(f.severity || "medium")}</span></p>
        <p class="subtitle">${escapeHtml(usdText(f.claim || f.description || ""))} <span class="run">${escapeHtml(f.run_id || f.id || "")}</span></p>
        <p class="fineprint">${escapeHtml(f.limitation || "Limitation: engine evidence, not proof of fraud or causality.")}</p>
        <div class="find-meta">
          <label>Owner <input data-field="owner" data-idx="${i}" value="${escapeHtml(f.owner || "")}" placeholder="Owner"></label>
          <label>Due <input data-field="due_date" data-idx="${i}" type="date" value="${escapeHtml(f.due_date || "")}"></label>
          <label>Status
            <select data-field="status" data-idx="${i}">
              ${["draft", "open", "accepted", "remediating", "resolved", "risk accepted"].map((s) => `<option${(f.status || "draft") === s ? " selected" : ""}>${s}</option>`).join("")}
            </select>
          </label>
        </div>
      </li>`
    )
    .join("");
  el.querySelectorAll("[data-field]").forEach((input) => {
    input.addEventListener("change", () => {
      const i = Number(input.dataset.idx);
      const pkg = state.findings || {};
      const list = [...(((pkg.investigation || {}).findings) || [])];
      list[i] = { ...list[i], [input.dataset.field]: input.value };
      pkg.investigation = { ...(pkg.investigation || {}), findings: list };
      setState({ findings: pkg });
    });
  });
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
          evidence_gap: state.evidenceGap,
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
