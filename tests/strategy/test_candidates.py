from uuid import uuid4

from packages.contracts import (
    ArtifactRef,
    ConfidenceRecord,
    Event,
    HookCandidate,
    StoryGraph,
)
from packages.contracts.strategy_candidates import CandidateBudget
from packages.strategy.candidates import (
    assemble_hook_set,
    discover_selling_points,
)


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef.model_validate({"artifact_id": uuid4(), "version": 1, "artifact_type": kind})


def confidence() -> ConfidenceRecord:
    return ConfidenceRecord.model_validate(
        {
            "score": 0.7,
            "status": "shadow",
            "method": "heuristic-test",
            "applicable_scope": "strategy:test",
            "risk_class": "high",
        }
    )


def evidence():
    return {
        "evidence_id": uuid4(),
        "source": ref("FactSet"),
        "source_range": {
            "start": {"value": 0, "rate_num": 25},
            "duration": {"value": 25, "rate_num": 25},
        },
        "evidence_type": "dialogue",
        "excerpt": "真相终于公开",
    }


def budget() -> CandidateBudget:
    return CandidateBudget(
        max_selling_points=2,
        max_strategy_directions=2,
        max_hooks_per_direction=2,
        max_total_candidates=4,
        max_revision_rounds=1,
        max_model_tokens=1000,
        max_estimated_cost_micros=0,
    )


def story() -> StoryGraph:
    event = Event.model_validate(
        {
            "event_id": uuid4(),
            "order_key": "event:1",
            "description": "身份真相公开",
            "participants": [],
            "evidence": [evidence()],
            "confidence": confidence(),
            "importance": "key",
        }
    )
    return StoryGraph(
        source_fact_refs=(ref("FactSet"),),
        characters=(),
        events=(event,),
        edges=(),
    )


def test_selling_points_are_bounded_and_grounded() -> None:
    story_ref = ref("StoryGraph")
    points, coverage = discover_selling_points(
        approved_story_ref=story_ref,
        story=story(),
        taxonomy_version="1.0.0",
        taxonomy_by_event_importance={"key": "reveal"},
        budget=budget(),
        confidence=confidence(),
    )
    assert len(points.selling_points) == 1
    assert points.selling_points[0].taxonomy_type == "reveal"
    assert coverage.uncovered_story_ref_ids == ()


def test_hook_unknown_story_moment_and_mechanic_are_blockers() -> None:
    known = uuid4()
    hook = HookCandidate.model_validate(
        {
            "hook_id": uuid4(),
            "hook_type": "unsupported",
            "opening_promise": "他究竟是谁?",
            "source_moment_refs": [uuid4()],
            "visual_intent": {"subject": "character"},
            "audience_question": "真相是什么?",
            "duration_budget": {"value": 3, "rate_num": 1},
            "continuation_beats": [known],
            "evidence": [evidence()],
            "heuristic_scores": {"comprehension": 0.5},
            "confidence": confidence(),
        }
    )
    result = assemble_hook_set(
        approved_story_ref=ref("StoryGraph"),
        strategy_candidate_set_ref=ref("StrategyCandidateSet"),
        proposed=(hook,),
        known_story_refs={known},
        allowed_mechanics={"identity-question"},
        budget=budget(),
    )
    assert result.validations[0].disposition.value == "rejected"
    assert {item.code for item in result.validations[0].blockers} == {
        "unsupported-hook-mechanic",
        "unknown-source-moment",
    }
