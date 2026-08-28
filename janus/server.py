"""JANUS API. Legacy /propose /run /health /sample.zip remain; v1 lives under /api/v1."""

from __future__ import annotations

import hashlib
import os
import time
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response

from janus import __version__
from janus.ingest import (
    IngestError,
    apply_mapping,
    load_csv,
    load_estimator,
    load_holdout,
    profile_frame,
    read_upload,
)
from janus.integrity.twins import counterfactual_twin, matched_observation_twins
from janus.llm import llm_status
from janus.model import inspect_wrapped, wrap_estimator
from janus.package import build_findings_package
from janus.policy import load_policy
from janus.reporting import html_report, json_bytes
from janus.remediation.scenarios import evaluate_scenario
from janus.run_uploaded import propose_upload
from janus.levers import lever_book, mutability_table
from janus.propose import rows_to_levers
from janus.schemas import (
    ApprovalBody,
    AssumptionConfirmBody,
    ComparisonBody,
    ConfigurationBody,
    FindingUpdateBody,
    RemediationScenarioBody,
    RunBody,
)
from janus.storage import build_store, now
from janus.validation.health import run_model_health
from janus.validation.scoring import predict_positive

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "sample"
CORS = [o.strip() for o in os.environ.get("JANUS_CORS_ORIGINS", "*").split(",") if o.strip()]

app = FastAPI(title="JANUS", version=__version__, docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS if CORS != ["*"] else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
STORE = build_store()


@app.middleware("http")
async def secure_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Request-Id"] = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    return response


def _err(status: int, message: str, code: str = "bad_request"):
    raise HTTPException(status, {"code": code, "message": message})


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "product": "JANUS",
        "version": __version__,
        **llm_status(),
        "persistence": "sqlite" if os.environ.get("JANUS_DB_PATH") else "memory",
    }


@app.get("/api/v1/capabilities")
def capabilities() -> dict:
    return {
        "version": __version__,
        "model_formats": [".joblib", ".pkl", ".pickle"],
        "max_rows": 20_000,
        "max_bytes": 50 * 1024 * 1024,
        "persistence": "sqlite" if os.environ.get("JANUS_DB_PATH") else "memory",
        "llm": llm_status(),
        "modules": [
            "model_health",
            "assumptions",
            "attack_lab",
            "decision_twins",
            "evidence_gap",
            "remediation",
            "integrity_watch",
            "evidence_room",
        ],
        "legacy_endpoints": ["/health", "/propose", "/run", "/sample.zip"],
        "policy_id": load_policy()["policy_id"],
    }


@app.get("/sample.zip")
def sample_zip() -> Response:
    path = SAMPLE / "janus-sample.zip"
    if path.exists():
        return Response(path.read_bytes(), media_type="application/zip", headers={"Content-Disposition": "attachment; filename=janus-sample.zip"})
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in ("holdout.csv", "model.joblib", "dictionary.txt", "context.txt"):
            file = SAMPLE / name
            if file.exists():
                zf.write(file, name)
    if buf.tell() == 0:
        raise HTTPException(404, "Sample pack is not in this checkout.")
    return Response(buf.getvalue(), media_type="application/zip", headers={"Content-Disposition": "attachment; filename=janus-sample.zip"})


