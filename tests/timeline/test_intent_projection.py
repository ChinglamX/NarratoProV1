"""Intent projection tests: deterministic, evidence-preserving J04 assembly intents."""

from uuid import uuid4

from packages.contracts import ArtifactRef
from packages.contracts.timeline_intent import (
    ClipCandidate,
    ClipSelection,
    ClipSelectionPlan,
    NarrationLine,
    NarrationLineSet,
)
from packages.timeline.intent_projection import (
    project_original_audio_intents,
    project_subtitle_intents_from_narration,
)


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=kind)


def candidate(beat_id: uuid4, evidence_id: uuid4) -> ClipCandidate:
    return ClipCandidate(
        candidate_id=uuid4(),
        beat_id=beat_id,
        source_ref=ref("SourceMedia"),
        source_range={
            "start": {"value": 0, "rate_num": 1},
            "duration": {"value": 5, "rate_num": 1},
        },
        story_refs=(uuid4(),),
        evidence_refs=(evidence_id,),
        quality={},
        continuity_features={},
        reframe_feasible=True,
        rights_allowed=True,
        score_components={"relevance": 1.0},
    )


def line(beat_id: uuid4, evidence_id: uuid4) -> NarrationLine:
    return NarrationLine(
        line_id=uuid4(),
        beat_id=beat_id,
        text="他推开门",
        function="bridge",
        story_refs=(uuid4(),),
        evidence_refs=(evidence_id,),
        target_duration={"value": 5, "rate_num": 1},
        dialogue_relationship="bridge",
    )


def test_original_audio_follows_selected_clips_and_is_replay_stable() -> None:
    beat_id, evidence_id = uuid4(), uuid4()
    first = candidate(beat_id, evidence_id)
    selections = ClipSelectionPlan(
        candidate_set_ref=ref("ClipCandidateSet"),
        selections=(
            ClipSelection(
                beat_id=beat_id,
                candidate_id=first.candidate_id,
                selected_range=first.source_range,
                rationale="grounded",
            ),
        ),
    )
    intents = project_original_audio_intents(selections, (first,))
    assert len(intents) == 1
    assert intents[0].source_ref == first.source_ref
    assert intents[0].timeline_range.start.seconds == 0
    assert intents == project_original_audio_intents(selections, (first,))


def test_subtitles_mirror_narration_with_safe_area_and_evidence() -> None:
    beat_id, evidence_id = uuid4(), uuid4()
    narration_line = line(beat_id, evidence_id)
    narration = NarrationLineSet(
        creative_brief_ref=ref("CreativeBrief"),
        rhythm_plan_ref=ref("RhythmPlan"),
        lines=(narration_line,),
        estimated_duration={"value": 5, "rate_num": 1},
    )
    style = ref("ConfigArtifact")
    intents = project_subtitle_intents_from_narration(narration, style)
    assert len(intents) == 1
    assert intents[0].text == narration_line.text
    assert intents[0].evidence_refs == narration_line.evidence_refs
    assert intents[0].style_ref == style
    assert set(intents[0].safe_area) == {"x", "y", "width", "height"}
    assert intents == project_subtitle_intents_from_narration(narration, style)
