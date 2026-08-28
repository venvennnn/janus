"""PSI and rolling stability. Skip honestly when a timestamp is missing."""

from __future__ import annotations

import numpy as np
import pandas as pd


def psi(expected: np.ndarray, actual: np.ndarray, n_bins: int = 10, eps: float = 1e-6) -> float | None:
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)
    if len(expected) < 20 or len(actual) < 20:
        return None
    edges = np.unique(np.quantile(expected, np.linspace(0, 1, n_bins + 1)))
    if len(edges) < 3:
        return None
    e_counts, _ = np.histogram(expected, bins=edges)
    a_counts, _ = np.histogram(actual, bins=edges)
    e = e_counts / max(e_counts.sum(), 1) + eps
    a = a_counts / max(a_counts.sum(), 1) + eps
    e = e / e.sum()
    a = a / a.sum()
    return float(np.sum((a - e) * np.log(a / e)))


def rolling_metrics(
    y: np.ndarray,
    p: np.ndarray,
    timestamps: pd.Series | None,
    cutoff: float,
    min_period_rows: int = 100,
) -> dict:
    if timestamps is None:
        return {
            "skipped": True,
            "reason": "Skipped — no usable observation date",
            "periods": [],
            "method_version": "janus.validation.stability.v1",
        }
    ts = pd.to_datetime(timestamps, errors="coerce")
    parsed = float(ts.notna().mean())
    if parsed < 0.8:
        return {
            "skipped": True,
            "reason": "Skipped — no usable observation date",
            "date_parse_rate": round(parsed, 4),
            "periods": [],
            "method_version": "janus.validation.stability.v1",
        }
    frame = pd.DataFrame({"y": y, "p": p, "ts": ts}).dropna(subset=["ts"])
    frame["period"] = frame["ts"].dt.to_period("M").astype(str)
    periods = []
    grouped = list(frame.groupby("period", sort=True))
    baseline_p = grouped[0][1]["p"].to_numpy() if grouped else np.array([])
    from sklearn.metrics import roc_auc_score, brier_score_loss

    from janus.validation.calibration import calibration_bins

    for name, g in grouped:
        if len(g) < min_period_rows or g["y"].nunique() < 2:
            periods.append({"period": name, "n": int(len(g)), "status": "suppressed"})
            continue
        yy, pp = g["y"].to_numpy(), g["p"].to_numpy()
        ece = calibration_bins(yy, pp)["ece"]
        rec = {
            "period": name,
            "n": int(len(g)),
            "auc": round(float(roc_auc_score(yy, pp)), 4),
            "default_rate": round(float(yy.mean()), 4),
            "acceptance_rate": round(float((pp <= cutoff).mean()), 4),
            "calibration_error": ece,
            "psi": None if len(baseline_p) < 20 else round(psi(baseline_p, pp) or 0.0, 4),
            "status": "ok",
        }
        periods.append(rec)
    return {
        "skipped": False,
        "date_parse_rate": round(parsed, 4),
        "date_min": str(ts.min()),
        "date_max": str(ts.max()),
        "periods": periods,
        "method_version": "janus.validation.stability.v1",
    }
