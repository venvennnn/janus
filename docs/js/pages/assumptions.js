import { $$, escapeHtml } from "../format.js";

export function fillProposeTable(rows) {
  const body = document.querySelector("#propose-table tbody");
  if (!body) return;
  body.innerHTML = (rows || [])
    .map((row) => {
      const payload = encodeURIComponent(JSON.stringify(row));
      const kinds = ["cosmetic", "genuine", "mixed", "immutable", "documentation"]
        .map((k) => `<option${k === row.kind ? " selected" : ""}>${k}</option>`)
        .join("");
      const dir = row.direction || "both";
      const dirs = ["up", "down", "both"].map((d) => `<option${d === dir ? " selected" : ""}>${d}</option>`).join("");
      return `<tr data-row="${payload}">
        <td><code>${escapeHtml(row.feature)}</code></td>
        <td><select name="kind">${kinds}</select></td>
        <td><select name="direction">${dirs}</select></td>
        <td><input name="attack" type="number" step="1" value="${row.attack_cost_jpy ?? ""}"></td>
        <td><input name="attack_days" type="number" step="0.1" value="${row.attack_days ?? ""}"></td>
        <td><input name="genuine" type="number" step="1" value="${row.genuine_cost_jpy ?? ""}"></td>
        <td><input name="genuine_days" type="number" step="0.1" value="${row.genuine_days ?? ""}"></td>
        <td><input name="rationale" type="text" value="${escapeHtml(row.rationale || "")}"></td>
      </tr>`;
    })
    .join("");
}

export function collectLevers() {
  return $$("#propose-table tbody tr").map((tr) => {
    const row = JSON.parse(decodeURIComponent(tr.dataset.row));
    const num = (name) => {
      const v = tr.querySelector(`[name=${name}]`).value;
      return v === "" ? null : Number(v);
    };
    return {
      ...row,
      kind: tr.querySelector("[name=kind]").value,
      direction: tr.querySelector("[name=direction]").value,
      attack_cost_jpy: num("attack"),
      attack_days: num("attack_days"),
      genuine_cost_jpy: num("genuine"),
      genuine_days: num("genuine_days"),
      rationale: tr.querySelector("[name=rationale]").value,
      proposal_source: row.proposal_source || "heuristic",
    };
  });
}
