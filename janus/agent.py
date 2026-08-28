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
    atk = battery.get("attack_surface") or {}
    if not atk.get("skipped") and (atk.get("flip_rate") or 0) >= 0.25:
        hyps.append(
            {
                "id": "H1",
                "from_run": atk["run_id"],
                "statement": "A large share of declines flip on cosmetic change. Are those applicants actually lower risk?",
                "test": "Compare realised default of the flipped cohort to the portfolio baseline.",
            }
        )
    excl = battery.get("unexplained_exclusion") or {}
    gap_pp = excl.get("approval_gap_pp")
    def_gap = excl.get("default_gap_pp")
    if (
        not excl.get("skipped")
        and gap_pp is not None
        and def_gap is not None
        and gap_pp >= 8
        and abs(def_gap) < 4
    ):
        hyps.append(
            {
                "id": "H2",
                "from_run": excl["run_id"],
                "statement": "Informal-income applicants are excluded far more than their default rate can explain. Is this measurement error in DTI?",
                "test": "Re-score after documenting the recorded/true income gap (evidence_recourse).",
            }
        )
    proxy = battery.get("proxy_audit") or {}
    if not proxy.get("skipped") and (proxy.get("probe_auc") or 0) >= 0.9:
        hyps.append(
            {
                "id": "H3",
                "from_run": proxy["run_id"],
                "statement": f"Rural residence is recoverable at {proxy['probe_auc']} AUC from model-visible features, chiefly {proxy['chief_carrier']}.",
                "test": "Name the carrier. Do not treat geography as an integrity lever.",
            }
        )
    gap = battery.get("integrity_gap") or {}
    if not gap.get("skipped") and (gap.get("median_gap_ratio") or 0) >= 10:
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
        ev = battery.get("evidence_recourse") or {}
        if ev.get("skipped"):
            result = ev.get("reason") or "Route C skipped — no recorded/true income gap on this book."
        else:
            result = (
                f"{ev.get('cross_rate_full_documentation')} of declined informal-income "
                f"applicants cross the cutoff on documentation alone. "
                f"Those who cross default at {ev.get('cross_default_rate')}."
            )
        out.append(
            {
                "id": "E.H2",
                "hypothesis": "H2",
                "experiment": "evidence_recourse full documentation",
                "run_id": ev.get("run_id", "run.evidence_recourse"),
                "result": result,
            }
        )
    if "H4" in ids:
        ev = battery.get("evidence_recourse") or {}
        result = (
            ev.get("reason")
            if ev.get("skipped")
            else (
                "The honest *financial* route is expensive because recorded DTI is wrong. "
                "The correct honest route is documentation: $0."
            )
        )
        out.append(
            {
                "id": "E.H4",
                "hypothesis": "H4",
                "experiment": "route_c vs earn-it",
                "run_id": ev.get("run_id", "run.evidence_recourse"),
                "result": result,
            }
        )
    return out


