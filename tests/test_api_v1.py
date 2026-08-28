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


def test_maps_dpd90_and_does_not_treat_revenue_as_exposure(monkeypatch):
    monkeypatch.setattr("janus.server.STORE", MemoryStore())
    client = TestClient(app)
    frame = pd.DataFrame(
        {
            "f1": [0.1, 0.4, 0.8, 1.2] * 50,
            "f2": [1, 0, 1, 0] * 50,
            "dpd90_index_x": [0, 1, 0, 1] * 50,
            "LOAN_CREATED_AT_LCL_TS": pd.date_range("2024-01-01", periods=200, freq="D").astype(str),
            "LOAN_COMPANY_REVENUE_LCL_AMT": [1000] * 200,
        }
    )
    clf = LogisticRegression(max_iter=200).fit(frame[["f1", "f2"]], frame["dpd90_index_x"])
    model_buf = io.BytesIO()
    joblib.dump(clf, model_buf)
    csv_buf = io.BytesIO()
    frame.to_csv(csv_buf, index=False)
    created = client.post(
        "/api/v1/runs",
        files={
            "model_file": ("model.joblib", model_buf.getvalue(), "application/octet-stream"),
            "holdout_file": ("holdout.csv", csv_buf.getvalue(), "text/csv"),
        },
        data={"cutoff": "0.5"},
    )
    assert created.status_code == 200, created.text
    suggestions = created.json()["schema_suggestions"]
    assert suggestions.get("dpd90_index_x") == "target"
    assert suggestions.get("LOAN_COMPANY_REVENUE_LCL_AMT") == "revenue_not_exposure"
    run_id = created.json()["run_id"]
    cfg = client.put(
        f"/api/v1/runs/{run_id}/configuration",
        json={
            "target_column": "dpd90_index_x",
            "positive_class": 1,
            "timestamp_column": "LOAN_CREATED_AT_LCL_TS",
            "cutoff": 0.5,
            "maturity_confirmed": True,
            "performance_window_confirmed": True,
        },
    )
    assert cfg.status_code == 200, cfg.text
    health = client.post(f"/api/v1/runs/{run_id}/model-health")
    assert health.status_code == 200, health.text
    assert health.json()["core_metrics"]["approved_loss_rate"] is None


def test_attack_lab_then_remediation_keeps_holdout(monkeypatch):
    monkeypatch.setattr("janus.server.STORE", MemoryStore())
    client = TestClient(app)
    model, holdout = _pack(200)
    created = client.post(
        "/api/v1/runs",
        files={
            "model_file": ("model.joblib", model, "application/octet-stream"),
            "holdout_file": ("holdout.csv", holdout, "text/csv"),
        },
        data={"cutoff": "0.5"},
    )
    run_id = created.json()["run_id"]
    client.put(
        f"/api/v1/runs/{run_id}/configuration",
        json={"target_column": "default", "positive_class": 1, "cutoff": 0.5, "maturity_confirmed": True, "performance_window_confirmed": True},
    )
    client.post(f"/api/v1/runs/{run_id}/model-health")
    proposed = client.post(f"/api/v1/runs/{run_id}/assumptions/propose")
    levers = proposed.json()["proposal"]
    client.put(f"/api/v1/runs/{run_id}/assumptions", json={"confirmed": True, "levers": levers, "reviewer": "tester"})
    atk = client.post(f"/api/v1/runs/{run_id}/attack-lab")
    assert atk.status_code == 200, atk.text
    assert "numerator" in atk.json()["metrics"]["attack_flip_rate"]
    listed = client.get(f"/api/v1/runs/{run_id}/remediation-scenarios")
    assert listed.status_code == 200
    assert len(listed.json()["scenarios"]) >= 2
    extra = client.post(
        f"/api/v1/runs/{run_id}/remediation-scenarios",
        json={"name": "Even tighter cutoff", "actions": [{"type": "cutoff", "value": 0.2}]},
    )
    assert extra.status_code == 200, extra.text
    done = client.post(f"/api/v1/runs/{run_id}/finalize")
    assert done.status_code == 200
    blocked = client.post(
        f"/api/v1/runs/{run_id}/remediation-scenarios",
        json={"name": "after drop", "actions": [{"type": "cutoff", "value": 0.1}]},
    )
    assert blocked.status_code == 400


def test_evidence_gap_with_verified_column(monkeypatch):
    monkeypatch.setattr("janus.server.STORE", MemoryStore())
    client = TestClient(app)
    frame = pd.DataFrame(
        {
            "f1": [0.1, 0.4, 0.8, 1.2] * 40,
            "f2": [1, 0, 1, 0] * 40,
            "f1_verified": [-0.2, 0.1, 0.3, 0.5] * 40,
            "default": [0, 1, 0, 1] * 40,
        }
    )
    clf = LogisticRegression(max_iter=200).fit(frame[["f1", "f2"]], frame["default"])
    model_buf = io.BytesIO()
    joblib.dump(clf, model_buf)
    csv_buf = io.BytesIO()
    frame.to_csv(csv_buf, index=False)
    created = client.post(
        "/api/v1/runs",
        files={
            "model_file": ("model.joblib", model_buf.getvalue(), "application/octet-stream"),
            "holdout_file": ("holdout.csv", csv_buf.getvalue(), "text/csv"),
        },
        data={"cutoff": "0.5"},
    )
    run_id = created.json()["run_id"]
    client.put(
        f"/api/v1/runs/{run_id}/configuration",
        json={
            "target_column": "default",
            "cutoff": 0.5,
            "evidence_mappings": [{"recorded": "f1", "verified": "f1_verified"}],
            "maturity_confirmed": True,
            "performance_window_confirmed": True,
        },
    )
    gap = client.post(f"/api/v1/runs/{run_id}/evidence-gap")
    assert gap.status_code == 200, gap.text
    assert gap.json()["status"] in {"tested", "partially_tested"}
