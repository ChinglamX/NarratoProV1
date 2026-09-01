"""E10 production workflow helper tests (pure functions)."""

from uuid import uuid4

from packages.contracts.timeline_intent import NarrationLine, NarrationLineSet
from workflows.production.activities import _build_cues_from_narration, _pointer, _ref
from workflows.project.models import ArtifactPointer


def _narration() -> NarrationLineSet:
    lines = tuple(
        NarrationLine(
            line_id=uuid4(),
            beat_id=uuid4(),
            text=f"解说行 {index}",
            function="bridge",
            story_refs=(uuid4(),),
            evidence_refs=(uuid4(),),
            target_duration={"value": value, "rate_num": 1_000_000},
            dialogue_relationship="bridge",
        )
        for index, value in enumerate([4_000_000, 5_000_000, 6_000_000])
    )
    return NarrationLineSet(
        creative_brief_ref=ArtifactRefModel("CreativeBrief"),
        rhythm_plan_ref=ArtifactRefModel("RhythmPlan"),
        lines=lines,
        estimated_duration={"value": 15_000_000, "rate_num": 1_000_000},
    )


def ArtifactRefModel(kind: str) -> object:
    from packages.contracts import ArtifactRef

    return ArtifactRef.model_validate(
        {"artifact_id": str(uuid4()), "version": 1, "artifact_type": kind}
    )


def test_build_cues_from_narration_accumulates_timeline() -> None:
    cues = _build_cues_from_narration(_narration())
    assert len(cues) == 3
    starts = [float(cue.timeline_range.start.seconds) for cue in cues]
    durations = [float(cue.timeline_range.duration.seconds) for cue in cues]
    assert starts == [0.0, 4.0, 9.0]
    assert durations == [4.0, 5.0, 6.0]
    assert cues[0].text == "解说行 0"
    assert cues[0].safe_area == {"y": 0.8, "height": 0.14}


def test_ref_pointer_roundtrip() -> None:
    pointer = ArtifactPointer(str(uuid4()), 1, "MasterTimeline")
    reference = _ref(pointer)
    assert str(reference.artifact_id) == pointer.artifact_id
    assert reference.artifact_type == "MasterTimeline"
    back = _pointer(reference)
    assert back.artifact_id == pointer.artifact_id
    assert back.version == 1


def test_build_cues_empty_narration_returns_empty() -> None:
    empty = NarrationLineSet(
        creative_brief_ref=ArtifactRefModel("CreativeBrief"),
        rhythm_plan_ref=ArtifactRefModel("RhythmPlan"),
        lines=(),
        estimated_duration={"value": 0, "rate_num": 1_000_000},
    )
    assert _build_cues_from_narration(empty) == ()


def test_planning_models_roundtrip() -> None:
    from workflows.production.models import (
        MediaProductionPlanningInput,
        MediaProductionPlanningStatus,
    )

    pointer = ArtifactPointer(str(uuid4()), 1, "MasterTimeline")
    request = MediaProductionPlanningInput(
        project_id="p",
        run_id="r",
        trace_id="t" * 32,
        timeline=pointer,
        narration_line_set=pointer,
        resource_profile=pointer,
    )
    assert request.timeline == pointer
    status = MediaProductionPlanningStatus("r", "planning")
    assert status.state == "planning"
    assert status.blocked_codes == ()


def test_workflow_init_and_status_query() -> None:
    from workflows.production.models import MediaProductionPlanningStatus
    from workflows.production.workflow import MediaProductionPlanningWorkflow

    workflow = MediaProductionPlanningWorkflow()
    assert workflow.status() is None
    workflow._status = MediaProductionPlanningStatus("r", "planning")
    assert workflow.status().state == "planning"


def test_ref_preserves_checksum() -> None:
    pointer = ArtifactPointer(str(uuid4()), 2, "MasterTimeline", "sha256:" + "a" * 64)
    assert str(_ref(pointer).checksum) == "sha256:" + "a" * 64


def test_planning_result_model() -> None:
    from workflows.production.models import MediaProductionPlanningResult

    pointer = ArtifactPointer(str(uuid4()), 1, "MixPlan")
    result = MediaProductionPlanningResult(pointer, pointer, pointer, tts_pending=True)
    assert result.tts_pending is True
    assert result.mix_plan.artifact_type == "MixPlan"
