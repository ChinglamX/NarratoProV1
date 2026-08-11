"""Canonical command, event, and error envelopes."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Self, TypeAlias

from pydantic import Field, JsonValue, RootModel, field_validator, model_validator

from packages.contracts.base import StrictContract
from packages.contracts.foundation import UUID, ActorRef, ArtifactRef, StableName

SchemaVersion: TypeAlias = Annotated[
    str,
    Field(pattern=r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$"),
]
EnvelopeType: TypeAlias = Annotated[
    str,
    Field(min_length=3, max_length=255, pattern=r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)+$"),
]
IdempotencyKey: TypeAlias = Annotated[
    str,
    Field(min_length=8, max_length=255, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]+$"),
]
JsonObject: TypeAlias = dict[str, JsonValue]


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("envelope timestamps must use UTC")
    return value


class TraceId(RootModel[str]):
    """W3C-compatible non-zero lowercase trace identifier."""

    root: Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]

    @field_validator("root")
    @classmethod
    def reject_zero_trace_id(cls, value: str) -> str:
        if value == "0" * 32:
            raise ValueError("trace_id must not be all zeros")
        return value


class CommandEnvelope(StrictContract):
    """Persistable intent accepted by the command boundary."""

    command_id: UUID
    command_type: EnvelopeType
    schema_version: SchemaVersion
    project_id: UUID
    run_id: UUID | None = None
    actor: ActorRef
    idempotency_key: IdempotencyKey
    expected_version: Annotated[int, Field(ge=0, le=2**63 - 1)] | None = None
    inputs: tuple[ArtifactRef, ...] = ()
    effective_config_ref: ArtifactRef | None = None
    payload: JsonObject
    requested_at: datetime

    _requested_at_utc = field_validator("requested_at")(_require_utc)


class EventEnvelope(StrictContract):
    """Immutable fact emitted through the transactional outbox."""

    event_id: UUID
    event_type: EnvelopeType
    schema_version: SchemaVersion
    aggregate_id: StableName
    aggregate_version: Annotated[int, Field(ge=1, le=2**63 - 1)]
    project_id: UUID
    run_id: UUID | None = None
    occurred_at: datetime
    producer: StableName
    trace_id: TraceId
    payload: JsonObject

    _occurred_at_utc = field_validator("occurred_at")(_require_utc)


class ErrorCategory(StrEnum):
    VALIDATION = "validation"
    CONFLICT_STALE = "conflict_stale"
    PERMISSION = "permission"
    RIGHTS_POLICY = "rights_policy"
    RESOURCE_BUDGET = "resource_budget"
    PROVIDER = "provider"
    WORKFLOW = "workflow"
    MEDIA = "media"
    QUALITY_BLOCKER = "quality_blocker"
    INTERNAL = "internal"


class DetailVisibility(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"


class ErrorDetail(StrictContract):
    """Typed diagnostic detail with an explicit disclosure boundary."""

    code: Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{2,127}$")]
    message: Annotated[str, Field(min_length=1, max_length=1_024)]
    visibility: DetailVisibility = DetailVisibility.INTERNAL
    data: JsonObject = Field(default_factory=dict)

    @model_validator(mode="after")
    def prevent_public_structured_data(self) -> Self:
        if self.visibility is DetailVisibility.PUBLIC and self.data:
            raise ValueError("public error details cannot carry arbitrary structured data")
        return self


class ResourceErrorRef(StrictContract):
    resource_type: StableName
    resource_id: StableName
    version: Annotated[int, Field(ge=0, le=2**63 - 1)] | None = None


class PublicErrorDetail(StrictContract):
    code: Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{2,127}$")]
    message: Annotated[str, Field(min_length=1, max_length=1_024)]


class PublicErrorEnvelope(StrictContract):
    code: Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{2,127}$")]
    category: ErrorCategory
    message: Annotated[str, Field(min_length=1, max_length=1_024)]
    retryable: bool
    details: tuple[PublicErrorDetail, ...] = ()
    request_id: IdempotencyKey
    trace_id: TraceId
    resource: ResourceErrorRef | None = None
    remediation: Annotated[str, Field(min_length=1, max_length=1_024)] | None = None


class ErrorEnvelope(StrictContract):
    """Internal error record that can be projected to a safe public DTO."""

    code: Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{2,127}$")]
    category: ErrorCategory
    message: Annotated[str, Field(min_length=1, max_length=1_024)]
    retryable: bool
    details: tuple[ErrorDetail, ...] = ()
    request_id: IdempotencyKey
    trace_id: TraceId
    resource: ResourceErrorRef | None = None
    remediation: Annotated[str, Field(min_length=1, max_length=1_024)] | None = None
    internal_message: Annotated[str, Field(min_length=1, max_length=8_192)] | None = None

    def to_public(self) -> PublicErrorEnvelope:
        return PublicErrorEnvelope(
            code=self.code,
            category=self.category,
            message=self.message,
            retryable=self.retryable,
            details=tuple(
                PublicErrorDetail(code=detail.code, message=detail.message)
                for detail in self.details
                if detail.visibility is DetailVisibility.PUBLIC
            ),
            request_id=self.request_id,
            trace_id=self.trace_id,
            resource=self.resource,
            remediation=self.remediation,
        )
