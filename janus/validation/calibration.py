"""Calibration bins and expected calibration error."""

from __future__ import annotations

import numpy as np


def calibration_bins(y: np.ndarray, p: np.ndarray, n_bins: int = 10, exposure: np.ndarray | None = None) -> dict:
    y = np.asarray(y).astype(int)
    p = np.asarray(p, dtype=float)
    qs = np.quantile(p, np.linspace(0, 1, n_bins + 1))
    edges = np.unique(qs)
    if len(edges) < 3:
        edges = np.array([0.0, 0.5, 1.0])
    bins = []
    ece = 0.0
    n = len(p)
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        if i == len(edges) - 2:
            mask = (p >= lo) & (p <= hi)
        else:
            mask = (p >= lo) & (p < hi)
        count = int(mask.sum())
        if count == 0:
            continue
        pred = float(p[mask].mean())
        obs = float(y[mask].mean())
        rec = {
            "bin": i,
            "lo": round(float(lo), 4),
            "hi": round(float(hi), 4),
            "count": count,
            "mean_predicted": round(pred, 4),
            "observed_default": round(obs, 4),
        }
        if exposure is not None:
            rec["exposure"] = float(np.asarray(exposure)[mask].sum())
        bins.append(rec)
        ece += (count / n) * abs(pred - obs)
    return {
        "bins": bins,
        "ece": round(float(ece), 4),
        "n_bins": len(bins),
        "method_version": "janus.validation.calibration.v1",
    }


def score_bands(y: np.ndarray, p: np.ndarray, n_bands: int = 8) -> list[dict]:
    y = np.asarray(y).astype(int)
    p = np.asarray(p, dtype=float)
    qs = np.quantile(p, np.linspace(0, 1, n_bands + 1))
    edges = np.unique(qs)
    out = []
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        mask = (p >= lo) & (p <= hi) if i == len(edges) - 2 else (p >= lo) & (p < hi)
        if not mask.any():
            continue
        out.append(
            {
                "band": i + 1,
                "lo": round(float(lo), 4),
                "hi": round(float(hi), 4),
                "count": int(mask.sum()),
                "mean_predicted": round(float(p[mask].mean()), 4),
                "observed_default": round(float(y[mask].mean()), 4),
            }
        )
    return out
