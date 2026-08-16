"""Assemble the findings package the demo binds to.

Used by the synthetic book (`run_audit`) and by an uploaded model
(`run_uploaded`). The agent never invents a number here.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from janus.agent import investigate
from janus.audits import (
    attack_surface,
    discover_broken_segments,
    evidence_recourse,
    gap_attribution,
    integrity_gap,
    proxy_audit,
    recourse_menu,
    unexplained_exclusion,
)
from janus.data_gen import DEMO_ID
from janus.levers import mutability_table


def pick_demo_row(holdout: pd.DataFrame, predictor) -> pd.Series:
    if "applicant_id" in holdout.columns:
        demo = holdout[holdout["applicant_id"] == DEMO_ID]
        if not demo.empty:
            return demo.iloc[0]
    p = predictor.predict_proba(holdout)
    declined = holdout.loc[p >= predictor.cutoff]
    pool = declined if not declined.empty else holdout
    if "is_informal" in pool.columns and "default" in pool.columns:
        preferred = pool[(pool["is_informal"] == 1) & (pool["default"] == 0)]
        if not preferred.empty:
            return preferred.iloc[0]
    return pool.iloc[0]


def demo_card(row: pd.Series) -> dict:
    def num(key, cast=float, default=None):
        if key not in row.index or pd.isna(row[key]):
            return default
        return cast(row[key])

    return {
        "applicant_id": str(row["applicant_id"]) if "applicant_id" in row.index else "row-0",
        "age": num("age", int),
        "is_informal": num("is_informal", int),
        "is_rural": num("is_rural", int),
        "self_employed": num("self_employed", int),
        "recorded_dti": num("debt_to_income", float),
        "true_dti": num("dti_true", float),
        "income_true": num("income_true", float),
        "income_recorded": num("income_recorded", float),
        "savings_balance": num("savings_balance", float),
        "credit_utilization": num("credit_utilization", float),
        "credit_inquiries_12m": num("credit_inquiries_12m", int),
        "default": num("default", int, 0),
    }


def build_findings_package(
    holdout: pd.DataFrame,
    predictor,
    model_info: dict,
    seed: int | None = None,
    source: str = "synthetic",
) -> dict:
    feats = list(getattr(predictor, "features", []))
    battery = {
        "attack_surface": attack_surface(holdout, predictor),
        "proxy_audit": proxy_audit(holdout, features=feats or None),
        "unexplained_exclusion": unexplained_exclusion(holdout, predictor),
        "broken_segments": discover_broken_segments(holdout, predictor),
        "integrity_gap": integrity_gap(holdout, predictor),
        "evidence_recourse": evidence_recourse(holdout, predictor),
        "gap_attribution": gap_attribution(holdout, predictor),
    }
    demo_row = pick_demo_row(holdout, predictor)
    menu = recourse_menu(demo_row, predictor, holdout)
    investigation = investigate(battery, model_info)
    return {
        "product": "JANUS",
        "version": "0.3.0",
        "source": source,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "model": model_info,
        "mutability_model": mutability_table(),
        "battery": battery,
        "demo_applicant": demo_card(demo_row),
        "recourse_menu": menu,
        "investigation": investigation,
        "figure_discipline": {
            "rule": "Only numbers from run_audit.py / integrity_gap / evidence_recourse may appear.",
            "attack_cost_medians_are_not_interchangeable": True,
            "sources": [
                "janus/run_audit.py",
                "janus/run_uploaded.py",
                "janus/audits.py",
            ],
        },
    }
