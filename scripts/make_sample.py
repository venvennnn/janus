"""Write a tiny upload pack so a judge without a bank model can still try the path."""

from __future__ import annotations

import zipfile
from pathlib import Path

import joblib
import pandas as pd

from janus.data_gen import AUDIT_LABELS, DEMO_ID, FEATURES, generate_portfolio
from janus.levers import MUTABILITY_MODEL
from janus.scorecard import calibrate_demo_applicant, train_scorecard

ROOT = Path(__file__).resolve().parents[1]
N_ROWS = 2_000


def write_sample_pack(root: Path = ROOT) -> Path:
    sample = root / "sample"
    docs_sample = root / "docs" / "sample"
    sample.mkdir(parents=True, exist_ok=True)
    docs_sample.mkdir(parents=True, exist_ok=True)

    portfolio = generate_portfolio(seed=20260811)
    scorecard = train_scorecard(portfolio)
    holdout = calibrate_demo_applicant(portfolio.holdout, scorecard)
    demo = holdout[holdout["applicant_id"] == DEMO_ID]
    rest = holdout[holdout["applicant_id"] != DEMO_ID].sample(N_ROWS - len(demo), random_state=11)
    pack = pd.concat([demo, rest], ignore_index=True)
    keep = list(dict.fromkeys(FEATURES + AUDIT_LABELS + ["self_employed"]))
    pack = pack[[c for c in keep if c in pack.columns]]

    joblib.dump(scorecard.pipeline, sample / "model.joblib")
    pack.to_csv(sample / "holdout.csv", index=False)
    (sample / "dictionary.txt").write_text(_dictionary(scorecard.cutoff))
    (sample / "context.txt").write_text(
        "Consumer unsecured book. Savings is a self-reported snapshot. "
        "Inquiries are a bureau timing artefact. Informal cash income is often unrecorded, "
        "so recorded DTI overstates leverage. Rural residence is not given to the model.\n"
    )

    zpath = sample / "janus-sample.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in ("holdout.csv", "model.joblib", "dictionary.txt", "context.txt"):
            zf.write(sample / name, name)
    dest = docs_sample / "janus-sample.zip"
    dest.write_bytes(zpath.read_bytes())
    return zpath


def _dictionary(cutoff: float) -> str:
    lines = [
        "Feature dictionary for the JANUS sample scorecard.",
        f"Approval cutoff for this fitted pipeline: {cutoff:.3f}",
        "",
    ]
    for feat in FEATURES:
        lever = MUTABILITY_MODEL.get(feat)
        why = lever.rationale if lever else ""
        lines.append(f"{feat}: {why}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    path = write_sample_pack()
    print(f"wrote {path}")
