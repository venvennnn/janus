"""Integrity metric wrappers. Numerators and denominators are always returned."""

from __future__ import annotations

from typing import Any


METHOD = "janus.integrity.metrics.v1"


def _metric(
    metric_id: str,
    *,
    value: float | None,
    numerator: float | None = None,
    denominator: float | None = None,
    unit: str | None = None,
    formula: str | None = None,
    limitations: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    status = "ok"
    if denominator == 0 or (value is None and (numerator is None or denominator is None or denominator == 0)):
        status = "skipped" if value is None else "ok"
    if denominator == 0:
        value = None
        status = "skipped"
        limitations = limitations or "Denominator is zero; value withheld."
    rec = {
        "metric_id": metric_id,
        "value": value,
        "unit": unit,
        "status": status,
        "numerator": numerator,
        "denominator": denominator,
        "formula": formula,
        "method_version": METHOD,
        "limitations": limitations,
    }
    if extra:
        rec.update(extra)
    return rec


def attack_flip_metric(attack: dict[str, Any]) -> dict[str, Any]:
    if attack.get("skipped"):
        return _metric(
            "attack_flip_rate",
            value=None,
            limitations=attack.get("reason") or "Attack surface skipped.",
        )
    n = attack.get("n_sampled")
    k = attack.get("n_flipped")
    return _metric(
        "attack_flip_rate",
        value=attack.get("flip_rate"),
        numerator=k,
        denominator=n,
        unit="rate",
        formula="successful_decision_flips / eligible_attacked_records",
        extra={"median_effort_usd": attack.get("median_cost_jpy")},
    )


def integrity_gap_metric(gap: dict[str, Any]) -> dict[str, Any]:
    """Cosmetic-route effectiveness versus genuine-route effectiveness."""
    if gap.get("skipped"):
        return _metric(
            "integrity_gap",
            value=None,
            limitations=gap.get("reason") or "Integrity gap skipped.",
        )
    cosmetic = gap.get("attack_flip_rate")
    genuine = gap.get("genuine_flip_rate")
    if cosmetic is None or genuine is None:
        return _metric(
            "integrity_gap",
            value=None,
            numerator=cosmetic,
            denominator=genuine,
            formula="cosmetic_route_flip_rate / genuine_route_flip_rate",
            limitations="Route rates are missing.",
        )
    value = None if genuine == 0 else round(float(cosmetic) / float(genuine), 4)
    return _metric(
        "integrity_gap",
        value=value,
        numerator=cosmetic,
        denominator=genuine,
        unit="ratio of flip rates",
        formula="cosmetic_route_flip_rate / genuine_route_flip_rate",
        extra={
            "median_cost_ratio": gap.get("median_gap_ratio"),
            "median_cost_ratio_note": gap.get("note"),
            "cosmetic_effort_usd": gap.get("median_attack_cost_jpy"),
            "genuine_effort_usd": gap.get("median_genuine_cost_jpy"),
        },
    )


def mask_record_ids(ids: list[str] | None) -> list[str]:
    """Replace raw identifiers with sequential masks. Synthetic A- ids stay readable."""
    out = []
    for i, raw in enumerate(ids or []):
        text = str(raw)
        if text.startswith("A-") and text[2:].isdigit():
            out.append(f"rec-{text[2:]}")
        else:
            out.append(f"rec-{i + 1:04d}")
    return out
