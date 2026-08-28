"""Assemble the one-page Model Health result."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from janus import __version__
from janus.policy import domain_status, load_policy, overall_conclusion
from janus.validation.calibration import calibration_bins, score_bands
from janus.validation.data_quality import data_health
from janus.validation.leakage import leakage_flags
from janus.validation.performance import performance_block
from janus.validation.scoring import predict_positive
from janus.validation.segments import segment_exceptions
from janus.validation.stability import psi, rolling_metrics


def run_model_health(
    estimator,
    frame: pd.DataFrame,
    *,
    features: list[str],
    cutoff: float,
    target_column: str = "default",
    positive_class: int = 1,
    timestamp_column: str | None = None,
    exposure_column: str | None = None,
    segment_columns: list[str] | None = None,
    maturity_confirmed: bool = False,
    performance_window_confirmed: bool = False,
    policy_id: str = "janus-default-credit-v1",
    model_name: str = "uploaded-model",
    model_version: str | None = None,
) -> dict[str, Any]:
    policy = load_policy(policy_id)
    y = pd.to_numeric(frame[target_column], errors="coerce")
    usable = y.isin([0, 1])
    work = frame.loc[usable].copy()
    y = y.loc[usable].astype(int).to_numpy()
    p = predict_positive(estimator, work, features, positive_class)
    exposure = None
    if exposure_column and exposure_column in work.columns:
        exposure = pd.to_numeric(work[exposure_column], errors="coerce").fillna(0).to_numpy()
        if (exposure < 0).any():
            exposure = None
    perf = performance_block(y, p, cutoff, exposure)
    cal = calibration_bins(y, p, exposure=exposure)
    bands = score_bands(y, p)
    ts = work[timestamp_column] if timestamp_column and timestamp_column in work.columns else None
    roll = rolling_metrics(y, p, ts, cutoff, min_period_rows=int(policy["minimums"]["period_rows"]))
    psi_value = None
    if ts is not None and not roll.get("skipped") and len(roll.get("periods") or []) >= 2:
        mid = len(p) // 2
        order = np.argsort(pd.to_datetime(ts, errors="coerce").to_numpy())
        psi_value = psi(p[order[:mid]], p[order[mid:]])
    quality = data_health(
        work,
        features,
        target_column,
        timestamp_column,
        maturity_confirmed,
        performance_window_confirmed,
    )
    leaks = leakage_flags(work, features, y)
    segs = segment_exceptions(
        work.reset_index(drop=True),
        y,
        p,
        cutoff,
        segment_columns or [],
        min_rows=int(policy["minimums"]["segment_rows"]),
    )
    mh = policy["model_health"]
    domains = {
        "data_readiness": _data_domain(quality, len(work), int(y.sum()), policy),
        "predictive_performance": domain_status(perf["roc_auc"], warn_below=mh.get("auc_warn_below"), fail_below=mh["auc_fail_below"]),
        "calibration": domain_status(cal["ece"], warn_above=mh["ece_warn_above"]),
        "stability": "skipped" if roll.get("skipped") else domain_status(psi_value, warn_above=mh["psi_warn_above"], fail_above=mh["psi_fail_above"]),
        "segment_reliability": "warn" if segs else "pass",
        "attack_resistance": "not_tested",
        "evidence_reliability": "not_tested",
        "governance_completeness": "not_tested",
    }
    if leaks:
        if domains["data_readiness"] == "pass":
            domains["data_readiness"] = "warn"
    conclusion = overall_conclusion(domains)
    warnings = [c["detail"] if isinstance(c["detail"], str) else c["id"] for c in quality if c["status"] in {"warn", "fail", "limited"}]
    warnings.extend(f["detail"] for f in leaks)
    return {
        "janus_version": __version__,
        "policy_id": policy_id,
        "policy_label": policy.get("label"),
        "conclusion_rule": policy.get("conclusion_rule"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "model_name": model_name,
            "model_version": model_version,
            "target_column": target_column,
            "positive_class": positive_class,
            "cutoff": cutoff,
            "approval_rule": "predicted_default_probability <= cutoff",
            "n": int(len(work)),
            "n_defaults": int(y.sum()),
            "default_rate": perf["default_rate"],
            "evaluation_period": None if roll.get("skipped") else f"{roll.get('date_min')} → {roll.get('date_max')}",
        },
        "core_metrics": {
            "roc_auc": perf["roc_auc"],
            "gini": perf["gini"],
            "ks": perf["ks"],
            "pr_auc": perf["pr_auc"],
            "brier": perf["brier"],
            "acceptance_rate": perf["acceptance_rate"],
            "approved_default_rate": perf["approved_default_rate"],
            "approved_loss_rate": perf["approved_loss_rate"],
        },
        "secondary_metrics": {
            "log_loss": perf["log_loss"],
            "accuracy": perf["accuracy"],
            "precision": perf["precision"],
            "recall": perf["recall"],
            "specificity": perf["specificity"],
            "f1": perf["f1"],
            "n": perf["n"],
            "n_defaults": perf["n_defaults"],
        },
        "curves": perf["curves"],
        "calibration": cal,
        "score_bands": bands,
        "rolling": roll,
        "psi": None if psi_value is None else round(float(psi_value), 4),
        "data_health": quality,
        "leakage_flags": leaks,
        "segment_exceptions": segs,
        "domain_statuses": domains,
        "conclusion": conclusion,
        "warnings": warnings,
        "skipped_tests": [roll["reason"]] if roll.get("skipped") else [],
        "method_version": "janus.validation.health.v1",
    }


def _data_domain(quality: list[dict], n: int, n_defaults: int, policy: dict) -> str:
    mins = policy["minimums"]
    if n < mins["rows"] or n_defaults < mins["defaults"]:
        return "blocked"
    if any(c["status"] == "fail" for c in quality):
        return "fail"
    if any(c["status"] == "warn" for c in quality):
        return "warn"
    return "pass"
