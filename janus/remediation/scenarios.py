"""Compare remediation scenarios against a Model Health baseline."""

from __future__ import annotations

from typing import Any

import pandas as pd

from janus.remediation.transforms import apply_actions
from janus.validation.health import run_model_health


def evaluate_scenario(
    estimator,
    frame: pd.DataFrame,
    *,
    features: list[str],
    cutoff: float,
    actions: list[dict],
    target_column: str = "default",
    positive_class: int = 1,
    timestamp_column: str | None = None,
    exposure_column: str | None = None,
    segment_columns: list[str] | None = None,
    baseline: dict | None = None,
    name: str = "scenario",
    **health_kwargs: Any,
) -> dict:
    work, new_cutoff, notes = apply_actions(frame, actions, cutoff)
    result = run_model_health(
        estimator,
        work,
        features=features,
        cutoff=new_cutoff,
        target_column=target_column,
        positive_class=positive_class,
        timestamp_column=timestamp_column,
        exposure_column=exposure_column,
        segment_columns=segment_columns,
        **health_kwargs,
    )
    core = result["core_metrics"]
    delta = {}
    if baseline:
        b = baseline.get("core_metrics") or baseline
        for key in core:
            if isinstance(core[key], (int, float)) and isinstance(b.get(key), (int, float)):
                delta[key] = round(float(core[key]) - float(b[key]), 4)
    return {
        "name": name,
        "actions": actions,
        "notes": notes,
        "cutoff": new_cutoff,
        "core_metrics": core,
        "delta_from_baseline": delta,
        "conclusion": result["conclusion"],
        "label": "Input/policy sensitivity — the estimator was not retrained.",
        "attack_flip_rate": None,
        "attack_flip_limitation": "Integrity metrics are not re-estimated for V1 input transforms. Compare Model Health deltas.",
    }


def default_v1_actions(frame: pd.DataFrame, levers: list[dict], cutoff: float) -> list[tuple[str, list[dict]]]:
    """Three V1 scenario types: cutoff, cap, neutralize. Never claims retraining."""
    cosmetic = [
        r.get("feature")
        for r in (levers or [])
        if r.get("kind") in {"cosmetic", "mixed"} and r.get("feature") in frame.columns
    ]
    feat = next((c for c in cosmetic if pd.api.types.is_numeric_dtype(frame[c])), None)
    out: list[tuple[str, list[dict]]] = [
        ("Tighter cutoff (policy)", [{"type": "cutoff", "value": round(float(cutoff) * 0.8, 4)}]),
    ]
    if feat:
        q90 = float(pd.to_numeric(frame[feat], errors="coerce").quantile(0.9))
        out.append((f"Cap {feat} at 90th percentile", [{"type": "cap", "feature": feat, "value": q90}]))
        out.append((f"Neutralize {feat} (sensitivity test)", [{"type": "neutralize", "feature": feat}]))
    else:
        numeric = [c for c in frame.columns if c not in {"default", "applicant_id"} and pd.api.types.is_numeric_dtype(frame[c])]
        if numeric:
            col = numeric[0]
            out.append((f"Winsorize {col}", [{"type": "winsorize", "feature": col, "lo_q": 0.01, "hi_q": 0.99}]))
    return out[:3]
