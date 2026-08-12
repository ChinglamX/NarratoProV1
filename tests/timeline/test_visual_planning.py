from uuid import UUID, uuid4

from packages.contracts import ArtifactRef, RationalTime
from packages.contracts.timeline_intent import (
    ClipCandidate,
    ClipRetrievalQuery,
    CompositionTarget,
    NarrativeBeat,
    NarrativeBeatGraph,
)
from packages.timeline.visual_planning import (
    analyze_continuity,
    choose_source_subtitle_policy,
    local_recompute_scope,
    plan_clip_sequence,
    retrieve_candidates,
    solve_crop_path,
)


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=kind)


def time(value: int) -> dict[str, int]:
    return {"value": value, "rate_num": 1}


def beat(beat_id: UUID, story_id: UUID) -> NarrativeBeat:
    return NarrativeBeat.model_validate(
        {
            "beat_id": beat_id,
            "function": "context",
            "story_refs": [story_id],
            "target_duration": time(4),
            "minimum_duration": time(2),
            "maximum_duration": time(6),
            "required_information": ["人物与行动"],
            "emotional_intent": {"energy": "steady"},
        }
    )


def candidate(
    beat_id: UUID,
    story_id: UUID,
    *,
    score: float,
    direction: str,
    location: str = "yard",
    character_id: UUID | None = None,
) -> ClipCandidate:
    return ClipCandidate.model_validate(
        {
            "candidate_id": uuid4(),
            "beat_id": beat_id,
            "source_ref": ref("SourceMedia"),
            "source_range": {"start": time(10), "duration": time(4)},
            "story_refs": [story_id],
            "evidence_refs": [uuid4()],
            "visible_character_refs": [character_id] if character_id else [],
            "quality": {"sharpness": 0.9},
            "continuity_features": {
                "screen_direction": direction,
                "location": location,
                "time": "day",
                "action_phase": "establish",
            },
            "reframe_feasible": True,
            "rights_allowed": True,
            "score_components": {"relevance": score},
        }
    )


class FakeIndex:
    def __init__(self, results: tuple[ClipCandidate, ...]) -> None:
        self.results = results

    def retrieve(self, _query: ClipRetrievalQuery) -> tuple[ClipCandidate, ...]:
        return self.results


def test_retrieval_rejects_wrong_beat_story_and_character() -> None:
    beat_id, story_id, character_id = uuid4(), uuid4(), uuid4()
    valid = candidate(beat_id, story_id, score=0.8, direction="left", character_id=character_id)
    wrong_story = candidate(beat_id, uuid4(), score=1.0, direction="left")
    query = ClipRetrievalQuery(
        beat_id=beat_id,
        story_refs=(story_id,),
        required_character_refs=(character_id,),
        routes=("evidence", "semantic"),
        top_k_per_route=5,
    )
    assert retrieve_candidates(queries=(query,), index=FakeIndex((wrong_story, valid))) == (valid,)


def test_sequence_score_penalizes_discontinuity_and_reports_blocker() -> None:
    story_id, first_id, second_id = uuid4(), uuid4(), uuid4()
    graph = NarrativeBeatGraph(
        creative_brief_ref=ref("CreativeBrief"),
        beats=(beat(first_id, story_id), beat(second_id, story_id)),
        target_duration=time(8),
    )
    first = candidate(first_id, story_id, score=0.8, direction="left")
    smooth = candidate(second_id, story_id, score=0.7, direction="left")
    jump = candidate(second_id, story_id, score=0.9, direction="right", location="room")
    plan = plan_clip_sequence(
        candidate_set_ref=ref("ClipCandidateSet"),
        beat_graph=graph,
        candidates=(first, smooth, jump),
    )
    assert plan.selections[-1].candidate_id == smooth.candidate_id
    forced = plan.model_copy(
        update={
            "selections": (
                plan.selections[0],
                plan.selections[1].model_copy(update={"candidate_id": jump.candidate_id}),
            )
        }
    )
    report = analyze_continuity(
        selection_plan_ref=ref("PatchProposal"),
        selections=forced,
        candidates=(first, smooth, jump),
    )
    assert report.checked_edges == 1 and {risk.risk_type for risk in report.risks} >= {
        "screen-direction-jump",
        "location-discontinuity",
    }


def test_crop_path_is_bounded_and_missing_targets_fall_back() -> None:
    selection_ref, candidate_id = ref("PatchProposal"), uuid4()
    targets = (
        CompositionTarget(
            target_ref=uuid4(),
            start=time(0),
            end=time(2),
            center_x=0.1,
            center_y=0.5,
            minimum_coverage=0.8,
            priority=100,
        ),
        CompositionTarget(
            target_ref=uuid4(),
            start=time(2),
            end=time(4),
            center_x=0.9,
            center_y=0.5,
            minimum_coverage=0.8,
            priority=100,
            locked=True,
        ),
    )
    path = solve_crop_path(
        selection_plan_ref=selection_ref,
        candidate_id=candidate_id,
        targets=targets,
        duration=RationalTime.model_validate(time(4)),
    )
    assert len(path.keyframes) == 2
    assert path.keyframes[1].x - path.keyframes[0].x <= 0.12
    fallback = solve_crop_path(
        selection_plan_ref=selection_ref,
        candidate_id=candidate_id,
        targets=(),
        duration=RationalTime.model_validate(time(4)),
    )
    assert fallback.manual_required and fallback.fallback == "background_fill"


def test_subtitle_policy_and_local_scope_are_explicit() -> None:
    candidate_id, track_id = uuid4(), uuid4()
    plan = choose_source_subtitle_policy(
        candidate_id=candidate_id,
        text_track_refs=(track_id,),
        required_for_story=True,
        crop_safe=False,
    )
    assert plan.policy == "preserve" and plan.human_confirmation_required
    beat_ids = (uuid4(), uuid4(), uuid4(), uuid4())
    assert local_recompute_scope(beat_ids, beat_ids[2]) == beat_ids[1:4]
