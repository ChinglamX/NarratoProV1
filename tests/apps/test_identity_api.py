import pytest
from fastapi import HTTPException

from apps.api.identities import _require_reviewer


def test_identity_api_requires_review_role() -> None:
    assert _require_reviewer("viewer,story_reviewer") == ("story_reviewer", "viewer")
    with pytest.raises(HTTPException) as captured:
        _require_reviewer("viewer")
    assert captured.value.status_code == 403
