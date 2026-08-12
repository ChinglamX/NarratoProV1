"""TimelinePlanningService tests: grounded planning with artifact persistence."""

from types import SimpleNamespace
from uuid import UUID, uuid4

from apps.services.timeline_planning import PlanningArtifactIds, TimelinePlanningService
from packages.contracts import ActorRef, ArtifactEnvelope, ArtifactRef
from packages.contracts.timeline_intent import (
    ClipCandidate,
    ClipRetrievalQuery,
    CompositionTarget,
    NarrativeBeat,
    NarrativeBeatGraph,
    RetrievalRoute,
)


class FakeArtifactRepository:
    def __init__(self) -> None:
        self.committed: list[ArtifactEnvelope] = []

    def reserve(self, _connection: object, **_kwargs: object) -> None:
        pass

    def commit_version(
        self,
        _connection: object,
        envelope: ArtifactEnvelope,
        *,
        expected_latest_version: int,
        blob_id: UUID | None = None,
    ) -> ArtifactRef:
        assert expected_latest_version == 0
        self.committed.append(envelope)
        return envelope.as_ref()


class FakeIndex:
    def __init__(self, candidates: tuple[ClipCandidate, ...]) -> None:
        self._candidates = candidates

    def retrieve(self, _query: ClipRetrievalQuery) -> tuple[ClipCandidate, ...]:
        return self._candidates


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=kind)


def beat(beat_id: UUID, story_id: UUID) -> NarrativeBeat:
    return NarrativeBeat(
        beat_id=beat_id,
        function="hook",
        story_refs=(story_id,),
        target_duration={"value": 5, "rate_num": 1},
        minimum_duration={"value": 3, "rate_num": 1},
        maximum_duration={"value": 7, "rate_num": 1},
        required_information=("who",),
        emotional_intent={},
    )


def candidate(beat_id: UUID, story_id: UUID, evidence_id: UUID, time: str) -> ClipCandidate:
    return ClipCandidate(
        candidate_id=uuid4(),
        beat_id=beat_id,
        source_ref=ref("SourceMedia"),
        source_range={
            "start": {"value": 0, "rate_num": 1},
            "duration": {"value": 5, "rate_num": 1},
        },
        story_refs=(story_id,),
        evidence_refs=(evidence_id,),
        quality={},
        continuity_features={"time": time},
        reframe_feasible=True,
        rights_allowed=True,
        score_components={"evidence": 0.9},
    )


def service_call(
    repository: FakeArtifactRepository,
    beat_graph: NarrativeBeatGraph,
    candidates: tuple[ClipCandidate, ...],
    *,
    targets: dict[UUID, tuple[CompositionTarget, ...]] | None = None,
) -> object:
    queries = tuple(
        ClipRetrievalQuery(
            beat_id=item.beat_id,
            story_refs=item.story_refs,
            routes=(RetrievalRoute.EVIDENCE,),
            top_k_per_route=10,
        )
        for item in beat_graph.beats
    )
    return TimelinePlanningService(repository).plan_visual(
        SimpleNamespace(),
        project_id=uuid4(),
        run_id=uuid4(),
        variant_id=None,
        trace_id="a" * 32,
        actor=ActorRef(kind="system", id="test"),
        resource_profile_ref=ref("ConfigArtifact"),
        beat_graph=beat_graph,
        beat_graph_ref=ref("NarrativeBeatGraph"),
        queries=queries,
        index=FakeIndex(candidates),
        composition_targets=targets,
        ids=PlanningArtifactIds(),
    )


def test_planning_persists_full_artifact_lineage() -> None:
    beat_id, story_id, evidence_id = uuid4(), uuid4(), uuid4()
    graph = NarrativeBeatGraph(
        creative_brief_ref=ref("CreativeBrief"),
        beats=(beat(beat_id, story_id),),
        target_duration={"value": 5, "rate_num": 1},
    )
    chosen = candidate(beat_id, story_id, evidence_id, "t1")
    repository = FakeArtifactRepository()
    outcome = service_call(repository, graph, (chosen,))
    types = {envelope.artifact_type for envelope in repository.committed}
    assert "ClipCandidateSet" in types
    assert "ClipSelectionPlan" in types
    assert "ContinuityReport" in types
    assert "VisualPlanningReport" in types
    assert "SourceSubtitleHandlingPlan" in types
    assert not outcome.incomplete and outcome.coverage_gaps == 0


def test_missing_coverage_fails_closed_with_gap_and_incomplete_flag() -> None:
    beat_id, story_id = uuid4(), uuid4()
    graph = NarrativeBeatGraph(
        creative_brief_ref=ref("CreativeBrief"),
        beats=(beat(beat_id, story_id),),
        target_duration={"value": 5, "rate_num": 1},
    )
    repository = FakeArtifactRepository()
    outcome = service_call(repository, graph, ())
    assert outcome.incomplete and outcome.coverage_gaps == 1
    assert outcome.selection_plan_ref is not None


def test_continuity_time_conflict_is_reported_as_blocker_metric() -> None:
    first_beat, second_beat, story_id = uuid4(), uuid4(), uuid4()
    graph = NarrativeBeatGraph(
        creative_brief_ref=ref("CreativeBrief"),
        beats=(beat(first_beat, story_id), beat(second_beat, story_id)),
        target_duration={"value": 10, "rate_num": 1},
    )
    first = candidate(first_beat, story_id, uuid4(), "day")
    second = candidate(second_beat, story_id, uuid4(), "night")
    repository = FakeArtifactRepository()
    outcome = service_call(repository, graph, (first, second))
    assert outcome.continuity_blockers == 1
    assert any(item.name == "timeline_continuity_blockers" for item in outcome.metrics)


def test_crop_path_committed_when_targets_supplied() -> None:
    beat_id, story_id, evidence_id = uuid4(), uuid4(), uuid4()
    graph = NarrativeBeatGraph(
        creative_brief_ref=ref("CreativeBrief"),
        beats=(beat(beat_id, story_id),),
        target_duration={"value": 5, "rate_num": 1},
    )
    chosen = candidate(beat_id, story_id, evidence_id, "t1")
    target = CompositionTarget(
        target_ref=uuid4(),
        start={"value": 0, "rate_num": 1},
        end={"value": 4, "rate_num": 1},
        center_x=0.5,
        center_y=0.5,
        minimum_coverage=0.4,
        priority=50,
    )
    repository = FakeArtifactRepository()
    outcome = service_call(repository, graph, (chosen,), targets={chosen.candidate_id: (target,)})
    assert len(outcome.crop_path_refs) == 1
    types = {envelope.artifact_type for envelope in repository.committed}
    assert "CropPath" in types
