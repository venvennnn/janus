"""Safe V1 input transforms. These do not retrain the model."""

from __future__ import annotations

import pandas as pd


def apply_actions(frame: pd.DataFrame, actions: list[dict], cutoff: float) -> tuple[pd.DataFrame, float, list[str]]:
    work = frame.copy()
    notes = []
    new_cutoff = cutoff
    for action in actions:
        kind = action.get("type")
        col = action.get("feature")
        if kind == "cutoff":
            new_cutoff = float(action["value"])
            notes.append(f"Cutoff set to {new_cutoff}. This is a policy change, not a retrained model.")
            continue
        if not col or col not in work.columns:
            notes.append(f"Skipped {kind} on {col}: column missing.")
            continue
        if kind == "cap":
            work[col] = work[col].clip(upper=float(action["value"]))
            notes.append(f"Capped {col} at {action['value']}. Sensitivity test on inputs, not a retrained model.")
        elif kind == "floor":
            work[col] = work[col].clip(lower=float(action["value"]))
            notes.append(f"Floored {col} at {action['value']}. Sensitivity test on inputs, not a retrained model.")
        elif kind == "winsorize":
            lo_q = float(action.get("lo_q", 0.01))
            hi_q = float(action.get("hi_q", 0.99))
            lo, hi = work[col].quantile(lo_q), work[col].quantile(hi_q)
            work[col] = work[col].clip(lo, hi)
            notes.append(f"Winsorized {col} to empirical {lo_q}-{hi_q} quantiles. Sensitivity test, not a retrained model.")
        elif kind == "replace":
            src = action.get("source")
            if src in work.columns:
                work[col] = work[src]
                notes.append(f"Replaced {col} with corroborated {src}. Not a retrained model.")
            else:
                notes.append(f"Replace skipped: {src} is not in the dataset.")
        elif kind == "neutralize":
            work[col] = work[col].median()
            notes.append(f"Neutralized {col} to its median. Sensitivity test, not a production challenger.")
        elif kind == "manual_review_flag":
            notes.append("Manual-review rule recorded as a policy overlay. Volume is estimated; the model is unchanged.")
        else:
            notes.append(f"Unknown action {kind} ignored.")
    return work, new_cutoff, notes
