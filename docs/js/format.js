export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

export function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function usdText(s) {
  return String(s ?? "")
    .replace(/\u00a5/g, "$")
    .replace(/¥/g, "$")
    .replace(/\bJPY\b/g, "USD");
}

export const fmt = {
  auc: (v) => (v == null || Number.isNaN(Number(v)) ? "—" : Number(v).toFixed(3)),
  p: (v) => (v == null || Number.isNaN(Number(v)) ? "—" : Number(v).toFixed(3)),
  pct: (v) => (v == null || Number.isNaN(Number(v)) ? "—" : `${Math.round(Number(v) * 100)}%`),
  pct1: (v) => (v == null || Number.isNaN(Number(v)) ? "—" : `${(Number(v) * 100).toFixed(1)}%`),
  pp: (v) => (v == null || Number.isNaN(Number(v)) ? "—" : `${Number(v).toFixed(1)}pp`),
  usd: (v) => (v == null || Number.isNaN(Number(v)) ? "—" : `$${Math.round(Number(v)).toLocaleString("en-US")}`),
  int: (v) => (v == null || Number.isNaN(Number(v)) ? "—" : Math.round(Number(v)).toLocaleString("en-US")),
  dti: (v) => (v == null || Number.isNaN(Number(v)) ? "—" : Number(v).toFixed(2)),
  times: (v) => (v == null || Number.isNaN(Number(v)) ? "—" : `${Math.round(Number(v))}×`),
  days: (v) => {
    if (v == null || Number.isNaN(Number(v))) return "—";
    const n = Math.round(Number(v));
    return n === 1 ? "1 day" : `${n} days`;
  },
  raw: (v) => usdText(v),
};

export function getPath(obj, path) {
  return path.split(".").reduce((acc, key) => (acc == null ? acc : acc[key]), obj);
}

export function bind(root, data) {
  $$("[data-bind]", root).forEach((el) => {
    const value = getPath(data, el.dataset.bind);
    const kind = el.dataset.fmt || "raw";
    el.textContent = value == null ? "—" : (fmt[kind] || fmt.raw)(value);
  });
}

export function statusLabel(s) {
  return String(s || "not_tested").replace(/_/g, " ");
}
