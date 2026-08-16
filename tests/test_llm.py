import pandas as pd

from janus.agent import investigate
from janus.llm import (
    _merge_investigation,
    _merge_levers,
    investigate_llm,
    llm_available,
    llm_status,
    propose_mutability_llm,
)
from janus.propose import propose_mutability


def test_llm_off_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert llm_available() is False
    assert llm_status()["llm"] == "off"


def test_propose_without_key_matches_heuristic(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    frame = pd.DataFrame(
        {
            "age": [21, 34, 45, 52],
            "savings_balance": [1000, 2000, 3000, 4000],
            "default": [0, 1, 0, 1],
        }
    )
    dictionary = "age is date of birth\nsavings_balance is an unverified snapshot"
    assert propose_mutability_llm(["age", "savings_balance"], frame, dictionary) == propose_mutability(
        ["age", "savings_balance"], frame, dictionary
    )


def test_merge_levers_keeps_data_bounds_and_known_features():
    baseline = propose_mutability(
        ["age", "savings_balance"],
        pd.DataFrame({"age": [20, 40], "savings_balance": [1.0, 9.0], "default": [0, 1]}),
        "age is date of birth\nsavings_balance is unverified",
    )
    proposed = [
        {
            "feature": "savings_balance",
            "kind": "cosmetic",
            "direction": "up",
            "attack_cost_jpy": 15,
            "rationale": "Claude: same-day transfer.",
        },
        {"feature": "invented_feature", "kind": "cosmetic", "direction": "up", "rationale": "ignore me"},
    ]
    merged = _merge_levers(baseline, proposed, ["age", "savings_balance"])
    names = [row["feature"] for row in merged]
    assert names == ["age", "savings_balance"]
    savings = next(row for row in merged if row["feature"] == "savings_balance")
    assert savings["rationale"] == "Claude: same-day transfer."
    assert savings["attack_cost_jpy"] == 15
    assert savings["lower"] is not None
    assert savings["upper"] is not None


def test_merge_investigation_keeps_engine_numbers():
    battery = {
        "attack_surface": {
            "run_id": "run.attack_surface",
            "flip_rate": 0.5,
            "n_sampled": 10,
            "budget_jpy": 60000,
            "median_cost_jpy": 64,
            "flipped_default_rate": 0.4,
            "baseline_default_rate": 0.3,
        },
        "proxy_audit": {"run_id": "run.proxy_audit", "skipped": True, "probe_auc": None},
        "unexplained_exclusion": {"run_id": "run.unexplained_exclusion", "skipped": True},
        "broken_segments": {"run_id": "run.discover_segments", "skipped": True, "young_self_employed": {"n": 0}},
        "integrity_gap": {"run_id": "run.integrity_gap", "skipped": True},
        "evidence_recourse": {"run_id": "run.evidence_recourse", "skipped": True},
    }
    engine = investigate(battery, {"auc_holdout": 0.66, "approval_rate": 0.48})
    claim = engine["findings"][0]["claim"]
    merged = _merge_investigation(
        engine,
        {
            "findings": [
                {
                    "id": "F01",
                    "title": "The model is cheap to game",
                    "severity": "high",
                    "reading": "This is the integrity question, not a fairness footnote.",
                }
            ],
            "hypotheses": engine["hypotheses"],
        },
    )
    assert merged["findings"][0]["claim"] == claim
    assert merged["findings"][0]["reading"].startswith("This is the integrity")
    assert merged["findings"][0]["title"] == "The model is cheap to game"
    assert merged["agent"] == "anthropic"


def test_investigate_without_key_is_heuristic(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    battery = {
        "attack_surface": {"run_id": "run.attack_surface", "skipped": True},
        "proxy_audit": {"run_id": "run.proxy_audit", "skipped": True},
        "unexplained_exclusion": {"run_id": "run.unexplained_exclusion", "skipped": True},
        "broken_segments": {"run_id": "run.discover_segments", "skipped": True, "young_self_employed": {"n": 0}},
        "integrity_gap": {"run_id": "run.integrity_gap", "skipped": True},
        "evidence_recourse": {"run_id": "run.evidence_recourse", "skipped": True},
    }
    out = investigate_llm(battery, {"auc_holdout": 0.6, "approval_rate": 0.5})
    assert out["agent"] == "heuristic"
