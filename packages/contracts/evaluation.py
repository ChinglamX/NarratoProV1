"""Canonical quality, correction, evaluation, calibration, and routing contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, JsonValue, field_validator, model_validator

from packages.contracts.base import StrictContract
from packages.contracts.calibration import DatasetSplitManifest
from packages.contracts.envelopes import JsonObject
from packages.contracts.evidence import ConfidenceRecord, ConfidenceStatus, EvidenceLink, RiskClass
from packages.contracts.foundation import UUID, ActorRef, ArtifactRef, StableName, TimeRange


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("timestamps must use UTC")
    return value


Version = Annotated[str, Field(min_length=1, max_length=128)]
Description = Annotated[str, Field(min_length=1, max_length=4_096)]


class QualitySeverity(StrEnum):
    S0 = "S0"
    S1 = "S1"
    S2 = "S2"
    S3 = "S3"


class QualityEventStatus(StrEnum):
    DETECTED = "detected"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"
    CORRECTED = "corrected"
    SUPERSEDED = "superseded"
    UNRESOLVED = "unresolved"


class QualityLabel(StrEnum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    INSUFFICIENT = "insufficient"
    DISPUTED = "disputed"


class QualityEvent(StrictContract):
    """One traceable issue without granting authority to mutate its target."""

    event_id: UUID
    module: StableName
    dimension: StableName
    issue_type: StableName
    severity: QualitySeverity
    blocker: bool
    target: ArtifactRef
    target_range: TimeRange | None = None
    evidence: tuple[EvidenceLink, ...] = ()
    raw_metrics: JsonObject = Field(default_factory=dict)
    detector: StableName
    detector_version: Version
    confidence: ConfidenceRecord
    profile_rule: StableName | None = None
    suggested_fix: Description | None = None
    status: QualityEventStatus
    reviewer_label: QualityLabel | None = None
    disagreement: bool = False
    occurred_at: datetime

    _occurred_at_utc = field_validator("occurred_at")(_require_utc)

    @model_validator(mode="after")
    def enforce_severity_and_resolution(self) -> Self:
        if self.severity is QualitySeverity.S0 and not self.blocker:
            raise ValueError("S0 quality events must be blockers")
        if self.severity is QualitySeverity.S3 and self.blocker:
            raise ValueError("S3 preference events cannot be blockers")
        if self.status is QualityEventStatus.UNRESOLVED and self.reviewer_label in {
            QualityLabel.CORRECT,
            QualityLabel.INCORRECT,
        }:
            raise ValueError("unresolved quality events cannot carry a resolved reviewer label")
        if self.disagreement and self.reviewer_label is not QualityLabel.DISPUTED:
            raise ValueError("detector or reviewer disagreement requires a disputed label")
        if self.reviewer_label is QualityLabel.DISPUTED and not self.disagreement:
            raise ValueError("a disputed label requires disagreement=true")
        return self


class CorrectionEligibility(StrEnum):
    TRAINING = "training"
    EVALUATION_ONLY = "evaluation_only"
    PROHIBITED = "prohibited"
    UNRESOLVED = "unresolved"


class Correction(StrictContract):
    """Immutable semantic change between two exact artifact versions."""

    correction_id: UUID
    project_id: UUID
    run_id: UUID
    variant_id: UUID | None = None
    module: StableName
    dimension: StableName
    correction_type: StableName
    target_before: ArtifactRef
    target_after: ArtifactRef
    semantic_operation: JsonObject
    before: JsonValue
    after: JsonValue
    reason_taxonomy: tuple[StableName, ...]
    reason: Description
    target_range: TimeRange | None = None
    severity: QualitySeverity
    blocker: bool
    model_version: Version | None = None
    prompt_version: Version | None = None
    config_version: Version
    profile_version: Version
    policy_version: Version
    reviewer: ActorRef
    created_at: datetime
    dependency_impact: tuple[ArtifactRef, ...] = ()
    eligibility: CorrectionEligibility
    consent_recorded: bool
    source_correction_id: UUID | None = None

    _created_at_utc = field_validator("created_at")(_require_utc)

    @model_validator(mode="after")
    def enforce_version_lineage_and_usage(self) -> Self:
        before = self.target_before
        after = self.target_after
        if before.artifact_id != after.artifact_id or before.artifact_type != after.artifact_type:
            raise ValueError("correction before/after must identify the same artifact lineage")
        if after.version <= before.version:
            raise ValueError("correction target_after must be a newer artifact version")
        if before.checksum is not None and before.checksum == after.checksum:
            raise ValueError("correction before/after checksums must differ")
        if not self.semantic_operation:
            raise ValueError("correction requires a structured semantic_operation")
        if not self.reason_taxonomy:
            raise ValueError("correction requires at least one reason taxonomy label")
        if self.eligibility is CorrectionEligibility.TRAINING and not self.consent_recorded:
            raise ValueError("training-eligible correction requires recorded consent")
        if self.severity is QualitySeverity.S0 and not self.blocker:
            raise ValueError("S0 corrections must describe blocker issues")
        if self.severity is QualitySeverity.S3 and self.blocker:
            raise ValueError("S3 preference corrections cannot be blockers")
        return self


class DatasetManifest(StrictContract):
    """Immutable feedback dataset snapshot with complete source lineage."""

    dataset: ArtifactRef
    version: Version
    parent: ArtifactRef | None = None
    split_manifest: DatasetSplitManifest
    correction_refs: tuple[ArtifactRef, ...]
    guideline_refs: tuple[ArtifactRef, ...]
    taxonomy_version: Version
    source_schema_version: Version
    generated_by_version: Version
    content_checksum: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    created_at: datetime

    _created_at_utc = field_validator("created_at")(_require_utc)

    @model_validator(mode="after")
    def enforce_manifest_lineage(self) -> Self:
        if self.dataset.artifact_type != "DatasetManifest":
            raise ValueError("dataset must reference a DatasetManifest artifact")
        if self.parent is not None:
            if self.parent.artifact_type != self.dataset.artifact_type:
                raise ValueError("dataset parent must use the same artifact type")
            if self.parent.artifact_id != self.dataset.artifact_id:
                raise ValueError("dataset parent must use the same artifact id")
            if self.parent.version >= self.dataset.version:
                raise ValueError("dataset parent must precede the current version")
        if len(set(self.correction_refs)) != len(self.correction_refs):
            raise ValueError("correction_refs must be unique")
        return self


class ApplicableScope(StrictContract):
    """Exact domain in which calibration and routing claims are valid."""

    module: StableName
    task: StableName
    output_type: StableName
    provider: StableName
    model_version: Version
    prompt_version: Version | None = None
    config_version: Version
    schema_version: Version
    genres: frozenset[StableName]
    languages: frozenset[StableName]
    platforms: frozenset[StableName]
    risk_classes: frozenset[RiskClass]

    @model_validator(mode="after")
    def require_bounded_scope(self) -> Self:
        if not self.genres or not self.languages or not self.platforms or not self.risk_classes:
            raise ValueError("applicable scope dimensions must be explicit and non-empty")
        return self


class CalibrationLifecycle(StrEnum):
    SHADOW = "shadow"
    CANDIDATE = "candidate"
    APPROVED = "approved"
    DRIFTED = "drifted"
    DEPRECATED = "deprecated"
    REVOKED = "revoked"


class CalibrationArtifact(StrictContract):
    calibration: ArtifactRef
    version: Version
    parent: ArtifactRef | None = None
    status: CalibrationLifecycle
    method: StableName
    scope: ApplicableScope
    dataset_ref: ArtifactRef
    evaluation_run_ref: ArtifactRef
    feature_schema_version: Version
    code_version: Version
    metrics: JsonObject
    approved_by: ActorRef | None = None
    approved_at: datetime | None = None
    created_at: datetime

    _approved_at_utc = field_validator("approved_at")(_require_utc)
    _created_at_utc = field_validator("created_at")(_require_utc)

    @model_validator(mode="after")
    def enforce_lifecycle_and_lineage(self) -> Self:
        if self.calibration.artifact_type != "CalibrationArtifact":
            raise ValueError("calibration must reference a CalibrationArtifact")
        if self.parent is not None:
            if self.parent.artifact_id != self.calibration.artifact_id:
                raise ValueError("calibration parent must use the same artifact id")
            if self.parent.version >= self.calibration.version:
                raise ValueError("calibration parent must precede the current version")
        approved = self.status is CalibrationLifecycle.APPROVED
        if approved != (self.approved_by is not None and self.approved_at is not None):
            raise ValueError("approved calibration requires approver and approval timestamp only")
        return self


class EvaluationStatus(StrEnum):
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INCOMPLETE = "incomplete"


class EvaluationRun(StrictContract):
    evaluation: ArtifactRef
    plan_ref: ArtifactRef
    candidate_ref: ArtifactRef
    champion_ref: ArtifactRef
    dataset_ref: ArtifactRef
    applicable_slices: tuple[StableName, ...]
    metric_versions: dict[StableName, Version]
    blocker_gates: tuple[StableName, ...]
    code_version: Version
    dependency_lock_checksum: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    seed: Annotated[int, Field(ge=0, le=2**63 - 1)]
    status: EvaluationStatus
    result_refs: tuple[ArtifactRef, ...] = ()
    missing_shards: tuple[StableName, ...] = ()
    started_at: datetime
    completed_at: datetime | None = None

    _started_at_utc = field_validator("started_at")(_require_utc)
    _completed_at_utc = field_validator("completed_at")(_require_utc)

    @model_validator(mode="after")
    def enforce_run_state(self) -> Self:
        if self.evaluation.artifact_type != "EvaluationRun":
            raise ValueError("evaluation must reference an EvaluationRun artifact")
        if self.candidate_ref == self.champion_ref:
            raise ValueError("candidate and champion must be different artifact versions")
        if self.status is EvaluationStatus.COMPLETED:
            if self.completed_at is None or self.missing_shards:
                raise ValueError("completed evaluation requires completed_at and no missing shards")
        elif self.completed_at is not None:
            raise ValueError("only completed evaluations may set completed_at")
        return self


class RoutingOutcome(StrEnum):
    AUTO_FLOW = "auto_flow"
    SUGGEST_REVIEW = "suggest_review"
    REQUIRED_REVIEW = "required_review"


class RoutingDecision(StrictContract):
    decision: ArtifactRef
    target: ArtifactRef
    gate: Annotated[str, Field(pattern=r"^(story|strategy|timeline|release)$")]
    automation_level: Annotated[str, Field(pattern=r"^L[0-4]$")]
    effective_policy_ref: ArtifactRef
    calibration_ref: ArtifactRef | None = None
    scope: ApplicableScope
    confidence: ConfidenceRecord
    quality_events: tuple[ArtifactRef, ...] = ()
    required_checks_complete: bool
    has_blocker: bool
    has_rights_risk: bool
    has_conflict: bool
    has_unresolved: bool
    has_disagreement: bool
    outcome: RoutingOutcome
    reasons: tuple[Description, ...]
    decided_at: datetime

    _decided_at_utc = field_validator("decided_at")(_require_utc)

    @model_validator(mode="after")
    def fail_closed(self) -> Self:
        if self.decision.artifact_type != "RoutingDecision":
            raise ValueError("decision must reference a RoutingDecision artifact")
        must_review = (
            self.gate == "release"
            or self.automation_level in {"L0", "L1"}
            or not self.required_checks_complete
            or self.has_blocker
            or self.has_rights_risk
            or self.has_conflict
            or self.has_unresolved
            or self.has_disagreement
            or self.confidence.status
            in {ConfidenceStatus.UNAVAILABLE, ConfidenceStatus.DRIFTED, ConfidenceStatus.SHADOW}
            or self.calibration_ref is None
        )
        if must_review and self.outcome is not RoutingOutcome.REQUIRED_REVIEW:
            raise ValueError("unsafe, unresolved, shadow, or release routing must require review")
        if (
            self.outcome is RoutingOutcome.AUTO_FLOW
            and self.confidence.status is not ConfidenceStatus.CALIBRATED
        ):
            raise ValueError("auto-flow requires calibrated confidence")
        if not self.reasons:
            raise ValueError("routing decision requires at least one reason")
        return self
