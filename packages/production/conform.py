"""Deterministic E10 voice-duration conform and subtitle cue construction."""

from __future__ import annotations

from uuid import UUID

from packages.contracts.envelopes import JsonObject
from packages.contracts.foundation import ArtifactRef, RationalTime, TimeRange
from packages.contracts.media_production import AlignmentArtifact, SubtitleCue, SubtitleCueSet


class ConformConflict(RuntimeError):
    pass


def duration_delta(estimated: RationalTime, actual: RationalTime) -> RationalTime:
    if estimated.rate_num != actual.rate_num or estimated.rate_den != actual.rate_den:
        raise ConformConflict("duration comparison requires the same rational rate")
    return actual.model_copy(update={"value": actual.value - estimated.value})


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
