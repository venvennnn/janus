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
    return validate_holdout(load_csv(data, filename))


def load_csv(data: bytes, filename: str = "holdout.csv") -> pd.DataFrame:
    if len(data) > MAX_BYTES:
        raise IngestError(f"Holdout file exceeds {MAX_BYTES // (1024 * 1024)} MB.")
    try:
        frame = pd.read_csv(io.BytesIO(data))
    except Exception as exc:
        raise IngestError(f"Could not parse {filename} as CSV.") from exc
    if frame.empty:
        raise IngestError("Holdout CSV is empty.")
    if len(frame) > MAX_ROWS:
        raise IngestError(f"Holdout has {len(frame)} rows; the cap is {MAX_ROWS}.")
    return frame


def apply_mapping(frame: pd.DataFrame, target_column: str, id_column: str | None = None) -> pd.DataFrame:
    if target_column not in frame.columns:
        raise IngestError(f"Target column `{target_column}` is not in the holdout.")
    out = frame.copy()
    if target_column != "default":
        out["default"] = out[target_column]
    return validate_holdout(out, id_column=id_column)


def profile_frame(frame: pd.DataFrame) -> dict:
    cols = []
    for name in frame.columns:
        s = frame[name]
        rec = {
            "name": str(name),
            "dtype": str(s.dtype),
            "n_unique": int(s.nunique(dropna=True)),
            "missing_rate": round(float(s.isna().mean()), 4),
            "suggested": _suggest(str(name), s),
        }
        cols.append(rec)
    return {
        "row_count": int(len(frame)),
        "column_count": int(frame.shape[1]),
        "duplicate_rows": int(frame.duplicated().sum()),
        "columns": cols,
    }


def _suggest(name: str, s) -> str | None:
    n = name.lower()
    if n in {"default", "dpd90_index_x", "dpd90", "target"}:
        return "target"
    if "created_at" in n or n.endswith("_ts") or "timestamp" in n:
        return "timestamp"
    if n in {"applicant_id", "loan_id", "id"}:
        return "id"
    if "revenue" in n:
        return "revenue_not_exposure"
    if "amount" in n or "exposure" in n or "balance" in n:
        return "confirm_semantic_role"
    return None


def validate_holdout(frame: pd.DataFrame, id_column: str | None = None) -> pd.DataFrame:
    if frame.empty:
        raise IngestError("Holdout CSV is empty.")
    if len(frame) > MAX_ROWS:
        raise IngestError(f"Holdout has {len(frame)} rows; the cap is {MAX_ROWS}.")
    if "default" not in frame.columns:
        raise IngestError("Holdout must include a `default` column (0/1). Without outcomes, gamed approvals cannot be tested for risk.")
    out = frame.copy()
    out["default"] = pd.to_numeric(out["default"], errors="coerce")
    usable = out["default"].isin([0, 1])
    if int(usable.sum()) < 2:
        raise IngestError("`default` must contain both 0 and 1 after dropping nulls.")
    if out["default"].isna().any():
        out = out.loc[usable].copy()
    if out["default"].nunique() < 2:
        raise IngestError("`default` must contain both 0 and 1.")
    out["default"] = out["default"].astype(int)
    id_col = id_column if id_column and id_column in out.columns else ("applicant_id" if "applicant_id" in out.columns else None)
    if id_col is None:
        out["applicant_id"] = [f"R-{i}" for i in range(len(out))]
    else:
        out["applicant_id"] = out[id_col].astype(str)
    return out


def read_upload(file: BinaryIO) -> bytes:
    data = file.read()
    if not data:
        raise IngestError("Uploaded file is empty.")
    if len(data) > MAX_BYTES:
        raise IngestError(f"File exceeds {MAX_BYTES // (1024 * 1024)} MB.")
    return data
