"""Typed Speech observations; speaker clusters are never character identities."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, model_validator

from packages.contracts.base import StrictContract
from packages.contracts.evidence import ConfidenceRecord
from packages.contracts.foundation import UUID, ArtifactRef, ProviderIdentity, StableName, TimeRange


class SpeechObservationStatus(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    UNAVAILABLE = "unavailable"


class AlignmentGranularity(StrEnum):
    SEGMENT = "segment"
    WORD = "word"
    CHARACTER = "character"


class VADSegment(StrictContract):
    segment_id: UUID
    source_range: TimeRange
    padded_range: TimeRange | None = None
    speech_probability: Annotated[float, Field(ge=0.0, le=1.0)] | None = None

    @model_validator(mode="after")
    def require_non_empty(self) -> Self:
        if self.source_range.is_empty:
            raise ValueError("VAD segment range must be non-empty")
        return self


class AlignedToken(StrictContract):
    token_id: UUID
    text: Annotated[str, Field(min_length=1, max_length=512)]
    source_range: TimeRange
    granularity: AlignmentGranularity
    estimated_error_ms: Annotated[int, Field(ge=0, le=60_000)]
    confidence: ConfidenceRecord


class TranscriptSegment(StrictContract):
    segment_id: UUID
    source_range: TimeRange
    raw_text: Annotated[str, Field(min_length=1, max_length=32_768)]
    normalized_text: Annotated[str, Field(min_length=1, max_length=32_768)]
    language: StableName | None = None
    tokens: tuple[AlignedToken, ...] = ()
    speaker_cluster_id: StableName | None = None
    confidence: ConfidenceRecord

    @model_validator(mode="after")
    def validate_range_and_tokens(self) -> Self:
        if self.source_range.is_empty:
            raise ValueError("transcript range must be non-empty")
        if any(
            token.source_range.start.seconds < self.source_range.start.seconds
            or token.source_range.end_seconds > self.source_range.end_seconds
            for token in self.tokens
        ):
            raise ValueError("aligned token must remain inside transcript range")
        return self


class SpeakerObservation(StrictContract):
    observation_id: UUID
    cluster_id: StableName
    source_ranges: tuple[TimeRange, ...]
    provider: ProviderIdentity
    confidence: ConfidenceRecord

    @model_validator(mode="after")
    def require_ranges(self) -> Self:
        if not self.source_ranges or any(item.is_empty for item in self.source_ranges):
            raise ValueError("speaker observation requires non-empty ranges")
        return self


class SpeechConflict(StrictContract):
    conflict_id: UUID
    conflict_type: StableName
    source_range: TimeRange
    candidate_refs: tuple[ArtifactRef, ...]
    detail: Annotated[str, Field(min_length=1, max_length=2_048)]


class SpeechObservation(StrictContract):
    source_audio_ref: ArtifactRef
    raw_response_ref: ArtifactRef
    provider: ProviderIdentity
    vad_segments: tuple[VADSegment, ...]
    transcripts: tuple[TranscriptSegment, ...]
    speakers: tuple[SpeakerObservation, ...] = ()
    conflicts: tuple[SpeechConflict, ...] = ()
    status: SpeechObservationStatus
    unavailable_reasons: tuple[StableName, ...] = ()

    @model_validator(mode="after")
    def enforce_status(self) -> Self:
        ids = [item.segment_id for item in self.transcripts]
        if len(ids) != len(set(ids)):
            raise ValueError("transcript segment ids must be unique")
        if self.status is SpeechObservationStatus.UNAVAILABLE:
            if self.transcripts or not self.unavailable_reasons:
                raise ValueError("unavailable speech requires reasons and no transcripts")
        elif self.unavailable_reasons and self.status is not SpeechObservationStatus.INCOMPLETE:
            raise ValueError("unavailable reasons require incomplete status")
        return self
