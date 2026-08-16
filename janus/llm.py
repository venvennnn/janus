"""Claude reads language. The engine still owns every number.

JANUS is an agent for an AI competition. The model proposes how features
can move and how to read the battery. It is forbidden from inventing a
statistic. If the key is missing or the call fails, the heuristic
stand-in in `propose.py` / `agent.py` is used so the demo still runs.
"""

from __future__ import annotations

import json
import os
from typing import Any

from janus.agent import investigate
from janus.propose import propose_mutability

DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")

_PROPOSE_TOOL = {
    "name": "propose_mutability",
    "description": "Propose a feature mutability table for this lender. No portfolio statistics.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["levers"],
        "properties": {
            "levers": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["feature", "kind", "direction", "rationale"],
                    "properties": {
                        "feature": {"type": "string"},
                        "kind": {
                            "type": "string",
                            "enum": ["cosmetic", "genuine", "mixed", "immutable", "documentation"],
                        },
                        "direction": {"type": "string", "enum": ["up", "down"]},
                        "attack_cost_jpy": {"type": ["number", "null"]},
                        "attack_days": {"type": ["number", "null"]},
                        "genuine_cost_jpy": {"type": ["number", "null"]},
                        "genuine_days": {"type": ["number", "null"]},
                        "rationale": {"type": "string"},
                    },
                },
            }
        },
    },
}

_INVESTIGATE_TOOL = {
    "name": "file_investigation",
    "description": "Read the completed battery. Cite only numbers already in the JSON. Write the investigation.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["hypotheses", "findings"],
        "properties": {
            "hypotheses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "from_run", "statement", "test"],
                    "properties": {
                        "id": {"type": "string"},
                        "from_run": {"type": "string"},
                        "statement": {"type": "string"},
                        "test": {"type": "string"},
                    },
                },
            },
            "follow_ups": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "hypothesis", "experiment", "run_id", "result"],
                    "properties": {
                        "id": {"type": "string"},
                        "hypothesis": {"type": "string"},
                        "experiment": {"type": "string"},
                        "run_id": {"type": "string"},
                        "result": {"type": "string"},
                    },
                },
            },
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "reading"],
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                        "reading": {
                            "type": "string",
                            "description": "Why this finding matters. Do not invent a number.",
                        },
                    },
                },
            },
        },
    },
}


def llm_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def llm_status() -> dict:
    if not llm_available():
        return {"llm": "off", "model": None, "note": "Set ANTHROPIC_API_KEY to let Claude read the dictionary."}
    return {"llm": "anthropic", "model": DEFAULT_MODEL}


def propose_mutability_llm(
    features: list[str],
    holdout,
    dictionary: str = "",
    context: str = "",
) -> list[dict]:
    """Claude proposes mutability. Bounds and missing rows come from the heuristic table."""
    baseline = propose_mutability(features, holdout, dictionary, context)
    if not llm_available():
        return baseline
    prompt = (
        "You are JANUS, a red-team agent for credit-model integrity.\n"
        "A lender uploaded a scorecard. Propose how each MODEL feature can move "
        "inside an application window.\n\n"
        "kind:\n"
        "- cosmetic: cheap to present a different value without changing capacity "
        "(unverified snapshot, timing artefact).\n"
        "- genuine: moves only with real financial change (earn, repay).\n"
        "- mixed: both paths exist (e.g. utilisation parked vs repaid).\n"
        "- immutable: outside the window (age, bureau history, geography).\n"
        "- documentation: Route C — make existing income visible, not a cosmetic lever.\n\n"
        "Attack cost is what it costs to *present* the value. Genuine cost is what "
        "it costs to *become* the value. Currency is JPY. "
        "If a path should not be offered, set that cost to null.\n"
        "Do not invent portfolio statistics, AUC, default rates, or flip rates.\n"
        "Only propose levers for the listed model features.\n\n"
        f"MODEL FEATURES:\n{json.dumps(features)}\n\n"
        f"FEATURE DICTIONARY:\n{dictionary or '(none provided)'}\n\n"
        f"BUSINESS CONTEXT:\n{context or '(none provided)'}\n"
    )
    try:
        raw = _tool_call(prompt, _PROPOSE_TOOL, "propose_mutability")
        return _merge_levers(baseline, raw.get("levers") or [], features)
    except Exception:
        return baseline


