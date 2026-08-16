"""Vectorized counterfactual search.

Each greedy step evaluates every remaining (applicant × lever) candidate
in one `predict_proba` call. This is the P0 fix: single-row scoring was
~515× slower than the batched marginal cost.

Greedy coordinate descent returns one path by construction. Diverse
Route-B options re-run with the first-chosen lever forbidden, then the
top two forbidden.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd

from janus.levers import Lever, apply_step, levers_for
from janus.scorecard import Scorecard

Mode = Literal["attack", "genuine"]


@dataclass
class PathResult:
    flipped: np.ndarray
    cost_jpy: np.ndarray
    days: np.ndarray
    steps: np.ndarray
    p_final: np.ndarray
    p_start: np.ndarray
    used_features: list[list[str]] = field(default_factory=list)
    first_feature: list[str | None] = field(default_factory=list)


def greedy_paths(
    X: pd.DataFrame,
    scorecard: Scorecard,
    mode: Mode,
    budget_jpy: float,
    max_steps: int = 12,
    forbidden: set[str] | None = None,
    step_cap: int = 4,
) -> PathResult:
    """Greedy descent on declined-looking rows. Scores candidates in batch."""
    features = scorecard.features
    work = X[features].to_numpy(dtype=float, copy=True)
    n = len(work)
    levers = [
        lv
        for lv in levers_for(mode)
        if lv.feature not in (forbidden or set()) and lv.feature in features
    ]
    if not levers:
        p = scorecard.predict_proba(work)
        return PathResult(
            flipped=p < scorecard.cutoff,
            cost_jpy=np.zeros(n),
            days=np.zeros(n),
            steps=np.zeros(n, dtype=int),
            p_final=p,
            p_start=p,
            used_features=[[] for _ in range(n)],
            first_feature=[None] * n,
        )

    origin = work.copy()
    p = scorecard.predict_proba(work)
    p_start = p.copy()
    cost = np.zeros(n, dtype=float)
    days = np.zeros(n, dtype=float)
    steps = np.zeros(n, dtype=int)
    used: list[list[str]] = [[] for _ in range(n)]
    first: list[str | None] = [None] * n
    remaining = np.full(n, True)

    for _ in range(max_steps):
        active = remaining & (p >= scorecard.cutoff) & (cost < budget_jpy)
        if not active.any():
            break
        idx = np.flatnonzero(active)
        block, meta = _candidate_block(work[idx], origin[idx], levers, mode, step_cap, features)
        p_cand = scorecard.predict_proba(block)
        n_lev = len(levers)
        p_cand = p_cand.reshape(len(idx), n_lev, step_cap)
        # Improvement per yen; infeasible (zero-change / over-budget) → -inf
        p_now = p[idx][:, None, None]
        gain = p_now - p_cand
        step_cost = np.array(
            [
                [(lv.attack if mode == "attack" else lv.genuine).cost_jpy * s for s in range(1, step_cap + 1)]
                for lv in levers
            ],
            dtype=float,
        )
        step_days = np.array(
            [
                [(lv.attack if mode == "attack" else lv.genuine).days * s for s in range(1, step_cap + 1)]
                for lv in levers
            ],
            dtype=float,
        )
        # Detect no-ops (already at bound)
        changed = np.abs(block.reshape(len(idx), n_lev, step_cap, -1) - work[idx][:, None, None, :]).sum(axis=-1) > 1e-9
        afford = (cost[idx][:, None, None] + step_cost[None, :, :]) <= budget_jpy
        score = np.where(changed & afford & (gain > 1e-6), gain / np.maximum(step_cost, 1e-6), -np.inf)
        flat = score.reshape(len(idx), -1)
        best_flat = flat.argmax(axis=1)
        best_val = flat.max(axis=1)
        take = best_val > 0
        if not take.any():
            remaining[idx] = False
            continue
        chosen_idx = idx[take]
        chosen_flat = best_flat[take]
        lev_i = chosen_flat // step_cap
        stp_i = chosen_flat % step_cap + 1
        for local, row_i, li, si in zip(np.flatnonzero(take), chosen_idx, lev_i, stp_i):
            lever = levers[int(li)]
            feat_i = features.index(lever.feature)
            proposed = apply_step(
                np.array([work[row_i, feat_i]]), lever, int(si), mode
            )[0]
            work[row_i, feat_i] = _respect_max_delta(origin[row_i, feat_i], proposed, lever, mode)
            pc = (lever.attack if mode == "attack" else lever.genuine)
            cost[row_i] += pc.cost_jpy * int(si)
            days[row_i] += pc.days * int(si)
            steps[row_i] += int(si)
            if lever.feature not in used[row_i]:
                used[row_i].append(lever.feature)
            if first[row_i] is None:
                first[row_i] = lever.feature
        p = scorecard.predict_proba(work)
        remaining[idx[~take]] = False

    return PathResult(
        flipped=p < scorecard.cutoff,
        cost_jpy=cost,
        days=days,
        steps=steps,
        p_final=p,
        p_start=p_start,
        used_features=used,
        first_feature=first,
    )


def _candidate_block(
    base: np.ndarray,
    origin: np.ndarray,
    levers: list[Lever],
    mode: Mode,
    step_cap: int,
    features: list[str],
) -> tuple[np.ndarray, list[tuple[int, int]]]:
    n, p = base.shape
    block = np.repeat(base, len(levers) * step_cap, axis=0)
    meta: list[tuple[int, int]] = []
    cursor = 0
    for i in range(n):
        for lever in levers:
            col = features.index(lever.feature)
            for s in range(1, step_cap + 1):
                proposed = apply_step(np.array([base[i, col]]), lever, s, mode)[0]
                block[cursor, col] = _respect_max_delta(origin[i, col], proposed, lever, mode)
                meta.append((i, s))
                cursor += 1
    return block, meta


def _respect_max_delta(original: float, proposed: float, lever: Lever, mode: Mode) -> float:
    cost = lever.attack if mode == "attack" else lever.genuine
    if cost is None:
        return float(original)
    lo = max(lever.lower, original - cost.max_delta)
    hi = min(lever.upper, original + cost.max_delta)
    return float(np.clip(proposed, lo, hi))


def path_for_row(
    row: pd.Series,
    scorecard: Scorecard,
    mode: Mode,
    budget_jpy: float,
    forbidden: set[str] | None = None,
) -> dict:
    X = pd.DataFrame([row])
    result = greedy_paths(X, scorecard, mode, budget_jpy, forbidden=forbidden)
    return {
        "flipped": bool(result.flipped[0]),
        "cost_jpy": float(result.cost_jpy[0]),
        "days": float(result.days[0]),
        "steps": int(result.steps[0]),
        "p_start": float(result.p_start[0]),
        "p_final": float(result.p_final[0]),
        "features": result.used_features[0],
        "first_feature": result.first_feature[0],
    }
