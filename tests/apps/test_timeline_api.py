from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from apps.api import timelines as api
from packages.contracts import ArtifactRef
from packages.persistence.timeline_repository import TimelineSnapshot
from tests.timeline.fixtures import artifact_ref, item, patch, timeline


class FakeRepository:
    def __init__(self, snapshot: TimelineSnapshot) -> None:
        self.snapshot = snapshot
        self.commits: list[dict[str, object]] = []

    def lock_and_load(self, *_args: object, **_kwargs: object) -> tuple[TimelineSnapshot, ...]:
        return self.snapshot, self.snapshot

    def commit(self, *_args: object, **kwargs: object) -> int:
        self.commits.append(kwargs)
        return 2


def test_timeline_api_applies_valid_semantic_patch(monkeypatch: pytest.MonkeyPatch) -> None:
    value = timeline()
    target = value.tracks[0].items[0]
    timeline_id = uuid4()
    candidate = patch(target, "set_parameter", {"key": "crop", "value": "center"})
    candidate = candidate.model_copy(
        update={
            "base_timeline": ArtifactRef.model_validate(
                artifact_ref("MasterTimeline") | {"artifact_id": timeline_id}
            )
        }
    )
    snapshot = TimelineSnapshot(
        1,
        value.model_dump(mode="json"),
        "1.0.0",
        uuid4(),
        None,
        {"kind": "test"},
        "internal",
    )
    repository = FakeRepository(snapshot)
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(database_engine=object(), timeline_repository=repository)
        )
    )

    @contextmanager
    def fake_transaction(_engine: object):
        yield object()

    monkeypatch.setattr(api, "transaction", fake_transaction)
    response = api.apply_timeline_patch(  # type: ignore[arg-type]
        timeline_id, candidate, request, "editor", "a" * 32
    )
    assert response["version"] == 2 and response["rebased"] is False
    assert repository.commits[0]["artifact_id"] == timeline_id


def test_timeline_api_requires_editor_role() -> None:
    with pytest.raises(HTTPException) as captured:
        api.apply_timeline_patch(  # type: ignore[arg-type]
            uuid4(), patch(item(), "remove", {}), SimpleNamespace(), "viewer"
        )
    assert captured.value.status_code == 403
