"""Decision-twin construction. Never claim economic identity without designated evidence."""

from __future__ import annotations

import numpy as np
import pandas as pd


def counterfactual_twin(demo: dict, menu: dict) -> dict:
    """Build the reference counterfactual pair from a recorded recourse menu."""
    a = menu.get("route_a_fake_it") or {}
    return {
        "mode": "counterfactual",
        "label": "Counterfactual twin — presentation-sensitive change only",
        "limitation": "Matched on the same observed row. Not two economically identical businesses.",
        "left": {
            "title": "As recorded",
            "applicant_id": demo.get("applicant_id"),
            "p": menu.get("p_start"),
            "decision": "declined" if menu.get("declined") else "approved",
            "default": demo.get("default"),
            "held_constant": ["industry/operating history are not re-simulated"],
            "differs": {},
        },
        "right": {
            "title": "After cosmetic presentation (model owner only)",
            "applicant_id": demo.get("applicant_id"),
            "p": a.get("p_final"),
            "decision": "would_cross_cutoff" if a.get("flipped") else "still_declined",
            "default": demo.get("default"),
            "differs": {"features": a.get("features") or []},
        },
        "why": "The same applicant crosses the cutoff after presentation-sensitive changes. Underlying repayment capacity is not asserted to have changed.",
    }


def matched_observation_twins(
    frame: pd.DataFrame,
    p: np.ndarray,
    cutoff: float,
    core: list[str],
    cosmetic: list[str],
    n: int = 3,
) -> dict:
    if not core or not cosmetic:
        return {
            "skipped": True,
            "reason": "Matched-observation twins need designated core and presentation-sensitive features.",
            "pairs": [],
        }
    work = frame.copy()
    work["_p"] = p
    work["_approved"] = p <= cutoff
    present = [c for c in core if c in work.columns]
    cos = [c for c in cosmetic if c in work.columns]
    if not present or not cos:
        return {"skipped": True, "reason": "Designated twin features are not in this dataset.", "pairs": []}
    approved = work[work["_approved"]]
    declined = work[~work["_approved"]]
    if approved.empty or declined.empty:
        return {"skipped": True, "reason": "Need both approved and declined records.", "pairs": []}
    pairs = []
    sample = declined.head(min(200, len(declined)))
    for _, row in sample.iterrows():
        cand = approved.copy()
        dist = np.zeros(len(cand))
        for col in present:
            if pd.api.types.is_numeric_dtype(work[col]):
                scale = cand[col].std() or 1.0
                dist = dist + ((cand[col] - row[col]) / scale).abs().to_numpy()
        idx = int(np.argmin(dist))
        other = cand.iloc[idx]
        if dist[idx] > 1.5:
            continue
        differs = {c: {"left": _val(row[c]), "right": _val(other[c])} for c in cos if _val(row[c]) != _val(other[c])}
        if not differs:
            continue
        pairs.append(
            {
                "mode": "matched-observation",
                "matching_distance": round(float(dist[idx]), 4),
                "limitation": "Matched on designated core features. Not economically identical.",
                "left": {
                    "title": "Declined",
                    "applicant_id": str(row.get("applicant_id", "")),
                    "p": float(row["_p"]),
                    "decision": "declined",
                    "default": int(row["default"]) if "default" in row else None,
                    "held_constant": present,
                    "differs": differs,
                },
                "right": {
                    "title": "Approved",
                    "applicant_id": str(other.get("applicant_id", "")),
                    "p": float(other["_p"]),
                    "decision": "approved",
                    "default": int(other["default"]) if "default" in other else None,
                    "held_constant": present,
                    "differs": differs,
                },
                "why": "Similar on designated core features, different on presentation-sensitive fields and decision.",
            }
        )
        if len(pairs) >= n:
            break
    if not pairs:
        return {"skipped": True, "reason": "No close observed pairs under the designated match.", "pairs": []}
    return {"skipped": False, "pairs": pairs, "method_version": "janus.integrity.twins.v1"}


def _val(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if hasattr(v, "item"):
        return v.item()
    return v
