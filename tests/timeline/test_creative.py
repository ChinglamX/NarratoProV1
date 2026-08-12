from uuid import uuid4

import pytest

from packages.contracts import ArtifactRef
from packages.contracts.timeline_intent import ClipCandidate, NarrativeBeat, NarrativeBeatGraph
from packages.timeline.creative import (
    CreativeTimelineConflict,
    assemble_intent_timeline,
    select_grounded_clips,
)


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=kind)


def time(value: int) -> dict[str, int]:
    return {"value": value, "rate_num": 1}


def fixture() -> tuple[NarrativeBeatGraph, ClipCandidate]:
    story_id, evidence_id, beat_id = uuid4(), uuid4(), uuid4()
    beat = NarrativeBeat.model_validate(
        {
            "beat_id": beat_id,
            "function": "hook",
            "story_refs": [story_id],
            "target_duration": time(5),
            "minimum_duration": time(2),
            "maximum_duration": time(8),
            "required_information": ["冲突"],
            "emotional_intent": {"energy": "rising"},
        }
    )
    graph = NarrativeBeatGraph(
        creative_brief_ref=ref("CreativeBrief"), beats=(beat,), target_duration=time(5)
    )
    candidate = ClipCandidate.model_validate(
        {
            "candidate_id": uuid4(),
            "beat_id": beat_id,
            "source_ref": ref("SourceMedia"),
            "source_range": {"start": time(10), "duration": time(5)},
            "story_refs": [story_id],
            "evidence_refs": [evidence_id],
            "quality": {},
            "continuity_features": {},
            "reframe_feasible": True,
            "rights_allowed": True,
            "score_components": {"relevance": 0.9, "quality": 0.8},
        }
    )
    return graph, candidate


def test_grounded_selection_and_timeline_are_deterministic() -> None:
    graph, candidate = fixture()
    candidate_ref = ref("ClipCandidateSet")
    candidate_set, selection = select_grounded_clips(
        candidate_set_ref=candidate_ref, beat_graph=graph, candidates=(candidate,)
    )
    assert not candidate_set.incomplete
    timeline = assemble_intent_timeline(
        timeline_id=uuid4(),
        beat_graph=graph,
        selections=selection,
        candidates=(candidate,),
        dependencies=(graph.creative_brief_ref, candidate_ref),
        track_id=uuid4(),
        item_ids=(uuid4(),),
    )
    assert timeline.duration.seconds == 5 and timeline.tracks[0].items[0].evidence_refs


def test_missing_or_mismatched_clip_never_silently_fills() -> None:
    graph, candidate = fixture()
    candidate_set, selection = select_grounded_clips(
        candidate_set_ref=ref("ClipCandidateSet"),
        beat_graph=graph,
        candidates=(candidate.model_copy(update={"rights_allowed": False}),),
    )
    assert candidate_set.incomplete and candidate_set.coverage_gaps and not selection.selections
    with pytest.raises(CreativeTimelineConflict, match="every beat"):
        assemble_intent_timeline(
            timeline_id=uuid4(),
            beat_graph=graph,
            selections=selection,
            candidates=(candidate,),
            dependencies=(),
            track_id=uuid4(),
            item_ids=(),
        )
