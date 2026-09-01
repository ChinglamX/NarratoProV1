"""Conservative cue localization inside coarse timed ASR segments."""

from __future__ import annotations

import re
from dataclasses import dataclass

_SRT_BLOCK = re.compile(
    r"\d+\s*\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\s*\n(.+?)(?=\n\n|\Z)",
    re.DOTALL,
)


@dataclass(frozen=True)
class CoarseTranscriptSegment:
    start_seconds: float
    end_seconds: float
    text: str


@dataclass(frozen=True)
class LocalizedCue:
    cue: str
    start_seconds: float
    end_seconds: float
    excerpt: str
    precision: str


def parse_srt(content: str) -> tuple[CoarseTranscriptSegment, ...]:
    return tuple(
        CoarseTranscriptSegment(_seconds(start), _seconds(end), text.replace("\n", " ").strip())
        for start, end, text in _SRT_BLOCK.findall(content.strip())
    )


def localize_cue(
    segments: tuple[CoarseTranscriptSegment, ...],
    cue: str,
    *,
    padding_seconds: float = 4.0,
) -> LocalizedCue:
    """Locate a literal cue; interpolate only inside a coarse ASR segment.

    Interpolation is explicitly labelled ``coarse_interpolated`` and is meant
    for frame sampling, never as a final cut boundary or canonical alignment.
    """

    normalized_cue = _normalize(cue)
    if not normalized_cue:
        raise ValueError("cue cannot be empty")
    for segment in segments:
        normalized_text = _normalize(segment.text)
        offset = normalized_text.find(normalized_cue)
        if offset < 0:
            continue
        duration = segment.end_seconds - segment.start_seconds
        text_length = max(len(normalized_text), 1)
        estimated_start = segment.start_seconds + duration * offset / text_length
        estimated_end = (
            segment.start_seconds + duration * (offset + len(normalized_cue)) / text_length
        )
        return LocalizedCue(
            cue=cue,
            start_seconds=max(segment.start_seconds, estimated_start - padding_seconds),
            end_seconds=min(segment.end_seconds, estimated_end + padding_seconds),
            excerpt=segment.text[max(0, offset - 20) : offset + len(cue) + 20],
            precision=(
                "timed_segment"
                if len(normalized_text) <= len(normalized_cue) * 2
                else "coarse_interpolated"
            ),
        )
    raise ValueError(f"cue not found in transcript: {cue}")


def _seconds(timestamp: str) -> float:
    hours, minutes, tail = timestamp.split(":")
    seconds, milliseconds = tail.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000


def _normalize(value: str) -> str:
    return "".join(character for character in value if character.isalnum()).lower()
