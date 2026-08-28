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
    }
