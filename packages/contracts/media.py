"""Canonical media catalog contracts; these describe media without story inference."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, model_validator

from packages.contracts.base import StrictContract
from packages.contracts.envelopes import JsonObject
from packages.contracts.evidence import ConfidenceRecord
from packages.contracts.foundation import (
    UUID,
    ArtifactRef,
    Checksum,
    PositiveInt64,
    ProviderIdentity,
    RationalTime,
    StableName,
    TimeRange,
)
from packages.contracts.rights import RightsMetadata


class MediaRole(StrEnum):
    SOURCE = "source"
    PROXY = "proxy"
    FRAME = "frame"
    ORIGINAL_AUDIO = "original_audio"
    VOICE = "voice"
    BGM = "bgm"
    SFX = "sfx"
    RENDER = "render"


class VideoStream(StrictContract):
    stream_index: Annotated[int, Field(ge=0)]
    codec: StableName
    width: Annotated[int, Field(gt=0)]
    height: Annotated[int, Field(gt=0)]
    pixel_format: StableName
    time_base_num: Annotated[int, Field(gt=0)]
    time_base_den: Annotated[int, Field(gt=0)]
    frame_rate_num: Annotated[int, Field(gt=0)] | None = None
    frame_rate_den: Annotated[int, Field(gt=0)] | None = None
    rotation_degrees: Annotated[int, Field(ge=-359, le=359)] = 0
    variable_frame_rate: bool = False

    @model_validator(mode="after")
    def require_complete_frame_rate(self) -> Self:
        if (self.frame_rate_num is None) != (self.frame_rate_den is None):
            raise ValueError("frame rate numerator and denominator must appear together")
        return self


class AudioStream(StrictContract):
    stream_index: Annotated[int, Field(ge=0)]
    codec: StableName
    sample_rate: Annotated[int, Field(gt=0)]
    channels: Annotated[int, Field(gt=0)]
    channel_layout: StableName | None = None


class MediaTechnicalMetadata(StrictContract):
    duration: RationalTime
    start_time: RationalTime
    format_name: StableName
    mime_type: Annotated[str, Field(min_length=1, max_length=255)]
    byte_size: Annotated[int, Field(ge=0, le=2**63 - 1)]
    video_streams: tuple[VideoStream, ...] = ()
    audio_streams: tuple[AudioStream, ...] = ()

    @model_validator(mode="after")
    def require_media_stream(self) -> Self:
        if self.duration.value < 0:
            raise ValueError("media duration must be non-negative")
        if not self.video_streams and not self.audio_streams:
            raise ValueError("media must contain at least one audio or video stream")
        indexes = [item.stream_index for item in self.video_streams]
        indexes.extend(item.stream_index for item in self.audio_streams)
        if len(indexes) != len(set(indexes)):
            raise ValueError("stream indexes must be unique")
        return self


class MediaAsset(StrictContract):
    asset_id: UUID
    episode_id: UUID | None = None
    role: MediaRole
    uri: Annotated[str, Field(min_length=1, max_length=4_096)]
    checksum: Checksum
    technical: MediaTechnicalMetadata
    rights: RightsMetadata
    source_ref: ArtifactRef | None = None
    derivation_profile_ref: ArtifactRef | None = None
    source_to_proxy_map_ref: ArtifactRef | None = None

    @model_validator(mode="after")
    def require_derivation_source(self) -> Self:
        if self.role is MediaRole.SOURCE and self.source_ref is not None:
            raise ValueError("source media cannot declare a derivation source")
        if self.role is not MediaRole.SOURCE and self.source_ref is None:
            raise ValueError("derived media requires source_ref")
        return self


class Episode(StrictContract):
    episode_id: UUID
    series_id: UUID
    sequence: PositiveInt64
    title: Annotated[str, Field(min_length=1, max_length=512)]
    source_media_ref: ArtifactRef


class EpisodeCatalog(StrictContract):
    series_id: UUID
    episodes: tuple[Episode, ...]

    @model_validator(mode="after")
    def require_unique_order_and_identity(self) -> Self:
        ids = [item.episode_id for item in self.episodes]
        order = [item.sequence for item in self.episodes]
        if len(ids) != len(set(ids)) or len(order) != len(set(order)):
            raise ValueError("episode ids and sequence values must be unique")
        if any(item.series_id != self.series_id for item in self.episodes):
            raise ValueError("all episodes must belong to the catalog series")
        return self


class SegmentKind(StrEnum):
    SCENE = "scene"
    SHOT = "shot"


class DetectionStatus(StrEnum):
    DETECTED = "detected"
    CORRECTED = "corrected"
    APPROVED = "approved"


class SceneShot(StrictContract):
    segment_id: UUID
    kind: SegmentKind
    source: ArtifactRef
    source_range: TimeRange
    detector: ProviderIdentity
    confidence: ConfidenceRecord
    status: DetectionStatus
    parent_scene_id: UUID | None = None

    @model_validator(mode="after")
    def enforce_hierarchy(self) -> Self:
        if self.kind is SegmentKind.SCENE and self.parent_scene_id is not None:
            raise ValueError("scene cannot have parent_scene_id")
        if self.source_range.is_empty:
            raise ValueError("scene/shot range must be non-empty")
        return self


class SceneShotCatalog(StrictContract):
    source: ArtifactRef
    segments: tuple[SceneShot, ...]

    @model_validator(mode="after")
    def require_consistent_source_and_ids(self) -> Self:
        if any(item.source != self.source for item in self.segments):
            raise ValueError("all segments must reference the catalog source")
        ids = [item.segment_id for item in self.segments]
        if len(ids) != len(set(ids)):
            raise ValueError("scene/shot ids must be unique")
        return self


class SamplingPurpose(StrEnum):
    OCR = "ocr"
    IDENTITY = "identity"
    VLM = "vlm"
    QUALITY = "quality"


class FrameSample(StrictContract):
    sample_id: UUID
    source_time: RationalTime
    frame_index: Annotated[int, Field(ge=0)] | None = None
    reason: StableName


class FrameSamplePlan(StrictContract):
    source: ArtifactRef
    purpose: SamplingPurpose
    profile_ref: ArtifactRef
    samples: tuple[FrameSample, ...]
    parameters: JsonObject = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_unique_samples(self) -> Self:
        ids = [item.sample_id for item in self.samples]
        if len(ids) != len(set(ids)):
            raise ValueError("frame sample ids must be unique")
        return self
