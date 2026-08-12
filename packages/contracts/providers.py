"""Provider admission and invocation boundary contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, model_validator

from packages.contracts.base import StrictContract
from packages.contracts.envelopes import JsonObject
from packages.contracts.foundation import ArtifactRef, Checksum, ProviderIdentity, StableName


class ProviderCapability(StrEnum):
    VAD = "vad"
    ASR = "asr"
    ALIGNMENT = "alignment"
    DIARIZATION = "diarization"
    OCR = "ocr"
    DETECTION = "detection"
    TRACKING = "tracking"
    FACE_EMBEDDING = "face_embedding"
    VISUAL_EMBEDDING = "visual_embedding"
    VLM = "vlm"


class ProviderAdmission(StrEnum):
    PRODUCTION = "production"
    RESEARCH = "research"
    BLOCKED = "blocked"


class ExecutionLocation(StrEnum):
    LOCAL = "local"
    PRIVATE_NETWORK = "private_network"
    EXTERNAL_CLOUD = "external_cloud"


class ProviderErrorCode(StrEnum):
    INVALID_INPUT = "invalid_input"
    POLICY_BLOCKED = "policy_blocked"
    RIGHTS_BLOCKED = "rights_blocked"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    MALFORMED_RESPONSE = "malformed_response"
    INTERNAL = "internal"


class ProviderDataPolicy(StrictContract):
    execution_location: ExecutionLocation
    allowed_residencies: tuple[StableName, ...]
    transmits_source_media: bool
    retains_input: bool
    retention_days: Annotated[int, Field(ge=0, le=36_500)] | None = None

    @model_validator(mode="after")
    def require_retention_disclosure(self) -> Self:
        if self.retains_input and self.retention_days is None:
            raise ValueError("retaining providers must disclose retention_days")
        if not self.retains_input and self.retention_days not in (None, 0):
            raise ValueError("non-retaining providers cannot declare positive retention")
        return self


class ProviderPackage(StrictContract):
    identity: ProviderIdentity
    capabilities: tuple[ProviderCapability, ...]
    admission: ProviderAdmission
    code_license: Annotated[str, Field(min_length=1, max_length=255)]
    weight_license: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    commercial_use_allowed: bool
    model_checksum: Checksum | None = None
    data_policy: ProviderDataPolicy
    supported_hardware: tuple[StableName, ...]
    supported_languages: tuple[StableName, ...] = ()
    deterministic: bool
    retry_safe: bool
    max_batch_size: Annotated[int, Field(gt=0, le=65_536)]
    known_limitations: tuple[Annotated[str, Field(min_length=1, max_length=1_024)], ...] = ()

    @model_validator(mode="after")
    def enforce_admission_evidence(self) -> Self:
        if not self.capabilities:
            raise ValueError("provider package requires at least one capability")
        if len(self.capabilities) != len(set(self.capabilities)):
            raise ValueError("provider capabilities must be unique")
        if self.admission is ProviderAdmission.PRODUCTION:
            if not self.commercial_use_allowed:
                raise ValueError("production provider requires commercial-use approval")
            if self.identity.model and (not self.weight_license or not self.model_checksum):
                raise ValueError("production model requires weight license and checksum")
        return self


class ProviderResourceEstimate(StrictContract):
    cpu_cores: Annotated[int, Field(ge=0, le=1_024)]
    memory_bytes: Annotated[int, Field(ge=0, le=2**63 - 1)]
    accelerator: StableName | None = None
    accelerator_memory_bytes: Annotated[int, Field(ge=0, le=2**63 - 1)] = 0
    temporary_disk_bytes: Annotated[int, Field(ge=0, le=2**63 - 1)] = 0
    estimated_duration_ms: Annotated[int, Field(ge=0, le=2**63 - 1)]
    estimated_cost_micros: Annotated[int, Field(ge=0, le=2**63 - 1)] = 0


class ProviderInvocationRequest(StrictContract):
    capability: ProviderCapability
    inputs: tuple[ArtifactRef, ...]
    config_ref: ArtifactRef
    resource_profile_ref: ArtifactRef
    idempotency_key: Annotated[str, Field(min_length=1, max_length=255)]
    timeout_ms: Annotated[int, Field(gt=0, le=86_400_000)]
    parameters: JsonObject = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_inputs(self) -> Self:
        if not self.inputs:
            raise ValueError("provider invocation requires inputs")
        return self


class RawProviderResponse(StrictContract):
    provider: ProviderIdentity
    capability: ProviderCapability
    request_checksum: Checksum
    payload_uri: Annotated[str, Field(min_length=1, max_length=4_096)]
    payload_checksum: Checksum
    media_type: Annotated[str, Field(min_length=1, max_length=255)]
    provider_schema_version: Annotated[str, Field(min_length=1, max_length=128)]
    redacted: bool


class ProviderInvocationResult(StrictContract):
    capability: ProviderCapability
    provider: ProviderIdentity
    raw_response_ref: ArtifactRef
    normalized_refs: tuple[ArtifactRef, ...]
    duration_ms: Annotated[int, Field(ge=0, le=2**63 - 1)]
    cost_micros: Annotated[int, Field(ge=0, le=2**63 - 1)]
    fallback_reason: Annotated[str, Field(min_length=1, max_length=1_024)] | None = None


class ProviderFailure(StrictContract):
    code: ProviderErrorCode
    message: Annotated[str, Field(min_length=1, max_length=2_048)]
    retryable: bool
    unavailable: bool
    retry_after_ms: Annotated[int, Field(ge=0, le=86_400_000)] | None = None

    @model_validator(mode="after")
    def enforce_retry_semantics(self) -> Self:
        never_retry = {
            ProviderErrorCode.INVALID_INPUT,
            ProviderErrorCode.POLICY_BLOCKED,
            ProviderErrorCode.RIGHTS_BLOCKED,
            ProviderErrorCode.MALFORMED_RESPONSE,
        }
        if self.code in never_retry and self.retryable:
            raise ValueError(f"{self.code} cannot be retryable")
        if self.retry_after_ms is not None and not self.retryable:
            raise ValueError("retry_after_ms requires retryable=true")
        return self
