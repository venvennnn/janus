"""Leakage flags. They are review items, not proof."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score


def leakage_flags(frame: pd.DataFrame, features: list[str], y: np.ndarray) -> list[dict]:
    flags = []
    target_like = [c for c in features if "default" in c.lower() or c.lower().endswith("_y") or "target" in c.lower()]
    for col in target_like:
        flags.append({"id": "target_name_leakage", "feature": col, "status": "warn", "detail": "Feature name resembles the target. Review required."})
    if len(np.unique(y)) < 2:
        return flags
    for col in features:
        if col not in frame.columns:
            continue
        s = pd.to_numeric(frame[col], errors="coerce")
        if s.nunique(dropna=True) < 2:
            continue
        filled = s.fillna(s.median())
        try:
            auc = float(roc_auc_score(y, filled))
        except Exception:
            continue
        auc = max(auc, 1 - auc)
        if auc >= 0.98:
            flags.append(
                {
                    "id": "near_perfect_univariate",
                    "feature": col,
                    "status": "warn",
                    "univariate_auc": round(auc, 4),
                    "detail": "Near-perfect univariate relationship with the target. Possible leakage or encoding of the outcome.",
                }
            )
    return flags