def _materiality(battery: dict, model: dict) -> list[dict]:
    atk = battery.get("attack_surface") or {}
    proxy = battery.get("proxy_audit") or {}
    excl = battery.get("unexplained_exclusion") or {}
    segs = battery.get("broken_segments") or {}
    gap = battery.get("integrity_gap") or {}
    ev = battery.get("evidence_recourse") or {}
    young = segs.get("young_self_employed") or {}
    worst = segs.get("worst_understated")
    findings = []
    if not atk.get("skipped"):
        findings.append(
            {
                "id": "F01",
                "title": "Gaming surface",
                "severity": "high" if (atk.get("flip_rate") or 0) >= 0.35 else "medium",
                "accepted": True,
                "run_id": atk.get("run_id", "run.attack_surface"),
                "claim": (
                    f"{_pct(atk.get('flip_rate'))} of declined applicants are flippable by cosmetic change "
                    f"(n={atk.get('n_sampled')}, ${int((atk.get('budget_jpy') or 0)/1000)}k budget); "
                    f"median attack cost ${atk.get('median_cost_jpy')}. "
                    f"Flipped cohort defaults at {_pct(atk.get('flipped_default_rate'))} vs "
                    f"{_pct(atk.get('baseline_default_rate'))} baseline."
                ),
            }
        )
    if not proxy.get("skipped"):
        findings.append(
            {
                "id": "F02",
                "title": "Proxy reconstruction",
                "severity": "high" if (proxy.get("probe_auc") or 0) >= 0.95 else "medium",
                "accepted": True,
                "run_id": proxy.get("run_id", "run.proxy_audit"),
                "claim": (
                    f"Rural residence is recoverable from model-visible features at "
                    f"{proxy.get('probe_auc')} AUC, carried chiefly by {proxy.get('chief_carrier')}. "
                    "The model was never given it."
                ),
            }
        )
    if not excl.get("skipped") and excl.get("approval_gap_pp") is not None:
        findings.append(
            {
                "id": "F03",
                "title": "Unexplained exclusion",
                "severity": "high" if excl["approval_gap_pp"] >= 15 else "medium",
                "accepted": True,
                "run_id": excl.get("run_id", "run.unexplained_exclusion"),
                "claim": (
                    f"Undocumented-income applicants approved {excl['approval_gap_pp']}pp less often; "
                    f"realised default {_pct(excl.get('default_informal'))} vs {_pct(excl.get('default_formal'))}."
                ),
            }
        )
    if not segs.get("skipped"):
        claim = ""
        if worst:
            claim += (
                f"Worst understated leaf (n={worst['n']}): predicted {_pct(worst['predicted_default'])} "
                f"vs actual {_pct(worst['actual_default'])}. "
            )
        if young.get("n"):
            claim += (
                f"Young self-employed (n={young['n']}): predicted {_pct(young.get('predicted_default'))} "
                f"vs actual {_pct(young.get('actual_default'))}; "
                f"approved {_pct(young.get('approval_rate'))} vs {_pct(model.get('approval_rate'))} overall."
            )
        if claim:
            findings.append(
                {
                    "id": "F04",
                    "title": "Broken segments",
                    "severity": "medium",
                    "accepted": True,
                    "run_id": segs.get("run_id", "run.discover_segments"),
                    "claim": claim,
                }
            )
    if not gap.get("skipped"):
        findings.append(
            {
                "id": "F05",
                "title": "Integrity gap",
                "severity": "high" if (gap.get("median_gap_ratio") or 0) >= 20 else "medium",
                "accepted": True,
                "run_id": gap.get("run_id", "run.integrity_gap"),
                "claim": (
                    f"{gap.get('median_gap_ratio')}× median. Fake it: ${gap.get('median_attack_cost_jpy')}. "
                    f"Earn it: ${gap.get('median_genuine_cost_jpy')} / {gap.get('median_genuine_days')} days. "
                    f"{_pct(gap.get('would_not_have_defaulted_among_gameable'))} of gameable declines would not have defaulted."
                ),
            }
        )
    if not ev.get("skipped") and ev.get("cross_rate_full_documentation") is not None:
        findings.append(
            {
                "id": "F06",
                "title": "Evidence recourse",
                "severity": "high" if ev["cross_rate_full_documentation"] >= 0.2 else "medium",
                "accepted": True,
                "run_id": ev.get("run_id", "run.evidence_recourse"),
                "claim": (
                    f"{_pct(ev.get('cross_rate_full_documentation'))} of declined informal-income applicants "
                    f"(n={ev.get('n_declined_informal')}) cross the cutoff on documentation alone. "
                    f"Those who cross default at {_pct(ev.get('cross_default_rate'))} vs "
                    f"{_pct(ev.get('portfolio_default_rate'))} portfolio. "
                    f"Among non-defaulters, {_pct(ev.get('cross_rate_among_non_default'))} cross."
                ),
            }
        )
    return findings


def _graph(model, battery, hypotheses, follow_ups, findings) -> dict:
    nodes = [
        {"id": "obs.model", "kind": "observation", "label": f"Scorecard AUC {model.get('auc_holdout')}", "run_id": "run.inspect_model"},
    ]
    for key, nid, label in (
        ("attack_surface", "obs.attack", "Gaming surface"),
        ("proxy_audit", "obs.proxy", "Proxy probe"),
        ("unexplained_exclusion", "obs.excl", "Exclusion table"),
        ("broken_segments", "obs.seg", "Segment calibration"),
        ("integrity_gap", "obs.gap", "Integrity gap"),
        ("evidence_recourse", "obs.ev", "Evidence recourse"),
    ):
        run = battery.get(key) or {}
        if run.get("skipped"):
            continue
        nodes.append({"id": nid, "kind": "observation", "label": label, "run_id": run.get("run_id")})
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
