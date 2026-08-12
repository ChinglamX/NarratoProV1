"""E11 deterministic render, technical QC and human Release Gate contracts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, model_validator

from packages.contracts.base import StrictContract
from packages.contracts.envelopes import JsonObject
from packages.contracts.foundation import UUID, ActorRef, ArtifactRef, RationalTime, StableName
from packages.contracts.rights import RightsMetadata


class RenderMode(StrEnum):
    PROXY = "proxy"
    FINAL = "final"


class RenderOperation(StrictContract):
    operation_id: UUID
    operation_type: StableName
    input_refs: tuple[ArtifactRef, ...]
    parameters: JsonObject
    cache_key: StableName


class RenderPlanContract(StrictContract):
    conformed_timeline_ref: ArtifactRef
    mixed_audio_ref: ArtifactRef
    ass_artifact_ref: ArtifactRef
    platform_profile_ref: ArtifactRef
    toolchain_version: StableName
    mode: RenderMode
    operations: tuple[RenderOperation, ...]
    expected_duration: RationalTime
    output_spec: JsonObject
    checksum: StableName
    blocker_codes: tuple[StableName, ...] = ()

    @model_validator(mode="after")
    def require_renderable_plan(self) -> Self:
        if not self.operations or self.expected_duration.value <= 0:
            raise ValueError("render plan requires operations and positive duration")
        return self


class RenderExecutionReport(StrictContract):
    render_plan_ref: ArtifactRef
    attempt: Annotated[int, Field(ge=1)]
    output_blob_ref: StableName | None = None
    output_checksum: StableName | None = None
    cache_hits: Annotated[int, Field(ge=0)] = 0
    cache_misses: Annotated[int, Field(ge=0)] = 0
    duration_ms: Annotated[int, Field(ge=0)]
    peak_memory_bytes: Annotated[int, Field(ge=0)]
    ffmpeg_version: StableName
    succeeded: bool
    failure_code: StableName | None = None

    @model_validator(mode="after")
    def reconcile_execution(self) -> Self:
        if self.succeeded and (self.output_blob_ref is None or self.output_checksum is None):
            raise ValueError("successful render requires output and checksum")
        if not self.succeeded and self.failure_code is None:
            raise ValueError("failed render requires failure code")
        return self


class TechnicalCheck(StrictContract):
    check_id: StableName
    status: Annotated[str, Field(pattern=r"^(passed|failed|blocked|unavailable)$")]
    measured: JsonObject
    profile_ref: ArtifactRef
    blocker: bool
    detail: Annotated[str, Field(min_length=1, max_length=2_048)]


class TechnicalQCReport(StrictContract):
    candidate_ref: ArtifactRef
    checks: tuple[TechnicalCheck, ...]
    blocker_codes: tuple[StableName, ...] = ()
    passed: bool

    @model_validator(mode="after")
    def blockers_dominate_qc(self) -> Self:
        has_blocker = bool(self.blocker_codes) or any(
            check.blocker and check.status != "passed" for check in self.checks
        )
        if self.passed == has_blocker:
            raise ValueError("technical QC pass state must be the inverse of blockers")
        return self


class RightsManifestEntry(StrictContract):
    asset_ref: ArtifactRef
    role: StableName
    rights: RightsMetadata
    release_blockers: tuple[StableName, ...] = ()


class ReleaseRightsManifest(StrictContract):
    candidate_ref: ArtifactRef
    platform: StableName
    territory: StableName
    evaluated_at: datetime
    entries: tuple[RightsManifestEntry, ...]
    blocker_codes: tuple[StableName, ...] = ()

    @model_validator(mode="after")
    def require_complete_cleared_manifest(self) -> Self:
        if not self.entries:
            raise ValueError("release rights manifest cannot be empty")
        if any(entry.release_blockers for entry in self.entries) and not self.blocker_codes:
            raise ValueError("asset rights blockers must propagate to manifest")
        return self


class QualityDimensionScore(StrictContract):
    dimension: StableName
    score: Annotated[float, Field(ge=0.0, le=5.0)]
    evidence: tuple[Annotated[str, Field(min_length=1, max_length=2_048)], ...]


class OfflineQualityReview(StrictContract):
    candidate_ref: ArtifactRef
    rubric_profile_ref: ArtifactRef
    dimension_scores: tuple[QualityDimensionScore, ...]
    weighted_score: Annotated[float, Field(ge=0.0, le=100.0)]
    blocker_codes: tuple[StableName, ...] = ()
    verdict: Annotated[str, Field(pattern=r"^(pass|revise|reject)$")]

    @model_validator(mode="after")
    def blockers_force_reject(self) -> Self:
        if self.blocker_codes and self.verdict != "reject":
            raise ValueError("offline quality blockers require reject")
        return self


class FinalCandidate(StrictContract):
    render_plan_ref: ArtifactRef
    execution_report_ref: ArtifactRef
    media_blob_ref: StableName
    checksum: StableName
    duration: RationalTime
    technical_qc_ref: ArtifactRef
    rights_manifest_ref: ArtifactRef
    quality_review_ref: ArtifactRef


class ReleaseReviewPackage(StrictContract):
    final_candidate_ref: ArtifactRef
    candidate_checksum: StableName
    technical_qc_ref: ArtifactRef
    rights_manifest_ref: ArtifactRef
    quality_review_ref: ArtifactRef
    blocker_codes: tuple[StableName, ...] = ()
    incomplete: bool = False


class ReleaseRecord(StrictContract):
    final_candidate_ref: ArtifactRef
    candidate_checksum: StableName
    release_decision_ref: ArtifactRef
    approved_by: ActorRef
    approved_at: datetime
    platform_profile_ref: ArtifactRef
    rights_manifest_ref: ArtifactRef

    @model_validator(mode="after")
    def require_human_approval(self) -> Self:
        if self.approved_by.kind.value != "human":
            raise ValueError("release record requires human approver")
        return self
