"""Evidence-gated Story Brief assembly for an L1 host-agent candidate."""

# ruff: noqa: RUF001 - Chinese punctuation is intentionally normalized.

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from packages.contracts import (
    ArtifactRef,
    ConfidenceRecord,
    Event,
    EvidenceLink,
    RationalTime,
    StoryGraph,
    StoryImportance,
    TimeRange,
    UnresolvedQuestion,
)

_TIMECODE = re.compile(r"(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2})[,.](?P<ms>\d{3})")


@dataclass(frozen=True)
class TranscriptCue:
    cue_id: int
    source_range: TimeRange
    text: str


@dataclass(frozen=True)
class StoryClaim:
    claim_id: str
    description: str
    cue_ids: tuple[int, ...]
    excerpts: tuple[str, ...]
    importance: StoryImportance = StoryImportance.SUPPORTING


def _microseconds(value: str) -> int:
    match = _TIMECODE.fullmatch(value.strip())
    if match is None:
        raise ValueError(f"invalid SRT timecode: {value}")
    return (
        int(match["h"]) * 3_600_000_000
        + int(match["m"]) * 60_000_000
        + int(match["s"]) * 1_000_000
        + int(match["ms"]) * 1_000
    )


def parse_srt(path: Path) -> tuple[TranscriptCue, ...]:
    blocks = re.split(r"\n\s*\n", path.read_text(encoding="utf-8-sig").strip())
    cues = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3 or " --> " not in lines[1]:
            raise ValueError("invalid SRT cue block")
        cue_id = int(lines[0])
        raw_start, raw_end = lines[1].split(" --> ", maxsplit=1)
        start, end = _microseconds(raw_start), _microseconds(raw_end)
        if end <= start:
            raise ValueError("SRT cue must have positive duration")
        cues.append(
            TranscriptCue(
                cue_id=cue_id,
                source_range=TimeRange(
                    start=RationalTime(value=start, rate_num=1_000_000),
                    duration=RationalTime(value=end - start, rate_num=1_000_000),
                ),
                text=" ".join(lines[2:]),
            )
        )
    if not cues:
        raise ValueError("transcript requires at least one cue")
    return tuple(cues)


def _normalized(text: str) -> str:
    return re.sub(r"[\s，。！？、：；,.!?:;]", "", text)


def build_story_brief(
    *,
    fact_ref: ArtifactRef,
    transcript_ref: ArtifactRef,
    cues: Sequence[TranscriptCue],
    claims: Sequence[StoryClaim],
    unresolved: Sequence[str],
    id_factory: Callable[[], UUID] = uuid4,
) -> StoryGraph:
    """Compile host-agent claims only when every claim cites transcript evidence."""

    cue_by_id = {cue.cue_id: cue for cue in cues}
    if len(cue_by_id) != len(cues):
        raise ValueError("transcript cue ids must be unique")
    if not claims:
        raise ValueError("story brief requires at least one claim")
    events = []
    for order, claim in enumerate(claims):
        if len(claim.cue_ids) != len(claim.excerpts) or not claim.cue_ids:
            raise ValueError(f"claim {claim.claim_id} requires one excerpt per cue")
        evidence = []
        ranges = []
        for cue_id, excerpt in zip(claim.cue_ids, claim.excerpts, strict=True):
            try:
                cue = cue_by_id[cue_id]
            except KeyError as error:
                raise ValueError(f"claim {claim.claim_id} cites unknown cue {cue_id}") from error
            if _normalized(excerpt) not in _normalized(cue.text):
                raise ValueError(f"claim {claim.claim_id} excerpt is absent from cue {cue_id}")
            ranges.append(cue.source_range)
            evidence.append(
                EvidenceLink.model_validate(
                    {
                        "evidence_id": id_factory(),
                        "source": transcript_ref,
                        "source_range": cue.source_range,
                        "evidence_type": "dialogue",
                        "excerpt": excerpt,
                    }
                )
            )
        start = min(item.start.seconds for item in ranges)
        end = max(item.end_seconds for item in ranges)
        source_range = TimeRange(
            start=RationalTime(value=round(start * 1_000_000), rate_num=1_000_000),
            duration=RationalTime(value=round((end - start) * 1_000_000), rate_num=1_000_000),
        )
        confidence = ConfidenceRecord.model_validate(
            {
                "score": None,
                "status": "unavailable",
                "method": "host-agent-claim-with-exact-transcript-excerpt-v1",
                "applicable_scope": "story-brief:transcript-grounded:l1-review-required",
                "risk_class": "high",
                "evidence": [item.model_dump(mode="json") for item in evidence],
                "opposing_factors": [
                    {
                        "code": "semantic-entailment-unreviewed",
                        "description": (
                            "Exact excerpt presence does not prove the summary interpretation."
                        ),
                    }
                ],
            }
        )
        events.append(
            Event(
                event_id=id_factory(),
                order_key=f"event:{order:08d}",
                description=claim.description,
                participants=(),
                source_range=source_range,
                evidence=tuple(evidence),
                confidence=confidence,
                importance=claim.importance,
            )
        )
    questions = tuple(
        UnresolvedQuestion(
            question_id=id_factory(),
            question=item,
            related_refs=(),
        )
        for item in unresolved
    )
    return StoryGraph(
        source_fact_refs=(fact_ref,),
        characters=(),
        events=tuple(events),
        edges=(),
        unresolved_questions=questions,
    )
