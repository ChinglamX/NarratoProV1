"""Canonical master-timeline, item, marker, patch, and conflict contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, model_validator

from packages.contracts.base import StrictContract
from packages.contracts.envelopes import JsonObject
from packages.contracts.foundation import (
    UUID,
    ActorRef,
    ArtifactRef,
    PositiveInt64,
    RationalTime,
    StableName,
    TimeRange,
)


class TimelineTrackKind(StrEnum):
    VIDEO = "video"
    ORIGINAL_AUDIO = "original_audio"
    NARRATION = "narration"
    BGM = "bgm"
    SFX = "sfx"
    SUBTITLE = "subtitle"
    OVERLAY = "overlay"


class TimelineItemType(StrEnum):
    CLIP = "clip"
    GAP = "gap"
    TRANSITION = "transition"
    TEXT = "text"
    EFFECT = "effect"


class TimelineItem(StrictContract):
    item_id: UUID
    item_version: PositiveInt64
    item_type: TimelineItemType
    timeline_range: TimeRange
    source_ref: ArtifactRef | None = None
    source_range: TimeRange | None = None
    content_ref: StableName | None = None
    parameters: JsonObject = Field(default_factory=dict)
    evidence_refs: tuple[UUID, ...] = ()
    generation_dependencies: tuple[ArtifactRef, ...] = ()
    locked: bool = False

    @model_validator(mode="after")
    def validate_source_and_duration(self) -> Self:
        if self.timeline_range.is_empty:
            raise ValueError("timeline item duration must be positive")
        if (self.source_ref is None) != (self.source_range is None):
            raise ValueError("source_ref and source_range must appear together")
        if self.item_type is TimelineItemType.CLIP and self.source_ref is None:
            raise ValueError("clip requires source_ref and source_range")
        if self.item_type is TimelineItemType.GAP and (
            self.source_ref is not None or self.content_ref is not None
        ):
            raise ValueError("gap cannot reference source or content")
        return self


class TimelineTrack(StrictContract):
    track_id: UUID
    kind: TimelineTrackKind
    order: Annotated[int, Field(ge=0)]
    items: tuple[TimelineItem, ...]

    @model_validator(mode="after")
    def require_unique_items(self) -> Self:
        ids = [item.item_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("timeline item ids must be unique within a track")
        return self


class TimelineMarker(StrictContract):
    marker_id: UUID
    position: RationalTime
    marker_type: StableName
    label: Annotated[str, Field(min_length=1, max_length=1_024)]
    metadata: JsonObject = Field(default_factory=dict)


class TimelineLifecycle(StrEnum):
    DRAFT = "draft"
    APPROVED_INTENT = "approved_intent"
    CONFORMED = "conformed"


class MasterTimeline(StrictContract):
    timeline_id: UUID
    lifecycle: TimelineLifecycle
    rate_num: Annotated[int, Field(gt=0)]
    rate_den: Annotated[int, Field(gt=0)] = 1
    global_start: RationalTime
    duration: RationalTime
    tracks: tuple[TimelineTrack, ...]
    markers: tuple[TimelineMarker, ...] = ()
    dependencies: tuple[ArtifactRef, ...] = ()
    metadata_namespace_version: Annotated[str, Field(min_length=1, max_length=128)]

    @model_validator(mode="after")
    def validate_timeline_identity_and_bounds(self) -> Self:
        if self.duration.value <= 0:
            raise ValueError("master timeline duration must be positive")
        track_ids = [item.track_id for item in self.tracks]
        track_orders = [item.order for item in self.tracks]
        if len(track_ids) != len(set(track_ids)) or len(track_orders) != len(set(track_orders)):
            raise ValueError("timeline track ids and orders must be unique")
        item_ids = [item.item_id for track in self.tracks for item in track.items]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("timeline item ids must be globally unique")
        start = self.global_start.seconds
        end = start + self.duration.seconds
        if any(
            item.timeline_range.start.seconds < start or item.timeline_range.end_seconds > end
            for track in self.tracks
            for item in track.items
        ):
            raise ValueError("timeline item falls outside master timeline bounds")
        if any(
            marker.position.seconds < start or marker.position.seconds > end
            for marker in self.markers
        ):
            raise ValueError("timeline marker falls outside master timeline bounds")
        return self


class PatchOperationType(StrEnum):
    INSERT = "insert"
    REMOVE = "remove"
    MOVE = "move"
    TRIM = "trim"
    SPLIT = "split"
    REPLACE = "replace"
    RETIME = "retime"
    SET_PARAMETER = "set_parameter"


class TimelinePatchOperation(StrictContract):
    operation_id: UUID
    op: PatchOperationType
    target_item_id: UUID | None = None
    expected_item_version: PositiveInt64 | None = None
    payload: JsonObject

    @model_validator(mode="after")
    def require_compare_and_swap_target(self) -> Self:
        if self.op is PatchOperationType.INSERT:
            if self.target_item_id is not None or self.expected_item_version is not None:
                raise ValueError("insert cannot target an existing item version")
        elif self.target_item_id is None or self.expected_item_version is None:
            raise ValueError("non-insert operation requires target and expected item version")
        return self


class TimelinePatch(StrictContract):
    patch_id: UUID
    base_timeline: ArtifactRef
    operations: tuple[TimelinePatchOperation, ...]
    author: ActorRef
    reason: Annotated[str, Field(min_length=1, max_length=4_096)]

    @model_validator(mode="after")
    def require_operations_and_unique_ids(self) -> Self:
        if not self.operations:
            raise ValueError("timeline patch requires at least one operation")
        ids = [item.operation_id for item in self.operations]
        if len(ids) != len(set(ids)):
            raise ValueError("timeline patch operation ids must be unique")
        return self


class TimelineConflict(StrictContract):
    conflict_id: UUID
    patch_ref: ArtifactRef
    base_timeline_ref: ArtifactRef
    current_timeline_ref: ArtifactRef
    operation_id: UUID
    conflict_type: StableName
    expected_item_version: PositiveInt64 | None = None
    actual_item_version: PositiveInt64 | None = None
    resolution_required: bool = True
