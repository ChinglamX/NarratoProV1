from types import SimpleNamespace
from uuid import uuid4

import pytest

from packages.contracts import ArtifactRef
from packages.persistence.identity_repository import IdentityRepository, IdentityStorageConflict


class Result:
    def __init__(self, *, first=None, mapping=None) -> None:
        self._first = first
        self._mapping = mapping

    def first(self):
        return self._first

    def mappings(self):
        return self

    def one(self):
        return self._mapping


class Connection:
    def __init__(self, results) -> None:
        self.results = iter(results)

    def execute(self, _statement):
        return next(self.results)


def graph_ref(version: int = 1) -> ArtifactRef:
    return ArtifactRef.model_validate(
        {"artifact_id": uuid4(), "version": version, "artifact_type": "IdentityGraph"}
    )


def test_identity_repository_rejects_stale_pointer_under_project_lock() -> None:
    connection = Connection((Result(), Result(first=SimpleNamespace(version=2))))
    with pytest.raises(IdentityStorageConflict, match="stale"):
        IdentityRepository().lock_and_load(  # type: ignore[arg-type]
            connection, project_id=uuid4(), graph_ref=graph_ref(1)
        )
