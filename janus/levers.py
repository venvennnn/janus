"""Feature mutability model — the load-bearing assumptions of JANUS.

These judgments are lender-specific. The values below are the *proposed*
model for the synthetic book, written as a human-confirmable table.

Two cost functions exist and are not interchangeable:

* attack  — what it costs to *present* a different value (cosmetic / fake)
* genuine — what it costs to *become* that value (earn, wait, repay)

Route C (evidence / documentation) is not a lever on a cosmetic feature.
It changes recorded DTI by making existing income visible, priced in
documentation months rather than currency.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from typing import Iterator, Literal

import numpy as np

Direction = Literal["up", "down"]
Kind = Literal["cosmetic", "genuine", "mixed", "immutable", "documentation"]


@dataclass(frozen=True)
class PathCost:
    step: float
    cost_jpy: float
    days: float
    max_delta: float
    legitimate: bool


@dataclass(frozen=True)
class Lever:
    feature: str
    kind: Kind
    direction: Direction
    lower: float
    upper: float
    attack: PathCost | None
    genuine: PathCost | None
    rationale: str

    def as_dict(self) -> dict:
        payload = asdict(self)
        return payload


# Proposed mutability model for the synthetic scorecard.
# A domain expert is expected to accept / edit this table (human gate 1).
MUTABILITY_MODEL: dict[str, Lever] = {
    "savings_balance": Lever(
        feature="savings_balance",
        kind="cosmetic",
        direction="up",
        lower=0,
        upper=400_000,
        attack=PathCost(step=14_000, cost_jpy=20, days=0.15, max_delta=28_000, legitimate=False),
        genuine=PathCost(step=14_000, cost_jpy=14_000, days=30, max_delta=70_000, legitimate=True),
        rationale="Unverified snapshot. A same-day transfer presents a higher balance; earning it takes a pay cycle.",
    ),
    "credit_inquiries_12m": Lever(
        feature="credit_inquiries_12m",
        kind="cosmetic",
        direction="down",
        lower=0,
        upper=12,
        attack=PathCost(step=1, cost_jpy=24, days=0.2, max_delta=2, legitimate=False),
        genuine=None,  # waiting is not "earn it" — excluded from the integrity-gap genuine path
        rationale="Timing artefact. Suppressing inquiries is cosmetic. Ageing them out is not a financial improvement.",
    ),
    "credit_utilization": Lever(
        feature="credit_utilization",
        kind="mixed",
        direction="down",
        lower=0.05,
        upper=0.98,
        attack=PathCost(step=0.08, cost_jpy=40, days=0.4, max_delta=0.16, legitimate=False),
        genuine=PathCost(step=0.08, cost_jpy=2_200, days=22, max_delta=0.40, legitimate=True),
        rationale="Balance can be parked on another card (cosmetic) or repaid (genuine).",
    ),
    "requested_amount": Lever(
        feature="requested_amount",
        kind="cosmetic",
        direction="down",
        lower=5_000,
        upper=180_000,
        attack=None,
        genuine=None,
        rationale="Applicant choice. Asking for less does not change capacity and is not an integrity lever.",
    ),
    "debt_to_income": Lever(
        feature="debt_to_income",
        kind="genuine",
        direction="down",
        lower=0.05,
        upper=2.4,
        attack=None,  # faking DTI is a documentation lie — not offered as Route A
        genuine=PathCost(step=0.05, cost_jpy=1_450, days=16, max_delta=0.40, legitimate=True),
        rationale="Genuine path: earn more or retire debt. Documentation of existing income is Route C, not this lever.",
    ),
    "employment_months": Lever(
        feature="employment_months",
        kind="genuine",
        direction="up",
        lower=0,
        upper=360,
        attack=None,
        genuine=None,
        rationale="Tenure only moves with time. Not priced as an earn-it lever.",
    ),
    "bank_relationship_months": Lever(
        feature="bank_relationship_months",
        kind="genuine",
        direction="up",
        lower=0,
        upper=360,
        attack=None,
        genuine=None,
        rationale="Relationship length is calendar time.",
    ),
    "late_payments_24m": Lever(
        feature="late_payments_24m",
        kind="immutable",
        direction="down",
        lower=0,
        upper=8,
        attack=None,
        genuine=None,
        rationale="Bureau history. Not legitimately editable inside an application window.",
    ),
    "credit_history_months": Lever(
        feature="credit_history_months",
        kind="immutable",
        direction="up",
        lower=0,
        upper=480,
        attack=None,
        genuine=None,
        rationale="Ages only with time beyond the audit horizon.",
    ),
    "age": Lever(
        feature="age",
        kind="immutable",
        direction="up",
        lower=19,
        upper=71,
        attack=None,
        genuine=None,
        rationale="Immutable.",
    ),
    "postal_density": Lever(
        feature="postal_density",
        kind="immutable",
        direction="up",
        lower=8,
        upper=320,
        attack=None,
        genuine=None,
        rationale="Geography. The rural proxy. Moving house is outside the recourse window.",
    ),
    "residence_months": Lever(
        feature="residence_months",
        kind="immutable",
        direction="up",
        lower=2,
        upper=600,
        attack=None,
        genuine=None,
        rationale="Time at address. Not a one-cycle lever.",
    ),
    "open_trade_lines": Lever(
        feature="open_trade_lines",
        kind="mixed",
        direction="down",
        lower=0,
        upper=16,
        attack=None,
        genuine=None,
        rationale="Closing a trade to move a score is possible but weak on this book; left inert.",
    ),
}


_LEVER_BOOK: ContextVar[dict[str, Lever] | None] = ContextVar("lever_book", default=None)


@contextmanager
def lever_book(model: dict[str, Lever]) -> Iterator[None]:
    token = _LEVER_BOOK.set(model)
    try:
        yield
    finally:
        _LEVER_BOOK.reset(token)


def active_book() -> dict[str, Lever]:
    return _LEVER_BOOK.get() or MUTABILITY_MODEL


def levers_for(mode: Literal["attack", "genuine"]) -> list[Lever]:
    out = []
    for lever in active_book().values():
        cost = lever.attack if mode == "attack" else lever.genuine
        if cost is None:
            continue
        if mode == "attack" and not cost.legitimate and lever.kind == "genuine":
            continue
        out.append(lever)
    return out


def apply_step(values: np.ndarray, lever: Lever, steps: int, mode: Literal["attack", "genuine"]) -> np.ndarray:
    cost = lever.attack if mode == "attack" else lever.genuine
    if cost is None or steps <= 0:
        return values
    delta = cost.step * steps
    if lever.direction == "down":
        delta = -delta
    updated = values + delta
    return np.clip(updated, lever.lower, lever.upper)


def mutability_table() -> list[dict]:
    rows = []
    for lever in active_book().values():
        rows.append(
            {
                "feature": lever.feature,
                "kind": lever.kind,
                "direction": lever.direction,
                "attack_cost_jpy": None if lever.attack is None else lever.attack.cost_jpy,
                "attack_days": None if lever.attack is None else lever.attack.days,
                "genuine_cost_jpy": None if lever.genuine is None else lever.genuine.cost_jpy,
                "genuine_days": None if lever.genuine is None else lever.genuine.days,
                "legitimate_attack": None if lever.attack is None else lever.attack.legitimate,
                "rationale": lever.rationale,
            }
        )
    return rows
