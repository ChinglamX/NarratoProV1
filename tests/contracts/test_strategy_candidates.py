from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.contracts.strategy_candidates import CandidateBudget, CandidateValidation


def test_candidate_budget_prevents_cartesian_explosion() -> None:
    with pytest.raises(ValidationError, match="global candidate bound"):
        CandidateBudget(
            max_selling_points=5,
            max_strategy_directions=4,
            max_hooks_per_direction=4,
            max_total_candidates=8,
            max_revision_rounds=1,
            max_model_tokens=100,
            max_estimated_cost_micros=0,
        )


def test_blocker_cannot_be_scored_valid() -> None:
    with pytest.raises(ValidationError, match="cannot be valid"):
        CandidateValidation.model_validate(
            {
                "candidate_id": uuid4(),
                "disposition": "valid",
                "blockers": [
                    {"code": "fabricated", "field": "story_refs", "detail": "not in Story"}
                ],
            }
        )
