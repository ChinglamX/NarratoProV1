"""Deterministic E10 voice-duration conform and subtitle cue construction."""

from __future__ import annotations

from uuid import UUID, uuid4

from packages.contracts.envelopes import JsonObject
from packages.contracts.foundation import ActorRef, ArtifactRef, RationalTime, TimeRange
from packages.contracts.media_production import AlignmentArtifact, SubtitleCue, SubtitleCueSet
from packages.contracts.timeline import PatchOperationType, TimelinePatch


class ConformConflict(RuntimeError):
    pass


def duration_delta(estimated: RationalTime, actual: RationalTime) -> RationalTime:
    if estimated.rate_num != actual.rate_num or estimated.rate_den != actual.rate_den:
        raise ConformConflict("duration comparison requires the same rational rate")
    return actual.model_copy(update={"value": actual.value - estimated.value})


def plan_voice_conform_patch(
    *,
    timeline_ref: ArtifactRef,
    narration_item_id: UUID,
    current_range: TimeRange,
    actual_duration: RationalTime,
    author: ActorRef,
) -> tuple[TimelinePatch, RationalTime]:
    """Build an audit-safe RETIME patch that conforms one narration item.

    Returns the patch and the signed duration delta. The patch is applied
    through the normal TimelinePatch pipeline (versioned, CAS, append-only),
    so a conform is a first-class timeline revision rather than a hidden FFmpeg
    fix (Stage 5 rule).
    """
    delta = duration_delta(current_range.duration, actual_duration)
    if delta.value == 0:
        raise ConformConflict("voice duration matches estimate; nothing to conform")
    patch = TimelinePatch.model_validate(
        {
            "patch_id": str(uuid4()),
            "base_timeline": timeline_ref.model_dump(mode="json"),
            "operations": [
                {
                    "operation_id": str(uuid4()),
                    "op": PatchOperationType.RETIME.value,
                    "target_item_id": str(narration_item_id),
                    "expected_item_version": 1,
                    "payload": {
                        "timeline_range": {
                            "start": current_range.start.model_dump(mode="json"),
                            "duration": actual_duration.model_dump(mode="json"),
                        }
                    },
                }
            ],
            "author": author.model_dump(mode="json"),
            "reason": "voice duration conform",
        }
    )
    return patch, delta


def build_subtitle_cues(
    *,
    alignment: AlignmentArtifact,
    alignment_ref: ArtifactRef,
    style_profile_ref: ArtifactRef,
    texts: dict[UUID, str],
    cue_ids: dict[UUID, UUID],
    safe_area: JsonObject,
) -> SubtitleCueSet:
    by_line: dict[UUID, list[TimeRange]] = {}
    for token in alignment.tokens:
        by_line.setdefault(token.line_id, []).append(token.timeline_range)
    cues = []
    for line_id in sorted(by_line, key=str):
        if line_id not in texts or line_id not in cue_ids:
            raise ConformConflict("alignment line is missing text or preallocated cue ID")
        ranges = by_line[line_id]
        start = min(item.start.seconds for item in ranges)
        end = max(item.end_seconds for item in ranges)
        first = ranges[0].start
        cues.append(
            SubtitleCue(
                cue_id=cue_ids[line_id],
                line_id=line_id,
                timeline_range=TimeRange(
                    start=first.model_copy(
                        update={"value": int(start * first.rate_num / first.rate_den)}
                    ),
                    duration=first.model_copy(
                        update={"value": int((end - start) * first.rate_num / first.rate_den)}
                    ),
                ),
                text=texts[line_id],
                style_ref="primary",
                safe_area=safe_area,
            )
        )
    return SubtitleCueSet(
        alignment_ref=alignment_ref, cues=tuple(cues), style_profile_ref=style_profile_ref
    )
