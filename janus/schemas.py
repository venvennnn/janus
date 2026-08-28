"""Pydantic contracts for JANUS v1 services. Legacy /propose and /run stay dict-shaped."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class RunBody(BaseModel):
    job_id: str
    confirmed: bool = False
    levers: list[dict] = Field(default_factory=list)


class MetricResult(BaseModel):
    metric_id: str
    value: float | None = None
    unit: str | None = None
    status: str = "ok"
    threshold: float | None = None
    population: int | None = None
    numerator: float | None = None
    denominator: float | None = None
    method_version: str | None = None
    limitations: str | None = None


class MutabilityAssumption(BaseModel):
    feature: str
    feature_class: Literal["genuine", "cosmetic", "mixed", "immutable", "documentation"] | str
    allowed_direction: str | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None
    step: float | None = None
    effort: float | None = None
    effort_unit: str | None = "USD"
    rationale: str | None = None
    proposal_source: str | None = None
    confirmed_by: str | None = None
    confirmed_at: datetime | None = None


class Finding(BaseModel):
    id: str
    domain: str = "integrity"
    title: str
    description: str = ""
    severity: Literal["low", "medium", "high", "critical"] | str = "medium"
    evidence_refs: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)
    segments: list[str] = Field(default_factory=list)
    limitation: str | None = None
    recommended_action: str | None = None
    owner: str | None = None
    due_date: str | None = None
    status: str = "draft"
    reviewer: str | None = None
    approved_at: datetime | None = None


class ApprovalEvent(BaseModel):
    id: str
    object_type: str
    object_id: str
    action: str
    actor: str
    timestamp: datetime
    comment: str | None = None


class ConfigurationBody(BaseModel):
    target_column: str = "default"
    positive_class: int = 1
    timestamp_column: str | None = None
    id_column: str | None = "applicant_id"
    exposure_column: str | None = None
    segment_columns: list[str] = Field(default_factory=list)
    cutoff: float = 0.275
    decision_rule: str = "predicted_default_probability <= cutoff"
    maturity_confirmed: bool = False
    performance_window_confirmed: bool = False
    evidence_mappings: list[dict[str, str]] = Field(default_factory=list)
    name: str | None = None


class AssumptionConfirmBody(BaseModel):
    confirmed: bool = False
    levers: list[dict] = Field(default_factory=list)
    reviewer: str = "local-user"


class FindingUpdateBody(BaseModel):
    title: str | None = None
    description: str | None = None
    severity: str | None = None
    domain: str | None = None
    status: str | None = None
    owner: str | None = None
    due_date: str | None = None
    recommended_action: str | None = None
    reviewer: str | None = None
    limitation: str | None = None


class EvidenceGapBody(BaseModel):
    evidence_mappings: list[dict[str, str]] = Field(default_factory=list)


class ApprovalBody(BaseModel):
    object_type: str
    object_id: str
    action: str
    actor: str = "local-user"
    comment: str | None = None


class ComparisonBody(BaseModel):
    baseline_run_id: str
    comparison_run_id: str


class RemediationScenarioBody(BaseModel):
    name: str
    actions: list[dict[str, Any]] = Field(default_factory=list)
    created_by: str = "local-user"
    reviewer_status: str = "needs_review"
    rationale: str | None = None
