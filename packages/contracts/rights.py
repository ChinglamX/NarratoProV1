"""Canonical asset-rights metadata and typed artifact references."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from packages.contracts.base import StrictContract
from packages.contracts.foundation import ArtifactRef, StableName


class RightsGrantRef(ArtifactRef):
    artifact_type: Literal["RightsGrant"] = "RightsGrant"


class RightsManifestRef(ArtifactRef):
    artifact_type: Literal["RightsManifest"] = "RightsManifest"


class RightsStatus(StrEnum):
    UNKNOWN = "unknown"
    CLEARED = "cleared"
    RESTRICTED = "restricted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class RightsMetadata(StrictContract):
    """Immutable rights snapshot evaluated against an explicit release context."""

    status: RightsStatus
    source: Annotated[str, Field(min_length=1, max_length=1_024)] | None = None
    license: Annotated[str, Field(min_length=1, max_length=1_024)] | None = None
    grant_ref: RightsGrantRef | None = None
    evidence_refs: tuple[ArtifactRef, ...] = ()
    territories: frozenset[StableName] = frozenset()
    platforms: frozenset[StableName] = frozenset()
    commercial_use: bool = False
    modification: bool = False
    synchronization: bool = False
    attribution_required: bool = False
    attribution_text: Annotated[str, Field(min_length=1, max_length=2_048)] | None = None
    restrictions: tuple[Annotated[str, Field(min_length=1, max_length=1_024)], ...] = ()
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    checked_at: datetime

    @field_validator("valid_from", "valid_until", "checked_at")
    @classmethod
    def require_utc(cls, value: datetime | None) -> datetime | None:
        if value is not None and (
            value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value)
        ):
            raise ValueError("rights timestamps must use UTC")
        return value

    @model_validator(mode="after")
    def enforce_rights_snapshot(self) -> Self:
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_until <= self.valid_from
        ):
            raise ValueError("valid_until must be later than valid_from")
        if self.attribution_required and self.attribution_text is None:
            raise ValueError("attribution_text is required when attribution is required")
        if self.status is RightsStatus.CLEARED:
            missing = []
            if self.source is None:
                missing.append("source")
            if self.license is None:
                missing.append("license")
            if self.grant_ref is None:
                missing.append("grant_ref")
            if not self.territories:
                missing.append("territories")
            if not self.platforms:
                missing.append("platforms")
            if missing:
                raise ValueError(f"cleared rights missing required fields: {', '.join(missing)}")
        return self

    def release_blockers(
        self,
        *,
        at: datetime,
        platform: str,
        territory: str,
        requires_modification: bool = True,
        requires_synchronization: bool = True,
    ) -> tuple[str, ...]:
        """Return deterministic release blockers; an empty tuple means eligible."""

        normalized_at = self.require_utc(at)
        if normalized_at is None:  # pragma: no cover - the signature excludes None
            raise ValueError("release evaluation time is required")
        blockers: list[str] = []
        if self.status is not RightsStatus.CLEARED:
            blockers.append(f"rights_status:{self.status.value}")
        if not self.commercial_use:
            blockers.append("commercial_use_not_granted")
        if requires_modification and not self.modification:
            blockers.append("modification_not_granted")
        if requires_synchronization and not self.synchronization:
            blockers.append("synchronization_not_granted")
        if platform not in self.platforms:
            blockers.append("platform_out_of_scope")
        if territory not in self.territories:
            blockers.append("territory_out_of_scope")
        if self.valid_from is not None and normalized_at < self.valid_from:
            blockers.append("rights_not_yet_valid")
        if self.valid_until is not None and normalized_at >= self.valid_until:
            blockers.append("rights_expired")
        if self.restrictions:
            blockers.append("rights_restrictions_require_review")
        return tuple(blockers)
