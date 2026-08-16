import io

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from janus.agent import investigate
from janus.ingest import IngestError, load_estimator, validate_holdout
from janus.levers import lever_book
from janus.model import inspect_wrapped, wrap_estimator
from janus.package import build_findings_package
from janus.propose import propose_mutability, rows_to_levers


def test_holdout_requires_default():
    with pytest.raises(IngestError, match="default"):
        validate_holdout(pd.DataFrame({"x": [1, 2, 3]}))


def test_holdout_adds_applicant_ids():
    frame = validate_holdout(pd.DataFrame({"default": [0, 1, 0, 1], "x": [1, 2, 3, 4]}))
    assert list(frame["applicant_id"]) == ["R-0", "R-1", "R-2", "R-3"]


def test_holdout_rejects_single_class():
    with pytest.raises(IngestError, match="both 0 and 1"):
        validate_holdout(pd.DataFrame({"default": [0, 0, 0]}))


def test_load_estimator_requires_predict_proba():
    import joblib

    buf = io.BytesIO()
    joblib.dump({"not": "a model"}, buf)
    with pytest.raises(IngestError, match="predict_proba"):
        load_estimator(buf.getvalue(), "x.joblib")


def test_propose_marks_age_immutable_and_savings_cosmetic():
    frame = pd.DataFrame(
        {
            "age": [21, 34, 45, 52],
            "savings_balance": [1000, 2000, 3000, 4000],
            "default": [0, 1, 0, 1],
        }
    )
    rows = propose_mutability(
        ["age", "savings_balance"],
        frame,
        "age is date of birth\nsavings_balance is an unverified snapshot",
    )
    kinds = {row["feature"]: row["kind"] for row in rows}
    assert kinds["age"] == "immutable"
    assert kinds["savings_balance"] == "cosmetic"
    book = rows_to_levers(rows)
    assert book["age"].attack is None
    assert book["savings_balance"].attack is not None


def _plain_book(n: int = 400, seed: int = 0):
    rng = np.random.default_rng(seed)
    frame = pd.DataFrame(
        {
            "f1": rng.normal(size=n),
            "f2": rng.normal(size=n),
            "default": rng.integers(0, 2, size=n),
        }
    )
    clf = LogisticRegression(max_iter=200).fit(frame[["f1", "f2"]], frame["default"])
    model = wrap_estimator(clf, frame, 0.5)
    return frame, model


def test_skip_paths_without_audit_labels():
    frame, model = _plain_book()
    rows = propose_mutability(model.features, frame)
    info = inspect_wrapped(model, frame)
    with lever_book(rows_to_levers(rows)):
        package = build_findings_package(frame, model, info, source="upload")
    battery = package["battery"]
    assert battery["proxy_audit"]["skipped"] is True
    assert battery["unexplained_exclusion"]["skipped"] is True
    assert battery["evidence_recourse"]["skipped"] is True
    assert package["recourse_menu"]["route_c_document_it"]["skipped"] is True
    ids = {f["id"] for f in package["investigation"]["findings"]}
    assert "F02" not in ids
    assert "F03" not in ids
    assert "F06" not in ids


def test_agent_tolerates_skipped_battery():
    battery = {
        "attack_surface": {"run_id": "run.attack_surface", "skipped": True, "flip_rate": None},
        "proxy_audit": {"run_id": "run.proxy_audit", "skipped": True, "probe_auc": None},
        "unexplained_exclusion": {"run_id": "run.unexplained_exclusion", "skipped": True, "approval_gap_pp": None},
        "broken_segments": {"run_id": "run.discover_segments", "skipped": True, "young_self_employed": {"n": 0}},
        "integrity_gap": {"run_id": "run.integrity_gap", "skipped": True, "median_gap_ratio": None},
        "evidence_recourse": {"run_id": "run.evidence_recourse", "skipped": True, "cross_rate_full_documentation": None},
    }
    out = investigate(battery, {"auc_holdout": 0.6, "approval_rate": 0.5})
    assert out["findings"] == []
    assert out["hypotheses"] == []
