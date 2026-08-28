"""Segment exceptions only — suppress small cells."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from janus.validation.calibration import calibration_bins


def segment_exceptions(
    frame: pd.DataFrame,
    y: np.ndarray,
    p: np.ndarray,
    cutoff: float,
    segment_columns: list[str],
    min_rows: int = 100,
) -> list[dict]:
    overall_auc = float(roc_auc_score(y, p)) if len(np.unique(y)) > 1 else None
    overall_dr = float(np.mean(y))
    overall_ar = float((p <= cutoff).mean())
    overall_ece = calibration_bins(y, p)["ece"]
    rows = []
    for col in segment_columns:
        if col not in frame.columns:
            continue
        for value, idx in frame.groupby(col, dropna=False).groups.items():
            n = len(idx)
            yy, pp = y[frame.index.get_indexer(idx)], p[frame.index.get_indexer(idx)]
            # groupby index labels may not match numpy positions if index is not range
            mask = frame[col].eq(value) if pd.notna(value) else frame[col].isna()
            yy = y[mask.to_numpy()]
            pp = p[mask.to_numpy()]
            n = int(len(yy))
            if n < min_rows or len(np.unique(yy)) < 2:
                continue
            auc = float(roc_auc_score(yy, pp))
            dr = float(yy.mean())
            ar = float((pp <= cutoff).mean())
            ece = calibration_bins(yy, pp)["ece"]
            delta = max(
                abs(dr - overall_dr),
                abs(ar - overall_ar),
                0 if overall_auc is None else abs(auc - overall_auc),
                abs(ece - overall_ece),
            )
            status = "exception" if delta >= 0.08 else "in_line"
            if status != "exception":
                continue
            rows.append(
                {
                    "segment_field": col,
                    "segment_value": None if pd.isna(value) else str(value),
                    "count": n,
                    "default_rate": round(dr, 4),
                    "approval_rate": round(ar, 4),
                    "auc": round(auc, 4),
                    "calibration_error": ece,
                    "difference_from_overall": round(float(delta), 4),
                    "status": status,
                }
            )
    rows.sort(key=lambda r: r["difference_from_overall"], reverse=True)
    return rows[:20]
