import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from packages.contracts.timeline_qualification import TimelineEngineeringQualification

PATH = Path("evaluation/qualification/e09_j06.json")


def test_e09_engineering_complete_keeps_real_quality_pending() -> None:
    value = TimelineEngineeringQualification.model_validate_json(PATH.read_text())
    assert value.engineering_complete and value.production_decision.value == "pending_human"
    assert sum(check.blocker for check in value.checks) == 4


def test_e09_cannot_bypass_checkpoint_or_synthesize_approval() -> None:
    raw = json.loads(PATH.read_text())
    raw["timeline_checkpoint_required"] = False
    with pytest.raises(ValidationError, match="cannot bypass"):
        TimelineEngineeringQualification.model_validate(raw)
    raw["timeline_checkpoint_required"] = True
    raw["production_decision"] = "approved"
    with pytest.raises(ValidationError, match="all checks passed"):
        TimelineEngineeringQualification.model_validate(raw)
