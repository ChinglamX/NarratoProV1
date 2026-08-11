"""Canonical immutable artifact envelope and dependency contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, field_validator, model_validator

from packages.contracts.base import StrictContract
from packages.contracts.envelopes import JsonObject, SchemaVersion, TraceId
from packages.contracts.foundation import (
    UUID,
    ActorRef,
    ArtifactRef,
    ArtifactType,
    Checksum,
    PositiveInt64,
    ProviderIdentity,
    StableName,
)


def require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("timestamps must use UTC")
    return value


class ArtifactState(StrEnum):
    STAGING = "staging"
    COMMITTED = "committed"
    APPROVED = "approved"
    STALE = "stale"
    SUPERSEDED = "superseded"
    BLOCKED = "blocked"
    DELETED_LOGICALLY = "deleted_logically"


class ProducerRecord(StrictContract):
    module: StableName
    module_version: Annotated[str, Field(min_length=1, max_length=128)]
    provider: ProviderIdentity | None = None
    prompt_version: Annotated[str, Field(min_length=1, max_length=128)] | None = None
    config_refs: tuple[ArtifactRef, ...] = ()
    tool_refs: tuple[ArtifactRef, ...] = ()
    resource_profile_ref: ArtifactRef


class ArtifactEnvelope(StrictContract):
    """Metadata shared by every persisted immutable business artifact."""

    artifact_id: UUID
    artifact_type: ArtifactType
    schema_version: SchemaVersion
    version: PositiveInt64
    project_id: UUID
    run_id: UUID
    variant_id: UUID | None = None
    state: ArtifactState
    created_at: datetime
    created_by: ActorRef
    inputs: tuple[ArtifactRef, ...] = ()
    producer: ProducerRecord
    checksum: Checksum
    rights_class: StableName
    trace_id: TraceId
    payload_uri: Annotated[str, Field(min_length=1, max_length=4_096)] | None = None
    payload: JsonObject | None = None

    _created_at_utc = field_validator("created_at")(require_utc)

    @model_validator(mode="after")
    def require_payload_and_identity_match(self) -> Self:
        if self.payload is None and self.payload_uri is None:
            raise ValueError("artifact requires payload or payload_uri")
        if len(set(self.inputs)) != len(self.inputs):
            raise ValueError("artifact inputs must be unique exact-version references")
        if any(
            item.artifact_id == self.artifact_id and item.version >= self.version
            for item in self.inputs
        ):
            raise ValueError("artifact cannot depend on its current or future version")
        return self

    def as_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.artifact_id,
            artifact_type=self.artifact_type,
            version=self.version,
            checksum=self.checksum,
        )


class DependencyType(StrEnum):
    SEMANTIC = "semantic"
    TIMING = "timing"
    MEDIA = "media"
    CONFIG = "config"
    RIGHTS = "rights"


class ArtifactDependency(StrictContract):
    upstream: ArtifactRef
    downstream: ArtifactRef
    dependency_type: DependencyType
    invalidation_rule: StableName

    @model_validator(mode="after")
    def reject_self_dependency(self) -> Self:
        if self.upstream == self.downstream:
            raise ValueError("artifact cannot depend on itself")
        return self
