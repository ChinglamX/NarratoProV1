from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.contracts.strategy_config import StrategyProfile


def profile(kind="genre", status="experimental", hard=None, validated=()):
    return StrategyProfile.model_validate(
        {
            "profile_id": uuid4(),
            "profile_version": "1.0.0",
            "schema_version": "1.0.0",
            "kind": kind,
            "name": f"{kind}-v1",
            "applicable_scope": ["short-drama"],
            "validated_scope": validated,
            "source": "project configuration",
            "owner": "strategy",
            "status": status,
            "hard_constraints": hard or {},
            "soft_preferences": {"pacing": "fast"},
        }
    )


def test_profile_status_and_hard_soft_boundary() -> None:
    assert profile().status.value == "experimental"
    with pytest.raises(ValidationError, match="cannot create hard"):
        profile(hard={"max_duration_seconds": 60})
    with pytest.raises(ValidationError, match="validated scope"):
        profile(kind="platform", status="approved")
