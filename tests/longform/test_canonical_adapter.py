from uuid import uuid4

import pytest

from packages.contracts import ArtifactRef
from packages.longform.canonical_adapter import project_to_canonical_timeline_inputs
from packages.longform.clip_planning import ChapterClipPlan, ClipPlanningFinding, SelectedShot
from packages.longform.planning import Chapter, ChapterBlueprint, ChapterFunction


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=kind)


def fixture() -> tuple[ChapterBlueprint, ChapterClipPlan]:
    blueprint = ChapterBlueprint(
        arc_id="arc-1",
        target_seconds=180.0,
        chapters=(
            Chapter(
                chapter_id="chapter-1",
                function=ChapterFunction.HOOK,
                event_refs=("event-1",),
                target_seconds=180.0,
                narration_budget_seconds=60.0,
                protects_original_audio=True,
            ),
        ),
        findings=(),
    )
    plan = ChapterClipPlan(
        target_seconds=180.0,
        selected=(
            SelectedShot(
                chapter_id="chapter-1",
                shot_id="shot-1",
                source_path="episode-1.mp4",
                episode=1,
                start_seconds=10.0,
                duration_seconds=180.0,
                event_refs=("event-1",),
                contains_protected_audio=True,
            ),
        ),
        findings=(),
    )
    return blueprint, plan


def test_projects_complete_plan_into_existing_canonical_contracts() -> None:
    blueprint, plan = fixture()
    story_id, evidence_id = uuid4(), uuid4()
    result = project_to_canonical_timeline_inputs(
        blueprint=blueprint,
        clip_plan=plan,
        creative_brief_ref=ref("CreativeBrief"),
        candidate_set_ref=ref("ClipCandidateSet"),
        source_refs={"episode-1.mp4": ref("SourceMedia")},
        story_refs={"event-1": story_id},
        evidence_refs={"shot-1": (evidence_id,)},
    )

    assert result.beat_graph.target_duration.seconds == 180
    assert result.candidate_set.candidates[0].story_refs == (story_id,)
    assert result.selection_plan.selections[0].candidate_id == (
        result.candidate_set.candidates[0].candidate_id
    )


def test_rejects_blocked_or_incomplete_plan_and_missing_persisted_refs() -> None:
    blueprint, plan = fixture()
    kwargs = {
        "blueprint": blueprint,
        "clip_plan": plan,
        "creative_brief_ref": ref("CreativeBrief"),
        "candidate_set_ref": ref("ClipCandidateSet"),
        "source_refs": {"episode-1.mp4": ref("SourceMedia")},
        "story_refs": {"event-1": uuid4()},
        "evidence_refs": {"shot-1": (uuid4(),)},
    }
    blocked = ChapterClipPlan(
        target_seconds=180.0,
        selected=plan.selected,
        findings=(ClipPlanningFinding("chapter-1", "gap", True, "missing"),),
    )
    with pytest.raises(ValueError, match="blocked"):
        project_to_canonical_timeline_inputs(**(kwargs | {"clip_plan": blocked}))  # type: ignore[arg-type]

    short = ChapterClipPlan(
        target_seconds=180.0,
        selected=(
            plan.selected[0].__class__(**(plan.selected[0].__dict__ | {"duration_seconds": 179.0})),
        ),
        findings=(),
    )
    with pytest.raises(ValueError, match="unique video"):
        project_to_canonical_timeline_inputs(**(kwargs | {"clip_plan": short}))  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Story/Evidence"):
        project_to_canonical_timeline_inputs(**(kwargs | {"evidence_refs": {}}))  # type: ignore[arg-type]
