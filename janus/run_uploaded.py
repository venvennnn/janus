"""Run the mandatory battery on an uploaded model after mutability is confirmed."""

from __future__ import annotations

from janus.levers import lever_book
from janus.llm import llm_available, llm_status, propose_mutability_llm
from janus.model import inspect_wrapped, wrap_estimator
from janus.package import build_findings_package
from janus.propose import propose_mutability, rows_to_levers


def propose_upload(
    estimator,
    holdout,
    cutoff: float,
    dictionary: str = "",
    context: str = "",
) -> tuple[object, dict, list[dict], dict]:
    model = wrap_estimator(estimator, holdout, cutoff)
    info = inspect_wrapped(model, holdout)
    if llm_available():
        proposal = propose_mutability_llm(model.features, holdout, dictionary, context)
        meta = {**llm_status(), "task": "propose_mutability"}
    else:
        proposal = propose_mutability(model.features, holdout, dictionary, context)
        meta = {**llm_status(), "task": "propose_mutability"}
    return model, info, proposal, meta


def run_uploaded(
    model,
    holdout,
    lever_rows: list[dict],
    seed: int | None = None,
    dictionary: str = "",
    context: str = "",
) -> dict:
    info = inspect_wrapped(model, holdout)
    with lever_book(rows_to_levers(lever_rows)):
        return build_findings_package(
            holdout,
            model,
            info,
            seed=seed,
            source="upload",
            dictionary=dictionary,
            context=context,
            use_llm=llm_available(),
        )
