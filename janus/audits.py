"""Deterministic audit battery. The agent never computes a figure here."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text

from janus.counterfactual import greedy_paths
from janus.data_gen import FEATURES, documented_dti
from janus.scorecard import Scorecard

Predictor = Scorecard  # Scorecard and WrappedModel share predict_proba / cutoff / features


def attack_surface(
    holdout: pd.DataFrame,
    scorecard: Scorecard,
    n: int = 300,
    budget_jpy: float = 60_000,
    seed: int = 2026,
) -> dict:
    declined = _declined(holdout, scorecard)
    baseline_default = float(holdout["default"].mean())
    if declined.empty:
        return {
            "run_id": "run.attack_surface",
            "skipped": True,
            "reason": "No declined applicants at this cutoff.",
            "n_sampled": 0,
            "n_flipped": 0,
            "flip_rate": 0.0,
            "median_cost_jpy": None,
            "p90_cost_jpy": None,
            "budget_jpy": budget_jpy,
            "flipped_default_rate": None,
            "baseline_default_rate": round(baseline_default, 4),
            "gamed_worse_than_baseline": False,
            "would_not_have_defaulted": None,
            "flipped_applicant_ids": [],
        }
    sample = declined.sample(n=min(n, len(declined)), random_state=seed)
    paths = greedy_paths(sample, scorecard, mode="attack", budget_jpy=budget_jpy)
    flipped = paths.flipped
    costs = paths.cost_jpy[flipped]
    if "applicant_id" in sample.columns:
        flipped_ids = sample.loc[flipped, "applicant_id"].astype(str).tolist()
    else:
        flipped_ids = [str(i) for i in sample.index[flipped].tolist()]
    flipped_default = float(sample.loc[flipped, "default"].mean()) if flipped.any() else None
    return {
        "run_id": "run.attack_surface",
        "n_sampled": int(len(sample)),
        "n_flipped": int(flipped.sum()),
        "flip_rate": round(float(flipped.mean()), 4),
        "median_cost_jpy": _median(costs),
        "p90_cost_jpy": _p90(costs),
        "budget_jpy": budget_jpy,
        "flipped_default_rate": None if flipped_default is None else round(flipped_default, 4),
        "baseline_default_rate": round(baseline_default, 4),
        "gamed_worse_than_baseline": bool(
            flipped_default is not None and flipped_default > baseline_default
        ),
        "would_not_have_defaulted": round(float(1 - sample.loc[flipped, "default"].mean()), 4)
        if flipped.any()
        else None,
        "flipped_applicant_ids": flipped_ids[:25],
    }


def integrity_gap(
    holdout: pd.DataFrame,
    scorecard: Scorecard,
    n: int = 250,
    budget_jpy: float = 80_000,
    seed: int = 2026,
) -> dict:
    declined = _declined(holdout, scorecard)
    if declined.empty:
        return {
            "run_id": "run.integrity_gap",
            "skipped": True,
            "reason": "No declined applicants at this cutoff.",
            "n_sampled": 0,
            "n_dual_flip": 0,
            "median_attack_cost_jpy": None,
            "median_genuine_cost_jpy": None,
            "median_genuine_days": None,
            "median_gap_ratio": None,
            "note": "Median of per-applicant (genuine/attack) ratios. Not the ratio of medians.",
            "attack_flip_rate": None,
            "genuine_flip_rate": None,
            "would_not_have_defaulted_among_gameable": None,
        }
    sample = declined.sample(n=min(n, len(declined)), random_state=seed)
    attack = greedy_paths(sample, scorecard, mode="attack", budget_jpy=budget_jpy)
    genuine = greedy_paths(sample, scorecard, mode="genuine", budget_jpy=budget_jpy)
    both = attack.flipped & genuine.flipped
    if not both.any():
        ratios = np.array([])
    else:
        ratios = genuine.cost_jpy[both] / np.maximum(attack.cost_jpy[both], 1.0)
    attack_costs = attack.cost_jpy[attack.flipped]
    genuine_costs = genuine.cost_jpy[genuine.flipped]
    genuine_days = genuine.days[genuine.flipped]
    return {
        "run_id": "run.integrity_gap",
        "n_sampled": int(len(sample)),
        "n_dual_flip": int(both.sum()),
        "median_attack_cost_jpy": _median(attack_costs),
        "median_genuine_cost_jpy": _median(genuine_costs),
        "median_genuine_days": _median(genuine_days),
        "median_gap_ratio": _median(ratios),
        "note": "Median of per-applicant (genuine/attack) ratios. Not the ratio of medians. "
        "Not interchangeable with attack_surface.median_cost_jpy.",
        "attack_flip_rate": round(float(attack.flipped.mean()), 4),
        "genuine_flip_rate": round(float(genuine.flipped.mean()), 4),
        "would_not_have_defaulted_among_gameable": round(
            float(1 - sample.loc[attack.flipped, "default"].mean()), 4
        )
        if attack.flipped.any()
        else None,
    }


def evidence_recourse(holdout: pd.DataFrame, scorecard: Predictor) -> dict:
    needed = {"income_true", "income_recorded", "debt_to_income"}
    if not needed.issubset(holdout.columns):
        return {
            "run_id": "run.evidence_recourse",
            "skipped": True,
            "reason": "Route C needs a recorded/true income gap. On real data that gap must be estimated from cash-flow evidence. Until then this is a directional signal, not the clean demo figure.",
            "n_declined_informal": 0,
            "median_recorded_dti": None,
            "median_true_dti": None,
            "cross_rate_full_documentation": None,
            "n_cross_full": 0,
            "cross_default_rate": None,
            "portfolio_default_rate": round(float(holdout["default"].mean()), 4),
            "cross_rate_among_non_default": None,
            "n_informal_non_default": 0,
            "documentation_curve": [],
            "priced_in": "documentation_months",
            "median_documentation_months": 6,
            "cost_jpy": 0,
        }
    declined = _declined(holdout, scorecard)
    informal = declined
    if "is_informal" in declined.columns:
        informal = declined.loc[declined["is_informal"] == 1].copy()
    if informal.empty:
        informal = declined.copy()
    shares = (0.25, 0.50, 0.75, 1.00)
    curve = []
    X = informal[scorecard.features].copy()
    p0 = scorecard.predict_proba(X)
    for share in shares:
        trial = X.copy()
        trial["debt_to_income"] = documented_dti(
            informal["income_true"].to_numpy(),
            informal["income_recorded"].to_numpy(),
            informal["debt_to_income"].to_numpy(),
            share,
        )
        p = scorecard.predict_proba(trial)
        crossed = p < scorecard.cutoff
        curve.append(
            {
                "documented_share": share,
                "cross_rate": round(float(crossed.mean()), 4),
                "n_cross": int(crossed.sum()),
            }
        )
    full = curve[-1]
    trial = X.copy()
    trial["debt_to_income"] = documented_dti(
        informal["income_true"].to_numpy(),
        informal["income_recorded"].to_numpy(),
        informal["debt_to_income"].to_numpy(),
        1.0,
    )
    p1 = scorecard.predict_proba(trial)
    crossed = p1 < scorecard.cutoff
    cross_default = float(informal.loc[crossed, "default"].mean()) if crossed.any() else None
    non_def = informal["default"] == 0
    cross_among_good = float(crossed[non_def].mean()) if non_def.any() else None
    recorded_dti = float(informal["debt_to_income"].median())
    if "dti_true" in informal.columns:
        true_dti = float(informal["dti_true"].median())
    else:
        true_dti = float(np.median(trial["debt_to_income"].to_numpy()))
    return {
        "run_id": "run.evidence_recourse",
        "n_declined_informal": int(len(informal)),
        "median_recorded_dti": round(recorded_dti, 4),
        "median_true_dti": round(true_dti, 4),
        "cross_rate_full_documentation": full["cross_rate"],
        "n_cross_full": full["n_cross"],
        "cross_default_rate": None if cross_default is None else round(cross_default, 4),
        "portfolio_default_rate": round(float(holdout["default"].mean()), 4),
        "cross_rate_among_non_default": None
        if cross_among_good is None
        else round(cross_among_good, 4),
        "n_informal_non_default": int(non_def.sum()),
        "documentation_curve": curve,
        "priced_in": "documentation_months",
        "median_documentation_months": 6,
        "cost_jpy": 0,
        "mean_p_start": round(float(p0.mean()), 4),
        "mean_p_documented": round(float(p1.mean()), 4),
    }


def proxy_audit(holdout: pd.DataFrame, features: list[str] | None = None) -> dict:
    target = next((c for c in ("is_rural", "rural") if c in holdout.columns), None)
    feats = features or [c for c in FEATURES if c in holdout.columns]
    if target is None or holdout[target].nunique() < 2:
        return {
            "run_id": "run.proxy_audit",
            "skipped": True,
            "reason": "No held-out residence label. Proxy reconstruction needs a sensitive attribute the model was not trained on.",
            "target": None,
            "given_to_model": False,
            "probe_auc": None,
            "n": int(len(holdout)),
            "base_rate": None,
            "carriers": [],
            "chief_carrier": None,
        }
    y = holdout[target].to_numpy()
    X = holdout[feats]
    pipe = Pipeline(
        [
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(max_iter=400)),
        ]
    )
    pipe.fit(X, y)
    p = pipe.predict_proba(X)[:, 1]
    auc = float(roc_auc_score(y, p))
    coef = pipe.named_steps["clf"].coef_[0]
    ranked = sorted(zip(feats, coef), key=lambda kv: abs(kv[1]), reverse=True)
    return {
        "run_id": "run.proxy_audit",
        "target": target,
        "given_to_model": False,
        "probe_auc": round(auc, 4),
        "n": int(len(holdout)),
        "base_rate": round(float(y.mean()), 4),
        "carriers": [{"feature": f, "coefficient": round(float(c), 4)} for f, c in ranked[:5]],
        "chief_carrier": ranked[0][0],
        "skipped": False,
    }


def unexplained_exclusion(holdout: pd.DataFrame, scorecard: Scorecard) -> dict:
    p = scorecard.predict_proba(holdout)
    approved = p < scorecard.cutoff
    frame = holdout.assign(approved=approved)
    if "is_informal" in frame.columns:
        informal = frame["is_informal"] == 1
        segment = "is_informal"
    elif "income_source" in frame.columns:
        informal = frame["income_source"].astype(str).str.lower() == "informal"
        segment = "income_source"
    else:
        return {
            "run_id": "run.unexplained_exclusion",
            "skipped": True,
            "reason": "No informal-income label (is_informal or income_source). Exclusion needs a segment the model was not trained on.",
            "segment": None,
            "n_informal": 0,
            "n_formal": 0,
            "approval_informal": None,
            "approval_formal": None,
            "approval_gap_pp": None,
            "default_informal": None,
            "default_formal": None,
            "default_gap_pp": None,
            "mechanism": None,
        }
    formal = ~informal
    if informal.sum() < 80 or formal.sum() < 80:
        return {
            "run_id": "run.unexplained_exclusion",
            "skipped": True,
            "reason": "Not enough informal/formal rows to compare approval against default.",
            "segment": segment,
            "n_informal": int(informal.sum()),
            "n_formal": int(formal.sum()),
            "approval_informal": None,
            "approval_formal": None,
            "approval_gap_pp": None,
            "default_informal": None,
            "default_formal": None,
            "default_gap_pp": None,
            "mechanism": None,
        }
    appr_i = float(frame.loc[informal, "approved"].mean())
    appr_f = float(frame.loc[formal, "approved"].mean())
    def_i = float(frame.loc[informal, "default"].mean())
    def_f = float(frame.loc[formal, "default"].mean())
    return {
        "run_id": "run.unexplained_exclusion",
        "segment": segment,
        "n_informal": int(informal.sum()),
        "n_formal": int(formal.sum()),
        "approval_informal": round(appr_i, 4),
        "approval_formal": round(appr_f, 4),
        "approval_gap_pp": round((appr_f - appr_i) * 100, 2),
        "default_informal": round(def_i, 4),
        "default_formal": round(def_f, 4),
        "default_gap_pp": round((def_i - def_f) * 100, 2),
        "mechanism": "Cash income unrecorded → recorded DTI inflates → DTI is the heaviest feature.",
        "skipped": False,
    }


def discover_broken_segments(holdout: pd.DataFrame, scorecard: Scorecard, min_leaf: int = 120) -> dict:
    feats = [f for f in scorecard.features if f in holdout.columns]
    if len(holdout) < 80 or len(feats) < 2:
        return {
            "run_id": "run.discover_segments",
            "skipped": True,
            "reason": "Not enough rows or model features to grow a residual tree.",
            "tree": "",
            "leaves": [],
            "worst_understated": None,
            "young_self_employed": {"n": 0, "predicted_default": None, "actual_default": None, "approval_rate": None},
        }
    p = scorecard.predict_proba(holdout)
    residual = holdout["default"].to_numpy() - p
    y = (residual > 0.08).astype(int)
    leaf_n = min(min_leaf, max(40, len(holdout) // 10))
    tree = DecisionTreeClassifier(max_depth=3, min_samples_leaf=leaf_n, random_state=7)
    tree.fit(holdout[feats], y)
    leaf = tree.apply(holdout[feats])
    rows = []
    for lid in np.unique(leaf):
        mask = leaf == lid
        if mask.sum() < leaf_n:
            continue
        pred = float(p[mask].mean())
        actual = float(holdout.loc[mask, "default"].mean())
        appr = float((p[mask] < scorecard.cutoff).mean())
        rows.append(
            {
                "leaf": int(lid),
                "n": int(mask.sum()),
                "predicted_default": round(pred, 4),
                "actual_default": round(actual, 4),
                "gap_pp": round((actual - pred) * 100, 2),
                "approval_rate": round(appr, 4),
                "kind": "understated" if actual - pred > 0.04 else "overstated" if pred - actual > 0.04 else "calibrated",
            }
        )
    rows.sort(key=lambda r: abs(r["gap_pp"]), reverse=True)
    young = {"n": 0, "predicted_default": None, "actual_default": None, "approval_rate": None}
    if "age" in holdout.columns and "self_employed" in holdout.columns:
        young_se = (holdout["age"] <= 29) & (holdout["self_employed"] == 1)
        young = {
            "n": int(young_se.sum()),
            "predicted_default": round(float(p[young_se].mean()), 4) if young_se.any() else None,
            "actual_default": round(float(holdout.loc[young_se, "default"].mean()), 4) if young_se.any() else None,
            "approval_rate": round(float((p[young_se] < scorecard.cutoff).mean()), 4) if young_se.any() else None,
        }
    return {
        "run_id": "run.discover_segments",
        "tree": export_text(tree, feature_names=feats, max_depth=3),
        "leaves": rows[:8],
        "worst_understated": max((r for r in rows if r["gap_pp"] > 0), key=lambda r: r["gap_pp"], default=None),
        "young_self_employed": young,
        "skipped": False,
    }


def gap_attribution(holdout: pd.DataFrame, scorecard: Scorecard) -> dict:
    """Integrity-gap attribution by feature group — not willingness/ability/macro."""
    groups = {
        "leverage_and_income": ["debt_to_income", "requested_amount"],
        "presentable_balances": ["savings_balance", "credit_utilization"],
        "bureau_timing": ["credit_inquiries_12m", "open_trade_lines", "late_payments_24m"],
        "tenure": ["employment_months", "credit_history_months", "bank_relationship_months", "age", "residence_months"],
        "geography_proxy": ["postal_density"],
    }
    coef = getattr(scorecard, "coefficients", {}) or {}
    total = sum(abs(v) for v in coef.values()) or 1.0
    used = set()
    out = []
    for name, feats in groups.items():
        present = [f for f in feats if f in coef]
        if not present:
            continue
        used.update(present)
        out.append(
            {
                "group": name,
                "features": present,
                "abs_coefficient_share": round(sum(abs(coef[f]) for f in present) / total, 4),
            }
        )
    leftover = [f for f in coef if f not in used]
    if leftover:
        out.append(
            {
                "group": "other",
                "features": leftover,
                "abs_coefficient_share": round(sum(abs(coef[f]) for f in leftover) / total, 4),
            }
        )
    return {
        "run_id": "run.gap_attribution",
        "groups": out,
        "note": "Share of |coefficient| mass. Real scorecards are not willingness/ability/macro.",
    }


def recourse_menu(
    row: pd.Series,
    scorecard: Scorecard,
    holdout: pd.DataFrame,
    attack_budget: float = 60_000,
    genuine_budget: float = 80_000,
) -> dict:
    from janus.counterfactual import path_for_row

    p = float(scorecard.predict_proba(pd.DataFrame([row]))[0])
    route_a = path_for_row(row, scorecard, "attack", attack_budget)
    route_b = path_for_row(row, scorecard, "genuine", genuine_budget)
    # Diverse Route B: forbid the first-chosen lever, then the top two.
    route_b_alt = []
    forbidden: set[str] = set()
    if route_b.get("first_feature"):
        forbidden.add(route_b["first_feature"])
        alt1 = path_for_row(row, scorecard, "genuine", genuine_budget, forbidden=forbidden)
        route_b_alt.append(alt1)
        if alt1.get("first_feature"):
            forbidden.add(alt1["first_feature"])
            route_b_alt.append(
                path_for_row(row, scorecard, "genuine", genuine_budget, forbidden=forbidden)
            )

    # Route C — document existing income. Needs a recorded/true income gap.
    can_document = (
        "debt_to_income" in scorecard.features
        and "income_true" in row.index
        and "income_recorded" in row.index
        and pd.notna(row["income_true"])
        and pd.notna(row["income_recorded"])
    )
    if can_document:
        trial = pd.DataFrame([row])[scorecard.features].copy()
        trial["debt_to_income"] = documented_dti(
            np.array([row["income_true"]]),
            np.array([row["income_recorded"]]),
            np.array([row["debt_to_income"]]),
            1.0,
        )
        p_c = float(scorecard.predict_proba(trial)[0])
        dti_true = float(row["dti_true"]) if "dti_true" in row.index else float(trial["debt_to_income"].iloc[0])
        route_c = {
            "flipped": p_c < scorecard.cutoff,
            "cost_jpy": 0.0,
            "days": 180.0,
            "documentation_months": 6,
            "p_start": p,
            "p_final": p_c,
            "dti_start": float(row["debt_to_income"]),
            "dti_final": float(trial["debt_to_income"].iloc[0]),
            "dti_true": dti_true,
            "features": ["debt_to_income"],
            "ask": "Change nothing. Make existing income visible.",
            "skipped": False,
        }
    else:
        route_c = {
            "flipped": False,
            "cost_jpy": 0.0,
            "days": 0.0,
            "documentation_months": None,
            "p_start": p,
            "p_final": p,
            "dti_start": float(row["debt_to_income"]) if "debt_to_income" in row.index else None,
            "dti_final": None,
            "dti_true": None,
            "features": [],
            "ask": "Route C needs a recorded/true income gap, estimated from cash-flow on real data.",
            "skipped": True,
        }
    genuine_options = [route_b, *route_b_alt]
    flipped_genuine = [g for g in genuine_options if g.get("flipped")]
    if flipped_genuine:
        route_b = min(flipped_genuine, key=lambda g: (g["cost_jpy"], g["days"]))
        route_b_alt = [g for g in genuine_options if g is not route_b]
    return {
        "run_id": "run.recourse_menu",
        "applicant_id": str(row["applicant_id"]) if "applicant_id" in row.index else "row-0",
        "p_start": p,
        "cutoff": scorecard.cutoff,
        "declined": p >= scorecard.cutoff,
        "default": int(row["default"]),
        "route_a_fake_it": {**route_a, "audience": "model_owner_only"},
        "route_b_earn_it": route_b,
        "route_b_alternatives": route_b_alt,
        "route_c_document_it": route_c,
    }


def _declined(holdout: pd.DataFrame, scorecard: Scorecard) -> pd.DataFrame:
    p = scorecard.predict_proba(holdout)
    return holdout.loc[p >= scorecard.cutoff].copy()


def _median(x: np.ndarray) -> float | None:
    if x is None or len(x) == 0:
        return None
    return round(float(np.median(x)), 2)


def _p90(x: np.ndarray) -> float | None:
    if x is None or len(x) == 0:
        return None
    return round(float(np.quantile(x, 0.9)), 2)