@app.post("/propose")
async def propose(
    model: UploadFile = File(...),
    holdout: UploadFile = File(...),
    cutoff: float = Form(...),
    dictionary: UploadFile | None = File(None),
    dictionary_text: str = Form(""),
    context: str = Form(""),
):
    STORE.purge()
    try:
        estimator = load_estimator(await _bytes(model), model.filename or "model.joblib")
        frame = load_holdout(await _bytes(holdout), holdout.filename or "holdout.csv")
        blob = dictionary_text
        if dictionary is not None and dictionary.filename:
            blob = (await _bytes(dictionary)).decode("utf-8", errors="replace") + "\n" + blob
        wrapped, info, proposal, meta = propose_upload(estimator, frame, cutoff, blob, context)
    except IngestError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(400, f"Could not inspect the upload: {exc}") from exc

    rec = STORE.create(
        {
            "mode": "live",
            "status": "awaiting_assumption_confirmation",
            "name": model.filename or "upload",
            "estimator": wrapped.estimator,
            "holdout": frame,
            "info": info,
            "dictionary": blob,
            "context": context,
            "configuration": {"cutoff": cutoff, "target_column": "default", "positive_class": 1},
            "proposal": proposal,
            "agent": meta,
            "created_ts": time.time(),
        }
    )
    return {
        "job_id": rec["id"],
        "model": info,
        "proposal": proposal,
        "agent": meta,
        "warnings": _warnings(),
    }


@app.post("/run")
def run(body: RunBody):
    STORE.purge()
    if not body.confirmed:
        raise HTTPException(400, "Confirm the mutability table before search runs.")
    if not body.levers:
        raise HTTPException(400, "Send the confirmed lever rows.")
    job = STORE.get(body.job_id)
    if job is None:
        raise HTTPException(404, "Job expired or unknown. Propose again.")
    try:
        with lever_book(rows_to_levers(body.levers)):
            package = build_findings_package(
                job["holdout"],
                wrap_estimator(job["estimator"], job["holdout"], job["configuration"]["cutoff"]),
                job["info"],
                source="upload",
                dictionary=job.get("dictionary") or "",
                context=job.get("context") or "",
            )
    except Exception as exc:
        STORE.drop_raw(body.job_id)
        raise HTTPException(400, f"Audit failed: {exc}") from exc
    STORE.drop_raw(body.job_id)
    STORE.update(body.job_id, status="integrity_tests_complete", findings_package=package)
    return package


@app.post("/api/v1/runs")
async def create_run(
    model_file: UploadFile = File(...),
    holdout_file: UploadFile = File(...),
    cutoff: float = Form(0.275),
    target_column: str = Form("default"),
    dictionary: UploadFile | None = File(None),
    dictionary_text: str = Form(""),
    context: str = Form(""),
    mapping_json: str = Form(""),
):
    STORE.purge()
    try:
        model_bytes = await _bytes(model_file)
        holdout_bytes = await _bytes(holdout_file)
        estimator = load_estimator(model_bytes, model_file.filename or "model.joblib")
        raw = load_csv(holdout_bytes, holdout_file.filename or "holdout.csv")
        blob = dictionary_text
        if dictionary is not None and dictionary.filename:
            blob = (await _bytes(dictionary)).decode("utf-8", errors="replace") + "\n" + blob
    except IngestError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(400, f"Could not inspect the upload: {exc}") from exc
    profile = profile_frame(raw)
    rec = STORE.create(
        {
            "mode": "live",
            "status": "draft",
            "name": model_file.filename or "upload",
            "estimator": estimator,
            "holdout_raw": raw,
            "dictionary": blob,
            "context": context,
            "dataset_hash": hashlib.sha256(holdout_bytes).hexdigest()[:16],
            "model_hash": hashlib.sha256(model_bytes).hexdigest()[:16],
            "dataset_profile": profile,
            "configuration": {
                "cutoff": cutoff,
                "target_column": target_column,
                "positive_class": 1,
                "maturity_confirmed": False,
                "performance_window_confirmed": False,
                "segment_columns": [],
            },
            "warnings": _warnings() + [
                "Confirm the semantic role of amount/revenue columns. Revenue is not exposure.",
            ],
            "created_ts": time.time(),
        }
    )
    STORE.update(rec["id"], estimator=estimator, holdout_raw=raw)
    return {
        "run_id": rec["id"],
        "status": rec["status"],
        "model": {"name": rec["name"], "sha256": rec["model_hash"]},
        "dataset_profile": profile,
        "schema_suggestions": {c["name"]: c.get("suggested") for c in profile["columns"] if c.get("suggested")},
        "warnings": rec["warnings"],
    }


