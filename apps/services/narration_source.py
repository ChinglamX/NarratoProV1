"""Persistence-backed narration source adapter (application layer)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Connection

from packages.contracts import ArtifactRef
from packages.contracts.timeline_intent import NarrationLineSet
from packages.persistence.artifact_repository import ArtifactNotFound, ArtifactRepository
from packages.timeline.narration import NarrationSourceUnavailable


class PersistenceNarrationSource:
    """Adapter reading exact-version ``NarrationLineSet`` payloads from storage."""

    def __init__(self, repository: ArtifactRepository, connection: Connection) -> None:
        self._repository = repository
        self._connection = connection

    def load(self, line_set_ref: ArtifactRef) -> NarrationLineSet:
        if line_set_ref.artifact_type != "NarrationLineSet":
            raise NarrationSourceUnavailable(
                f"narration source requires NarrationLineSet, got {line_set_ref.artifact_type}"
            )
        try:
            row = self._repository.get_version(self._connection, line_set_ref)
        except ArtifactNotFound as error:
            raise NarrationSourceUnavailable(str(error)) from error
        payload: Any = row.get("payload_json")
        if not isinstance(payload, dict):
            raise NarrationSourceUnavailable("narration line set payload is unavailable")
        return NarrationLineSet.model_validate(payload)
