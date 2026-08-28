"""Predictive performance metrics. Holdout only — no refit."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
    precision_recall_curve,
)


def ks_statistic(y: np.ndarray, p: np.ndarray) -> float | None:
    y = np.asarray(y).astype(int)
    p = np.asarray(p, dtype=float)
    n1 = int(y.sum())
    n0 = int(len(y) - n1)
    if n0 == 0 or n1 == 0:
        return None
    order = np.argsort(p)
    y_s = y[order]
    cdf1 = np.cumsum(y_s) / n1
    cdf0 = np.cumsum(1 - y_s) / n0
    return float(np.max(np.abs(cdf1 - cdf0)))


def cutoff_metrics(y: np.ndarray, p: np.ndarray, cutoff: float, exposure: np.ndarray | None = None) -> dict:
    approved = p <= cutoff
    n_approved = int(approved.sum())
    pred_pos = ~approved
    tn = int((approved & (y == 0)).sum())
    fp = int((pred_pos & (y == 0)).sum())
    out = {
        "acceptance_rate": float(approved.mean()),
        "n_approved": n_approved,
        "approved_default_rate": float(y[approved].mean()) if n_approved else None,
        "accuracy": float(accuracy_score(y, pred_pos.astype(int))),
        "precision": float(precision_score(y, pred_pos.astype(int), zero_division=0)),
        "recall": float(recall_score(y, pred_pos.astype(int), zero_division=0)),
        "f1": float(f1_score(y, pred_pos.astype(int), zero_division=0)),
        "specificity": float(tn / (tn + fp)) if (tn + fp) else None,
    }
    if exposure is not None and n_approved:
        exp = np.asarray(exposure, dtype=float)
        den = float(exp[approved].sum())
        num = float(exp[approved & (y == 1)].sum())
        out["approved_loss_rate"] = None if den <= 0 else num / den
        out["approved_exposure"] = den
    else:
        out["approved_loss_rate"] = None
    return out


def roc_pr_points(y: np.ndarray, p: np.ndarray, max_points: int = 80) -> dict:
    fpr, tpr, _ = roc_curve(y, p)
    prec, rec, _ = precision_recall_curve(y, p)
    return {
        "roc": _downsample(fpr, tpr, max_points),
        "pr": _downsample(rec, prec, max_points),
    }


def _downsample(x, y, n):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) <= n:
        return [{"x": float(a), "y": float(b)} for a, b in zip(x, y)]
    idx = np.linspace(0, len(x) - 1, n).round().astype(int)
    return [{"x": float(x[i]), "y": float(y[i])} for i in idx]


def performance_block(y: np.ndarray, p: np.ndarray, cutoff: float, exposure=None) -> dict:
    auc = float(roc_auc_score(y, p))
    pr_auc = float(average_precision_score(y, p))
    brier = float(brier_score_loss(y, p))
    p_clip = np.clip(p, 1e-15, 1 - 1e-15)
    loss = float(log_loss(y, p_clip))
    cut = cutoff_metrics(y, p, cutoff, exposure)
    return {
        "roc_auc": round(auc, 4),
        "gini": round(2 * auc - 1, 4),
        "ks": None if (ks := ks_statistic(y, p)) is None else round(ks, 4),
        "pr_auc": round(pr_auc, 4),
        "brier": round(brier, 4),
        "log_loss": round(loss, 4),
        "n": int(len(y)),
        "n_defaults": int(y.sum()),
        "default_rate": round(float(y.mean()), 4),
        **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in cut.items()},
        "curves": roc_pr_points(y, p),
        "method_version": "janus.validation.performance.v1",
    }
