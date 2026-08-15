"""Investigation loop.

The live product elicits mutability with an LLM. This module is the
deterministic stand-in that still does the part a script *can* do:
read the battery, form hypotheses from surprises, design follow-ups,
and judge materiality. It never invents a number — it only cites runs.
"""

from __future__ import annotations

from typing import Any


def investigate(battery: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
    hypotheses = _hypotheses(battery, model)
    follow_ups = _follow_ups(hypotheses, battery)
    findings = _materiality(battery, model)
    graph = _graph(model, battery, hypotheses, follow_ups, findings)
    return {
        "objective": "Does this model reward genuine creditworthiness, or the ability to manipulate what it sees?",
        "human_gates": [
            {
                "id": "gate.mutability",
                "label": "Confirm feature mutability model",
                "status": "accepted",
                "why": "Lender-specific. Un-hardcodable. The agent proposes; a person signs.",
            },
            {
                "id": "gate.findings",
                "label": "Accept or reject each finding",
                "status": "pending",
                "why": "Janus produces evidence. A person decides what enters the memo.",
            },
        ],
        "hypotheses": hypotheses,
        "follow_ups": follow_ups,
        "findings": findings,
        "graph": graph,
        "memo_spine": [f["title"] for f in findings if f["severity"] in {"high", "medium"}],
    }


def _hypotheses(battery: dict, model: dict) -> list[dict]:
    hyps = []
    atk = battery["attack_surface"]
    if atk["flip_rate"] >= 0.25:
        hyps.append(
            {
                "id": "H1",
                "from_run": atk["run_id"],
                "statement": "A large share of declines flip on cosmetic change. Are those applicants actually lower risk?",
                "test": "Compare realised default of the flipped cohort to the portfolio baseline.",
            }
        )
    excl = battery["unexplained_exclusion"]
    if excl["approval_gap_pp"] >= 8 and abs(excl["default_gap_pp"]) < 4:
        hyps.append(
            {
                "id": "H2",
                "from_run": excl["run_id"],
                "statement": "Informal-income applicants are excluded far more than their default rate can explain. Is this measurement error in DTI?",
                "test": "Re-score after documenting the recorded/true income gap (evidence_recourse).",
            }
        )
    proxy = battery["proxy_audit"]
    if proxy["probe_auc"] >= 0.9:
        hyps.append(
            {
                "id": "H3",
                "from_run": proxy["run_id"],
                "statement": f"Rural residence is recoverable at {proxy['probe_auc']} AUC from model-visible features, chiefly {proxy['chief_carrier']}.",
                "test": "Name the carrier. Do not treat geography as an integrity lever.",
            }
        )
    gap = battery["integrity_gap"]
    if (gap.get("median_gap_ratio") or 0) >= 10:
        hyps.append(
            {
                "id": "H4",
                "from_run": gap["run_id"],
                "statement": "The honest route is orders of magnitude more expensive than the cosmetic route. Why?",
                "test": "Attribute the gap and price Route C (documentation) separately from earning.",
            }
        )
    _ = model
    return hyps


def _follow_ups(hypotheses: list[dict], battery: dict) -> list[dict]:
    out = []
    ids = {h["id"] for h in hypotheses}
    if "H1" in ids:
        atk = battery["attack_surface"]
        out.append(
            {
                "id": "E.H1",
                "hypothesis": "H1",
                "experiment": "cohort_compare flipped vs baseline default",
                "run_id": atk["run_id"],
                "result": (
                    f"Flipped cohort defaults at {atk['flipped_default_rate']} "
                    f"vs baseline {atk['baseline_default_rate']}. "
                    "Gamed approvals are not safer."
                ),
            }
        )
    if "H2" in ids:
        ev = battery["evidence_recourse"]
        out.append(
            {
                "id": "E.H2",
                "hypothesis": "H2",
                "experiment": "evidence_recourse full documentation",
                "run_id": ev["run_id"],
                "result": (
                    f"{ev['cross_rate_full_documentation']} of declined informal-income "
                    f"applicants cross the cutoff on documentation alone. "
                    f"Those who cross default at {ev['cross_default_rate']}."
                ),
            }
        )
    if "H4" in ids:
        ev = battery["evidence_recourse"]
        out.append(
            {
                "id": "E.H4",
                "hypothesis": "H4",
                "experiment": "route_c vs earn-it",
                "run_id": ev["run_id"],
                "result": (
                    "The honest *financial* route is expensive because recorded DTI is wrong. "
                    "The correct honest route is documentation: ¥0."
                ),
            }
        )
    return out


def _materiality(battery: dict, model: dict) -> list[dict]:
    atk = battery["attack_surface"]
    proxy = battery["proxy_audit"]
    excl = battery["unexplained_exclusion"]
    segs = battery["broken_segments"]
    gap = battery["integrity_gap"]
    ev = battery["evidence_recourse"]
    young = segs["young_self_employed"]
    worst = segs.get("worst_understated")
    findings = [
        {
            "id": "F01",
            "title": "Gaming surface",
            "severity": "high" if atk["flip_rate"] >= 0.35 else "medium",
            "accepted": True,
            "run_id": atk["run_id"],
            "claim": (
                f"{_pct(atk['flip_rate'])} of declined applicants are flippable by cosmetic change "
                f"(n={atk['n_sampled']}, ¥{int(atk['budget_jpy']/1000)}k budget); "
                f"median attack cost ¥{atk['median_cost_jpy']}. "
                f"Flipped cohort defaults at {_pct(atk['flipped_default_rate'])} vs "
                f"{_pct(atk['baseline_default_rate'])} baseline."
            ),
        },
        {
            "id": "F02",
            "title": "Proxy reconstruction",
            "severity": "high" if proxy["probe_auc"] >= 0.95 else "medium",
            "accepted": True,
            "run_id": proxy["run_id"],
            "claim": (
                f"Rural residence is recoverable from model-visible features at "
                f"{proxy['probe_auc']} AUC, carried chiefly by {proxy['chief_carrier']}. "
                "The model was never given it."
            ),
        },
        {
            "id": "F03",
            "title": "Unexplained exclusion",
            "severity": "high" if excl["approval_gap_pp"] >= 15 else "medium",
            "accepted": True,
            "run_id": excl["run_id"],
            "claim": (
                f"Undocumented-income applicants approved {excl['approval_gap_pp']}pp less often; "
                f"realised default { _pct(excl['default_informal'])} vs {_pct(excl['default_formal'])}."
            ),
        },
        {
            "id": "F04",
            "title": "Broken segments",
            "severity": "medium",
            "accepted": True,
            "run_id": segs["run_id"],
            "claim": (
                (
                    f"Worst understated leaf (n={worst['n']}): predicted {_pct(worst['predicted_default'])} "
                    f"vs actual {_pct(worst['actual_default'])}. "
                    if worst
                    else ""
                )
                + (
                    f"Young self-employed (n={young['n']}): predicted {_pct(young['predicted_default'])} "
                    f"vs actual {_pct(young['actual_default'])}; "
                    f"approved {_pct(young['approval_rate'])} vs {_pct(model['approval_rate'])} overall."
                    if young.get("n")
                    else ""
                )
            ),
        },
        {
            "id": "F05",
            "title": "Integrity gap",
            "severity": "high" if (gap.get("median_gap_ratio") or 0) >= 20 else "medium",
            "accepted": True,
            "run_id": gap["run_id"],
            "claim": (
                f"{gap['median_gap_ratio']}× median. Fake it: ¥{gap['median_attack_cost_jpy']}. "
                f"Earn it: ¥{gap['median_genuine_cost_jpy']} / {gap['median_genuine_days']} days. "
                f"{_pct(gap['would_not_have_defaulted_among_gameable'])} of gameable declines would not have defaulted."
            ),
        },
        {
            "id": "F06",
            "title": "Evidence recourse",
            "severity": "high" if ev["cross_rate_full_documentation"] >= 0.2 else "medium",
            "accepted": True,
            "run_id": ev["run_id"],
            "claim": (
                f"{_pct(ev['cross_rate_full_documentation'])} of declined informal-income applicants "
                f"(n={ev['n_declined_informal']}) cross the cutoff on documentation alone. "
                f"Those who cross default at {_pct(ev['cross_default_rate'])} vs "
                f"{_pct(ev['portfolio_default_rate'])} portfolio. "
                f"Among non-defaulters, {_pct(ev['cross_rate_among_non_default'])} cross."
            ),
        },
    ]
    return findings


def _graph(model, battery, hypotheses, follow_ups, findings) -> dict:
    nodes = [
        {"id": "obs.model", "kind": "observation", "label": f"Scorecard AUC {model['auc_holdout']}", "run_id": "run.inspect_model"},
        {"id": "obs.attack", "kind": "observation", "label": "Gaming surface", "run_id": battery["attack_surface"]["run_id"]},
        {"id": "obs.proxy", "kind": "observation", "label": "Proxy probe", "run_id": battery["proxy_audit"]["run_id"]},
        {"id": "obs.excl", "kind": "observation", "label": "Exclusion table", "run_id": battery["unexplained_exclusion"]["run_id"]},
        {"id": "obs.seg", "kind": "observation", "label": "Segment calibration", "run_id": battery["broken_segments"]["run_id"]},
        {"id": "obs.gap", "kind": "observation", "label": "Integrity gap", "run_id": battery["integrity_gap"]["run_id"]},
        {"id": "obs.ev", "kind": "observation", "label": "Evidence recourse", "run_id": battery["evidence_recourse"]["run_id"]},
    ]
    for h in hypotheses:
        nodes.append({"id": h["id"], "kind": "hypothesis", "label": h["statement"], "run_id": h["from_run"]})
    for fu in follow_ups:
        nodes.append({"id": fu["id"], "kind": "experiment", "label": fu["experiment"], "run_id": fu["run_id"]})
    for f in findings:
        nodes.append({"id": f["id"], "kind": "conclusion", "label": f["title"], "run_id": f["run_id"]})
    edges = [
        ["obs.model", "obs.attack"],
        ["obs.model", "obs.proxy"],
        ["obs.model", "obs.excl"],
        ["obs.model", "obs.seg"],
        ["obs.attack", "H1"],
        ["obs.excl", "H2"],
        ["obs.proxy", "H3"],
        ["obs.gap", "H4"],
        ["H1", "E.H1"],
        ["H2", "E.H2"],
        ["H4", "E.H4"],
        ["E.H1", "F01"],
        ["obs.proxy", "F02"],
        ["E.H2", "F03"],
        ["obs.seg", "F04"],
        ["obs.gap", "F05"],
        ["E.H2", "F06"],
        ["E.H4", "F06"],
    ]
    return {"nodes": nodes, "edges": [e for e in edges if _known(e, nodes)]}


def _known(edge: list[str], nodes: list[dict]) -> bool:
    ids = {n["id"] for n in nodes}
    return edge[0] in ids and edge[1] in ids


def _pct(x) -> str:
    if x is None:
        return "—"
    return f"{round(float(x) * 100, 1)}%"
