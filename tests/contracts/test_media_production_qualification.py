from pathlib import Path

from packages.contracts.media_production_qualification import (
    MediaProductionEngineeringQualification,
)


def test_e10_engineering_complete_keeps_production_pending() -> None:
    value = MediaProductionEngineeringQualification.model_validate_json(
        Path("evaluation/qualification/e10_k06.json").read_text()
    )
    assert value.engineering_complete and value.production_decision.value == "pending_human"
    assert sum(check.blocker for check in value.checks) == 4
