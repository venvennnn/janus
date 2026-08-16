"""Tiny FastAPI service for judge uploads. No database. Nothing persists after the run."""

from __future__ import annotations

import os
import time
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from janus import __version__
from janus.ingest import IngestError, load_estimator, load_holdout, read_upload
from janus.run_uploaded import propose_upload, run_uploaded

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "sample"
MAX_JOBS = 8
JOB_TTL_S = 30 * 60

app = FastAPI(title="JANUS", version=__version__, docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_JOBS: dict[str, dict] = {}


class RunBody(BaseModel):
    job_id: str
    confirmed: bool = False
    levers: list[dict] = Field(default_factory=list)


def _purge() -> None:
    now = time.time()
    dead = [k for k, j in _JOBS.items() if now - j["created"] > JOB_TTL_S]
    for k in dead:
        _JOBS.pop(k, None)
    while len(_JOBS) > MAX_JOBS:
        oldest = min(_JOBS, key=lambda k: _JOBS[k]["created"])
        _JOBS.pop(oldest, None)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "product": "JANUS", "version": __version__}


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
    _purge()
    try:
        estimator = load_estimator(await _bytes(model), model.filename or "model.joblib")
        frame = load_holdout(await _bytes(holdout), holdout.filename or "holdout.csv")
        blob = dictionary_text
        if dictionary is not None and dictionary.filename:
            blob = (await _bytes(dictionary)).decode("utf-8", errors="replace") + "\n" + blob
        wrapped, info, proposal = propose_upload(estimator, frame, cutoff, blob, context)
    except IngestError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(400, f"Could not inspect the upload: {exc}") from exc

    job_id = uuid.uuid4().hex[:12]
    _JOBS[job_id] = {
        "created": time.time(),
        "model": wrapped,
        "holdout": frame,
        "info": info,
    }
    return {
        "job_id": job_id,
        "model": info,
        "proposal": proposal,
        "warnings": [
            "Do not upload PII. Synthetic or already-anonymised holdout only.",
            "Pickle/joblib can execute code. Only load a model you trust.",
            "Cap is 20,000 rows / 50 MB. The holdout is dropped after the run.",
            "Route C is clean only when recorded and true income both exist. On real data it is directional.",
        ],
    }


@app.post("/run")
def run(body: RunBody):
    _purge()
    if not body.confirmed:
        raise HTTPException(400, "Confirm the mutability table before search runs.")
    if not body.levers:
        raise HTTPException(400, "Send the confirmed lever rows.")
    job = _JOBS.get(body.job_id)
    if job is None:
        raise HTTPException(404, "Job expired or unknown. Propose again.")
    try:
        package = run_uploaded(job["model"], job["holdout"], body.levers)
    except Exception as exc:
        raise HTTPException(400, f"Audit failed: {exc}") from exc
    _JOBS.pop(body.job_id, None)
    return package


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
