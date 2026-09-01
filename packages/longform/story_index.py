"""Evidence-first aggregate view over episode-level story events."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum


class EventFunction(StrEnum):
    CONTEXT = "context"
    GOAL = "goal"
    CONFLICT = "conflict"
    ESCALATION = "escalation"
    TURN = "turn"
    CLIMAX = "climax"
    PAYOFF = "payoff"


@dataclass(frozen=True)
class SeriesEvidence:
    evidence_id: str
    episode: int
    start_seconds: float
    end_seconds: float
    kind: str
    excerpt: str | None = None

    def __post_init__(self) -> None:
        if self.episode < 1 or self.start_seconds < 0 or self.end_seconds <= self.start_seconds:
            raise ValueError("evidence requires a valid episode time range")
        if self.kind not in {"dialogue", "visual", "audio", "human"}:
            raise ValueError(f"unsupported evidence kind: {self.kind}")


@dataclass(frozen=True)
class SeriesEvent:
    event_id: str
    episode: int
    order_in_episode: int
    description: str
    function: EventFunction
    character_refs: tuple[str, ...]
    evidence: tuple[SeriesEvidence, ...]
    causes: tuple[str, ...] = ()
    importance: int = 3
    visual_payoff: int = 0
    original_audio_value: int = 0

    def __post_init__(self) -> None:
        if not self.event_id or not self.description:
            raise ValueError("event id and description are required")
        if self.episode < 1 or self.order_in_episode < 0:
            raise ValueError("event ordering must be non-negative")
        if not self.evidence:
            raise ValueError("series event requires evidence")
        if any(item.episode != self.episode for item in self.evidence):
            raise ValueError("event evidence must belong to the same episode")
        if not 1 <= self.importance <= 5:
            raise ValueError("importance must be between 1 and 5")
        if not 0 <= self.visual_payoff <= 5 or not 0 <= self.original_audio_value <= 5:
            raise ValueError("visual and original-audio values must be between 0 and 5")

    @property
    def has_dialogue_evidence(self) -> bool:
        return any(item.kind in {"dialogue", "audio"} for item in self.evidence)

    @property
    def has_visual_evidence(self) -> bool:
        return any(item.kind == "visual" for item in self.evidence)


@dataclass(frozen=True)
class StoryConflict:
    conflict_id: str
    description: str
    event_refs: tuple[str, ...]
    escalation_refs: tuple[str, ...]
    payoff_refs: tuple[str, ...]


@dataclass(frozen=True)
class SeriesStoryIndex:
    series_id: str
    events: tuple[SeriesEvent, ...]
    conflicts: tuple[StoryConflict, ...]
    unresolved: tuple[str, ...]

    @property
    def episode_count(self) -> int:
        return len({event.episode for event in self.events})

    @property
    def blocked(self) -> bool:
        return not self.events or not self.conflicts


def build_series_story_index(
    *,
    series_id: str,
    events: Iterable[SeriesEvent],
    unresolved: Iterable[str] = (),
) -> SeriesStoryIndex:
    """Build a stable cross-episode view and reject broken causal references."""

    ordered = tuple(sorted(events, key=lambda item: (item.episode, item.order_in_episode)))
    event_ids = {event.event_id for event in ordered}
    if len(event_ids) != len(ordered):
        raise ValueError("series event ids must be unique")
    missing = {cause for event in ordered for cause in event.causes if cause not in event_ids}
    if missing:
        raise ValueError(f"events reference unknown causes: {', '.join(sorted(missing))}")

    conflicts: list[StoryConflict] = []
    conflict_events = [event for event in ordered if event.function is EventFunction.CONFLICT]
    for number, conflict in enumerate(conflict_events, 1):
        reachable = _downstream(conflict.event_id, ordered)
        escalations = tuple(
            event.event_id
            for event in ordered
            if event.event_id in reachable
            and event.function
            in {EventFunction.ESCALATION, EventFunction.TURN, EventFunction.CLIMAX}
        )
        payoffs = tuple(
            event.event_id
            for event in ordered
            if event.event_id in reachable and event.function is EventFunction.PAYOFF
        )
        if escalations and payoffs:
            conflicts.append(
                StoryConflict(
                    conflict_id=f"conflict-{number}",
                    description=conflict.description,
                    event_refs=(conflict.event_id,),
                    escalation_refs=escalations,
                    payoff_refs=payoffs,
                )
            )
    return SeriesStoryIndex(
        series_id=series_id,
        events=ordered,
        conflicts=tuple(conflicts),
        unresolved=tuple(unresolved),
    )


def _downstream(root: str, events: tuple[SeriesEvent, ...]) -> set[str]:
    reachable = {root}
    changed = True
    while changed:
        changed = False
        for event in events:
            if event.event_id not in reachable and set(event.causes) & reachable:
                reachable.add(event.event_id)
                changed = True
    return reachable
