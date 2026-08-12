"""Load Strategy inputs exclusively through the project Approved Story publication."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import Engine

from packages.contracts import ArtifactRef, StoryGraph
from packages.persistence import ArtifactRepository
from packages.persistence.review_repository import ReviewRepository


class ApprovedStoryRequired(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ApprovedStrategyInput:
    approved_story_ref: ArtifactRef
    story: StoryGraph


class StrategyInputService:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.reviews = ReviewRepository()
        self.artifacts = ArtifactRepository()

    def load(self, *, project_id: UUID) -> ApprovedStrategyInput:
        with self.engine.connect() as connection:
            raw_ref = self.reviews.approved_story(connection, project_id=project_id)
            if raw_ref is None:
                raise ApprovedStoryRequired("Strategy requires a human-approved StoryGraph")
            reference = ArtifactRef.model_validate(raw_ref)
            row: dict[str, Any] = self.artifacts.get_version(connection, reference)
        return ApprovedStrategyInput(reference, StoryGraph.model_validate(row["payload_json"]))
