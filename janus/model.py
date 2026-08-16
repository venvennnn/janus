"""Anything with predict_proba. Janus never looks inside."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

AUDIT_COLUMNS = {
    "default",
    "applicant_id",
    "is_informal",
    "is_rural",
    "income_true",
    "income_recorded",
    "dti_true",
    "split",
    "true_income",
    "informal",
    "rural",
}


@dataclass
class WrappedModel:
    estimator: object
    features: list[str]
    cutoff: float
    coefficients: dict[str, float] = field(default_factory=dict)
    auc_holdout: float = 0.0

    def predict_proba(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        frame = X[self.features] if isinstance(X, pd.DataFrame) else pd.DataFrame(np.asarray(X), columns=self.features)
        raw = self.estimator.predict_proba(frame)
        if getattr(raw, "ndim", 1) == 2 and raw.shape[1] >= 2:
            return np.asarray(raw)[:, 1]
        return np.asarray(raw).reshape(-1)

    def decide(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        return (self.predict_proba(X) < self.cutoff).astype(int)


def wrap_estimator(estimator: object, holdout: pd.DataFrame, cutoff: float) -> WrappedModel:
    features = _infer_features(estimator, holdout)
    missing = [f for f in features if f not in holdout.columns]
    if missing:
        raise ValueError(f"Holdout is missing model features: {missing}")
    coef = _coefficients(estimator, features)
    if not coef:
        coef = _sensitivity(estimator, holdout, features)
    model = WrappedModel(estimator=estimator, features=features, cutoff=float(cutoff), coefficients=coef)
    if "default" in holdout.columns and holdout["default"].nunique() > 1:
        p = model.predict_proba(holdout)
        model.auc_holdout = float(roc_auc_score(holdout["default"], p))
    return model


def _infer_features(estimator: object, holdout: pd.DataFrame) -> list[str]:
    names = getattr(estimator, "feature_names_in_", None)
    if names is None and hasattr(estimator, "named_steps"):
        for step in estimator.named_steps.values():
            names = getattr(step, "feature_names_in_", None)
            if names is not None:
                break
    if names is not None:
        return [str(n) for n in names]
    numeric = holdout.select_dtypes(include=[np.number]).columns.tolist()
    return [c for c in numeric if c not in AUDIT_COLUMNS]


def _coefficients(estimator: object, features: list[str]) -> dict[str, float]:
    clf = estimator
    if hasattr(estimator, "named_steps"):
        clf = list(estimator.named_steps.values())[-1]
    coef = getattr(clf, "coef_", None)
    if coef is None:
        return {}
    flat = np.asarray(coef).reshape(-1)
    if len(flat) != len(features):
        return {}
    return {f: float(c) for f, c in zip(features, flat)}


def _sensitivity(estimator: object, holdout: pd.DataFrame, features: list[str]) -> dict[str, float]:
    """Black-box influence: mean |Δp| when a feature moves by 0.25 of its IQR."""
    probe = holdout[features].head(min(200, len(holdout))).copy()
    model = WrappedModel(estimator=estimator, features=features, cutoff=0.5)
    base = model.predict_proba(probe)
    out = {}
    for feat in features:
        trial = probe.copy()
        iqr = float(trial[feat].quantile(0.75) - trial[feat].quantile(0.25))
        step = iqr * 0.25 if iqr > 0 else 1.0
        trial[feat] = trial[feat] + step
        out[feat] = float(np.mean(np.abs(model.predict_proba(trial) - base)))
    return out


def inspect_wrapped(model: WrappedModel, holdout: pd.DataFrame) -> dict:
    p = model.predict_proba(holdout)
    approved = p < model.cutoff
    ranked = sorted(model.coefficients.items(), key=lambda kv: abs(kv[1]), reverse=True)
    return {
        "n_features": len(model.features),
        "features": model.features,
        "protected_attributes": [],
        "cutoff": model.cutoff,
        "auc_holdout": round(model.auc_holdout, 4),
        "approval_rate": round(float(approved.mean()), 4),
        "n_holdout": int(len(holdout)),
        "default_rate_holdout": round(float(holdout["default"].mean()), 4),
        "default_rate_approved": round(float(holdout.loc[approved, "default"].mean()), 4) if approved.any() else None,
        "coefficients": {k: round(v, 4) for k, v in model.coefficients.items()},
        "influence_rank": [{"feature": k, "coefficient": round(v, 4)} for k, v in ranked],
        "heaviest_feature": ranked[0][0] if ranked else model.features[0],
    }
