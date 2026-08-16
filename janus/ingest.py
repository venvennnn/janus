"""Load an uploaded model and holdout. Nothing is written to disk."""

from __future__ import annotations

import io
from typing import BinaryIO

import joblib
import pandas as pd

MAX_ROWS = 20_000
MAX_BYTES = 50 * 1024 * 1024


class IngestError(ValueError):
    """User-facing validation failure."""


def load_estimator(data: bytes, filename: str = "model.joblib"):
    if len(data) > MAX_BYTES:
        raise IngestError(f"Model file exceeds {MAX_BYTES // (1024 * 1024)} MB.")
    bio = io.BytesIO(data)
    try:
        estimator = joblib.load(bio)
    except Exception:
        bio.seek(0)
        import pickle

        try:
            estimator = pickle.load(bio)
        except Exception as exc:
            raise IngestError(
                f"Could not load {filename}. Upload a scikit-learn / joblib estimator with predict_proba."
            ) from exc
    if not hasattr(estimator, "predict_proba"):
        raise IngestError("The model must implement predict_proba(X) → P(default).")
    return estimator


def load_holdout(data: bytes, filename: str = "holdout.csv") -> pd.DataFrame:
    if len(data) > MAX_BYTES:
        raise IngestError(f"Holdout file exceeds {MAX_BYTES // (1024 * 1024)} MB.")
    try:
        frame = pd.read_csv(io.BytesIO(data))
    except Exception as exc:
        raise IngestError(f"Could not parse {filename} as CSV.") from exc
    return validate_holdout(frame)


def validate_holdout(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        raise IngestError("Holdout CSV is empty.")
    if len(frame) > MAX_ROWS:
        raise IngestError(f"Holdout has {len(frame)} rows; the cap is {MAX_ROWS}.")
    if "default" not in frame.columns:
        raise IngestError("Holdout must include a `default` column (0/1). Without outcomes, gamed approvals cannot be tested for risk.")
    out = frame.copy()
    out["default"] = pd.to_numeric(out["default"], errors="coerce")
    if out["default"].isna().any():
        raise IngestError("`default` must be numeric 0/1 with no missing values.")
    if out["default"].nunique() < 2:
        raise IngestError("`default` must contain both 0 and 1.")
    out["default"] = out["default"].astype(int)
    if "applicant_id" not in out.columns:
        out["applicant_id"] = [f"R-{i}" for i in range(len(out))]
    else:
        out["applicant_id"] = out["applicant_id"].astype(str)
    return out


def read_upload(file: BinaryIO) -> bytes:
    data = file.read()
    if not data:
        raise IngestError("Uploaded file is empty.")
    if len(data) > MAX_BYTES:
        raise IngestError(f"File exceeds {MAX_BYTES // (1024 * 1024)} MB.")
    return data
