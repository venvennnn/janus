"""Mandatory battery + export. Every figure in the demo comes from here."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

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
from janus.data_gen import DEMO_ID, generate_portfolio
from janus.levers import mutability_table
from janus.scorecard import calibrate_demo_applicant, inspect_model, train_scorecard


def run_battery(seed: int = 20260811) -> dict:
    portfolio = generate_portfolio(seed=seed)
    scorecard = train_scorecard(portfolio)
    holdout = calibrate_demo_applicant(portfolio.holdout, scorecard)
    model = inspect_model(scorecard, holdout)
    battery = {
        "attack_surface": attack_surface(holdout, scorecard),
        "proxy_audit": proxy_audit(holdout),
        "unexplained_exclusion": unexplained_exclusion(holdout, scorecard),
        "broken_segments": discover_broken_segments(holdout, scorecard),
        "integrity_gap": integrity_gap(holdout, scorecard),
        "evidence_recourse": evidence_recourse(holdout, scorecard),
        "gap_attribution": gap_attribution(holdout, scorecard),
    }
    demo_row = holdout.loc[holdout["applicant_id"] == DEMO_ID].iloc[0]
    menu = recourse_menu(demo_row, scorecard, holdout)
    investigation = investigate(battery, model)
    package = {
        "product": "JANUS",
        "version": "0.3.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "model": model,
        "mutability_model": mutability_table(),
        "battery": battery,
        "demo_applicant": {
            "applicant_id": DEMO_ID,
            "age": int(demo_row["age"]),
            "is_informal": int(demo_row["is_informal"]),
            "is_rural": int(demo_row["is_rural"]),
            "self_employed": int(demo_row["self_employed"]),
            "recorded_dti": float(demo_row["debt_to_income"]),
            "true_dti": float(demo_row["dti_true"]),
            "income_true": float(demo_row["income_true"]),
            "income_recorded": float(demo_row["income_recorded"]),
            "savings_balance": float(demo_row["savings_balance"]),
            "credit_utilization": float(demo_row["credit_utilization"]),
            "credit_inquiries_12m": int(demo_row["credit_inquiries_12m"]),
            "default": int(demo_row["default"]),
        },
        "recourse_menu": menu,
        "investigation": investigation,
        "figure_discipline": {
            "rule": "Only numbers from run_audit.py / integrity_gap / evidence_recourse may appear.",
            "attack_cost_medians_are_not_interchangeable": True,
            "sources": [
                "janus/run_audit.py",
                "janus/audits.py",
                "janus/data_gen.py",
            ],
        },
    }
    return package


def write_outputs(package: dict, root: Path) -> None:
    results = root / "results"
    docs_data = root / "docs" / "data"
    results.mkdir(parents=True, exist_ok=True)
    docs_data.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(package, indent=2)
    (results / "audit.json").write_text(payload)
    (docs_data / "findings.json").write_text(payload)
    (docs_data / "findings.js").write_text("window.JANUS_FINDINGS = " + payload + ";\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the JANUS mandatory audit battery.")
    parser.add_argument("--seed", type=int, default=20260811)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    package = run_battery(seed=args.seed)
    write_outputs(package, args.root)
    m = package["model"]
    b = package["battery"]
    print(f"AUC {m['auc_holdout']}  cutoff {m['cutoff']}  approval {m['approval_rate']}")
    print(f"attack flip {b['attack_surface']['flip_rate']}  median ¥{b['attack_surface']['median_cost_jpy']}")
    print(f"proxy AUC {b['proxy_audit']['probe_auc']}  via {b['proxy_audit']['chief_carrier']}")
    print(f"exclusion gap {b['unexplained_exclusion']['approval_gap_pp']}pp")
    print(f"integrity gap {b['integrity_gap']['median_gap_ratio']}×")
    print(f"evidence recourse {b['evidence_recourse']['cross_rate_full_documentation']}")
    print(f"A-7100 p {package['recourse_menu']['p_start']:.3f} → C {package['recourse_menu']['route_c_document_it']['p_final']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
