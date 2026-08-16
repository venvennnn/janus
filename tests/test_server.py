import io
from pathlib import Path

import joblib
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from janus.server import app


def _pack():
    frame = pd.DataFrame(
        {
            "f1": [0.1, 0.4, 0.8, 1.2, 0.3, 0.9, 1.1, 0.2],
            "f2": [1, 0, 1, 0, 1, 0, 1, 0],
            "default": [0, 1, 0, 1, 0, 1, 0, 1],
        }
    )
    clf = LogisticRegression(max_iter=200).fit(frame[["f1", "f2"]], frame["default"])
    model_buf = io.BytesIO()
    joblib.dump(clf, model_buf)
    csv_buf = io.BytesIO()
    frame.to_csv(csv_buf, index=False)
    return model_buf.getvalue(), csv_buf.getvalue()


def test_health():
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["llm"] in {"off", "anthropic"}


def test_propose_rejects_holdout_without_default():
    client = TestClient(app)
    model, _ = _pack()
    bad = pd.DataFrame({"f1": [1, 2], "f2": [0, 1]}).to_csv(index=False).encode()
    res = client.post(
        "/propose",
        files={
            "model": ("model.joblib", model, "application/octet-stream"),
            "holdout": ("holdout.csv", bad, "text/csv"),
        },
        data={"cutoff": "0.5"},
    )
    assert res.status_code == 400
    assert "default" in res.json()["detail"]


def test_run_requires_confirmation():
    client = TestClient(app)
    model, holdout = _pack()
    proposed = client.post(
        "/propose",
        files={
            "model": ("model.joblib", model, "application/octet-stream"),
            "holdout": ("holdout.csv", holdout, "text/csv"),
        },
        data={"cutoff": "0.5", "dictionary_text": "f1 is unverified snapshot"},
    )
    assert proposed.status_code == 200, proposed.text
    job = proposed.json()
    denied = client.post("/run", json={"job_id": job["job_id"], "confirmed": False, "levers": job["proposal"]})
    assert denied.status_code == 400
    ran = client.post("/run", json={"job_id": job["job_id"], "confirmed": True, "levers": job["proposal"]})
    assert ran.status_code == 200, ran.text
    body = ran.json()
    assert body["source"] == "upload"
    assert "battery" in body
    assert body["battery"]["evidence_recourse"]["skipped"] is True


def test_sample_pack_produces_full_review():
    root = Path("sample")
    if not (root / "model.joblib").exists():
        pytest.skip("sample pack not in checkout")
    client = TestClient(app)
    proposed = client.post(
        "/propose",
        files={
            "model": ("model.joblib", (root / "model.joblib").read_bytes(), "application/octet-stream"),
            "holdout": ("holdout.csv", (root / "holdout.csv").read_bytes(), "text/csv"),
            "dictionary": ("dictionary.txt", (root / "dictionary.txt").read_bytes(), "text/plain"),
        },
        data={"cutoff": "0.275", "context": (root / "context.txt").read_text()},
    )
    assert proposed.status_code == 200, proposed.text
    job = proposed.json()
    ran = client.post("/run", json={"job_id": job["job_id"], "confirmed": True, "levers": job["proposal"]})
    assert ran.status_code == 200, ran.text
    package = ran.json()
    assert package["demo_applicant"]["applicant_id"] == "A-7100"
    assert package["battery"]["attack_surface"]["flip_rate"] > 0.2
    assert package["battery"]["evidence_recourse"].get("skipped") is not True
    ids = {f["id"] for f in package["investigation"]["findings"]}
    assert {"F01", "F05", "F06"} <= ids
