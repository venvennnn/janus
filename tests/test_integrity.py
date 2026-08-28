import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from janus.integrity.evidence_gap import run_evidence_gap
from janus.integrity.metrics import attack_flip_metric, integrity_gap_metric, mask_record_ids


def test_integrity_gap_returns_parts():
    gap = {"attack_flip_rate": 0.5, "genuine_flip_rate": 0.25, "median_gap_ratio": 12.0, "note": "median of ratios"}
    rec = integrity_gap_metric(gap)
    assert rec["numerator"] == 0.5
    assert rec["denominator"] == 0.25
    assert rec["value"] == 2.0
    assert rec["formula"]


def test_integrity_gap_zero_denominator():
    rec = integrity_gap_metric({"attack_flip_rate": 0.4, "genuine_flip_rate": 0})
    assert rec["value"] is None
    assert rec["status"] == "skipped"


def test_attack_flip_skipped_not_zero():
    rec = attack_flip_metric({"skipped": True, "reason": "No declined applicants at this cutoff."})
    assert rec["value"] is None
    assert "No declined" in rec["limitations"]


def test_mask_ids():
    assert mask_record_ids(["A-7100", "cust-99"]) == ["rec-7100", "rec-0002"]


def test_evidence_gap_skip_without_pair():
    frame = pd.DataFrame({"f1": [0.1, 0.9], "default": [0, 1]})
    clf = LogisticRegression().fit(frame[["f1"]], frame["default"])
    out = run_evidence_gap(clf, frame, features=["f1"], cutoff=0.5, mappings=[])
    assert out["status"] == "skipped"


def test_evidence_gap_substitution():
    rng = np.random.default_rng(0)
    x = rng.normal(size=80)
    y = (x > 0).astype(int)
    frame = pd.DataFrame({"f1": x, "f1_verified": x - 0.8, "default": y})
    clf = LogisticRegression().fit(frame[["f1"]], y)
    out = run_evidence_gap(
        clf,
        frame,
        features=["f1"],
        cutoff=0.5,
        mappings=[{"recorded": "f1", "verified": "f1_verified"}],
    )
    assert out["status"] == "tested"
    assert out["result"]["n_matched"] == 80
    assert "cross_rate" in out["result"]
