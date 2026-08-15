"""Train the reference scorecard and choose the 0.26-class cutoff.

The model is a standard logistic scorecard on the 13 visible features.
No protected attributes. No informal / rural labels. No true income.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from janus.data_gen import FEATURES, Portfolio

TARGET_APPROVAL = 0.482
CUTOFF_GRID = np.round(np.linspace(0.12, 0.48, 73), 4)


@dataclass
class Scorecard:
    pipeline: Pipeline
    features: list[str]
    cutoff: float
    auc_holdout: float
    approval_holdout: float
    coefficients: dict[str, float]

    def predict_proba(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        frame = _as_frame(X, self.features)
        return self.pipeline.predict_proba(frame)[:, 1]

    def decide(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        return (self.predict_proba(X) < self.cutoff).astype(int)


def _as_frame(X: pd.DataFrame | np.ndarray, features: list[str]) -> pd.DataFrame:
    if isinstance(X, pd.DataFrame):
        return X[features]
    return pd.DataFrame(np.asarray(X), columns=features)


def train_scorecard(portfolio: Portfolio) -> Scorecard:
    train = portfolio.train
    holdout = portfolio.holdout
    pipe = Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "clf",
                LogisticRegression(
                    max_iter=400,
                    C=0.85,
                    solver="lbfgs",
                ),
            ),
        ]
    )
    pipe.fit(train[FEATURES], train["default"])
    p_hold = pipe.predict_proba(holdout[FEATURES])[:, 1]
    auc = float(roc_auc_score(holdout["default"], p_hold))
    cutoff = _calibrate_cutoff(p_hold, TARGET_APPROVAL)
    approval = float((p_hold < cutoff).mean())
    coef = pipe.named_steps["clf"].coef_[0]
    coefficients = {f: float(c) for f, c in zip(FEATURES, coef)}
    return Scorecard(
        pipeline=pipe,
        features=list(FEATURES),
        cutoff=float(cutoff),
        auc_holdout=auc,
        approval_holdout=approval,
        coefficients=coefficients,
    )


def _calibrate_cutoff(p: np.ndarray, target_approval: float) -> float:
    best = 0.26
    best_err = 1e9
    for c in CUTOFF_GRID:
        err = abs(float((p < c).mean()) - target_approval)
        if err < best_err:
            best_err = err
            best = float(c)
    return best


def calibrate_demo_applicant(holdout: pd.DataFrame, scorecard: Scorecard, target_p: float = 0.35) -> pd.DataFrame:
    """Nudge A-7100's presentable features so the story row is a real decline.

    Age, informal flag, recorded/true DTI, and the default label stay fixed.
    Utilization and inquiries are the only knobs — both are already in the
    applicant card.
    """
    from janus.data_gen import DEMO_ID, FEATURES

    out = holdout.copy()
    mask = out["applicant_id"] == DEMO_ID
    if not mask.any():
        return out
    loc = out.index[mask][0]
    best = None
    for util in np.linspace(0.38, 0.88, 26):
        for inq in range(0, 8):
            trial = out.loc[[loc], FEATURES].copy()
            trial["credit_utilization"] = util
            trial["credit_inquiries_12m"] = inq
            p = float(scorecard.predict_proba(trial)[0])
            if p < scorecard.cutoff:
                continue
            err = abs(p - target_p)
            if best is None or err < best[0]:
                best = (err, util, inq, p)
    if best is None:
        # Last resort: raise utilization to the bound.
        out.loc[loc, "credit_utilization"] = 0.88
        out.loc[loc, "credit_inquiries_12m"] = 7
        return out
    _, util, inq, _ = best
    out.loc[loc, "credit_utilization"] = round(float(util), 4)
    out.loc[loc, "credit_inquiries_12m"] = int(inq)
    return out


def inspect_model(scorecard: Scorecard, holdout: pd.DataFrame) -> dict:
    p = scorecard.predict_proba(holdout)
    approved = p < scorecard.cutoff
    ranked = sorted(scorecard.coefficients.items(), key=lambda kv: abs(kv[1]), reverse=True)
    return {
        "n_features": len(scorecard.features),
        "features": scorecard.features,
        "protected_attributes": [],
        "cutoff": scorecard.cutoff,
        "auc_holdout": round(scorecard.auc_holdout, 4),
        "approval_rate": round(float(approved.mean()), 4),
        "n_holdout": int(len(holdout)),
        "default_rate_holdout": round(float(holdout["default"].mean()), 4),
        "default_rate_approved": round(float(holdout.loc[approved, "default"].mean()), 4),
        "coefficients": {k: round(v, 4) for k, v in scorecard.coefficients.items()},
        "influence_rank": [{"feature": k, "coefficient": round(v, 4)} for k, v in ranked],
        "heaviest_feature": ranked[0][0],
    }
