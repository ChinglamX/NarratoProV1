import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from packages.contracts.strategy_qualification import StrategyEngineeringQualification

PATH = Path("evaluation/qualification/e08_i05.json")


def test_e08_engineering_complete_is_not_production_approval() -> None:
    value = StrategyEngineeringQualification.model_validate_json(PATH.read_text())
    assert value.engineering_complete
    assert value.production_decision.value == "pending_human"
    assert value.automation_level == "L1" and value.confidence_shadow
    assert sum(check.blocker for check in value.checks) == 5


@pytest.mark.parametrize("gate", ["story_gate_required", "strategy_gate_required"])
def test_e08_cannot_bypass_human_gates(gate: str) -> None:
    raw = json.loads(PATH.read_text())
    raw[gate] = False
    with pytest.raises(ValidationError, match="cannot bypass"):
        StrategyEngineeringQualification.model_validate(raw)


def test_e08_cannot_synthesize_production_approval() -> None:
    raw = json.loads(PATH.read_text())
    raw["production_decision"] = "approved"
    with pytest.raises(ValidationError, match="all checks passed"):
        StrategyEngineeringQualification.model_validate(raw)
    raw["production_decision"] = "pending_human"
    raw["approved_by"] = {"kind": "human", "id": "owner"}
    with pytest.raises(ValidationError, match="cannot carry approver"):
        StrategyEngineeringQualification.model_validate(raw)


def test_e08_cannot_enable_uncalibrated_automation_or_empty_taxonomy() -> None:
    raw = json.loads(PATH.read_text())
    raw["automation_level"] = "L2"
    with pytest.raises(ValidationError, match="retain L1"):
        StrategyEngineeringQualification.model_validate(raw)
    raw["automation_level"] = "L1"
    raw["severe_errors"] = []
    with pytest.raises(ValidationError, match="requires checks and severe errors"):
        StrategyEngineeringQualification.model_validate(raw)
