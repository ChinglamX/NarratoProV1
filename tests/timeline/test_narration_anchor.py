from uuid import uuid4

import pytest

from packages.contracts import RationalTime, TimeRange
from packages.timeline.narration_anchor import (
    AnchorSource,
    NarrationAnchorRequest,
    VisualEventAnchor,
    plan_narration_anchors,
)


def t(value: float) -> RationalTime:
    return RationalTime(value=round(value * 1000), rate_num=1000)


def event(name: str, start: float, duration: float, *, locked: bool = False) -> VisualEventAnchor:
    return VisualEventAnchor(
        event_id=name,
        timeline_range=TimeRange(start=t(start), duration=t(duration)),
        evidence_refs=(uuid4(),),
        protects_original_sound=locked,
    )


def request(name: str, duration: float, **changes: object) -> NarrationAnchorRequest:
    values: dict[str, object] = {
        "line_id": uuid4(),
        "required_event_ids": (name,),
        "measured_duration": t(duration),
        "preferred_delay": t(0.2),
        "post_roll": t(2.0),
    }
    values.update(changes)
    return NarrationAnchorRequest(**values)  # type: ignore[arg-type]


def test_planner_never_starts_before_visual_evidence() -> None:
    plan = plan_narration_anchors(
        requests=(request("cash", 2.0),),
        events=(event("cash", 10.0, 3.0),),
        timeline_duration=t(20),
    )
    assert not plan.blocked
    assert float(plan.decisions[0].timeline_range.start.seconds) == pytest.approx(10.2)


def test_missing_event_and_unexplained_override_block() -> None:
    missing = plan_narration_anchors(
        requests=(request("cash", 1.0),), events=(), timeline_duration=t(20)
    )
    assert missing.blocked and missing.findings[0].code == "missing-visual-evidence"
    override = plan_narration_anchors(
        requests=(request("cash", 1.0, manual_start=t(10.5)),),
        events=(event("cash", 10.0, 2.0),),
        timeline_duration=t(20),
    )
    assert override.blocked and override.findings[0].code == "unexplained-director-override"


def test_director_override_is_explicit_and_cannot_spoil() -> None:
    accepted = plan_narration_anchors(
        requests=(
            request(
                "cash",
                1.0,
                manual_start=t(10.5),
                manual_override_reason="preserve the reaction beat",
            ),
        ),
        events=(event("cash", 10.0, 2.0),),
        timeline_duration=t(20),
    )
    assert not accepted.blocked
    assert accepted.decisions[0].source is AnchorSource.DIRECTOR_OVERRIDE
    spoiled = plan_narration_anchors(
        requests=(
            request("cash", 1.0, manual_start=t(9.0), manual_override_reason="forced suspense"),
        ),
        events=(event("cash", 10.0, 2.0),),
        timeline_duration=t(20),
    )
    assert spoiled.blocked and spoiled.findings[0].code == "narration-before-evidence"


def test_measured_duration_reflows_after_locked_original_sound() -> None:
    plan = plan_narration_anchors(
        requests=(request("offer", 1.5),),
        events=(event("offer", 5.0, 2.0, locked=True),),
        timeline_duration=t(12),
    )
    assert not plan.blocked
    assert plan.decisions[0].timeline_range.start.seconds == 7.0


def test_measured_duration_overflow_is_blocker() -> None:
    plan = plan_narration_anchors(
        requests=(request("short", 4.0, post_roll=t(0.2)),),
        events=(event("short", 1.0, 1.0),),
        timeline_duration=t(10),
    )
    assert plan.blocked and plan.findings[0].code == "tts-duration-overflow"
