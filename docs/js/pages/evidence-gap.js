import { escapeHtml, fmt } from "../format.js";
import { state, setState } from "../state.js";
import { renderRoom } from "./evidence-room.js";

export function renderEvidenceGap() {
  const live = state.evidenceGap;
  const book = ((state.findings || {}).battery || {}).evidence_recourse || {};
  const el = document.getElementById("evidence-root");
  if (!el) return;
  const status = live?.status || (book.skipped ? "skipped" : book.cross_rate_full_documentation != null ? "tested" : "not_started");
  const ev = (live && live.result) || book;
  if (status === "skipped" || ev.skipped) {
    el.innerHTML = `<p class="skipped">${escapeHtml(live?.reason || ev.reason || "Skipped — no evidence pair")}</p>
      <p class="note">Provide a recorded↔verified mapping at intake, or a deterministic verification rule. JANUS does not invent verified values.</p>`;
    return;
  }
  if (status === "blocked") {
    el.innerHTML = `<p class="skipped">${escapeHtml(live?.reason || "Blocked — insufficient matched records")}</p>`;
    return;
  }
  const cross = ev.cross_rate_full_documentation ?? ev.cross_rate;
  el.innerHTML = `
    <p class="badge">${escapeHtml(status)}</p>
    <div class="evidence">
      <article class="card"><h3>Cross-cutoff rate</h3><p class="big">${fmt.pct1(cross)}</p><p class="meaning">Eligible declined records that cross after verified values replace recorded values.</p></article>
      <article class="card"><h3>Crossers' default</h3><p class="big">${fmt.pct1(ev.cross_default_rate)}</p><p class="meaning">Portfolio default ${fmt.pct1(ev.portfolio_default_rate)}.</p></article>
      <article class="card"><h3>Recorded vs verified</h3><p class="big">${ev.median_recorded_dti != null ? `${fmt.dti(ev.median_recorded_dti)} → ${fmt.dti(ev.median_true_dti)}` : fmt.int(ev.n_matched)}</p><p class="meaning">Never fabricated. Cost $0 when documentation already exists.</p></article>
    </div>
    <p class="fineprint">${escapeHtml(ev.limitations || "Route C requires a recorded-versus-verified pair.")}</p>
    <p><button type="button" class="btn btn-ghost" id="btn-document-finding">Document it</button></p>
  `;
  el.querySelector("#btn-document-finding")?.addEventListener("click", () => {
    const pkg = state.findings || {};
    pkg.investigation = pkg.investigation || { findings: [] };
    pkg.investigation.findings = pkg.investigation.findings || [];
    pkg.investigation.findings.unshift({
      id: `EG${pkg.investigation.findings.length + 1}`,
      title: "Evidence gap at the cutoff",
      claim: `Verified values moved ${fmt.pct1(cross)} of eligible declines across the cutoff.`,
      severity: "high",
      status: "draft",
      owner: "",
      due_date: "",
      limitation: "Substitution test. Not proof of fraud or of true economic capacity.",
    });
    setState({ findings: pkg });
    renderRoom();
    location.hash = "#room";
  });
}
