"""Propose a mutability table from a feature dictionary. A human must confirm."""

from __future__ import annotations

import re

import pandas as pd

from janus.levers import Lever, PathCost, mutability_table
from janus.model import AUDIT_COLUMNS

_COSMETIC = re.compile(
    r"snapshot|self[- ]?report|unverified|screenshot|stated|declared|inquir",
    re.I,
)
_GENUINE = re.compile(r"income|dti|debt.to.income|repay|earn|tenure|employment", re.I)
_IMMUTABLE = re.compile(r"\bage\b|history|late.?pay|bureau|postal|density|rural|sex|gender", re.I)
_UTIL = re.compile(r"utili[sz]ation|revolving", re.I)
_SAVINGS = re.compile(r"saving|balance|deposit|liquidity", re.I)
_DTI = re.compile(r"dti|debt.to.income", re.I)


def propose_mutability(
    features: list[str],
    holdout: pd.DataFrame,
    dictionary: str = "",
    context: str = "",
) -> list[dict]:
    """Heuristic proposal. The operator edits this before search runs."""
    blob = f"{dictionary}\n{context}"
    rows = []
    for feat in features:
        if feat in AUDIT_COLUMNS:
            continue
        text = _entry(blob, feat)
        series = holdout[feat] if feat in holdout.columns else None
        lo, hi, step = _bounds(series)
        kind, direction, attack, genuine, rationale = _classify(feat, text, step, lo, hi)
        rows.append(
            Lever(
                feature=feat,
                kind=kind,
                direction=direction,
                lower=lo,
                upper=hi,
                attack=attack,
                genuine=genuine,
                rationale=rationale,
            )
        )
    if not rows:
        return mutability_table()
    return [
        {
            "feature": lv.feature,
            "kind": lv.kind,
            "direction": lv.direction,
            "lower": lv.lower,
            "upper": lv.upper,
            "attack_step": None if lv.attack is None else lv.attack.step,
            "attack_cost_jpy": None if lv.attack is None else lv.attack.cost_jpy,
            "attack_days": None if lv.attack is None else lv.attack.days,
            "attack_max_delta": None if lv.attack is None else lv.attack.max_delta,
            "legitimate_attack": None if lv.attack is None else lv.attack.legitimate,
            "genuine_step": None if lv.genuine is None else lv.genuine.step,
            "genuine_cost_jpy": None if lv.genuine is None else lv.genuine.cost_jpy,
            "genuine_days": None if lv.genuine is None else lv.genuine.days,
            "genuine_max_delta": None if lv.genuine is None else lv.genuine.max_delta,
            "rationale": lv.rationale,
        }
        for lv in rows
    ]


def rows_to_levers(rows: list[dict]) -> dict[str, Lever]:
    book = {}
    for row in rows:
        attack = _cost(
            row.get("attack_step"),
            row.get("attack_cost_jpy"),
            row.get("attack_days"),
            row.get("attack_max_delta"),
            bool(row.get("legitimate_attack") or False),
        )
        genuine = _cost(
            row.get("genuine_step"),
            row.get("genuine_cost_jpy"),
            row.get("genuine_days"),
            row.get("genuine_max_delta"),
            True,
        )
        book[row["feature"]] = Lever(
            feature=row["feature"],
            kind=row.get("kind") or "mixed",
            direction=row.get("direction") or "up",
            lower=float(row.get("lower") or 0),
            upper=float(row.get("upper") or 1),
            attack=attack,
            genuine=genuine,
            rationale=row.get("rationale") or "",
        )
    return book


def _cost(step, cost, days, max_delta, legitimate) -> PathCost | None:
    if step is None or cost is None:
        return None
    return PathCost(
        step=float(step),
        cost_jpy=float(cost),
        days=float(days or 1),
        max_delta=float(max_delta if max_delta is not None else float(step) * 3),
        legitimate=bool(legitimate),
    )


def _entry(blob: str, feat: str) -> str:
    if not blob.strip():
        return feat
    pattern = re.compile(rf"{re.escape(feat)}.*", re.I)
    hits = [line for line in blob.splitlines() if pattern.search(line)]
    return " ".join(hits) if hits else f"{feat} {blob[:400]}"


def _bounds(series: pd.Series | None) -> tuple[float, float, float]:
    if series is None or series.empty:
        return 0.0, 1.0, 0.1
    lo = float(series.quantile(0.01))
    hi = float(series.quantile(0.99))
    if lo == hi:
        hi = lo + 1.0
    step = (hi - lo) / 12.0
    return lo, hi, step


def _classify(feat: str, text: str, step: float, lo: float, hi: float):
    blob = f"{feat} {text}"
    max_delta = step * 3
    if _IMMUTABLE.search(blob) and not _SAVINGS.search(blob):
        return "immutable", "up", None, None, f"{feat}: treated as outside the application window."
    if _DTI.search(blob):
        genuine = PathCost(step=step, cost_jpy=1_450, days=16, max_delta=max_delta, legitimate=True)
        return (
            "genuine",
            "down",
            None,
            genuine,
            f"{feat}: genuine path is earn/repay. Documentation of existing income is Route C, not this lever.",
        )
    if _SAVINGS.search(blob) or _COSMETIC.search(blob):
        attack = PathCost(step=step, cost_jpy=20, days=0.2, max_delta=max_delta, legitimate=False)
        genuine = PathCost(step=step, cost_jpy=max(step, 1_000), days=28, max_delta=max_delta, legitimate=True)
        return (
            "cosmetic",
            "up",
            attack,
            genuine,
            f"{feat}: dictionary suggests a presentable or unverified value. Cheap to show, expensive to earn.",
        )
    if _UTIL.search(blob):
        attack = PathCost(step=step, cost_jpy=40, days=0.4, max_delta=max_delta, legitimate=False)
        genuine = PathCost(step=step, cost_jpy=2_200, days=22, max_delta=max_delta, legitimate=True)
        return "mixed", "down", attack, genuine, f"{feat}: can be parked (cosmetic) or repaid (genuine)."
    if _GENUINE.search(blob):
        genuine = PathCost(step=step, cost_jpy=1_200, days=20, max_delta=max_delta, legitimate=True)
        return "genuine", "down" if "debt" in feat.lower() else "up", None, genuine, f"{feat}: moves with real financial change."
    return (
        "mixed",
        "up",
        PathCost(step=step, cost_jpy=30, days=0.5, max_delta=max_delta, legitimate=False),
        PathCost(step=step, cost_jpy=2_000, days=21, max_delta=max_delta, legitimate=True),
        f"{feat}: no clear dictionary cue. Proposed as mixed — edit before confirming.",
    )
