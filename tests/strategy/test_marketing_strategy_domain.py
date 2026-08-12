"""Marketing Strategy planning and comparison domain tests."""

from uuid import uuid4

import pytest

from packages.contracts import (
    ArtifactRef,
    SellingPoint,
    SellingPointSet,
    StrategyCandidateSet,
    StrategyDirection,
)
from packages.contracts.strategy_candidates import CandidateBudget
from packages.contracts.strategy_evaluation import CandidateEvaluation
from packages.strategy.evaluation import assemble_comparison, diversity_report
from packages.strategy.planning import StrategyPlanningConflict, build_strategy_candidate_set


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef.model_validate({"artifact_id": uuid4(), "version": 1, "artifact_type": kind})


def direction(point_id, function="conflict") -> StrategyDirection:
    return StrategyDirection.model_validate(
        {
            "strategy_id": uuid4(),
            "objective": "建立身份悬念",
            "audience_hypothesis": "偏好人物反转的观众",
            "platform_profile_ref": ref("ConfigArtifact"),
            "genre_config_ref": ref("ConfigArtifact"),
            "primary_selling_point_refs": [point_id],
            "protagonist_ref": uuid4(),
            "viewpoint": "protagonist",
            "opening_promise": "身份即将揭晓",
            "ending_payoff": "真相得到回应",
            "narrative_spine": [
                {
                    "beat_id": uuid4(),
                    "function": function,
                    "story_refs": [uuid4()],
                    "priority": 100,
                    "information_owner": "mixed",
                    "required": True,
                }
            ],
            "reveal_policy": {"identity": "withhold"},
            "emotional_curve_intent": ["curiosity"],
            "target_duration": {"value": 60, "rate_num": 1},
            "production_estimate": {"complexity": "medium"},
            "feasible": True,
        }
    )


def evaluation(candidate_id, disposition="valid") -> CandidateEvaluation:
    return CandidateEvaluation.model_validate(
        {
            "candidate_id": candidate_id,
            "disposition": disposition,
            "deterministic_blockers": [],
            "critic_results": [],
            "risks": [],
            "feasibility": {
                "candidate_id": candidate_id,
                "feasible": True,
                "source_coverage": 1.0,
                "duration_feasible": True,
                "production_complexity": 1,
            },
            "cost": {
                "method_version": "1",
                "resource_profile_ref": ref("ResourceProfile"),
                "minimum_micros": 0,
                "maximum_micros": 100,
                "estimated_review_seconds": 60,
                "components_micros": {"model": 0},
            },
        }
    )


def test_diversity_is_structural_and_comparison_preserves_candidates() -> None:
    left, right = direction(uuid4()), direction(uuid4(), "payoff")
    candidate_set = StrategyCandidateSet(
        approved_story_ref=ref("StoryGraph"),
        selling_point_set_ref=ref("SellingPointSet"),
        effective_config_ref=ref("EffectiveConfigSnapshot"),
        candidates=(left, right),
    )
    candidate_ref = ref("StrategyCandidateSet")
    report = diversity_report(candidate_ref, candidate_set)
    assert report.pairs[0].differing_dimensions
    package = assemble_comparison(
        approved_story_ref=candidate_set.approved_story_ref,
        effective_config_ref=candidate_set.effective_config_ref,
        selling_point_set_ref=candidate_set.selling_point_set_ref,
        strategy_candidate_set_ref=candidate_ref,
        hook_candidate_set_ref=ref("HookCandidateSet"),
        candidate_set=candidate_set,
        evaluation_refs=(ref("EvaluationRun"), ref("EvaluationRun")),
        evaluations=(evaluation(left.strategy_id), evaluation(right.strategy_id)),
    )
    assert package.blocker_candidate_ids == ()


def test_strategy_planner_rejects_ungrounded_spine() -> None:
    point_id = uuid4()
    point = SellingPoint.model_validate(
        {
            "selling_point_id": point_id,
            "taxonomy_type": "reveal",
            "description": "身份揭晓",
            "story_refs": [uuid4()],
            "evidence": [
                {
                    "evidence_id": uuid4(),
                    "source": ref("FactSet"),
                    "evidence_type": "dialogue",
                    "excerpt": "真相",
                }
            ],
            "audience_rationale": "人工验证",
            "platform_fit": [],
            "narrative_role": "core",
            "spoiler_level": 1,
            "source_coverage": {},
            "risk_class": "high",
            "heuristic_components": {},
            "confidence": {
                "score": 0.5,
                "status": "shadow",
                "method": "test",
                "applicable_scope": "strategy:test",
                "risk_class": "high",
            },
        }
    )
    points = SellingPointSet(
        approved_story_ref=ref("StoryGraph"),
        taxonomy_version="1",
        selling_points=(point,),
    )
    candidate = direction(point_id)
    candidate = candidate.model_copy(
        update={
            "narrative_spine": tuple(
                beat.model_copy(update={"story_refs": (uuid4(),)})
                for beat in candidate.narrative_spine
            )
        }
    )
    candidate_budget = CandidateBudget(
        max_selling_points=2,
        max_strategy_directions=2,
        max_hooks_per_direction=2,
        max_total_candidates=4,
        max_revision_rounds=1,
        max_model_tokens=100,
        max_estimated_cost_micros=0,
    )
    with pytest.raises(StrategyPlanningConflict, match="not grounded"):
        build_strategy_candidate_set(
            approved_story_ref=points.approved_story_ref,
            selling_point_set_ref=ref("SellingPointSet"),
            effective_config_ref=ref("EffectiveConfigSnapshot"),
            selling_points=points,
            proposed=(candidate,),
            known_story_refs=set(),
            budget=candidate_budget,
        )
