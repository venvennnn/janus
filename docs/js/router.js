import { $, $$ } from "./format.js?v=032";

export const ROUTES = [
  ["#overview", "Overview"],
  ["#health", "Model Health"],
  ["#attack", "Attack Lab"],
  ["#twins", "Decision Twins"],
  ["#evidence", "Evidence Gap"],
  ["#remediation", "Remediation"],
  ["#watch", "Integrity Watch"],
  ["#room", "Evidence Room"],
];

export function currentHash() {
  const raw = (location.hash || "#overview").split("?")[0];
  return ROUTES.some(([h]) => h === raw) || raw === "#audit" ? raw : "#overview";
}

export function showRoute(hash) {
  const id = (hash || currentHash()).replace("#", "");
  $$(".panel").forEach((el) => el.classList.toggle("is-active", el.id === id));
  $$(".nav a").forEach((a) => {
    a.setAttribute("aria-current", a.getAttribute("href") === `#${id}` || (id === "audit" && a.getAttribute("href") === "#audit") ? "page" : "false");
  });
}

export function initRouter() {
  document.documentElement.classList.add("js");
  window.addEventListener("hashchange", () => showRoute(currentHash()));
  showRoute(currentHash());
}
