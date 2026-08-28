"""Mandatory battery + Model Health export. Every demo figure comes from here."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from janus.data_gen import generate_portfolio
from janus.integrity.twins import counterfactual_twin, matched_observation_twins
from janus.package import build_findings_package
from janus.remediation.scenarios import evaluate_scenario
from janus.scorecard import calibrate_demo_applicant, inspect_model, train_scorecard
from janus.validation.health import run_model_health
from janus.validation.scoring import predict_positive


def run_battery(seed: int = 20260811) -> tuple[dict, object, object]:
    portfolio = generate_portfolio(seed=seed)
    scorecard = train_scorecard(portfolio)
    holdout = calibrate_demo_applicant(portfolio.holdout, scorecard)
    model = inspect_model(scorecard, holdout)
    package = build_findings_package(holdout, scorecard, model, seed=seed, source="synthetic")
    return package, holdout, scorecard


def build_model_health(holdout, scorecard) -> dict:
    return run_model_health(
        scorecard.pipeline,
        holdout,
        features=scorecard.features,
        cutoff=scorecard.cutoff,
        target_column="default",
        positive_class=1,
        segment_columns=[c for c in ("is_informal", "is_rural", "self_employed") if c in holdout.columns],
        maturity_confirmed=True,
        performance_window_confirmed=True,
        model_name="reference-scorecard",
        model_version="synthetic-seed-20260811",
    )


def build_reference_extras(package: dict, holdout, scorecard) -> dict:
    health = build_model_health(holdout, scorecard)
    p = predict_positive(scorecard.pipeline, holdout, scorecard.features, 1)
    twins = {
        "counterfactual": counterfactual_twin(package["demo_applicant"], package["recourse_menu"]),
        "matched_observation": matched_observation_twins(
            holdout,
            p,
            scorecard.cutoff,
            core=[c for c in ("age", "employment_months", "requested_amount") if c in holdout.columns],
            cosmetic=[c for c in ("savings_balance", "credit_utilization", "credit_inquiries_12m") if c in holdout.columns],
        ),
        "capital_injection_example": {
            "label": "Conceptual example — not engine output",
            "note": "A capital injection is not inherently illegitimate. The integrity risk is treating a temporary balance as durable repayment capacity.",
        },
    }
    scenarios = []
    for name, actions in [
        ("Baseline", []),
        (
            "Cap savings_balance at 90th percentile",
            [{"type": "cap", "feature": "savings_balance", "value": float(holdout["savings_balance"].quantile(0.9))}],
        ),
        ("Tighter cutoff 0.22", [{"type": "cutoff", "value": 0.22}]),
        (
            "Replace recorded DTI with true DTI",
            [{"type": "replace", "feature": "debt_to_income", "source": "dti_true"}],
        ),
    ]:
        scenarios.append(
            evaluate_scenario(
                scorecard.pipeline,
                holdout,
                features=scorecard.features,
                cutoff=scorecard.cutoff,
                actions=actions,
                segment_columns=[c for c in ("is_informal",) if c in holdout.columns],
                baseline=health,
                name=name,
                maturity_confirmed=True,
                performance_window_confirmed=True,
                model_name="reference-scorecard",
            )
        )
    watch = {
        "skipped": True,
        "reason": "Integrity Watch compares two runs. The synthetic reference case is a single recorded run.",
        "baseline_run_id": "reference",
    }
    return {"model_health": health, "twins": twins, "remediation": {"scenarios": scenarios}, "watch": watch}


def write_outputs(package: dict, extras: dict, root: Path) -> None:
    results = root / "results"
    docs_data = root / "docs" / "data"
    results.mkdir(parents=True, exist_ok=True)
    docs_data.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(package, indent=2)
    (results / "audit.json").write_text(payload)
    (docs_data / "findings.json").write_text(payload)
    (docs_data / "findings.js").write_text("window.JANUS_FINDINGS = " + payload + ";\n")
    (docs_data / "model_health.json").write_text(json.dumps(extras["model_health"], indent=2))
    (docs_data / "twins.json").write_text(json.dumps(extras["twins"], indent=2))
    (docs_data / "remediation.json").write_text(json.dumps(extras["remediation"], indent=2))
    (docs_data / "watch.json").write_text(json.dumps(extras["watch"], indent=2))
    src = Path(__file__).resolve().parent / "data" / "janus-default-credit-v1.json"
    shutil.copy(src, docs_data / "policy.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the JANUS mandatory audit battery.")
    parser.add_argument("--seed", type=int, default=20260811)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    package, holdout, scorecard = run_battery(seed=args.seed)
    extras = build_reference_extras(package, holdout, scorecard)
    write_outputs(package, extras, args.root)
    m = package["model"]
    b = package["battery"]
    h = extras["model_health"]["core_metrics"]
    print(f"AUC {m['auc_holdout']}  cutoff {m['cutoff']}  approval {m['approval_rate']}")
    print(f"health gini {h['gini']}  ks {h['ks']}  brier {h['brier']}  conclusion {extras['model_health']['conclusion']}")
    print(f"attack flip {b['attack_surface']['flip_rate']}  median ${b['attack_surface']['median_cost_jpy']}")
    print(f"proxy AUC {b['proxy_audit']['probe_auc']}  via {b['proxy_audit']['chief_carrier']}")
    print(f"exclusion gap {b['unexplained_exclusion']['approval_gap_pp']}pp")
    print(f"integrity gap {b['integrity_gap']['median_gap_ratio']}×")
    print(f"evidence recourse {b['evidence_recourse']['cross_rate_full_documentation']}")
    print(f"A-7100 p {package['recourse_menu']['p_start']:.3f} → C {package['recourse_menu']['route_c_document_it']['p_final']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
