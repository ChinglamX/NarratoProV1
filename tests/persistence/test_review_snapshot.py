from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from packages.persistence.review_repository import ReviewRepository


def test_review_snapshot_returns_immutable_workspace_input() -> None:
    review_id = uuid4()
    project_id = uuid4()
    row = {
        "id": review_id,
        "project_id": project_id,
        "gate": "timeline",
        "state": "awaiting_review",
        "target_ref": {"artifact_id": str(uuid4()), "version": 3},
        "policy_snapshot": {"timeline_review_package": {"incomplete": False}},
    }
    result = MagicMock()
    result.mappings.return_value.first.return_value = row
    connection = SimpleNamespace(execute=lambda _statement: result)

    snapshot = ReviewRepository().snapshot(connection, review_id=review_id)

    assert snapshot is not None
    assert snapshot.review_id == review_id
    assert snapshot.project_id == project_id
    assert snapshot.target_ref["version"] == 3
    assert snapshot.policy_snapshot is not row["policy_snapshot"]


def test_review_snapshot_returns_none_for_unknown_review() -> None:
    result = MagicMock()
    result.mappings.return_value.first.return_value = None
    connection = SimpleNamespace(execute=lambda _statement: result)

    assert ReviewRepository().snapshot(connection, review_id=uuid4()) is None
