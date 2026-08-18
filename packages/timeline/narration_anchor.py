"""Evidence-gated narration timing and post-TTS deterministic reflow."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from uuid import UUID

from packages.contracts import RationalTime, TimeRange


class AnchorSource(StrEnum):
    TOOL = "tool"
    DIRECTOR_OVERRIDE = "director_override"


@dataclass(frozen=True)
class VisualEventAnchor:
    event_id: str
    timeline_range: TimeRange
    evidence_refs: tuple[UUID, ...]
    protects_original_sound: bool = False


@dataclass(frozen=True)
class NarrationAnchorRequest:
    line_id: UUID
    required_event_ids: tuple[str, ...]
    measured_duration: RationalTime
    preferred_delay: RationalTime
    post_roll: RationalTime
    manual_start: RationalTime | None = None
    manual_override_reason: str | None = None


@dataclass(frozen=True)
class NarrationAnchorFinding:
    line_id: UUID
    code: str
    explanation: str
    blocker: bool


@dataclass(frozen=True)
class NarrationAnchorDecision:
    line_id: UUID
    timeline_range: TimeRange
    earliest_allowed_start: RationalTime
    preferred_start: RationalTime
    latest_end: RationalTime
    required_event_ids: tuple[str, ...]
    source: AnchorSource
    override_reason: str | None = None


@dataclass(frozen=True)
class NarrationAnchorPlan:
    decisions: tuple[NarrationAnchorDecision, ...]
    findings: tuple[NarrationAnchorFinding, ...]

    @property
    def blocked(self) -> bool:
        return any(finding.blocker for finding in self.findings)


def plan_narration_anchors(
    *,
    requests: Iterable[NarrationAnchorRequest],
    events: Iterable[VisualEventAnchor],
    timeline_duration: RationalTime,
    minimum_gap: RationalTime | None = None,
    maximum_gap: RationalTime | None = None,
) -> NarrationAnchorPlan:
    """Schedule measured narration only after its required evidence is visible.

    The planner never invents evidence and never silently accepts a director
    override. Overrides require an explicit reason and remain visible in the
    resulting plan.
    """

    minimum_gap = minimum_gap or RationalTime(value=100_000, rate_num=1_000_000)
    maximum_gap = maximum_gap or RationalTime(value=1_500_000, rate_num=1_000_000)
    event_map = {event.event_id: event for event in events}
    findings: list[NarrationAnchorFinding] = []
    decisions: list[NarrationAnchorDecision] = []
    previous_end = RationalTime(value=0, rate_num=1)

    for request in requests:
        missing = tuple(
            event_id for event_id in request.required_event_ids if event_id not in event_map
        )
        if missing:
            findings.append(
                NarrationAnchorFinding(
                    line_id=request.line_id,
                    code="missing-visual-evidence",
                    explanation=f"required visual events are missing: {', '.join(missing)}",
                    blocker=True,
                )
            )
            continue
        if not request.required_event_ids:
            findings.append(
                NarrationAnchorFinding(
                    line_id=request.line_id,
                    code="unsupported-narration-claim",
                    explanation="narration requires at least one visual evidence event",
                    blocker=True,
                )
            )
            continue

        required = tuple(event_map[event_id] for event_id in request.required_event_ids)
        earliest_seconds = max(event.timeline_range.start.seconds for event in required)
        evidence_end_seconds = max(event.timeline_range.end_seconds for event in required)
        earliest = _seconds(earliest_seconds)
        preferred = _seconds(earliest_seconds + request.preferred_delay.seconds)
        latest_end = _seconds(
            min(timeline_duration.seconds, evidence_end_seconds + request.post_roll.seconds)
        )
        source = AnchorSource.TOOL
        override_reason: str | None = None

        if request.manual_start is not None:
            if not request.manual_override_reason:
                findings.append(
                    NarrationAnchorFinding(
                        line_id=request.line_id,
                        code="unexplained-director-override",
                        explanation="manual timing override requires a reason",
                        blocker=True,
                    )
                )
                continue
            preferred = request.manual_start
            source = AnchorSource.DIRECTOR_OVERRIDE
            override_reason = request.manual_override_reason
            if preferred.seconds < earliest.seconds:
                findings.append(
                    NarrationAnchorFinding(
                        line_id=request.line_id,
                        code="narration-before-evidence",
                        explanation="director override starts before required visual evidence",
                        blocker=True,
                    )
                )
                continue

        start_seconds = max(preferred.seconds, previous_end.seconds + minimum_gap.seconds)
        protected = tuple(
            event.timeline_range for event in required if event.protects_original_sound
        )
        start_seconds = _move_after_protected_sound(
            start_seconds=start_seconds,
            duration_seconds=request.measured_duration.seconds,
            protected_ranges=protected,
        )
        end_seconds = start_seconds + request.measured_duration.seconds
        if end_seconds > latest_end.seconds:
            findings.append(
                NarrationAnchorFinding(
                    line_id=request.line_id,
                    code="tts-duration-overflow",
                    explanation="measured narration cannot fit its evidence-backed timing window",
                    blocker=True,
                )
            )
            continue
        if decisions and start_seconds - previous_end.seconds > maximum_gap.seconds:
            findings.append(
                NarrationAnchorFinding(
                    line_id=request.line_id,
                    code="excessive-narration-gap",
                    explanation="gap exceeds the configured rhythm maximum",
                    blocker=False,
                )
            )
        start = _seconds(start_seconds)
        duration = _seconds(request.measured_duration.seconds)
        decisions.append(
            NarrationAnchorDecision(
                line_id=request.line_id,
                timeline_range=TimeRange(start=start, duration=duration),
                earliest_allowed_start=earliest,
                preferred_start=preferred,
                latest_end=latest_end,
                required_event_ids=request.required_event_ids,
                source=source,
                override_reason=override_reason,
            )
        )
        previous_end = _seconds(end_seconds)

    return NarrationAnchorPlan(decisions=tuple(decisions), findings=tuple(findings))


def _move_after_protected_sound(
    *,
    start_seconds: Fraction,
    duration_seconds: Fraction,
    protected_ranges: tuple[TimeRange, ...],
) -> Fraction:
    candidate = start_seconds
    for protected in sorted(protected_ranges, key=lambda item: item.start.seconds):
        end = candidate + duration_seconds
        if candidate < protected.end_seconds and end > protected.start.seconds:
            candidate = protected.end_seconds
    return candidate


def _seconds(value: Fraction | float) -> RationalTime:
    fraction = Fraction(value).limit_denominator(1_000_000)
    return RationalTime(value=fraction.numerator, rate_num=fraction.denominator)
