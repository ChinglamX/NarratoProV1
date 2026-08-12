"""PersistenceClipIndex adapter tests: deterministic routing over committed candidate sets."""

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from apps.services.clip_index import ClipIndexUnavailable, PersistenceClipIndex
from packages.contracts import ArtifactRef
from packages.contracts.timeline_intent import (
    ClipCandidate,
    ClipCandidateSet,
    ClipRetrievalQuery,
    RetrievalRoute,
)
from packages.persistence.artifact_repository import ArtifactNotFound


class FakeRepository:
    def __init__(self, payloads: dict[UUID, dict]) -> None:
        self._payloads = payloads

    def get_version(self, _connection: object, reference: ArtifactRef) -> dict:
        if reference.artifact_id not in self._payloads:
            raise ArtifactNotFound(str(reference.artifact_id))
        return {"payload_json": self._payloads[reference.artifact_id]}


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=kind)


def candidate(
    *,
    beat_id: UUID,
    story_id: UUID,
    evidence_id: UUID,
    score: float = 0.8,
    start: int = 0,
    duration: int = 2,
) -> ClipCandidate:
    return ClipCandidate(
        candidate_id=uuid4(),
        beat_id=beat_id,
        source_ref=ref("SourceMedia"),
        source_range={
            "start": {"value": start, "rate_num": 1},
            "duration": {"value": duration, "rate_num": 1},
        },
        story_refs=(story_id,),
        evidence_refs=(evidence_id,),
        quality={},
        continuity_features={},
        reframe_feasible=True,
        rights_allowed=True,
        score_components={"evidence": score, "semantic": score / 2},
    )


def build_index(candidates: tuple[ClipCandidate, ...]) -> PersistenceClipIndex:
    candidate_set = ClipCandidateSet(
        beat_graph_ref=ref("NarrativeBeatGraph"), candidates=candidates
    )
    candidate_set_ref = ref("ClipCandidateSet")
    repository = FakeRepository(
        {candidate_set_ref.artifact_id: candidate_set.model_dump(mode="json")}
    )
    return PersistenceClipIndex(repository, SimpleNamespace(), (candidate_set_ref,))


def test_retrieve_routes_per_route_top_k_deterministically() -> None:
    beat_id, story_id, evidence_id = uuid4(), uuid4(), uuid4()
    strong = candidate(beat_id=beat_id, story_id=story_id, evidence_id=evidence_id, score=0.9)
    weak = candidate(beat_id=beat_id, story_id=story_id, evidence_id=evidence_id, score=0.4)
    index = build_index((strong, weak))
    query = ClipRetrievalQuery(
        beat_id=beat_id,
        story_refs=(story_id,),
        routes=(RetrievalRoute.EVIDENCE,),
        top_k_per_route=1,
    )
    assert [item.candidate_id for item in index.retrieve(query)] == [strong.candidate_id]


def test_retrieve_drops_out_of_range_sources_when_durations_known() -> None:
    beat_id, story_id, evidence_id = uuid4(), uuid4(), uuid4()
    long = candidate(
        beat_id=beat_id, story_id=story_id, evidence_id=evidence_id, start=0, duration=9
    )
    ok = candidate(beat_id=beat_id, story_id=story_id, evidence_id=evidence_id, start=0, duration=2)
    index = build_index((long, ok))
    index._source_duration_by_ref = {long.source_ref.artifact_id: 3}
    query = ClipRetrievalQuery(
        beat_id=beat_id,
        story_refs=(story_id,),
        routes=(RetrievalRoute.EVIDENCE,),
        top_k_per_route=10,
    )
    assert [item.candidate_id for item in index.retrieve(query)] == [ok.candidate_id]


def test_index_rejects_non_candidate_set_refs() -> None:
    repository = FakeRepository({})
    with pytest.raises(ClipIndexUnavailable, match="ClipCandidateSet"):
        PersistenceClipIndex(repository, SimpleNamespace(), (ref("MasterTimeline"),))
