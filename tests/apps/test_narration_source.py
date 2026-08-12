"""PersistenceNarrationSource adapter tests: L1 human-approved line set loading."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from apps.services.narration_source import PersistenceNarrationSource
from packages.contracts import ArtifactRef
from packages.contracts.timeline_intent import NarrationLineSet
from packages.persistence.artifact_repository import ArtifactNotFound
from packages.timeline.narration import NarrationSourceUnavailable


class FakeRepository:
    def __init__(self, payloads: dict, fallback: object = None) -> None:
        self._payloads = payloads
        self._fallback = fallback

    def get_version(self, _connection: object, reference: ArtifactRef) -> dict:
        payload = self._payloads.get(reference.artifact_id, self._fallback)
        if payload is None:
            raise ArtifactNotFound(str(reference.artifact_id))
        return payload


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=kind)


def line_set() -> NarrationLineSet:
    return NarrationLineSet(
        creative_brief_ref=ref("CreativeBrief"),
        rhythm_plan_ref=ref("RhythmPlan"),
        lines=(),
        estimated_duration={"value": 0, "rate_num": 1},
    )


def test_load_returns_exact_version_line_set() -> None:
    value = line_set()
    value_ref = ref("NarrationLineSet")
    repository = FakeRepository(
        {value_ref.artifact_id: {"payload_json": value.model_dump(mode="json")}}
    )
    loaded = PersistenceNarrationSource(repository, SimpleNamespace()).load(value_ref)
    assert loaded == value


def test_load_rejects_wrong_artifact_type() -> None:
    repository = FakeRepository({})
    with pytest.raises(NarrationSourceUnavailable, match="NarrationLineSet"):
        PersistenceNarrationSource(repository, SimpleNamespace()).load(ref("MasterTimeline"))


def test_load_reports_missing_payload() -> None:
    value_ref = ref("NarrationLineSet")
    repository = FakeRepository({value_ref.artifact_id: {"payload_json": None}})
    with pytest.raises(NarrationSourceUnavailable, match="unavailable"):
        PersistenceNarrationSource(repository, SimpleNamespace()).load(value_ref)
