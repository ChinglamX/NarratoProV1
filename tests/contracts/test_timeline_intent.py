from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.contracts import ArtifactRef
from packages.contracts.timeline_intent import (
    BeatRhythm,
    CropKeyframe,
    NarrationLine,
    NarrativeBeat,
    NarrativeBeatGraph,
    RhythmPlan,
    TimelineIntentInput,
    TimelineReviewPackage,
)


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=kind)


def time(value: int) -> dict[str, int]:
    return {"value": value, "rate_num": 1}


def beat(duration: int = 5) -> NarrativeBeat:
    return NarrativeBeat.model_validate(
        {
            "beat_id": uuid4(),
            "function": "hook",
            "story_refs": [uuid4()],
            "target_duration": time(duration),
            "minimum_duration": time(2),
            "maximum_duration": time(8),
            "required_information": ["建立冲突"],
            "emotional_intent": {"energy": "rising"},
        }
    )


def test_timeline_input_requires_exact_approved_types() -> None:
    value = TimelineIntentInput(
        approved_creative_brief_ref=ref("CreativeBrief"),
        approved_variant_plan_ref=ref("VariantPlan"),
        approved_story_ref=ref("StoryGraph"),
        media_catalog_ref=ref("EpisodeCatalog"),
        platform_profile_ref=ref("ConfigArtifact"),
    )
    assert value.approved_creative_brief_ref.artifact_type == "CreativeBrief"
    with pytest.raises(ValidationError, match="approved typed boundaries"):
        value.model_copy(update={"approved_story_ref": ref("FactSet")}).model_validate(
            value.model_copy(update={"approved_story_ref": ref("FactSet")}).model_dump()
        )


def test_beat_and_rhythm_budget_fail_closed() -> None:
    item = beat()
    graph = NarrativeBeatGraph(
        creative_brief_ref=ref("CreativeBrief"), beats=(item,), target_duration=time(5)
    )
    assert graph.beats[0].story_refs
    with pytest.raises(ValidationError, match="minimum beat budget"):
        NarrativeBeatGraph(
            creative_brief_ref=ref("CreativeBrief"), beats=(item,), target_duration=time(1)
        )
    rhythm = BeatRhythm(
        beat_id=item.beat_id,
        target_duration=time(5),
        entry_energy=0.2,
        exit_energy=0.8,
        information_density=0.7,
    )
    assert RhythmPlan(
        beat_graph_ref=ref("NarrativeBeatGraph"),
        selection_plan_ref=ref("PatchProposal"),
        beats=(rhythm,),
        target_duration=time(5),
    ).beats
    with pytest.raises(ValidationError, match="must equal"):
        RhythmPlan(
            beat_graph_ref=ref("NarrativeBeatGraph"),
            selection_plan_ref=ref("PatchProposal"),
            beats=(rhythm,),
            target_duration=time(6),
        )


def test_narration_and_crop_require_evidence_and_valid_geometry() -> None:
    with pytest.raises(ValidationError, match="Story and Evidence"):
        NarrationLine(
            line_id=uuid4(),
            beat_id=uuid4(),
            text="他终于明白了",
            function="bridge",
            story_refs=(),
            evidence_refs=(),
            target_duration=time(2),
            dialogue_relationship="bridge",
        )
    with pytest.raises(ValidationError, match="inside normalized frame"):
        CropKeyframe(position=time(0), x=0.8, y=0.0, width=0.5, height=1.0)


def test_timeline_review_package_freezes_exact_checkpoint_refs() -> None:
    package = TimelineReviewPackage(
        master_timeline_ref=ref("MasterTimeline"),
        preview_ref=ref("ProxyRender"),
        creative_brief_ref=ref("CreativeBrief"),
        approved_story_ref=ref("StoryGraph"),
        platform_profile_ref=ref("ConfigArtifact"),
        visual_planning_report_ref=ref("QualityReview"),
        narration_planning_report_ref=ref("QualityReview"),
        assembly_report_ref=ref("QualityReview"),
    )
    assert package.master_timeline_ref.artifact_type == "MasterTimeline"
    with pytest.raises(ValidationError, match="exact typed refs"):
        TimelineReviewPackage.model_validate(
            package.model_dump(mode="python") | {"preview_ref": ref("FinalCandidate")}
        )
