from pathlib import Path

import pytest
from pydantic import ValidationError

from packages.contracts import ProductionQualification
from packages.evaluation.qualification import load_qualification, qualification_summary


def test_g05_matrix_is_valid_and_explicitly_not_qualified() -> None:
    qualification = load_qualification(Path("evaluation/qualification/e06_g05.json"))
    result = qualification_summary(qualification)
    assert result["production_qualified"] is False
    assert result["engineering_recommendation"] == "rejected"
    assert "speech-provider-rights" in result["blockers"]


def test_approval_cannot_bypass_blocked_checks_or_human() -> None:
    qualification = load_qualification(Path("evaluation/qualification/e06_g05.json"))
    values = qualification.model_dump(mode="json")
    values["decision"] = "approved"
    with pytest.raises(ValidationError, match="every check to pass"):
        ProductionQualification.model_validate(values)
