import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from packages.contracts.render_release_qualification import (
    RenderReleaseEngineeringQualification,
)

PATH = Path("evaluation/qualification/e11_l06.json")


def test_e11_engineering_complete_keeps_release_pending() -> None:
    value = RenderReleaseEngineeringQualification.model_validate_json(PATH.read_text())
    assert value.engineering_complete and value.production_decision.value == "pending_human"
    assert sum(check.blocker for check in value.checks) == 6


def test_e11_never_allows_nonhuman_or_non_l1_release() -> None:
    raw = json.loads(PATH.read_text())
    raw["release_gate_human_only"] = False
    with pytest.raises(ValidationError, match="human-only"):
        RenderReleaseEngineeringQualification.model_validate(raw)
    raw["release_gate_human_only"] = True
    raw["automation_level"] = "L2"
    with pytest.raises(ValidationError, match="retain L1"):
        RenderReleaseEngineeringQualification.model_validate(raw)
