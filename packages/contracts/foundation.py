"""Canonical foundation value objects shared by every project domain."""

from __future__ import annotations

from enum import StrEnum
from fractions import Fraction
from hashlib import sha256
from math import gcd
from typing import Annotated, Self

from pydantic import UUID4, Field, GetJsonSchemaHandler, RootModel, field_validator, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema

from packages.contracts.artifact_catalog import ARTIFACT_TYPES, require_known_artifact_type
from packages.contracts.base import StrictContract

UUID = UUID4
Int64 = Annotated[int, Field(ge=-(2**63), le=2**63 - 1)]
PositiveInt64 = Annotated[int, Field(ge=1, le=2**63 - 1)]
StableName = Annotated[str, Field(min_length=1, max_length=255, pattern=r"^[A-Za-z0-9_.:/@+-]+$")]


class ArtifactType(str):
    """Registered artifact type, represented as a string on every transport."""

    @classmethod
    def _validate(cls, value: str) -> ArtifactType:
        return cls(require_known_artifact_type(value))

    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type: object, _handler: object) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(pattern=r"^[A-Z][A-Za-z0-9]{0,127}$"),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, schema: CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        json_schema = handler(schema)
        json_schema["enum"] = sorted(ARTIFACT_TYPES)
        json_schema["title"] = "ArtifactType"
        return json_schema


class Checksum(RootModel[str]):
    """Content checksum encoded as ``algorithm:lowercase-hex-digest``."""

    root: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]

    @classmethod
    def from_bytes(cls, payload: bytes) -> Self:
        return cls(f"sha256:{sha256(payload).hexdigest()}")

    @property
    def algorithm(self) -> str:
        return self.root.partition(":")[0]

    @property
    def digest(self) -> str:
        return self.root.partition(":")[2]

    def __str__(self) -> str:
        return self.root


class ArtifactRef(StrictContract):
    """Immutable reference to one exact artifact version."""

    artifact_id: UUID
    version: PositiveInt64
    artifact_type: ArtifactType
    checksum: Checksum | None = None


class RationalTime(StrictContract):
    """Exact media timestamp expressed as ticks at a rational rate."""

    value: Int64
    rate_num: PositiveInt64
    rate_den: PositiveInt64 = 1

    @model_validator(mode="after")
    def normalize_rate(self) -> Self:
        divisor = gcd(self.rate_num, self.rate_den)
        if divisor != 1:
            object.__setattr__(self, "rate_num", self.rate_num // divisor)
            object.__setattr__(self, "rate_den", self.rate_den // divisor)
        return self

    @property
    def rate(self) -> Fraction:
        return Fraction(self.rate_num, self.rate_den)

    @property
    def seconds(self) -> Fraction:
        return Fraction(self.value * self.rate_den, self.rate_num)

    def rescaled_to(self, rate_num: int, rate_den: int = 1) -> RationalTime:
        """Represent this instant at another rate, rejecting non-integral ticks."""

        target_rate = Fraction(rate_num, rate_den)
        target_value = self.seconds * target_rate
        if target_value.denominator != 1:
            raise ValueError("target rate cannot represent this time using integral ticks")
        return RationalTime(
            value=target_value.numerator,
            rate_num=target_rate.numerator,
            rate_den=target_rate.denominator,
        )


class TimeRange(StrictContract):
    """Half-open exact media interval ``[start, start + duration)``."""

    start: RationalTime
    duration: RationalTime

    @field_validator("duration")
    @classmethod
    def require_non_negative_duration(cls, value: RationalTime) -> RationalTime:
        if value.value < 0:
            raise ValueError("duration must be non-negative")
        return value

    @property
    def end_seconds(self) -> Fraction:
        return self.start.seconds + self.duration.seconds

    @property
    def is_empty(self) -> bool:
        return self.duration.value == 0


class ActorKind(StrEnum):
    HUMAN = "human"
    MODEL = "model"
    SYSTEM = "system"


class ActorRef(StrictContract):
    """Auditable identity of the human, model, or system issuing an action."""

    kind: ActorKind
    id: StableName


class ProviderIdentity(StrictContract):
    """Reproducible identity and licensing snapshot for a provider invocation."""

    provider: StableName
    implementation: StableName
    version: StableName
    model: StableName | None = None
    checksum: Checksum | None = None
    license: Annotated[str, Field(min_length=1, max_length=255)]
