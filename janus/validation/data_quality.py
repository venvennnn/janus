"""Compact data-health checks. Flags require human review."""

from __future__ import annotations

import numpy as np
import pandas as pd


def data_health(
    frame: pd.DataFrame,
    features: list[str],
    target: str,
    timestamp_column: str | None,
    maturity_confirmed: bool,
    performance_window_confirmed: bool,
) -> list[dict]:
    checks = []
    n = len(frame)
    checks.append(_status("performance_window", performance_window_confirmed, "User confirmed a sufficient performance window." if performance_window_confirmed else "Performance window is unconfirmed."))
    checks.append(_status("target_maturity", maturity_confirmed, "User confirmed the target is matured." if maturity_confirmed else "Target maturity is unconfirmed."))
    if timestamp_column and timestamp_column in frame.columns:
        ts = pd.to_datetime(frame[timestamp_column], errors="coerce")
        checks.append(
            {
                "id": "feature_target_time_overlap",
                "status": "limited",
                "detail": f"Date parse rate {float(ts.notna().mean()):.1%}. Temporal leakage cannot be proven without feature-as-of timestamps.",
            }
        )
    else:
        checks.append(
            {
                "id": "feature_target_time_overlap",
                "status": "limited",
                "detail": "No observation date. Temporal leakage checks are limited.",
            }
        )
    miss = {c: float(frame[c].isna().mean()) for c in features if c in frame.columns}
    high_miss = {k: round(v, 4) for k, v in miss.items() if v >= 0.2}
    checks.append(
        {
            "id": "missing_value_drift",
            "status": "warn" if high_miss else "pass",
            "detail": f"Features with ≥20% missing: {high_miss}" if high_miss else "No feature exceeds 20% missingness on this holdout.",
        }
    )
    numeric = frame[[c for c in features if c in frame.columns]].select_dtypes(include=[np.number])
    pairs = []
    if numeric.shape[1] >= 2:
        corr = numeric.corr().abs()
        cols = list(corr.columns)
        for i, a in enumerate(cols):
            for b in cols[i + 1 :]:
                val = corr.loc[a, b]
                if pd.notna(val) and val >= 0.95:
                    pairs.append({"a": a, "b": b, "abs_corr": round(float(val), 4)})
    checks.append(
        {
            "id": "highly_correlated_pairs",
            "status": "warn" if pairs else "pass",
            "detail": pairs[:8] if pairs else "No feature pair ≥ 0.95 absolute correlation.",
        }
    )
    missing_feats = [f for f in features if f not in frame.columns]
    checks.append(
        {
            "id": "model_data_alignment",
            "status": "fail" if missing_feats else "pass",
            "detail": f"Missing model features: {missing_feats}" if missing_feats else f"{len(features)} model features present. n={n}.",
        }
    )
    return checks


def _status(id_: str, ok: bool, detail: str) -> dict:
    return {"id": id_, "status": "pass" if ok else "warn", "detail": detail}