@app.put("/api/v1/runs/{run_id}/configuration")
def configure_run(run_id: str, body: ConfigurationBody):
    job = _job(run_id)
    raw = job.get("holdout_raw")
    if raw is None:
        raise HTTPException(400, "Raw holdout already dropped. Create a new run.")
    try:
        mapped = apply_mapping(raw, body.target_column, body.id_column)
        wrapped = wrap_estimator(job["estimator"], mapped, body.cutoff)
        info = inspect_wrapped(wrapped, mapped)
    except (IngestError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc
    STORE.update(
        run_id,
        holdout=mapped,
        wrapped=wrapped,
        info=info,
        configuration=body.model_dump(),
        status="data_mapped",
        name=body.name or job.get("name"),
    )
    return {"run_id": run_id, "status": "data_mapped", "model": info, "n": int(len(mapped))}


@app.post("/api/v1/runs/{run_id}/model-health")
def model_health(run_id: str):
    job = _job(run_id)
    cfg = job.get("configuration") or {}
    frame = job.get("holdout")
    if frame is None:
        raise HTTPException(400, "Map the target column before Model Health.")
    estimator = job.get("wrapped").estimator if job.get("wrapped") else job["estimator"]
    features = job["info"]["features"] if job.get("info") else list(getattr(estimator, "feature_names_in_", []))
    result = run_model_health(
        estimator,
        frame,
        features=features,
        cutoff=float(cfg.get("cutoff", 0.275)),
        target_column="default",
        positive_class=int(cfg.get("positive_class", 1)),
        timestamp_column=cfg.get("timestamp_column"),
        exposure_column=cfg.get("exposure_column"),
        segment_columns=cfg.get("segment_columns") or [],
        maturity_confirmed=bool(cfg.get("maturity_confirmed")),
        performance_window_confirmed=bool(cfg.get("performance_window_confirmed")),
        model_name=job.get("name") or "upload",
    )
    status = "model_health_complete" if result["conclusion"] != "Insufficient Evidence" else "data_blocked"
    STORE.update(run_id, model_health=result, status=status, conclusion=result["conclusion"])
    return result


@app.post("/api/v1/runs/{run_id}/assumptions/propose")
def propose_assumptions(run_id: str):
    job = _job(run_id)
    frame = job.get("holdout")
    if frame is None:
        raise HTTPException(400, "Map the schema first.")
    cutoff = float((job.get("configuration") or {}).get("cutoff", 0.275))
    wrapped, info, proposal, meta = propose_upload(
        job.get("wrapped").estimator if job.get("wrapped") else job["estimator"],
        frame,
        cutoff,
        job.get("dictionary") or "",
        job.get("context") or "",
    )
    STORE.update(run_id, proposal=proposal, info=info, wrapped=wrapped, agent=meta, status="awaiting_assumption_confirmation")
    return {"run_id": run_id, "proposal": proposal, "agent": meta, "model": info}


@app.put("/api/v1/runs/{run_id}/assumptions")
def confirm_assumptions(run_id: str, body: AssumptionConfirmBody):
    if not body.confirmed:
        raise HTTPException(400, "Confirm the mutability table before search runs.")
    if not body.levers:
        raise HTTPException(400, "Send the confirmed lever rows.")
    _job(run_id)
    STORE.update(
        run_id,
        levers=body.levers,
        assumptions_confirmed=True,
        assumptions_reviewer=body.reviewer,
        assumptions_confirmed_at=now(),
        status="assumptions_confirmed",
    )
    return {"run_id": run_id, "status": "assumptions_confirmed", "n_levers": len(body.levers)}


@app.post("/api/v1/runs/{run_id}/attack-lab")
def attack_lab(run_id: str):
    job = _ready_for_integrity(run_id)
    package = _integrity_package(job)
    STORE.update(run_id, findings_package=package, status="integrity_tests_complete")
    STORE.drop_raw(run_id)
    atk = package["battery"]["attack_surface"]
    menu = package["recourse_menu"]
    return {
        "status": "complete" if not atk.get("skipped") else "skipped",
        "reason": atk.get("reason"),
        "attack_surface": atk,
        "integrity_gap": package["battery"]["integrity_gap"],
        "recourse_menu": menu,
        "demo_applicant": package["demo_applicant"],
        "limitations": [
            "A decision change is not an improvement in model performance.",
            "Successful attacks are not proof of fraud or of changed creditworthiness.",
            "Detailed feature steps are model-owner only.",
        ],
    }


@app.post("/api/v1/runs/{run_id}/decision-twins")
def decision_twins(run_id: str):
    job = _job(run_id)
    package = job.get("findings_package")
    if package is None:
        job = _ready_for_integrity(run_id)
        package = _integrity_package(job)
        STORE.update(run_id, findings_package=package)
    cf = counterfactual_twin(package["demo_applicant"], package["recourse_menu"])
    frame = job.get("holdout")
    matched = {"skipped": True, "reason": "Holdout already dropped. Counterfactual twin is available from the recorded menu."}
    if frame is not None:
        cfg = job.get("configuration") or {}
        p = predict_positive(job["wrapped"].estimator if job.get("wrapped") else job["estimator"], frame, job["info"]["features"], cfg.get("positive_class", 1))
        cosmetic = [r["feature"] for r in (job.get("levers") or mutability_table()) if r.get("kind") in {"cosmetic", "mixed"}]
        core = [c for c in ("age", "employment_months", "requested_amount") if c in frame.columns]
        matched = matched_observation_twins(frame, p, float(cfg.get("cutoff", 0.275)), core, cosmetic)
    return {"counterfactual": cf, "matched_observation": matched}


@app.post("/api/v1/runs/{run_id}/evidence-gap")
def evidence_gap(run_id: str):
    job = _job(run_id)
    cfg = job.get("configuration") or {}
    mappings = cfg.get("evidence_mappings") or []
    package = job.get("findings_package")
    if package is None and job.get("levers"):
        package = _integrity_package(job)
        STORE.update(run_id, findings_package=package)
    ev = (package or {}).get("battery", {}).get("evidence_recourse") if package else None
    if ev and not ev.get("skipped"):
        return {"status": "tested", "result": ev, "source": "recorded_vs_true_income_on_this_book"}
    if not mappings:
        return {"status": "skipped", "reason": "Skipped — no evidence pair", "result": ev}
    return {"status": "partially_tested" if ev else "blocked", "reason": ev.get("reason") if ev else "Blocked — insufficient matched records", "result": ev}


@app.post("/api/v1/runs/{run_id}/remediation-scenarios")
def create_scenario(run_id: str, body: RemediationScenarioBody):
    job = _job(run_id)
    frame = job.get("holdout")
    if frame is None:
        raise HTTPException(400, "Holdout is no longer in memory. Create a new run to test remediations.")
    cfg = job.get("configuration") or {}
    baseline = job.get("model_health")
    result = evaluate_scenario(
        job.get("wrapped").estimator if job.get("wrapped") else job["estimator"],
        frame,
        features=job["info"]["features"],
        cutoff=float(cfg.get("cutoff", 0.275)),
        actions=body.actions,
        target_column="default",
        positive_class=int(cfg.get("positive_class", 1)),
        timestamp_column=cfg.get("timestamp_column"),
        exposure_column=cfg.get("exposure_column"),
        segment_columns=cfg.get("segment_columns") or [],
        baseline=baseline,
        name=body.name,
        model_name=job.get("name") or "upload",
    )
    result.update(
        {
            "id": f"scn_{uuid.uuid4().hex[:8]}",
            "created_by": body.created_by,
            "created_at": now(),
            "reviewer_status": body.reviewer_status,
            "rationale": body.rationale,
        }
    )
    scenarios = list(job.get("scenarios") or [])
    scenarios.append(result)
    STORE.update(run_id, scenarios=scenarios)
    return result


@app.get("/api/v1/runs/{run_id}/remediation-scenarios")
def list_scenarios(run_id: str):
    return {"scenarios": _job(run_id).get("scenarios") or []}


@app.put("/api/v1/runs/{run_id}/remediation-scenarios/{scenario_id}")
def update_scenario(run_id: str, scenario_id: str, body: RemediationScenarioBody):
    job = _job(run_id)
    scenarios = list(job.get("scenarios") or [])
    found = False
    for scn in scenarios:
        if scn.get("id") == scenario_id:
            scn["reviewer_status"] = body.reviewer_status
            scn["rationale"] = body.rationale
            found = True
    if not found:
        raise HTTPException(404, "Unknown scenario.")
    STORE.update(run_id, scenarios=scenarios)
    return {"ok": True, "id": scenario_id}


@app.get("/api/v1/runs/{run_id}/findings")
def get_findings(run_id: str):
    job = _job(run_id)
    return {"findings": job.get("findings") or _findings_from_package(job.get("findings_package"))}


@app.post("/api/v1/runs/{run_id}/findings")
def add_finding(run_id: str, body: FindingUpdateBody):
    job = _job(run_id)
    findings = list(job.get("findings") or _findings_from_package(job.get("findings_package")))
    rec = {
        "id": f"F{len(findings)+1:02d}",
        "title": body.recommended_action or "Draft finding",
        "status": body.status or "draft",
        "owner": body.owner,
        "due_date": body.due_date,
        "severity": "medium",
        "description": "",
    }
    findings.append(rec)
    STORE.update(run_id, findings=findings)
    return rec


@app.put("/api/v1/runs/{run_id}/findings/{finding_id}")
def update_finding(run_id: str, finding_id: str, body: FindingUpdateBody):
    job = _job(run_id)
    findings = list(job.get("findings") or _findings_from_package(job.get("findings_package")))
    for f in findings:
        if f.get("id") == finding_id:
            for key in ("status", "owner", "due_date", "recommended_action"):
                val = getattr(body, key)
                if val is not None:
                    f[key] = val
            if body.reviewer:
                f["reviewer"] = body.reviewer
                f["approved_at"] = now()
            STORE.update(run_id, findings=findings)
            return f
    raise HTTPException(404, "Unknown finding.")


@app.post("/api/v1/runs/{run_id}/approvals")
def approve(run_id: str, body: ApprovalBody):
    job = _job(run_id)
    events = list(job.get("approvals") or [])
    ev = body.model_dump()
    ev["id"] = f"appr_{uuid.uuid4().hex[:8]}"
    ev["timestamp"] = now()
    events.append(ev)
    STORE.update(run_id, approvals=events, status="awaiting_review" if body.action != "approve_run" else "approved")
    return ev


@app.get("/api/v1/runs")
def list_runs():
    return {"runs": STORE.list()}


@app.get("/api/v1/runs/{run_id}")
def get_run(run_id: str):
    job = _job(run_id)
    return {
        k: job.get(k)
        for k in (
            "id",
            "name",
            "status",
            "mode",
            "created_at",
            "updated_at",
            "created_by",
            "configuration",
            "dataset_profile",
            "conclusion",
            "warnings",
            "module_statuses",
        )
    }


@app.get("/api/v1/runs/{run_id}/results")
def get_results(run_id: str):
    job = _job(run_id)
    return {
        "model_health": job.get("model_health"),
        "findings_package": job.get("findings_package"),
        "scenarios": job.get("scenarios") or [],
        "findings": job.get("findings") or _findings_from_package(job.get("findings_package")),
        "approvals": job.get("approvals") or [],
    }


@app.post("/api/v1/comparisons")
def compare(body: ComparisonBody):
    a = _job(body.baseline_run_id)
    b = _job(body.comparison_run_id)
    ah = (a.get("model_health") or {}).get("core_metrics") or {}
    bh = (b.get("model_health") or {}).get("core_metrics") or {}
    deltas = {}
    for k in set(ah) | set(bh):
        if isinstance(ah.get(k), (int, float)) and isinstance(bh.get(k), (int, float)):
            deltas[k] = round(float(bh[k]) - float(ah[k]), 4)
    return {
        "baseline_run_id": body.baseline_run_id,
        "comparison_run_id": body.comparison_run_id,
        "metric_deltas": deltas,
        "assumption_policy_note": "Compare policy_id and assumption hashes before treating a delta as a model change.",
        "findings": {
            "baseline": _findings_from_package(a.get("findings_package")),
            "comparison": _findings_from_package(b.get("findings_package")),
        },
    }


@app.get("/api/v1/runs/{run_id}/export.json")
def export_json(run_id: str):
    job = _job(run_id)
    return Response(json_bytes(job), media_type="application/json")


@app.get("/api/v1/runs/{run_id}/report.html")
def export_html(run_id: str):
    return HTMLResponse(html_report(_job(run_id)))


def _job(run_id: str) -> dict:
    STORE.purge()
    job = STORE.get(run_id)
    if job is None:
        raise HTTPException(404, "Job expired or unknown.")
    return job


def _ready_for_integrity(run_id: str) -> dict:
    job = _job(run_id)
    if not job.get("assumptions_confirmed") and not job.get("levers"):
        raise HTTPException(400, "Confirm the mutability table before search runs.")
    if job.get("holdout") is None and job.get("findings_package") is None:
        raise HTTPException(400, "Holdout is no longer in memory.")
    return job


def _integrity_package(job: dict) -> dict:
    levers = job.get("levers") or []
    cutoff = float((job.get("configuration") or {}).get("cutoff", 0.275))
    wrapped = job.get("wrapped") or wrap_estimator(job["estimator"], job["holdout"], cutoff)
    with lever_book(rows_to_levers(levers)):
        return build_findings_package(
            job["holdout"],
            wrapped,
            job.get("info") or inspect_wrapped(wrapped, job["holdout"]),
            source="upload",
            dictionary=job.get("dictionary") or "",
            context=job.get("context") or "",
        )


def _findings_from_package(package: dict | None) -> list:
    if not package:
        return []
    items = (package.get("investigation") or {}).get("findings") or []
    out = []
    for f in items:
        out.append(
            {
                "id": f.get("id"),
                "domain": "integrity",
                "title": f.get("title"),
                "description": f.get("claim") or "",
                "severity": f.get("severity") or "medium",
                "evidence_refs": [f.get("run_id")] if f.get("run_id") else [],
                "status": "draft",
                "limitation": "Engine evidence. Not proof of fraud or causality.",
            }
        )
    return out


def _warnings() -> list[str]:
    return [
        "Do not upload PII. Synthetic or already-anonymised holdout only.",
        "Pickle/joblib can execute code. Only load a model you trust.",
        "Cap is 20,000 rows / 50 MB. The holdout is dropped after the run.",
        "Route C is clean only when recorded and true income both exist. On real data it is directional.",
    ]


async def _bytes(upload: UploadFile) -> bytes:
    return read_upload(upload.file)


@app.exception_handler(IngestError)
async def _ingest_error(_, exc: IngestError):
    return JSONResponse({"detail": str(exc)}, status_code=400)


if os.environ.get("JANUS_SERVE_DOCS") == "1":
    from fastapi.staticfiles import StaticFiles

    docs = ROOT / "docs"
    if docs.is_dir():
        app.mount("/", StaticFiles(directory=str(docs), html=True), name="docs")
