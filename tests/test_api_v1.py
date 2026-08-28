import io

import joblib
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from janus.server import app
from janus.storage import MemoryStore


def _pack(n=80):
    frame = pd.DataFrame(
        {
            "f1": [0.1, 0.4, 0.8, 1.2] * (n // 4),
            "f2": [1, 0, 1, 0] * (n // 4),
            "default": [0, 1, 0, 1] * (n // 4),
        }
    )
    clf = LogisticRegression(max_iter=200).fit(frame[["f1", "f2"]], frame["default"])
    model_buf = io.BytesIO()
    joblib.dump(clf, model_buf)
    csv_buf = io.BytesIO()
    frame.to_csv(csv_buf, index=False)
    return model_buf.getvalue(), csv_buf.getvalue()


def test_capabilities_and_health():
    client = TestClient(app)
    h = client.get("/health")
    assert h.status_code == 200
    cap = client.get("/api/v1/capabilities")
    assert cap.status_code == 200
    body = cap.json()
    assert "model_health" in body["modules"]
    assert "/propose" in body["legacy_endpoints"]


def test_v1_run_model_health_and_assumption_gate(monkeypatch):
    monkeypatch.setattr("janus.server.STORE", MemoryStore())
    client = TestClient(app)
    model, holdout = _pack(800)
    created = client.post(
        "/api/v1/runs",
        files={
            "model_file": ("model.joblib", model, "application/octet-stream"),
            "holdout_file": ("holdout.csv", holdout, "text/csv"),
        },
        data={"cutoff": "0.5", "target_column": "default"},
    )
    assert created.status_code == 200, created.text
    run_id = created.json()["run_id"]
    cfg = client.put(
        f"/api/v1/runs/{run_id}/configuration",
        json={
            "target_column": "default",
            "positive_class": 1,
            "cutoff": 0.5,
            "maturity_confirmed": True,
            "performance_window_confirmed": True,
        },
    )
    assert cfg.status_code == 200, cfg.text
    health = client.post(f"/api/v1/runs/{run_id}/model-health")
    assert health.status_code == 200, health.text
    body = health.json()
    assert "roc_auc" in body["core_metrics"]
    assert body["policy_id"] == "janus-default-credit-v1"
    denied = client.post(f"/api/v1/runs/{run_id}/attack-lab")
    assert denied.status_code == 400
    proposed = client.post(f"/api/v1/runs/{run_id}/assumptions/propose")
    assert proposed.status_code == 200
    levers = proposed.json()["proposal"]
    confirm = client.put(
        f"/api/v1/runs/{run_id}/assumptions",
        json={"confirmed": True, "levers": levers, "reviewer": "tester"},
    )
    assert confirm.status_code == 200
    report = client.get(f"/api/v1/runs/{run_id}/report.html")
    assert report.status_code == 200
    assert "JANUS" in report.text


def test_evidence_gap_skips_without_mapping(monkeypatch):
    monkeypatch.setattr("janus.server.STORE", MemoryStore())
    client = TestClient(app)
    model, holdout = _pack(80)
    created = client.post(
        "/api/v1/runs",
        files={
            "model_file": ("model.joblib", model, "application/octet-stream"),
            "holdout_file": ("holdout.csv", holdout, "text/csv"),
        },
        data={"cutoff": "0.5"},
    )
    run_id = created.json()["run_id"]
    gap = client.post(f"/api/v1/runs/{run_id}/evidence-gap")
    assert gap.status_code == 200
    assert gap.json()["status"] == "skipped"


def test_legacy_propose_still_works():
    client = TestClient(app)
    model, holdout = _pack(80)
    res = client.post(
        "/propose",
        files={
            "model": ("model.joblib", model, "application/octet-stream"),
            "holdout": ("holdout.csv", holdout, "text/csv"),
        },
        data={"cutoff": "0.5"},
    )
    assert res.status_code == 200, res.text
    assert "job_id" in res.json()
