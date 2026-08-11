"""Pure semantic patch, optimistic conflict and deterministic diff engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from packages.contracts import (
    MasterTimeline,
    PatchOperationType,
    TimelineItem,
    TimelinePatch,
    TimelineTrack,
    TimeRange,
)


class TimelinePatchConflict(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class TimelineChange:
    item_id: UUID
    change: str
    before_version: int | None
    after_version: int | None


def _locate(tracks: list[TimelineTrack], item_id: UUID) -> tuple[int, int, TimelineItem]:
    for track_index, track in enumerate(tracks):
        for item_index, item in enumerate(track.items):
            if item.item_id == item_id:
                return track_index, item_index, item
    raise TimelinePatchConflict(f"timeline item does not exist: {item_id}")


def _replace_track_items(
    tracks: list[TimelineTrack], track_index: int, items: list[TimelineItem]
) -> None:
    tracks[track_index] = tracks[track_index].model_copy(update={"items": tuple(items)})


def _payload_range(payload: dict[str, Any], key: str) -> TimeRange:
    try:
        return TimeRange.model_validate(payload[key])
    except (KeyError, ValidationError) as error:
        raise TimelinePatchConflict(f"invalid {key}") from error


def apply_patch(timeline: MasterTimeline, patch: TimelinePatch) -> MasterTimeline:
    tracks = list(timeline.tracks)
    for operation in patch.operations:
        if operation.op is PatchOperationType.INSERT:
            try:
                track_id = UUID(str(operation.payload["track_id"]))
                item = TimelineItem.model_validate(operation.payload["item"])
            except (KeyError, ValueError, ValidationError) as error:
                raise TimelinePatchConflict("invalid insert payload") from error
            track_index = next(
                (index for index, track in enumerate(tracks) if track.track_id == track_id), None
            )
            if track_index is None:
                raise TimelinePatchConflict("insert track does not exist")
            items = [*tracks[track_index].items, item]
            items.sort(key=lambda candidate: candidate.timeline_range.start.seconds)
            _replace_track_items(tracks, track_index, items)
            continue
        if operation.target_item_id is None or operation.expected_item_version is None:
            raise TimelinePatchConflict("operation lacks compare-and-swap target")
        track_index, item_index, item = _locate(tracks, operation.target_item_id)
        if item.item_version != operation.expected_item_version:
            raise TimelinePatchConflict(
                f"stale item {item.item_id}: expected {operation.expected_item_version}, "
                f"actual {item.item_version}"
            )
        items = list(tracks[track_index].items)
        if operation.op is PatchOperationType.REMOVE:
            del items[item_index]
        elif operation.op is PatchOperationType.REPLACE:
            try:
                replacement = TimelineItem.model_validate(operation.payload["item"])
            except (KeyError, ValidationError) as error:
                raise TimelinePatchConflict("invalid replacement item") from error
            if replacement.item_id != item.item_id:
                raise TimelinePatchConflict("replacement must preserve item_id")
            items[item_index] = replacement.model_copy(
                update={"item_version": item.item_version + 1}
            )
        elif operation.op in {PatchOperationType.MOVE, PatchOperationType.RETIME}:
            timeline_range = _payload_range(operation.payload, "timeline_range")
            items[item_index] = item.model_copy(
                update={"timeline_range": timeline_range, "item_version": item.item_version + 1}
            )
        elif operation.op is PatchOperationType.TRIM:
            timeline_range = _payload_range(operation.payload, "timeline_range")
            source_range = (
                _payload_range(operation.payload, "source_range")
                if item.source_range is not None
                else None
            )
            items[item_index] = item.model_copy(
                update={
                    "timeline_range": timeline_range,
                    "source_range": source_range,
                    "item_version": item.item_version + 1,
                }
            )
        elif operation.op is PatchOperationType.SET_PARAMETER:
            key = operation.payload.get("key")
            if not isinstance(key, str) or not key:
                raise TimelinePatchConflict("parameter key is required")
            parameters = dict(item.parameters)
            parameters[key] = operation.payload.get("value")
            items[item_index] = item.model_copy(
                update={"parameters": parameters, "item_version": item.item_version + 1}
            )
        elif operation.op is PatchOperationType.SPLIT:
            try:
                left = TimelineItem.model_validate(operation.payload["left"])
                right = TimelineItem.model_validate(operation.payload["right"])
            except (KeyError, ValidationError) as error:
                raise TimelinePatchConflict("invalid split payload") from error
            if left.item_id != item.item_id or right.item_id == item.item_id:
                raise TimelinePatchConflict("split must preserve left id and create a new right id")
            items[item_index : item_index + 1] = [
                left.model_copy(update={"item_version": item.item_version + 1}),
                right,
            ]
        else:
            raise TimelinePatchConflict(f"unsupported operation: {operation.op}")
        items.sort(key=lambda candidate: candidate.timeline_range.start.seconds)
        _replace_track_items(tracks, track_index, items)
    try:
        return MasterTimeline.model_validate(
            timeline.model_dump(mode="python") | {"tracks": tracks}
        )
    except ValidationError as error:
        raise TimelinePatchConflict("patch produced an invalid timeline") from error


def semantic_diff(before: MasterTimeline, after: MasterTimeline) -> tuple[TimelineChange, ...]:
    old = {item.item_id: item for track in before.tracks for item in track.items}
    new = {item.item_id: item for track in after.tracks for item in track.items}
    changes: list[TimelineChange] = []
    for item_id in sorted(set(old) | set(new), key=str):
        if item_id not in old:
            changes.append(TimelineChange(item_id, "inserted", None, new[item_id].item_version))
        elif item_id not in new:
            changes.append(TimelineChange(item_id, "removed", old[item_id].item_version, None))
        elif old[item_id] != new[item_id]:
            changes.append(
                TimelineChange(
                    item_id, "modified", old[item_id].item_version, new[item_id].item_version
                )
            )
    return tuple(changes)


def can_rebase(patch: TimelinePatch, changes_since_base: tuple[TimelineChange, ...]) -> bool:
    touched = {
        operation.target_item_id for operation in patch.operations if operation.target_item_id
    }
    changed = {change.item_id for change in changes_since_base}
    return touched.isdisjoint(changed)
