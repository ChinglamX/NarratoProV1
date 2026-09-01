from packages.longform.narration_planning import NarrationTextDraft, preflight_narration_drafts
from packages.longform.planning import Chapter, ChapterBlueprint, ChapterFunction
from packages.longform.story_index import (
    EventFunction,
    SeriesEvent,
    SeriesEvidence,
    SeriesStoryIndex,
    build_series_story_index,
)


def fixtures() -> tuple[SeriesStoryIndex, ChapterBlueprint]:
    evidence = SeriesEvidence(
        evidence_id="dialogue-1",
        episode=1,
        start_seconds=1,
        end_seconds=2,
        kind="dialogue",
        excerpt="这是原始对白",
    )
    index = build_series_story_index(
        series_id="series",
        events=(
            SeriesEvent(
                event_id="event-1",
                episode=1,
                order_in_episode=1,
                description="事件",
                function=EventFunction.CONFLICT,
                character_refs=("person",),
                evidence=(evidence,),
            ),
        ),
    )
    blueprint = ChapterBlueprint(
        arc_id="arc",
        target_seconds=10,
        chapters=(
            Chapter(
                chapter_id="chapter-1",
                function=ChapterFunction.CONFLICT,
                event_refs=("event-1",),
                target_seconds=10,
                narration_budget_seconds=5,
                protects_original_audio=False,
            ),
        ),
        findings=(),
    )
    return index, blueprint


def test_preflight_accepts_grounded_text_within_budget() -> None:
    index, blueprint = fixtures()
    result = preflight_narration_drafts(
        drafts=(NarrationTextDraft("line-1", "chapter-1", "危机突然找上门。", ("event-1",)),),
        story_index=index,
        blueprint=blueprint,
    )
    assert not result.blocked
    assert result.estimated_duration_seconds > 0


def test_preflight_blocks_missing_evidence_and_budget_overflow() -> None:
    index, blueprint = fixtures()
    result = preflight_narration_drafts(
        drafts=(
            NarrationTextDraft("missing", "chapter-1", "没有依据。", ()),
            NarrationTextDraft("long", "chapter-1", "危机" * 20, ("event-1",)),
        ),
        story_index=index,
        blueprint=blueprint,
    )
    assert {finding.code for finding in result.findings} == {
        "missing-story-evidence",
        "estimated-chapter-budget-overflow",
    }