def investigate_llm(
    battery: dict[str, Any],
    model: dict[str, Any],
    dictionary: str = "",
    context: str = "",
) -> dict[str, Any]:
    """Engine findings keep the numbers. Claude writes the reading."""
    engine = investigate(battery, model)
    engine["agent"] = "heuristic"
    if not llm_available():
        return engine
    prompt = (
        "You are JANUS. The deterministic engine has finished the mandatory battery. "
        "Every number below is already computed. You may quote those numbers. "
        "You must not invent a new statistic, percentage, yen amount, or AUC.\n"
        "Form hypotheses from surprises. Read each engine finding and write why it "
        "matters for model-risk review. Keep finding ids (F01…).\n\n"
        f"OBJECTIVE: {engine['objective']}\n\n"
        f"MODEL (engine):\n{json.dumps(model, default=str)[:4000]}\n\n"
        f"BATTERY (engine):\n{json.dumps(battery, default=str)[:12000]}\n\n"
        f"ENGINE FINDINGS (cite these claims; do not rewrite the numbers):\n"
        f"{json.dumps(engine.get('findings'), default=str)}\n\n"
        f"FEATURE DICTIONARY:\n{(dictionary or '')[:3000]}\n\n"
        f"BUSINESS CONTEXT:\n{(context or '')[:2000]}\n"
    )
    try:
        raw = _tool_call(prompt, _INVESTIGATE_TOOL, "file_investigation")
        return _merge_investigation(engine, raw)
    except Exception:
        return engine


def _merge_levers(baseline: list[dict], proposed: list[dict], features: list[str]) -> list[dict]:
    allowed = set(features)
    by_base = {row["feature"]: dict(row) for row in baseline}
    by_llm = {row.get("feature"): row for row in proposed if row.get("feature") in allowed}
    out = []
    for feat in features:
        row = by_base.get(feat)
        if row is None:
            continue
        extra = by_llm.get(feat) or {}
        merged = dict(row)
        for key in ("kind", "direction", "rationale", "attack_cost_jpy", "attack_days", "genuine_cost_jpy", "genuine_days"):
            if extra.get(key) is not None:
                merged[key] = extra[key]
        if merged.get("kind") == "immutable":
            merged["attack_cost_jpy"] = None
            merged["genuine_cost_jpy"] = None
            merged["attack_step"] = None
            merged["genuine_step"] = None
        out.append(merged)
    return out or baseline


def _merge_investigation(engine: dict, raw: dict) -> dict:
    readings = {f.get("id"): f for f in (raw.get("findings") or []) if f.get("id")}
    findings = []
    for item in engine.get("findings") or []:
        extra = readings.get(item["id"], {})
        row = dict(item)
        if extra.get("reading"):
            row["reading"] = extra["reading"]
        if extra.get("title"):
            row["title"] = extra["title"]
        if extra.get("severity") in {"high", "medium", "low"}:
            row["severity"] = extra["severity"]
        findings.append(row)
    hypotheses = raw.get("hypotheses") or engine.get("hypotheses")
    follow_ups = raw.get("follow_ups") or engine.get("follow_ups")
    out = dict(engine)
    out["hypotheses"] = hypotheses
    out["follow_ups"] = follow_ups
    out["findings"] = findings
    out["memo_spine"] = [f["title"] for f in findings if f.get("severity") in {"high", "medium"}]
    out["agent"] = "anthropic"
    out["model"] = DEFAULT_MODEL
    return out


def _tool_call(prompt: str, tool: dict, name: str) -> dict:
    import anthropic

    client = anthropic.Anthropic()
    message = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=4096,
        tools=[tool],
        tool_choice={"type": "tool", "name": name},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in message.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == name:
            return dict(block.input or {})
    raise RuntimeError("Claude did not return the expected tool payload.")
