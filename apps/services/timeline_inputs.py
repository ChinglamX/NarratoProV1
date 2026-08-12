"""Approved Strategy-only input boundary for E09 Creative Timeline."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Connection

from packages.contracts import ArtifactRef
from packages.contracts.timeline_intent import TimelineIntentInput
from packages.persistence.review_repository import ReviewRepository


class TimelineInputUnavailable(RuntimeError):
    pass


class TimelineInputService:
    def __init__(self, reviews: ReviewRepository) -> None:
        self._reviews = reviews

    def approved_strategy_refs(
        self, connection: Connection, *, project_id: UUID
    ) -> tuple[ArtifactRef, ArtifactRef]:
        brief = self._reviews.approved_strategy_ref(
            connection, project_id=project_id, registry_type="approved_creative_brief"
        )
        variants = self._reviews.approved_strategy_ref(
            connection, project_id=project_id, registry_type="approved_variant_plan"
        )
        if brief is None or variants is None:
            raise TimelineInputUnavailable("Creative Timeline requires approved Strategy pointers")
        return ArtifactRef.model_validate(brief), ArtifactRef.model_validate(variants)

    def build_input(
        self,
        connection: Connection,
        *,
        project_id: UUID,
        approved_story_ref: ArtifactRef,
        media_catalog_ref: ArtifactRef,
        platform_profile_ref: ArtifactRef,
    ) -> TimelineIntentInput:
        brief, variants = self.approved_strategy_refs(connection, project_id=project_id)
        return TimelineIntentInput(
            approved_creative_brief_ref=brief,
            approved_variant_plan_ref=variants,
            approved_story_ref=approved_story_ref,
            media_catalog_ref=media_catalog_ref,
            platform_profile_ref=platform_profile_ref,
        )
