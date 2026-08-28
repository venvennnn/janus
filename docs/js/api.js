export function apiUrl(path) {
  const base = (window.JANUS_API || "").replace(/\/$/, "");
  return `${base}${path}`;
}

export function apiDetail(body, fallback) {
  const detail = body && (body.detail || body.error);
  if (typeof detail === "string" && detail) return detail;
  if (detail && typeof detail === "object") return detail.message || JSON.stringify(detail);
  if (Array.isArray(detail)) return detail.map((item) => item.msg || JSON.stringify(item)).join("; ");
  return fallback;
}

export async function pingApi() {
  const res = await fetch(apiUrl("/health"), { cache: "no-store" });
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

export async function fetchJSON(path) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} ${res.status}`);
  return res.json();
}

async function parse(res, fallback) {
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(apiDetail(body, fallback || res.statusText));
  return body;
}

export async function postForm(path, data) {
  const res = await fetch(apiUrl(path), { method: "POST", body: data });
  return parse(res, "Upload failed");
}

export async function postJSON(path, payload) {
  const res = await fetch(apiUrl(path), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload ?? {}),
  });
  return parse(res, "Request failed");
}

export async function putJSON(path, payload) {
  const res = await fetch(apiUrl(path), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload ?? {}),
  });
  return parse(res, "Update failed");
}

export function apiDetail(body, fallback) {
  const detail = body && (body.detail || body.error);
  if (typeof detail === "string" && detail) return detail;
  if (detail && typeof detail === "object") return detail.message || JSON.stringify(detail);
  if (Array.isArray(detail)) return detail.map((item) => item.msg || JSON.stringify(item)).join("; ");
  return fallback;
}

export async function pingApi() {
  const res = await fetch(apiUrl("/health"), { cache: "no-store" });
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

export async function fetchJSON(path) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} ${res.status}`);
  return res.json();
}
