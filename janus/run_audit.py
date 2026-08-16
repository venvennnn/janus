"""Mandatory battery + export. Every figure in the demo comes from here."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from janus.data_gen import generate_portfolio
from janus.package import build_findings_package
from janus.scorecard import calibrate_demo_applicant, inspect_model, train_scorecard


def run_battery(seed: int = 20260811) -> dict:
    portfolio = generate_portfolio(seed=seed)
    scorecard = train_scorecard(portfolio)
    holdout = calibrate_demo_applicant(portfolio.holdout, scorecard)
    model = inspect_model(scorecard, holdout)
    return build_findings_package(holdout, scorecard, model, seed=seed, source="synthetic")


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
