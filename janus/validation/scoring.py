"""Resolve P(adverse event) from an estimator without assuming column index 1."""

from __future__ import annotations

import numpy as np
import pandas as pd


def class_index(estimator, positive_class=1) -> int:
    classes = getattr(estimator, "classes_", None)
    if classes is None:
        return 1
    labels = [int(c) if str(c).isdigit() else c for c in list(classes)]
    if positive_class in labels:
        return labels.index(positive_class)
    if str(positive_class) in [str(c) for c in labels]:
        return [str(c) for c in labels].index(str(positive_class))
    return 1 if len(labels) > 1 else 0


def predict_positive(estimator, frame: pd.DataFrame, features: list[str], positive_class=1) -> np.ndarray:
    missing = [f for f in features if f not in frame.columns]
    if missing:
        raise ValueError(f"Holdout is missing model features: {missing}")
    raw = estimator.predict_proba(frame[features])
    arr = np.asarray(raw, dtype=float)
    if arr.ndim == 1:
        p = arr
    else:
        p = arr[:, class_index(estimator, positive_class)]
    if not np.isfinite(p).all():
        raise ValueError("Model produced non-finite probabilities.")
    if p.min() < -1e-9 or p.max() > 1 + 1e-9:
        raise ValueError("Predicted probabilities are outside [0, 1].")
    return np.clip(p, 0.0, 1.0)
