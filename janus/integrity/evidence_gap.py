"""Evidence Gap: recorded values versus verified columns supplied by the user.

Never fabricates a verified series. If the pair is missing, the test is skipped
or blocked with a reason.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from janus.validation.scoring import predict_positive

METHOD = "janus.integrity.evidence_gap.v1"


def run_evidence_gap(
    estimator,
    frame: pd.DataFrame,
    *,
    features: list[str],
    cutoff: float,
    mappings: list[dict[str, str]] | None,
    positive_class: int = 1,
    target_column: str = "default",
    exposure_column: str | None = None,
) -> dict[str, Any]:
    if not mappings:
        return {
            "status": "skipped",
            "reason": "Skipped — no evidence pair",
            "method_version": METHOD,
            "result": None,
        }
    usable = []
    missing = []
    for item in mappings:
        recorded = (item or {}).get("recorded")
        verified = (item or {}).get("verified")
        if not recorded or not verified:
            missing.append("incomplete pair")
            continue
        if recorded not in frame.columns or verified not in frame.columns:
            missing.append(f"{recorded}↔{verified}")
            continue
        usable.append((recorded, verified))
    if not usable:
        return {
            "status": "blocked",
            "reason": "Blocked — insufficient matched records",
            "missing_pairs": missing,
            "method_version": METHOD,
            "result": None,
        }

    work = frame.copy()
    matched = np.ones(len(work), dtype=bool)
    diffs = {}
    for recorded, verified in usable:
        rec = pd.to_numeric(work[recorded], errors="coerce")
        ver = pd.to_numeric(work[verified], errors="coerce")
        both = rec.notna() & ver.notna()
        matched &= both.to_numpy()
        diffs[f"{recorded}_minus_{verified}"] = {
            "n_matched": int(both.sum()),
            "median_difference": None if not both.any() else round(float((rec - ver)[both].median()), 4),
            "missing_verification_rate": round(float(ver.isna().mean()), 4),
        }
        work.loc[both, recorded] = ver[both]

    n_matched = int(matched.sum())
    if n_matched < 2:
        return {
            "status": "blocked",
            "reason": "Blocked — insufficient matched records",
            "differences": diffs,
            "method_version": METHOD,
            "result": None,
        }

    p0 = predict_positive(estimator, frame, features, positive_class)
    p1 = predict_positive(estimator, work, features, positive_class)
    approved0 = p0 <= cutoff
    approved1 = p1 <= cutoff
    eligible = matched & (~approved0)
    cross = eligible & approved1
    n_eligible = int(eligible.sum())
    n_cross = int(cross.sum())
    y = pd.to_numeric(frame[target_column], errors="coerce").to_numpy() if target_column in frame.columns else None
    cross_default = None
    if y is not None and n_cross:
        cross_default = round(float(np.nanmean(y[cross])), 4)
    loss = None
    if exposure_column and exposure_column in frame.columns and y is not None and n_cross:
        exp = pd.to_numeric(frame[exposure_column], errors="coerce").fillna(0).to_numpy()
        den = float(exp[cross].sum())
        if den > 0:
            loss = round(float(exp[cross & (y == 1)].sum()) / den, 4)

    status = "tested" if not missing else "partially_tested"
    return {
        "status": status,
        "reason": None if not missing else f"Partially tested — missing {', '.join(missing)}",
        "method_version": METHOD,
        "differences": diffs,
        "result": {
            "n_matched": n_matched,
            "n_eligible_declines": n_eligible,
            "n_cross": n_cross,
            "cross_rate": None if n_eligible == 0 else round(n_cross / n_eligible, 4),
            "cross_default_rate": cross_default,
            "cross_loss_rate": loss,
            "pairs": [{"recorded": a, "verified": b} for a, b in usable],
            "limitations": "Substitution uses user-supplied verified columns. JANUS does not invent evidence.",
        },
    }
