from fractions import Fraction
from uuid import uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from packages.contracts import (
    ActorKind,
    ActorRef,
    ArtifactRef,
    Checksum,
    ProviderIdentity,
    RationalTime,
    TimeRange,
)


@given(st.binary())
def test_checksum_round_trips_arbitrary_bytes(payload: bytes) -> None:
    checksum = Checksum.from_bytes(payload)
    assert checksum.algorithm == "sha256"
    assert len(checksum.digest) == 64
    assert Checksum.model_validate_json(checksum.model_dump_json()) == checksum


@given(
    value=st.integers(min_value=-(2**63), max_value=2**63 - 1),
    rate_num=st.integers(min_value=1, max_value=100_000),
    rate_den=st.integers(min_value=1, max_value=100_000),
)
def test_rational_time_normalizes_without_changing_value(
    value: int, rate_num: int, rate_den: int
) -> None:
    timestamp = RationalTime(value=value, rate_num=rate_num, rate_den=rate_den)
    assert timestamp.rate == Fraction(rate_num, rate_den)
    assert timestamp.seconds == Fraction(value * rate_den, rate_num)
    assert timestamp.rate_num == timestamp.rate.numerator
    assert timestamp.rate_den == timestamp.rate.denominator


@given(
    value=st.integers(min_value=-1_000_000, max_value=1_000_000),
    rate=st.integers(min_value=1, max_value=1_000),
    multiplier=st.integers(min_value=1, max_value=1_000),
)
def test_exact_rescale_preserves_time(value: int, rate: int, multiplier: int) -> None:
    timestamp = RationalTime(value=value, rate_num=rate)
    rescaled = timestamp.rescaled_to(rate * multiplier)
    assert rescaled.seconds == timestamp.seconds
    assert rescaled.value == value * multiplier


def test_non_integral_rescale_is_rejected() -> None:
    with pytest.raises(ValueError, match="integral ticks"):
        RationalTime(value=1, rate_num=24).rescaled_to(25)


def test_time_range_rejects_negative_duration() -> None:
    with pytest.raises(ValidationError, match="non-negative"):
        TimeRange(
            start=RationalTime(value=0, rate_num=24),
            duration=RationalTime(value=-1, rate_num=24),
        )


def test_artifact_ref_canonical_serialization_is_stable() -> None:
    ref = ArtifactRef(
        artifact_id=uuid4(),
        version=3,
        artifact_type="StoryGraph",
        checksum=Checksum.from_bytes(b"story"),
    )
    restored = ArtifactRef.model_validate_json(ref.canonical_json())
    assert restored == ref
    assert restored.canonical_bytes() == ref.canonical_bytes()
    assert " " not in ref.canonical_json()


def test_foundation_contracts_are_frozen_and_forbid_unknown_fields() -> None:
    actor = ActorRef(kind=ActorKind.HUMAN, id="reviewer:42")
    with pytest.raises(ValidationError, match="Extra inputs"):
        ActorRef(kind="human", id="reviewer:42", display_name="Reviewer")
    with pytest.raises(ValidationError, match="frozen"):
        actor.id = "reviewer:43"  # type: ignore[misc]


def test_uuid4_is_the_uniform_internal_id_contract() -> None:
    with pytest.raises(ValidationError, match="UUID version 4"):
        ArtifactRef(
            artifact_id="00000000-0000-1000-8000-000000000000",
            version=1,
            artifact_type="FactSet",
        )


def test_provider_identity_requires_license_snapshot() -> None:
    provider = ProviderIdentity(
        provider="funasr",
        implementation="funasr-local",
        model="paraformer-zh",
        version="1.2.0",
        checksum=Checksum.from_bytes(b"weights"),
        license="MIT/code; model-card-v1/weights",
    )
    assert ProviderIdentity.model_validate_json(provider.canonical_json()) == provider

    with pytest.raises(ValidationError):
        ProviderIdentity(
            provider="funasr",
            implementation="funasr-local",
            version="1.2.0",
            license="",
        )
