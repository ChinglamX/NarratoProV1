"""Typed visual observations; candidates never imply identity or story truth."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, model_validator

from packages.contracts.base import StrictContract
from packages.contracts.evidence import ConfidenceRecord
from packages.contracts.foundation import (
    UUID,
    ArtifactRef,
    ProviderIdentity,
    RationalTime,
    StableName,
)


class VisualObservationStatus(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    UNAVAILABLE = "unavailable"


class TextRegionKind(StrEnum):
    BURNED_IN_SUBTITLE = "burned_in_subtitle"
    SCENE_TEXT = "scene_text"
    GRAPHIC_OVERLAY = "graphic_overlay"
    UNKNOWN = "unknown"


class VLMClaimKind(StrEnum):
    VISIBLE = "visible"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


UnitFloat = Annotated[float, Field(ge=0.0, le=1.0)]


class BoundingBox(StrictContract):
    x_min: UnitFloat
    y_min: UnitFloat
    x_max: UnitFloat
    y_max: UnitFloat

    @model_validator(mode="after")
    def require_positive_area(self) -> Self:
        if self.x_max <= self.x_min or self.y_max <= self.y_min:
            raise ValueError("bounding box requires positive normalized area")
        return self


class FrameEvidence(StrictContract):
    frame_ref: ArtifactRef
    sample_id: UUID
    source_time: RationalTime


class OCRObservation(StrictContract):
    observation_id: UUID
    frame: FrameEvidence
    text: Annotated[str, Field(min_length=1, max_length=16_384)]
    region: BoundingBox
    kind: TextRegionKind
    provider: ProviderIdentity
    confidence: ConfidenceRecord


class TextTrack(StrictContract):
    track_id: UUID
    text: Annotated[str, Field(min_length=1, max_length=16_384)]
    kind: TextRegionKind
    observations: tuple[OCRObservation, ...]
    provider: ProviderIdentity
    confidence: ConfidenceRecord

    @model_validator(mode="after")
    def require_ordered_observations(self) -> Self:
        if not self.observations:
            raise ValueError("text track requires observations")
        times = [item.frame.source_time.seconds for item in self.observations]
        if times != sorted(times):
            raise ValueError("text track observations must be source-time ordered")
        return self


class DetectionObservation(StrictContract):
    observation_id: UUID
    frame: FrameEvidence
    label: StableName
    region: BoundingBox
    provider: ProviderIdentity
    confidence: ConfidenceRecord


class TrackPoint(StrictContract):
    detection_id: UUID
    frame: FrameEvidence
    region: BoundingBox


class Tracklet(StrictContract):
    tracklet_id: UUID
    shot_ref: ArtifactRef
    label: StableName
    points: tuple[TrackPoint, ...]
    detection_coverage: UnitFloat
    occlusion_ratio: UnitFloat
    representative_frame_ref: ArtifactRef
    provider: ProviderIdentity
    confidence: ConfidenceRecord

    @model_validator(mode="after")
    def require_ordered_points(self) -> Self:
        if not self.points:
            raise ValueError("tracklet requires points")
        times = [point.frame.source_time.seconds for point in self.points]
        if times != sorted(times):
            raise ValueError("tracklet points must be source-time ordered")
        return self


class FaceObservation(StrictContract):
    observation_id: UUID
    frame: FrameEvidence
    region: BoundingBox
    pose: StableName | None = None
    quality_score: UnitFloat
    appearance_embedding_ref: ArtifactRef | None = None
    provider: ProviderIdentity
    confidence: ConfidenceRecord


class VisualEmbedding(StrictContract):
    embedding_id: UUID
    frame: FrameEvidence
    region: BoundingBox | None = None
    vector: tuple[float, ...]
    dimensions: Annotated[int, Field(gt=0, le=65_536)]
    normalized: bool
    provider: ProviderIdentity

    @model_validator(mode="after")
    def require_dimension_match(self) -> Self:
        if len(self.vector) != self.dimensions:
            raise ValueError("embedding dimensions must match vector length")
        return self


class VLMClaim(StrictContract):
    claim_id: UUID
    kind: VLMClaimKind
    statement: Annotated[str, Field(min_length=1, max_length=4_096)]
    frame_evidence: tuple[FrameEvidence, ...]
    confidence: ConfidenceRecord

    @model_validator(mode="after")
    def require_visible_evidence(self) -> Self:
        if self.kind is VLMClaimKind.VISIBLE and not self.frame_evidence:
            raise ValueError("visible VLM claims require frame evidence")
        return self


class SupplementarySampleRequest(StrictContract):
    request_id: UUID
    source_ref: ArtifactRef
    shot_ref: ArtifactRef
    reason: StableName
    expected_uncertainty_reduction: Annotated[str, Field(min_length=1, max_length=2_048)]
    requested_times: tuple[RationalTime, ...]
    remaining_shot_budget: Annotated[int, Field(ge=0, le=10_000)]

    @model_validator(mode="after")
    def require_bounded_request(self) -> Self:
        if not self.requested_times:
            raise ValueError("supplementary sample request requires times")
        if len(self.requested_times) > self.remaining_shot_budget:
            raise ValueError("supplementary sample request exceeds remaining budget")
        return self


class VisualQualityReport(StrictContract):
    frame: FrameEvidence
    blur_score: Annotated[float, Field(ge=0.0)]
    mean_luminance: UnitFloat
    contrast: UnitFloat
    usable_for_identity: bool
    provider: ProviderIdentity


class VisualObservation(StrictContract):
    source_ref: ArtifactRef
    frame_plan_ref: ArtifactRef
    raw_response_refs: tuple[ArtifactRef, ...]
    ocr: tuple[OCRObservation, ...] = ()
    text_tracks: tuple[TextTrack, ...] = ()
    detections: tuple[DetectionObservation, ...] = ()
    tracklets: tuple[Tracklet, ...] = ()
    faces: tuple[FaceObservation, ...] = ()
    embeddings: tuple[VisualEmbedding, ...] = ()
    vlm_claims: tuple[VLMClaim, ...] = ()
    quality: tuple[VisualQualityReport, ...] = ()
    supplementary_requests: tuple[SupplementarySampleRequest, ...] = ()
    status: VisualObservationStatus
    unavailable_capabilities: tuple[StableName, ...] = ()

    @model_validator(mode="after")
    def enforce_status_and_ids(self) -> Self:
        if self.status is VisualObservationStatus.UNAVAILABLE:
            if not self.unavailable_capabilities:
                raise ValueError("unavailable visual observation requires capabilities")
            if any(
                (
                    self.ocr,
                    self.text_tracks,
                    self.detections,
                    self.tracklets,
                    self.faces,
                    self.embeddings,
                    self.vlm_claims,
                )
            ):
                raise ValueError("unavailable visual observation cannot contain model observations")
        identities = [
            *(item.observation_id for item in self.ocr),
            *(item.observation_id for item in self.detections),
            *(item.observation_id for item in self.faces),
            *(item.embedding_id for item in self.embeddings),
            *(item.claim_id for item in self.vlm_claims),
        ]
        if len(identities) != len(set(identities)):
            raise ValueError("visual observation child ids must be unique")
        return self
