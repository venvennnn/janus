"""JSON and self-contained HTML export of derived evidence. No raw rows."""

from __future__ import annotations

import json
from html import escape
from typing import Any


def export_package(run: dict[str, Any]) -> dict[str, Any]:
    skip = {"estimator", "holdout", "holdout_raw", "wrapped", "model_bytes", "holdout_bytes"}
    return {k: v for k, v in run.items() if k not in skip}


def html_report(run: dict[str, Any]) -> str:
    pkg = export_package(run)
    health = pkg.get("model_health") or {}
    meta = health.get("metadata") or {}
    core = health.get("core_metrics") or {}
    findings = pkg.get("findings") or []
    rows = "".join(
        f"<tr><td>{escape(str(f.get('id','')))}</td><td>{escape(str(f.get('title','')))}</td>"
        f"<td>{escape(str(f.get('severity','')))}</td><td>{escape(str(f.get('status','')))}</td></tr>"
        for f in findings
    )
    metrics = "".join(
        f"<tr><th>{escape(k)}</th><td class='mono'>{escape(str(v))}</td></tr>" for k, v in core.items()
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>JANUS report — {escape(str(pkg.get('name') or pkg.get('id')))}</title>
<style>
body{{font-family:Inter,system-ui,sans-serif;background:#fff;color:#111;max-width:860px;margin:40px auto;padding:0 24px;line-height:1.5}}
h1{{font-weight:600;letter-spacing:-.03em}}
.mono{{font-family:ui-monospace,monospace}}
table{{border-collapse:collapse;width:100%}}
th,td{{border-bottom:1px solid #e6e6e6;text-align:left;padding:8px 6px}}
.badge{{display:inline-block;border:1px solid #111;padding:2px 8px;font-size:12px}}
</style></head><body>
<p class="badge">{escape(str(pkg.get('mode','run')))}</p>
<h1>JANUS validation report</h1>
<p>Run {escape(str(pkg.get('id','')))} · {escape(str(pkg.get('status','')))} · policy {escape(str((health.get('policy_id') or '')))}</p>
<p>Model {escape(str(meta.get('model_name') or ''))}. Target {escape(str(meta.get('target_column') or ''))}. Cutoff {escape(str(meta.get('cutoff') or ''))}.</p>
<p><strong>Conclusion:</strong> {escape(str(health.get('conclusion') or pkg.get('conclusion') or '—'))}</p>
<p class="mono">AUC tells you whether the model predicts. JANUS tells you whether the model can be trusted.</p>
<h2>Model Health</h2>
<table>{metrics}</table>
<h2>Findings</h2>
<table><thead><tr><th>ID</th><th>Title</th><th>Severity</th><th>Status</th></tr></thead><tbody>{rows or '<tr><td colspan=4>No findings recorded.</td></tr>'}</tbody></table>
<p>Synthetic reference results demonstrate method. They do not establish real-world prevalence. JANUS does not make credit decisions.</p>
</body></html>"""


def json_bytes(run: dict[str, Any]) -> bytes:
    return json.dumps(export_package(run), indent=2, default=str).encode("utf-8")
