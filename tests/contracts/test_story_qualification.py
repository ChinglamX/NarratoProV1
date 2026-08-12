from pathlib import Path

import pytest
from pydantic import ValidationError

from packages.contracts.story_qualification import StoryEngineeringQualification


def test_e07_qualification_is_engineering_complete_but_production_pending() -> None:
    value = StoryEngineeringQualification.model_validate_json(
        Path("evaluation/qualification/e07_h06.json").read_text()
    )
    assert value.engineering_complete
    assert value.production_decision.value == "pending_human"
    assert value.automation_level == "L1" and value.confidence_shadow
    assert any(item.blocker for item in value.checks)


def test_e07_qualification_cannot_fake_automation_or_human_approval() -> None:
    raw = __import__("json").loads(Path("evaluation/qualification/e07_h06.json").read_text())
    raw["automation_level"] = "L2"
    with pytest.raises(ValidationError, match="retain L1"):
        StoryEngineeringQualification.model_validate(raw)
    raw["automation_level"] = "L1"
    raw["story_gate_required"] = False
    with pytest.raises(ValidationError, match="cannot bypass"):
        StoryEngineeringQualification.model_validate(raw)
    raw["story_gate_required"] = True
    raw["production_decision"] = "approved"
    with pytest.raises(ValidationError, match="all checks passed"):
        StoryEngineeringQualification.model_validate(raw)
    raw["production_decision"] = "pending_human"
    raw["approved_by"] = {"kind": "human", "id": "owner"}
    with pytest.raises(ValidationError, match="cannot carry approver"):
        StoryEngineeringQualification.model_validate(raw)
