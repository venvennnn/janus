"""Synthetic lending portfolio with documented causal mechanisms.

Every planted mechanism is named here so a finding can be traced to a
data-generating process, not an accident of noise.

Mechanisms
----------
M1  Informal-income measurement error
    Cash income is real but unrecorded. Recorded DTI = debt / documented
    income, so apparent leverage inflates. True DTI = debt / true income.
    Default is generated from *true* risk. The model only sees recorded DTI.
    Exclusion therefore follows measurement error, not repayment capacity.

M2  Rural residence as a recoverable proxy
    `is_rural` is never given to the model. `postal_density` is almost a
    deterministic function of rural status (plus light noise), so a probe
    model can reconstruct residence from model-visible features.

M3  Cosmetic / unverified features
    `savings_balance` is a self-reported snapshot. `credit_inquiries_12m`
    is a timing artefact. Both enter the scorecard. Both are cheap to
    present differently without changing repayment capacity.

M4  Broken segments
    Young self-employed applicants have *lower* true default (multiple
    income streams) but the scorecard, lacking that interaction, overstates
    their risk. A high-recorded-DTI + high-utilisation leaf understates
    risk because recorded DTI is a noisy stand-in for true leverage.

M5  Demo applicant A-7100
    Injected into the holdout so the three-route screen is a real row,
    not a slide. Age 21, informal income, recorded DTI 1.07, true DTI 0.50,
    declined, did not default.

No protected attributes (sex, race, ethnicity, religion) are generated
or modelled. `is_rural` and `is_informal` are audit labels only.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

SEED = 20260811
N_APPLICANTS = 24_000
HOLDOUT_FRACTION = 0.35  # 8,400
CUTOFF_TARGET_APPROVAL = 0.482

# Model-visible scorecard features. Length is a product constraint (13).
FEATURES = [
    "age",
    "employment_months",
    "savings_balance",
    "debt_to_income",
    "credit_inquiries_12m",
    "open_trade_lines",
    "credit_history_months",
    "postal_density",
    "credit_utilization",
    "requested_amount",
    "late_payments_24m",
    "residence_months",
    "bank_relationship_months",
]

AUDIT_LABELS = [
    "applicant_id",
    "is_informal",
    "is_rural",
    "income_true",
    "income_recorded",
    "dti_true",
    "default",
    "split",
]

DEMO_ID = "A-7100"


@dataclass(frozen=True)
class Portfolio:
    frame: pd.DataFrame
    features: list[str]
    seed: int = SEED

    @property
    def train(self) -> pd.DataFrame:
        return self.frame.loc[self.frame["split"] == "train"]

    @property
    def holdout(self) -> pd.DataFrame:
        return self.frame.loc[self.frame["split"] == "holdout"]


def _rng(seed: int = SEED) -> np.random.Generator:
    return np.random.default_rng(seed)


def generate_portfolio(n: int = N_APPLICANTS, seed: int = SEED) -> Portfolio:
    """Draw the 24k-applicant book. Mechanisms M1–M5 are applied in order."""
    rng = _rng(seed)
    age = np.clip(rng.normal(37.5, 11.5, n), 19, 71).round().astype(int)

    # Self-employment is more common among younger applicants (M4).
    se_p = np.clip(0.11 + 0.22 * (age < 30) + 0.06 * (age < 25), 0.05, 0.55)
    self_employed = rng.random(n) < se_p

    # Informal / cash-income concentration (M1). Not a default driver.
    informal_p = np.clip(
        0.22 + 0.18 * self_employed + 0.08 * (age < 26), 0.12, 0.62
    )
    is_informal = rng.random(n) < informal_p

    # Rural residence (M2). Correlated with informality, not with default.
    is_rural = rng.random(n) < (0.28 + 0.16 * is_informal)

    # Postal density is the leaked proxy: rural ≈ low density (M2).
    # Overlap is intentional — a probe should recover residence at high, not
    # perfect, AUC. The leftover error is other density variation.
    postal_density = np.where(
        is_rural,
        rng.normal(58, 22, n),
        rng.normal(168, 36, n),
    )
    postal_density = np.clip(postal_density, 8, 320).round(1)

    employment_months = np.clip(
        rng.lognormal(mean=3.4, sigma=0.85, size=n) * (0.55 + 0.45 * ~self_employed),
        0,
        360,
    ).round().astype(int)
    employment_months = np.minimum(employment_months, np.maximum(0, (age - 17) * 12))

    credit_history_months = np.clip(
        (age - 18) * 12 * rng.uniform(0.35, 0.95, n), 0, 480
    ).round().astype(int)
    bank_relationship_months = np.clip(
        credit_history_months * rng.uniform(0.25, 0.9, n), 0, 360
    ).round().astype(int)
    # Residence length is visible; self-employment is an audit label only (M4).
    # The scorecard must not be handed the dummy that would correct young
    # self-employed risk — otherwise the broken segment disappears.
    residence_months = np.clip(
        age * 12 * rng.uniform(0.15, 0.7, n) * (0.85 + 0.2 * ~is_rural),
        2,
        600,
    ).round().astype(int)

    # True income. Informal applicants earn similarly; they just document less.
    income_true = np.clip(rng.lognormal(mean=10.55, sigma=0.42, size=n), 18_000, 240_000)
    documented_share = np.where(
        is_informal,
        rng.uniform(0.30, 0.52, n),
        np.clip(rng.normal(0.98, 0.02, n), 0.90, 1.0),
    )
    income_recorded = income_true * documented_share

    # Debt stock. True DTI is the repayment-capacity object (M1).
    dti_true = np.clip(rng.beta(2.1, 3.4, n) * 0.95 + rng.normal(0, 0.04, n), 0.04, 1.15)
    debt = dti_true * income_true
    dti_recorded = np.clip(debt / np.maximum(income_recorded, 1.0), 0.04, 2.4)

    savings_balance = np.clip(
        rng.lognormal(mean=9.4, sigma=1.15, size=n) * (1.15 - 0.35 * is_informal),
        0,
        1_200_000,
    ).round(0)
    credit_inquiries_12m = np.clip(
        rng.poisson(1.7 + 0.8 * (dti_true > 0.45) + 0.4 * is_informal, n), 0, 12
    )
    open_trade_lines = np.clip(rng.poisson(3.4, n) + (age > 40).astype(int), 0, 16)
    credit_utilization = np.clip(
        rng.beta(2.2, 2.8, n) + 0.12 * (dti_true > 0.5), 0.02, 0.98
    )
    requested_amount = np.clip(
        income_true * rng.uniform(0.12, 0.55, n), 8_000, 180_000
    ).round(0)
    late_payments_24m = np.clip(
        rng.poisson(0.15 + 0.45 * (dti_true > 0.60) + 0.25 * (credit_utilization > 0.8), n),
        0,
        8,
    )

    # True default process — repayment capacity, not documentation (M1, M4).
    # Recorded DTI is a noisy image of true DTI, so a linear scorecard puts
    # most of its weight there. Late payments are kept rare so they cannot
    # steal the heaviest-feature slot.
    young_self_emp = self_employed & (age <= 29)
    hidden_stress = (dti_true > 0.62) & (credit_utilization > 0.68) & (employment_months < 18)
    logit = (
        -1.05
        + 3.55 * (dti_true - 0.34)
        + 0.70 * (credit_utilization - 0.40)
        + 0.16 * late_payments_24m
        + 0.05 * credit_inquiries_12m
        + 0.10 * ((age < 23).astype(float))
        - 0.95 * young_self_emp.astype(float)  # M4: genuinely safer
        - 0.28 * (np.log1p(savings_balance) - 9.2)
        - 0.10 * (employment_months > 24).astype(float)
        + 1.15 * hidden_stress.astype(float)  # M4: linear model understates this leaf
    )
    # Informal status and rural residence do *not* enter the default equation.
    p_default = 1 / (1 + np.exp(-logit))
    default = rng.random(n) < p_default

    applicant_id = np.array([f"A-{i:05d}" for i in range(n)])
    split = np.where(rng.random(n) < HOLDOUT_FRACTION, "holdout", "train")

    frame = pd.DataFrame(
        {
            "applicant_id": applicant_id,
            "age": age,
            "employment_months": employment_months,
            "savings_balance": savings_balance,
            "debt_to_income": dti_recorded.round(4),
            "credit_inquiries_12m": credit_inquiries_12m,
            "open_trade_lines": open_trade_lines,
            "credit_history_months": credit_history_months,
            "postal_density": postal_density,
            "credit_utilization": credit_utilization.round(4),
            "requested_amount": requested_amount,
            "late_payments_24m": late_payments_24m,
            "self_employed": self_employed.astype(int),
            "residence_months": residence_months,
            "bank_relationship_months": bank_relationship_months,
            "is_informal": is_informal.astype(int),
            "is_rural": is_rural.astype(int),
            "income_true": income_true.round(2),
            "income_recorded": income_recorded.round(2),
            "dti_true": dti_true.round(4),
            "default": default.astype(int),
            "split": split,
        }
    )
    frame = _inject_demo_applicant(frame, rng)
    return Portfolio(frame=frame.reset_index(drop=True), features=list(FEATURES), seed=seed)


def _inject_demo_applicant(frame: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Mechanism M5 — A-7100 is a designed holdout row, not a cherry-pick."""
    # Borrow a plausible informal young row as a template, then overwrite.
    proto = frame.loc[frame["is_informal"] == 1].iloc[0]
    row = proto.copy()
    income_true = 48_000.0
    dti_true = 0.50
    documented_share = 0.50 / 1.07  # recorded DTI 1.07, true DTI 0.50
    income_recorded = income_true * documented_share
    debt = dti_true * income_true

    row["applicant_id"] = DEMO_ID
    row["age"] = 21
    row["employment_months"] = 11
    row["savings_balance"] = 4_200
    row["debt_to_income"] = 1.07
    row["credit_inquiries_12m"] = 4
    row["open_trade_lines"] = 2
    row["credit_history_months"] = 14
    row["postal_density"] = 38.0
    row["credit_utilization"] = 0.66
    row["requested_amount"] = 18_000
    row["late_payments_24m"] = 0
    row["self_employed"] = 1
    row["residence_months"] = 16
    row["bank_relationship_months"] = 5
    row["is_informal"] = 1
    row["is_rural"] = 1
    row["income_true"] = income_true
    row["income_recorded"] = round(income_recorded, 2)
    row["dti_true"] = dti_true
    row["default"] = 0
    row["split"] = "holdout"
    # Keep the debt identity consistent for Route C.
    assert abs(debt / income_recorded - 1.07) < 0.02
    _ = rng  # reserved if we jitter later; keeps signature stable
    if DEMO_ID in set(frame["applicant_id"]):
        frame = frame.loc[frame["applicant_id"] != DEMO_ID]
    return pd.concat([frame, pd.DataFrame([row])], ignore_index=True)


def documented_dti(income_true: np.ndarray, income_recorded: np.ndarray, dti_recorded: np.ndarray, share: float) -> np.ndarray:
    """Recompute recorded DTI after documenting `share` of the income gap.

    share=0 leaves recorded income unchanged; share=1 sets it to true income.
    """
    gap = np.maximum(income_true - income_recorded, 0.0)
    new_income = income_recorded + share * gap
    debt = dti_recorded * income_recorded
    return np.clip(debt / np.maximum(new_income, 1.0), 0.01, 3.0)
