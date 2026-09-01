"""Compile LLM event proposals only when exact episode evidence supports them."""

from __future__ import annotations

import re
from dataclasses import dataclass

from packages.longform.story_index import EventFunction, SeriesEvent, SeriesEvidence

NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?|[零一二三四五六七八九十百千万亿两]+")


@dataclass(frozen=True)
class TranscriptSegment:
    segment_id: str
    episode: int
    start_seconds: float
    end_seconds: float
    text: str
    speaker_ref: str | None = None

    def __post_init__(self) -> None:
        if not self.segment_id or not self.text.strip():
            raise ValueError("transcript segment requires identity and text")
        if self.episode < 1 or self.start_seconds < 0 or self.end_seconds <= self.start_seconds:
            raise ValueError("transcript segment requires a valid time range")


@dataclass(frozen=True)
class VisualObservation:
    observation_id: str
    episode: int
    start_seconds: float
    end_seconds: float
    description: str

    def __post_init__(self) -> None:
        if not self.observation_id or not self.description.strip():
            raise ValueError("visual observation requires identity and description")
        if self.episode < 1 or self.start_seconds < 0 or self.end_seconds <= self.start_seconds:
            raise ValueError("visual observation requires a valid time range")


@dataclass(frozen=True)
class EventProposal:
    event_id: str
    episode: int
    order_in_episode: int
    description: str
    function: EventFunction
    character_refs: tuple[str, ...]
    transcript_refs: tuple[str, ...] = ()
    visual_refs: tuple[str, ...] = ()
    causes: tuple[str, ...] = ()
    importance: int = 3
    visual_payoff: int = 0
    original_audio_value: int = 0


def compile_event_proposals(
    *,
    proposals: tuple[EventProposal, ...],
    transcripts: tuple[TranscriptSegment, ...],
    visuals: tuple[VisualObservation, ...],
    known_character_refs: frozenset[str],
) -> tuple[SeriesEvent, ...]:
    """Reject hallucinated refs, cross-episode evidence and unsupported numeric claims."""

    transcript_map = {item.segment_id: item for item in transcripts}
    visual_map = {item.observation_id: item for item in visuals}
    if len(transcript_map) != len(transcripts) or len(visual_map) != len(visuals):
        raise ValueError("observation ids must be unique")
    results: list[SeriesEvent] = []
    for proposal in proposals:
        unknown_characters = set(proposal.character_refs) - known_character_refs
        if unknown_characters:
            raise ValueError(
                f"event {proposal.event_id} references unknown characters: "
                f"{', '.join(sorted(unknown_characters))}"
            )
        try:
            dialogue = tuple(transcript_map[ref] for ref in proposal.transcript_refs)
            visual = tuple(visual_map[ref] for ref in proposal.visual_refs)
        except KeyError as error:
            raise ValueError(
                f"event {proposal.event_id} references unknown evidence: {error.args[0]}"
            ) from error
        if not dialogue and not visual:
            raise ValueError(f"event {proposal.event_id} has no evidence")
        if any(item.episode != proposal.episode for item in dialogue) or any(
            item.episode != proposal.episode for item in visual
        ):
            raise ValueError(f"event {proposal.event_id} mixes evidence across episodes")
        if proposal.function in {
            EventFunction.CONFLICT,
            EventFunction.CLIMAX,
            EventFunction.PAYOFF,
        } and (not dialogue or not visual):
            raise ValueError(
                f"core event {proposal.event_id} requires both dialogue and visual evidence"
            )
        evidence_text = " ".join(
            [item.text for item in dialogue] + [item.description for item in visual]
        )
        unsupported_numbers = set(NUMBER_PATTERN.findall(proposal.description)) - set(
            NUMBER_PATTERN.findall(evidence_text)
        )
        if unsupported_numbers:
            raise ValueError(
                f"event {proposal.event_id} contains unsupported numeric claims: "
                f"{', '.join(sorted(unsupported_numbers))}"
            )
        evidence = tuple(
            SeriesEvidence(
                evidence_id=item.segment_id,
                episode=item.episode,
                start_seconds=item.start_seconds,
                end_seconds=item.end_seconds,
                kind="dialogue",
                excerpt=item.text,
            )
            for item in dialogue
        ) + tuple(
            SeriesEvidence(
                evidence_id=item.observation_id,
                episode=item.episode,
                start_seconds=item.start_seconds,
                end_seconds=item.end_seconds,
                kind="visual",
                excerpt=item.description,
            )
            for item in visual
        )
        results.append(
            SeriesEvent(
                event_id=proposal.event_id,
                episode=proposal.episode,
                order_in_episode=proposal.order_in_episode,
                description=proposal.description,
                function=proposal.function,
                character_refs=proposal.character_refs,
                evidence=evidence,
                causes=proposal.causes,
                importance=proposal.importance,
                visual_payoff=proposal.visual_payoff,
                original_audio_value=proposal.original_audio_value,
            )
        )
    return tuple(results)
