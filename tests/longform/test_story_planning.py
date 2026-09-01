from packages.longform.planning import (
    build_chapter_blueprint,
    propose_marketing_arcs,
    select_default_arc,
)
from packages.longform.story_index import (
    EventFunction,
    SeriesEvent,
    SeriesEvidence,
    build_series_story_index,
)


def evidence(name: str, episode: int, kind: str = "visual") -> SeriesEvidence:
    return SeriesEvidence(
        evidence_id=name,
        episode=episode,
        start_seconds=1.0,
        end_seconds=3.0,
        kind=kind,
    )


def event(
    name: str,
    episode: int,
    function: EventFunction,
    *,
    causes: tuple[str, ...] = (),
    visual: int = 3,
    original_audio: int = 1,
) -> SeriesEvent:
    return SeriesEvent(
        event_id=name,
        episode=episode,
        order_in_episode=1,
        description=name,
        function=function,
        character_refs=("hero",),
        evidence=(evidence(f"{name}-v", episode), evidence(f"{name}-d", episode, "dialogue")),
        causes=causes,
        importance=4,
        visual_payoff=visual,
        original_audio_value=original_audio,
    )


def complete_index() -> object:
    return build_series_story_index(
        series_id="series-1",
        events=(
            event("goal", 1, EventFunction.GOAL),
            event("conflict", 2, EventFunction.CONFLICT, causes=("goal",)),
            event("escalate", 3, EventFunction.ESCALATION, causes=("conflict",)),
            event("turn", 4, EventFunction.TURN, causes=("escalate",), visual=5),
            event("climax", 5, EventFunction.CLIMAX, causes=("turn",), original_audio=5),
            event("payoff", 6, EventFunction.PAYOFF, causes=("climax",), visual=5),
        ),
    )


def test_cross_episode_conflict_chain_generates_distinct_arcs() -> None:
    index = complete_index()
    arcs = propose_marketing_arcs(index)  # type: ignore[arg-type]
    assert len(arcs) == 2
    assert arcs[0].label == "冲突递进"
    assert arcs[1].label == "结果倒叙"
    assert arcs[0].payoff_event_ref == "payoff"
    assert arcs[0].evidence_coverage == 1.0
    recommendation = select_default_arc(index, arcs)  # type: ignore[arg-type]
    assert recommendation.arc.label == "冲突递进"


def test_long_form_blueprint_is_budgeted_and_has_required_structure() -> None:
    index = complete_index()
    arc = propose_marketing_arcs(index)[0]  # type: ignore[arg-type]
    blueprint = build_chapter_blueprint(
        index=index,  # type: ignore[arg-type]
        arc=arc,
        target_seconds=240,
    )
    assert not blueprint.blocked
    assert 2 <= len(blueprint.chapters) <= 9
    assert sum(chapter.target_seconds for chapter in blueprint.chapters) == 240
    assert any(chapter.protects_original_audio for chapter in blueprint.chapters)
    assert all(
        chapter.narration_budget_seconds < chapter.target_seconds for chapter in blueprint.chapters
    )
    protected_refs: set[str] = set()
    for chapter in blueprint.chapters:
        if chapter.protects_original_audio:
            assert protected_refs.isdisjoint(chapter.event_refs)
            protected_refs.update(chapter.event_refs)
    body_refs = tuple(ref for chapter in blueprint.chapters[1:] for ref in chapter.event_refs)
    assert body_refs == ("goal", "conflict", "escalate", "turn", "climax", "payoff")


def test_missing_payoff_fails_closed() -> None:
    index = build_series_story_index(
        series_id="broken",
        events=(
            event("conflict", 1, EventFunction.CONFLICT),
            event("escalate", 2, EventFunction.ESCALATION, causes=("conflict",)),
        ),
    )
    assert index.blocked
    assert propose_marketing_arcs(index) == ()


def test_blueprint_accepts_evidence_grounded_hook_override_without_reordering_body() -> None:
    index = complete_index()
    arc = propose_marketing_arcs(index)[0]  # type: ignore[arg-type]
    default = build_chapter_blueprint(index=index, arc=arc)  # type: ignore[arg-type]
    revised = build_chapter_blueprint(  # type: ignore[arg-type]
        index=index,
        arc=arc,
        hook_event_ref="escalate",
    )
    assert revised.chapters[0].event_refs == ("escalate",)
    assert revised.chapters[1:] == default.chapters[1:]


def test_blueprint_rejects_hook_outside_selected_arc() -> None:
    index = complete_index()
    arc = propose_marketing_arcs(index)[0]  # type: ignore[arg-type]
    try:
        build_chapter_blueprint(  # type: ignore[arg-type]
            index=index,
            arc=arc,
            hook_event_ref="invented-event",
        )
    except ValueError as exc:
        assert "outside the selected arc" in str(exc)
    else:
        raise AssertionError("unknown hook event must fail closed")
