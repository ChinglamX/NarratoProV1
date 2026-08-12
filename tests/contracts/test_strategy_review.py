from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.contracts import ArtifactRef, StrategyGateSelection, VariantPlan, VariantSpec


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=kind)


def test_strategy_selection_freezes_only_registered_boundary_artifacts() -> None:
    selection = StrategyGateSelection(
        selected_strategy_id=uuid4(),
        selected_hook_id=uuid4(),
        creative_brief_ref=ref("CreativeBrief"),
        variant_plan_ref=ref("VariantPlan"),
    )
    assert selection.creative_brief_ref.artifact_type == "CreativeBrief"
    with pytest.raises(ValidationError, match="CreativeBrief"):
        selection.model_copy(update={"creative_brief_ref": ref("StoryGraph")}).model_validate(
            selection.model_copy(update={"creative_brief_ref": ref("StoryGraph")}).model_dump()
        )


def test_variant_plan_requires_one_control_and_enforces_budget() -> None:
    control = VariantSpec(
        variant_id=uuid4(),
        label="control",
        control=True,
        changed_dimensions={},
        estimated_incremental_cost_micros=0,
    )
    candidate = VariantSpec(
        variant_id=uuid4(),
        label="hook-b",
        control=False,
        changed_dimensions={"hook": "alternative"},
        estimated_incremental_cost_micros=10,
    )
    assert VariantPlan(
        creative_brief_ref=ref("CreativeBrief"), variants=(control, candidate), budget_micros=10
    ).candidate_variants_only
    with pytest.raises(ValidationError, match="exceeds budget"):
        VariantPlan(
            creative_brief_ref=ref("CreativeBrief"), variants=(control, candidate), budget_micros=9
        )
    with pytest.raises(ValidationError, match="exactly one control"):
        VariantPlan(
            creative_brief_ref=ref("CreativeBrief"), variants=(candidate,), budget_micros=10
        )
