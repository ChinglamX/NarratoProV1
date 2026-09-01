"""Evidence-grounded marketing arc and long-form chapter planning."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from packages.longform.story_index import EventFunction, SeriesEvent, SeriesStoryIndex


class ChapterFunction(StrEnum):
    HOOK = "hook"
    SETUP = "setup"
    CONFLICT = "conflict"
    ESCALATION = "escalation"
    TURN = "turn"
    CLIMAX = "climax"
    PAYOFF = "payoff"
    CONTINUATION = "continuation"


@dataclass(frozen=True)
class MarketingArcCandidate:
    arc_id: str
    label: str
    event_refs: tuple[str, ...]
    hook_event_ref: str
    payoff_event_ref: str
    evidence_coverage: float
    visual_score: float
    original_audio_score: float
    risk_codes: tuple[str, ...]


@dataclass(frozen=True)
class ArcRecommendation:
    arc: MarketingArcCandidate
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class Chapter:
    chapter_id: str
    function: ChapterFunction
    event_refs: tuple[str, ...]
    target_seconds: float
    narration_budget_seconds: float
    protects_original_audio: bool


@dataclass(frozen=True)
class ChapterBlueprint:
    arc_id: str
    target_seconds: float
    chapters: tuple[Chapter, ...]
    findings: tuple[str, ...]

    @property
    def blocked(self) -> bool:
        return any(item.startswith("blocker:") for item in self.findings)


def propose_marketing_arcs(index: SeriesStoryIndex) -> tuple[MarketingArcCandidate, ...]:
    """Return bounded, structurally distinct arcs from complete conflict chains."""

    events = {event.event_id: event for event in index.events}
    candidates: list[MarketingArcCandidate] = []
    for number, conflict in enumerate(index.conflicts, 1):
        ancestors = _upstream(conflict.event_refs[0], index.events)
        descendants = _downstream(conflict.event_refs[0], index.events)
        refs = _ordered_unique(
            (*ancestors, *descendants),
            index.events,
        )
        chain = tuple(events[ref] for ref in refs)
        candidates.append(_candidate(f"arc-{number}-conflict", "冲突递进", chain))
        payoff_first = (events[conflict.payoff_refs[-1]], *chain)
        candidates.append(_candidate(f"arc-{number}-payoff", "结果倒叙", payoff_first))
    return tuple(candidates[:3])


def select_default_arc(
    index: SeriesStoryIndex, candidates: tuple[MarketingArcCandidate, ...]
) -> ArcRecommendation:
    """Recommend a production default from evidence and coverage, not predicted performance."""

    if not candidates:
        raise ValueError("at least one marketing arc candidate is required")
    event_map = {event.event_id: event for event in index.events}

    def score(candidate: MarketingArcCandidate) -> tuple[int, int, float, int]:
        episodes = {event_map[ref].episode for ref in candidate.event_refs}
        return (
            len(episodes),
            len(candidate.event_refs),
            candidate.evidence_coverage * 5
            + candidate.visual_score
            + candidate.original_audio_score * 0.5
            - len(candidate.risk_codes) * 2,
            1 if candidate.label == "冲突递进" else 0,
        )

    selected = max(candidates, key=score)
    return ArcRecommendation(
        arc=selected,
        reason_codes=(
            "highest-evidence-and-visual-coverage",
            "widest-cross-episode-span",
            "recommendation-is-not-performance-prediction",
        ),
    )


def build_chapter_blueprint(
    *,
    index: SeriesStoryIndex,
    arc: MarketingArcCandidate,
    target_seconds: float = 240.0,
    hook_event_ref: str | None = None,
) -> ChapterBlueprint:
    if not 180 <= target_seconds <= 300:
        raise ValueError("long-form target must be between 180 and 300 seconds")
    event_map = {event.event_id: event for event in index.events}
    missing = tuple(ref for ref in arc.event_refs if ref not in event_map)
    if missing:
        raise ValueError(f"arc references unknown events: {', '.join(missing)}")
    if hook_event_ref is not None and hook_event_ref not in arc.event_refs:
        raise ValueError(f"hook event is outside the selected arc: {hook_event_ref}")
    events = tuple(event_map[ref] for ref in arc.event_refs)
    buckets = _chapter_buckets(events, hook_event_ref=hook_event_ref)
    body_weights = {
        ChapterFunction.SETUP: 1.0,
        ChapterFunction.CONFLICT: 1.3,
        ChapterFunction.ESCALATION: 1.4,
        ChapterFunction.TURN: 1.1,
        ChapterFunction.CLIMAX: 1.2,
        ChapterFunction.PAYOFF: 0.8,
        ChapterFunction.CONTINUATION: 0.7,
    }
    hook_seconds = min(max(target_seconds * 0.05, 9.0), 15.0)
    body_weight = sum(body_weights[function] for function, _ in buckets[1:])
    body_seconds = target_seconds - hook_seconds
    chapters: list[Chapter] = []
    protected_event_refs: set[str] = set()
    for number, (function, values) in enumerate(buckets, 1):
        seconds = (
            hook_seconds
            if function is ChapterFunction.HOOK
            else body_seconds * body_weights[function] / body_weight
        )
        if number == len(buckets):
            seconds = target_seconds - sum(chapter.target_seconds for chapter in chapters)
        eligible_protected_refs = {
            event.event_id
            for event in values
            if event.original_audio_value >= 4 and event.event_id not in protected_event_refs
        }
        chapters.append(
            Chapter(
                chapter_id=f"chapter-{number}",
                function=function,
                event_refs=tuple(event.event_id for event in values),
                target_seconds=round(seconds, 3),
                narration_budget_seconds=round(seconds * _narration_ratio(function), 3),
                protects_original_audio=bool(eligible_protected_refs),
            )
        )
        protected_event_refs.update(eligible_protected_refs)
    findings: list[str] = []
    present = {chapter.function for chapter in chapters}
    if ChapterFunction.CONFLICT not in present:
        findings.append("blocker:missing-conflict")
    if not present & {ChapterFunction.TURN, ChapterFunction.CLIMAX}:
        findings.append("blocker:missing-turn-or-climax")
    if ChapterFunction.PAYOFF not in present:
        findings.append("blocker:missing-payoff")
    if index.unresolved:
        findings.append("warning:unresolved-story-questions")
    return ChapterBlueprint(
        arc_id=arc.arc_id,
        target_seconds=target_seconds,
        chapters=tuple(chapters),
        findings=tuple(findings),
    )


def _candidate(
    arc_id: str, label: str, raw_events: tuple[SeriesEvent, ...]
) -> MarketingArcCandidate:
    events = tuple(dict.fromkeys(raw_events))
    grounded = sum(bool(event.evidence) for event in events)
    risk_codes = tuple(
        code
        for code, failed in (
            ("missing-dialogue-evidence", not all(event.has_dialogue_evidence for event in events)),
            ("missing-visual-evidence", not all(event.has_visual_evidence for event in events)),
        )
        if failed
    )
    return MarketingArcCandidate(
        arc_id=arc_id,
        label=label,
        event_refs=tuple(event.event_id for event in events),
        hook_event_ref=events[0].event_id,
        payoff_event_ref=next(
            event.event_id for event in reversed(events) if event.function is EventFunction.PAYOFF
        ),
        evidence_coverage=grounded / len(events),
        visual_score=sum(event.visual_payoff for event in events) / len(events),
        original_audio_score=sum(event.original_audio_value for event in events) / len(events),
        risk_codes=risk_codes,
    )


def _ordered_unique(refs: tuple[str, ...], events: tuple[SeriesEvent, ...]) -> tuple[str, ...]:
    wanted = set(refs)
    return tuple(event.event_id for event in events if event.event_id in wanted)


def _upstream(root: str, events: tuple[SeriesEvent, ...]) -> tuple[str, ...]:
    event_map = {event.event_id: event for event in events}
    reachable = {root}
    pending = [root]
    while pending:
        current = pending.pop()
        for cause in event_map[current].causes:
            if cause not in reachable:
                reachable.add(cause)
                pending.append(cause)
    return tuple(event.event_id for event in events if event.event_id in reachable)


def _downstream(root: str, events: tuple[SeriesEvent, ...]) -> tuple[str, ...]:
    reachable = {root}
    changed = True
    while changed:
        changed = False
        for event in events:
            if event.event_id not in reachable and set(event.causes) & reachable:
                reachable.add(event.event_id)
                changed = True
    return tuple(event.event_id for event in events if event.event_id in reachable)


def _chapter_buckets(
    events: tuple[SeriesEvent, ...],
    *,
    hook_event_ref: str | None = None,
) -> tuple[tuple[ChapterFunction, tuple[SeriesEvent, ...]], ...]:
    hook = (
        next(event for event in events if event.event_id == hook_event_ref)
        if hook_event_ref is not None
        else max(events, key=lambda event: (event.visual_payoff, event.importance))
    )
    movements: list[tuple[SeriesEvent, ...]] = []
    pending: list[SeriesEvent] = []
    for event in events:
        pending.append(event)
        if event.function in {EventFunction.TURN, EventFunction.PAYOFF}:
            movements.extend(_split_movement(tuple(pending)))
            pending = []
    if pending:
        movements.extend(_split_movement(tuple(pending)))
    return (
        (ChapterFunction.HOOK, (hook,)),
        *((_movement_function(values), values) for values in movements),
    )


def _split_movement(events: tuple[SeriesEvent, ...]) -> tuple[tuple[SeriesEvent, ...], ...]:
    """Keep chapters readable without breaking causal/episode order."""

    if len(events) <= 3:
        return (events,)
    chunks: list[tuple[SeriesEvent, ...]] = []
    cursor = 0
    while len(events) - cursor > 3:
        size = 3
        chunks.append(events[cursor : cursor + size])
        cursor += size
    chunks.append(events[cursor:])
    return tuple(chunks)


def _movement_function(events: tuple[SeriesEvent, ...]) -> ChapterFunction:
    present = {event.function for event in events}
    for source, target in (
        (EventFunction.PAYOFF, ChapterFunction.PAYOFF),
        (EventFunction.CLIMAX, ChapterFunction.CLIMAX),
        (EventFunction.TURN, ChapterFunction.TURN),
        (EventFunction.CONFLICT, ChapterFunction.CONFLICT),
        (EventFunction.ESCALATION, ChapterFunction.ESCALATION),
    ):
        if source in present:
            return target
    return ChapterFunction.SETUP


def _narration_ratio(function: ChapterFunction) -> float:
    if function in {ChapterFunction.HOOK, ChapterFunction.CLIMAX, ChapterFunction.PAYOFF}:
        return 0.45
    if function is ChapterFunction.SETUP:
        return 0.7
    return 0.6
