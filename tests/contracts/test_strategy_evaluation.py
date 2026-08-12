from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.contracts.strategy_evaluation import CandidateEvaluation, CostEstimate


def ref(kind="ResourceProfile"):
    return {"artifact_id": uuid4(), "version": 1, "artifact_type": kind}


def cost() -> dict[str, object]:
    return {
        "method_version": "1",
        "resource_profile_ref": ref(),
        "minimum_micros": 100,
        "maximum_micros": 200,
        "estimated_review_seconds": 60,
        "components_micros": {"review": 100},
    }


def feasibility(candidate_id):
    return {
        "candidate_id": candidate_id,
        "feasible": True,
        "source_coverage": 1.0,
        "duration_feasible": True,
        "production_complexity": 1,
    }


def test_cost_range_and_blocker_dominance() -> None:
    with pytest.raises(ValidationError, match="maximum"):
        CostEstimate.model_validate(cost() | {"maximum_micros": 50})
    candidate_id = uuid4()
    with pytest.raises(ValidationError, match="cannot be offset"):
        CandidateEvaluation.model_validate(
            {
                "candidate_id": candidate_id,
                "disposition": "valid",
                "deterministic_blockers": [
                    {"code": "rights", "field": "source", "detail": "rights unknown"}
                ],
                "critic_results": [],
                "risks": [],
                "feasibility": feasibility(candidate_id),
                "cost": cost(),
                "heuristic_scores": {"creative": 1.0},
            }
        )
