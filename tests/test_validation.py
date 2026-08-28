import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from janus.policy import load_policy, overall_conclusion
from janus.validation.calibration import calibration_bins
from janus.validation.health import run_model_health
from janus.validation.performance import ks_statistic, performance_block
from janus.validation.scoring import class_index, predict_positive
from janus.validation.stability import psi, rolling_metrics


def _book(n=400, seed=0, classes=(0, 1)):
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    y = (0.8 * x1 + 0.2 * x2 + rng.normal(scale=0.6, size=n) > 0).astype(int)
    frame = pd.DataFrame({"f1": x1, "f2": x2, "default": y})
    clf = LogisticRegression(max_iter=200).fit(frame[["f1", "f2"]], frame["default"])
    return frame, clf


def test_policy_loads():
    p = load_policy()
    assert p["policy_id"] == "janus-default-credit-v1"
    assert "configurable" in p["label"]


def test_auc_gini_ks_brier():
    y = np.array([0, 0, 1, 1])
    p = np.array([0.1, 0.4, 0.6, 0.9])
    block = performance_block(y, p, cutoff=0.5)
    assert block["roc_auc"] == 1.0
    assert block["gini"] == 1.0
    assert block["ks"] == 1.0
    assert 0 <= block["brier"] < 0.2
    assert abs(ks_statistic(y, p) - 1.0) < 1e-9


def test_cutoff_direction_lte():
    y = np.array([0, 0, 1, 1])
    p = np.array([0.2, 0.5, 0.5, 0.8])
    block = performance_block(y, p, cutoff=0.5)
    # p <= 0.5 approved → first three rows
    assert block["n_approved"] == 3
    assert block["acceptance_rate"] == 0.75


def test_calibration_duplicate_scores():
    y = np.array([0, 1, 0, 1, 0, 1])
    p = np.array([0.4, 0.4, 0.4, 0.7, 0.7, 0.7])
    cal = calibration_bins(y, p, n_bins=10)
    assert cal["bins"]
    assert cal["ece"] >= 0


def test_psi_empty_safe():
    assert psi(np.array([0.1, 0.2]), np.array([0.3, 0.4])) is None
    a = np.linspace(0, 1, 50)
    b = np.linspace(0, 1, 50)
    val = psi(a, b)
    assert val is not None and val < 0.05


def test_rolling_skipped_without_dates():
    y = np.array([0, 1, 0, 1])
    p = np.array([0.2, 0.8, 0.3, 0.7])
    out = rolling_metrics(y, p, None, 0.5)
    assert out["skipped"] is True
    assert "observation date" in out["reason"]


def test_positive_class_column_resolution():
    frame, clf = _book()
    assert class_index(clf, 1) == list(clf.classes_).index(1)
    p = predict_positive(clf, frame, ["f1", "f2"], 1)
    assert p.shape == (len(frame),)
    assert p.min() >= 0 and p.max() <= 1


def test_model_health_blocked_on_tiny_sample():
    frame, clf = _book(n=40)
    result = run_model_health(clf, frame, features=["f1", "f2"], cutoff=0.5, model_name="toy")
    assert result["domain_statuses"]["data_readiness"] == "blocked"
    assert result["conclusion"] == "Insufficient Evidence"
    assert result["policy_id"] == "janus-default-credit-v1"


def test_model_health_runs_on_reasonable_book():
    frame, clf = _book(n=800, seed=3)
    result = run_model_health(
        clf,
        frame,
        features=["f1", "f2"],
        cutoff=0.5,
        maturity_confirmed=True,
        performance_window_confirmed=True,
    )
    assert result["core_metrics"]["roc_auc"] > 0.5
    assert result["calibration"]["bins"]
    assert result["score_bands"]
    assert result["rolling"]["skipped"] is True
    assert result["conclusion"] in {"Pass", "Conditional Pass", "Remediation Required", "Fail"}


def test_overall_conclusion_rule():
    assert overall_conclusion({"data_readiness": "blocked"}) == "Insufficient Evidence"
    assert overall_conclusion({"data_readiness": "pass", "predictive_performance": "fail"}) == "Fail"
    assert overall_conclusion({"data_readiness": "pass", "predictive_performance": "pass", "attack_resistance": "fail"}) == "Remediation Required"
