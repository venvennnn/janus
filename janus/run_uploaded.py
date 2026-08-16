"""Run the mandatory battery on an uploaded model after mutability is confirmed."""

from __future__ import annotations

from janus.levers import lever_book
from janus.model import inspect_wrapped, wrap_estimator
from janus.package import build_findings_package
from janus.propose import propose_mutability, rows_to_levers


def propose_upload(
    estimator,
    holdout,
    cutoff: float,
    dictionary: str = "",
    context: str = "",
) -> tuple[object, dict, list[dict]]:
    model = wrap_estimator(estimator, holdout, cutoff)
    info = inspect_wrapped(model, holdout)
    proposal = propose_mutability(model.features, holdout, dictionary, context)
    return model, info, proposal


def run_uploaded(
    model,
    holdout,
    lever_rows: list[dict],
    seed: int | None = None,
) -> dict:
    info = inspect_wrapped(model, holdout)
    with lever_book(rows_to_levers(lever_rows)):
        return build_findings_package(holdout, model, info, seed=seed, source="upload")
