"""Versioned validation policy. Thresholds are assumptions, not law."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DEFAULT_POLICY_ID = "janus-default-credit-v1"
_DIR = Path(__file__).resolve().parent / "data"


def policy_path(policy_id: str = DEFAULT_POLICY_ID) -> Path:
    return _DIR / f"{policy_id}.json"


@lru_cache(maxsize=8)
def load_policy(policy_id: str = DEFAULT_POLICY_ID) -> dict[str, Any]:
    path = policy_path(policy_id)
    if not path.exists():
        raise FileNotFoundError(f"Unknown policy {policy_id}")
    return json.loads(path.read_text())


def domain_status(value: float | None, *, warn_below=None, fail_below=None, warn_above=None, fail_above=None) -> str:
    if value is None:
        return "skipped"
    if fail_below is not None and value < fail_below:
        return "fail"
    if fail_above is not None and value > fail_above:
        return "fail"
    if warn_below is not None and value < warn_below:
        return "warn"
    if warn_above is not None and value > warn_above:
        return "warn"
    return "pass"


def overall_conclusion(domains: dict[str, str]) -> str:
    vals = list(domains.values())
    if domains.get("data_readiness") == "blocked":
        return "Insufficient Evidence"
    if domains.get("data_readiness") == "fail" or domains.get("predictive_performance") == "fail":
        return "Fail"
    if "fail" in vals:
        return "Remediation Required"
    if "warn" in vals:
        return "Conditional Pass"
    if all(v in {"pass", "skipped", "not_tested"} for v in vals):
        return "Pass"
    return "Insufficient Evidence"
