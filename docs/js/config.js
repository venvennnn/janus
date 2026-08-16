// Pages: set this to your Render URL, e.g. "https://janus.onrender.com"
// Same-origin (Render serving this folder, or uvicorn on :8000): leave empty.
window.JANUS_API =
  window.JANUS_API ||
  (location.port === "8000" || /\.onrender\.com$/i.test(location.hostname) ? "" : "http://localhost:8000");
