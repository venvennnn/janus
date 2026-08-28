import { $, escapeHtml } from "../format.js?v=032";
import { state } from "../state.js?v=032";

function columns() {
  return ((state.datasetProfile || {}).columns || []).map((c) => c.name);
}

function suggestion(purpose) {
  const cols = (state.datasetProfile || {}).columns || [];
  const hit = cols.find((c) => c.suggested === purpose);
  return hit ? hit.name : "";
}

function options(selected, includeBlank) {
  const names = columns();
  const opts = includeBlank ? [`<option value="">— none —</option>`] : [];
  names.forEach((name) => {
    opts.push(`<option value="${escapeHtml(name)}"${name === selected ? " selected" : ""}>${escapeHtml(name)}</option>`);
  });
  return opts.join("");
}

function pickTarget() {
  return (
    suggestion("target") ||
    columns().find((n) => /dpd90_index_x|default|^target$/i.test(n)) ||
    columns()[0] ||
    ""
  );
}

export function fillMapping() {
  const stage = $("#map-stage");
  if (!stage) return;
  const profile = state.datasetProfile;
  if (!profile) {
    stage.hidden = true;
    return;
  }
  stage.hidden = false;
  const target = pickTarget();
  const ts = suggestion("timestamp") || columns().find((n) => /LOAN_CREATED_AT_LCL_TS|_ts$|created_at/i.test(n)) || "";
  const idCol = suggestion("id") || columns().find((n) => /applicant_id|loan_id|^id$/i.test(n)) || "";
  $("#map-target").innerHTML = options(target, false);
  $("#map-timestamp").innerHTML = options(ts, true);
  $("#map-id").innerHTML = options(idCol, true);
  $("#map-exposure").innerHTML = options("", true);
  $("#map-revenue").innerHTML = options(suggestion("revenue_not_exposure"), true);
  $("#map-segments").innerHTML = columns()
    .map((n) => `<option value="${escapeHtml(n)}">${escapeHtml(n)}</option>`)
    .join("");
  $("#map-recorded").innerHTML = options("", true);
  $("#map-verified").innerHTML = options("", true);
  const warn = $("#map-revenue-warn");
  if (warn) {
    const rev = suggestion("revenue_not_exposure");
    warn.hidden = !rev;
    warn.textContent = rev
      ? `${rev} looks like revenue associated with the application. It is not treated as exposure or loss unless you map it under Exposure after confirmation.`
      : "";
  }
  const meta = $("#map-profile");
  if (meta) {
    meta.textContent = `${profile.row_count} rows · ${profile.column_count} columns · ${profile.duplicate_rows} duplicate rows`;
  }
}

export function collectMapping() {
  const segments = [...($("#map-segments")?.selectedOptions || [])].map((o) => o.value).filter(Boolean);
  const recorded = $("#map-recorded")?.value;
  const verified = $("#map-verified")?.value;
  const mappings = recorded && verified ? [{ recorded, verified }] : [];
  return {
    target_column: $("#map-target").value,
    positive_class: 1,
    timestamp_column: $("#map-timestamp").value || null,
    id_column: $("#map-id").value || null,
    exposure_column: $("#map-exposure").value || null,
    segment_columns: segments,
    cutoff: Number($("#input-cutoff").value),
    decision_rule: "predicted_default_probability <= cutoff",
    maturity_confirmed: $("#map-matured").checked,
    performance_window_confirmed: $("#map-window").checked,
    evidence_mappings: mappings,
    name: "Live audit",
  };
}

export function mappingReady() {
  return $("#map-positive")?.checked && $("#map-matured")?.checked && $("#map-window")?.checked && $("#map-target")?.value;
}
