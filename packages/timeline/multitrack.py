"""Compile creative intents into the single canonical multi-track Master Timeline."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from packages.contracts import (
    ArtifactRef,
    MasterTimeline,
    RationalTime,
    TimelineItem,
    TimelineTrack,
    TimeRange,
)
from packages.contracts.timeline import TimelineItemType, TimelineLifecycle, TimelineTrackKind
from packages.contracts.timeline_intent import (
    AssemblyConflict,
    AudioIntent,
    AudioIntentRole,
    ClipCandidate,
    ClipSelectionPlan,
    NarrationLineSet,
    OverlayIntent,
    SubtitleIntent,
    TimelineAssemblyReport,
)


class TimelineAssemblyError(RuntimeError):
    pass


TRACK_ORDER = {
    TimelineTrackKind.VIDEO: 0,
    TimelineTrackKind.ORIGINAL_AUDIO: 1,
    TimelineTrackKind.NARRATION: 2,
    TimelineTrackKind.BGM: 3,
    TimelineTrackKind.SFX: 4,
    TimelineTrackKind.SUBTITLE: 5,
    TimelineTrackKind.OVERLAY: 6,
}


def assemble_multitrack_timeline(
    *,
    timeline_id: UUID,
    selections: ClipSelectionPlan,
    candidates: Sequence[ClipCandidate],
    narration: NarrationLineSet,
    audio_intents: Sequence[AudioIntent],
    subtitle_intents: Sequence[SubtitleIntent],
    overlay_intents: Sequence[OverlayIntent],
    dependencies: tuple[ArtifactRef, ...],
    track_ids: dict[TimelineTrackKind, UUID],
    item_ids: Sequence[UUID],
    duration: RationalTime,
    revision_budget: int = 3,
) -> tuple[MasterTimeline | None, TimelineAssemblyReport]:
    timeline_duration = duration
    candidate_by_id = {item.candidate_id: item for item in candidates}
    conflicts: list[AssemblyConflict] = []
    cursor = timeline_duration.model_copy(update={"value": 0})
    video_items: list[TimelineItem] = []
    for selection in selections.selections:
        candidate = candidate_by_id.get(selection.candidate_id)
        if candidate is None:
            raise TimelineAssemblyError("selection candidate is unavailable")
        selected_duration = selection.selected_range.duration
        video_items.append(
            TimelineItem(
                item_id=item_ids[len(video_items)],
                item_version=1,
                item_type=TimelineItemType.CLIP,
                timeline_range=TimeRange(start=cursor, duration=selected_duration),
                source_ref=candidate.source_ref,
                source_range=selection.selected_range,
                parameters={"beat_id": str(selection.beat_id), "intent_state": "planned"},
                evidence_refs=candidate.evidence_refs,
                generation_dependencies=dependencies,
            )
        )
        cursor = cursor.model_copy(update={"value": cursor.value + selected_duration.value})
    if cursor.seconds != timeline_duration.seconds:
        conflicts.append(
            AssemblyConflict(
                code="video-duration-mismatch",
                owner="rhythm",
                affected_range=TimeRange(
                    start=timeline_duration.model_copy(update={"value": 0}),
                    duration=timeline_duration,
                ),
                explanation="selected clip duration does not equal approved timeline duration",
                blocker=True,
                allowed_reflow_scope=3,
            )
        )

    id_cursor = len(video_items)
    tracks = [_track(track_ids, TimelineTrackKind.VIDEO, video_items)]
    grouped: dict[TimelineTrackKind, list[TimelineItem]] = {
        kind: [] for kind in TRACK_ORDER if kind is not TimelineTrackKind.VIDEO
    }
    for intent in audio_intents:
        kind = {
            AudioIntentRole.ORIGINAL: TimelineTrackKind.ORIGINAL_AUDIO,
            AudioIntentRole.NARRATION: TimelineTrackKind.NARRATION,
            AudioIntentRole.BGM: TimelineTrackKind.BGM,
            AudioIntentRole.SFX: TimelineTrackKind.SFX,
        }[intent.role]
        source_range = intent.timeline_range if intent.source_ref is not None else None
        grouped[kind].append(
            TimelineItem(
                item_id=item_ids[id_cursor],
                item_version=1,
                item_type=TimelineItemType.CLIP if intent.source_ref else TimelineItemType.EFFECT,
                timeline_range=intent.timeline_range,
                source_ref=intent.source_ref,
                source_range=source_range,
                content_ref=intent.content_ref,
                parameters={
                    "role": intent.role.value,
                    "duck_under_narration": intent.duck_under_narration,
                    "gain_db": intent.gain_db,
                    "intent_state": "planned",
                },
                generation_dependencies=dependencies,
            )
        )
        id_cursor += 1
    for line in narration.lines:
        grouped[TimelineTrackKind.NARRATION].append(
            TimelineItem(
                item_id=item_ids[id_cursor],
                item_version=1,
                item_type=TimelineItemType.TEXT,
                timeline_range=TimeRange(
                    start=_line_start(narration, line.line_id), duration=line.target_duration
                ),
                content_ref=str(line.line_id),
                parameters={
                    "text": line.text,
                    "intent_state": "placeholder",
                    "locked": line.locked,
                },
                evidence_refs=line.evidence_refs,
                generation_dependencies=dependencies,
                locked=line.locked,
            )
        )
        id_cursor += 1
    for subtitle in subtitle_intents:
        grouped[TimelineTrackKind.SUBTITLE].append(
            TimelineItem(
                item_id=item_ids[id_cursor],
                item_version=1,
                item_type=TimelineItemType.TEXT,
                timeline_range=subtitle.timeline_range,
                content_ref=str(subtitle.line_id),
                parameters={
                    "text": subtitle.text,
                    "safe_area": subtitle.safe_area,
                    "style_ref": subtitle.style_ref.model_dump(mode="json"),
                    "intent_state": "layout_proxy",
                },
                evidence_refs=subtitle.evidence_refs,
                generation_dependencies=dependencies,
            )
        )
        id_cursor += 1
    for overlay in overlay_intents:
        grouped[TimelineTrackKind.OVERLAY].append(
            TimelineItem(
                item_id=item_ids[id_cursor],
                item_version=1,
                item_type=TimelineItemType.EFFECT,
                timeline_range=overlay.timeline_range,
                content_ref=overlay.content_ref,
                parameters={
                    "overlay_type": overlay.overlay_type,
                    "safe_area": overlay.safe_area,
                    "style_ref": overlay.style_ref.model_dump(mode="json"),
                    "intent_state": "layout_proxy",
                },
                generation_dependencies=dependencies,
            )
        )
        id_cursor += 1
    if id_cursor != len(item_ids):
        raise TimelineAssemblyError("preallocated item IDs do not match assembled items")
    for kind, items in grouped.items():
        if items:
            tracks.append(_track(track_ids, kind, items))
    report = TimelineAssemblyReport(
        track_kinds=tuple(track.kind.value for track in tracks),
        conflicts=tuple(conflicts),
        invalidated_artifact_types=(
            "VoiceAsset",
            "AlignmentArtifact",
            "SubtitleCueSet",
            "MixedAudio",
            "RenderPlan",
        ),
        revision_budget=revision_budget,
    )
    if any(conflict.blocker for conflict in conflicts):
        return None, report
    return MasterTimeline(
        timeline_id=timeline_id,
        lifecycle=TimelineLifecycle.DRAFT,
        rate_num=timeline_duration.rate_num,
        rate_den=timeline_duration.rate_den,
        global_start=timeline_duration.model_copy(update={"value": 0}),
        duration=timeline_duration,
        tracks=tuple(sorted(tracks, key=lambda track: track.order)),
        dependencies=dependencies,
        metadata_namespace_version="e09-j04-v1",
    ), report


def _track(
    track_ids: dict[TimelineTrackKind, UUID], kind: TimelineTrackKind, items: Sequence[TimelineItem]
) -> TimelineTrack:
    if kind not in track_ids:
        raise TimelineAssemblyError(f"missing preallocated track id: {kind.value}")
    return TimelineTrack(
        track_id=track_ids[kind],
        kind=kind,
        order=TRACK_ORDER[kind],
        items=tuple(sorted(items, key=lambda item: item.timeline_range.start.seconds)),
    )


def _line_start(lines: NarrationLineSet, line_id: UUID) -> RationalTime:
    start = lines.estimated_duration.model_copy(update={"value": 0})
    for line in lines.lines:
        if line.line_id == line_id:
            return start
        start = start.model_copy(update={"value": start.value + line.target_duration.value})
    raise TimelineAssemblyError("narration line is outside line set")
