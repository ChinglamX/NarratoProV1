"""RhythmPlanningService tests: budgets, conflicts, narration review and revision."""

from types import SimpleNamespace
from uuid import uuid4

from apps.services.rhythm_planning import RhythmPlanningService
from packages.contracts import ActorRef, ArtifactEnvelope, ArtifactRef, RationalTime
from packages.contracts.timeline_intent import (
    NarrationLine,
    NarrationLineSet,
    NarrativeBeat,
    NarrativeBeatGraph,
)


class FakeArtifactRepository:
    def __init__(self) -> None:
        self.committed: list[ArtifactEnvelope] = []

    def reserve(self, _connection: object, **_kwargs: object) -> None:
        pass

    def commit_version(
        self, _connection: object, envelope: ArtifactEnvelope, **kwargs: object
    ) -> ArtifactRef:
        self.committed.append(envelope)
        return envelope.as_ref()


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=kind)


def graph(*, minimum: int = 3, target_beat: int = 5, target: int = 5) -> NarrativeBeatGraph:
    beat = NarrativeBeat(
        beat_id=uuid4(),
        function="hook",
        story_refs=(uuid4(),),
        target_duration={"value": target_beat, "rate_num": 1},
        minimum_duration={"value": minimum, "rate_num": 1},
        maximum_duration={"value": 7, "rate_num": 1},
        required_information=("who",),
        emotional_intent={},
    )
    return NarrativeBeatGraph(
        creative_brief_ref=ref("CreativeBrief"),
        beats=(beat,),
        target_duration={"value": target, "rate_num": 1},
    )


def service(repository: FakeArtifactRepository) -> RhythmPlanningService:
    return RhythmPlanningService(repository)


def common() -> dict:
    return {
        "connection": SimpleNamespace(),
        "project_id": uuid4(),
        "run_id": uuid4(),
        "variant_id": None,
        "trace_id": "a" * 32,
        "actor": ActorRef(kind="system", id="test"),
        "resource_profile_ref": ref("ConfigArtifact"),
    }


def test_plan_rhythm_commits_reconciled_plan() -> None:
    repository = FakeArtifactRepository()
    outcome = service(repository).plan_rhythm(
        **common(),
        beat_graph=graph(),
        beat_graph_ref=ref("NarrativeBeatGraph"),
        selection_plan_ref=ref("ClipSelectionPlan"),
    )
    assert outcome.rhythm_plan_ref is not None and outcome.duration_conflict is None
    assert repository.committed[-1].artifact_type == "RhythmPlan"


def test_plan_rhythm_reports_infeasible_budget_without_committing() -> None:
    repository = FakeArtifactRepository()
    # The beat-graph contract rejects min>target, so the defensive conflict
    # branch is exercised with a graph that bypasses validation.
    heavy_beat = NarrativeBeat.model_construct(
        beat_id=uuid4(),
        function="hook",
        story_refs=(uuid4(),),
        target_duration=RationalTime(value=5, rate_num=1),
        minimum_duration=RationalTime(value=6, rate_num=1),
        maximum_duration=RationalTime(value=7, rate_num=1),
        required_information=("who",),
        emotional_intent={},
        locked=False,
    )
    unvalidated = NarrativeBeatGraph.model_construct(
        creative_brief_ref=ref("CreativeBrief"),
        beats=(heavy_beat,),
        target_duration=RationalTime(value=5, rate_num=1),
    )
    outcome = service(repository).plan_rhythm(
        **common(),
        beat_graph=unvalidated,
        beat_graph_ref=ref("NarrativeBeatGraph"),
        selection_plan_ref=ref("ClipSelectionPlan"),
    )
    assert outcome.rhythm_plan_ref is None
    assert outcome.duration_conflict is not None
    assert outcome.duration_conflict.alternatives
    assert repository.committed == []


def test_review_lines_persists_report_with_blockers() -> None:
    line_id = uuid4()
    line = NarrationLine(
        line_id=line_id,
        beat_id=uuid4(),
        text="你站住",
        function="bridge",
        story_refs=(uuid4(),),
        evidence_refs=(uuid4(),),
        target_duration={"value": 2, "rate_num": 1},
        dialogue_relationship="none",
    )
    lines = NarrationLineSet(
        creative_brief_ref=ref("CreativeBrief"),
        rhythm_plan_ref=ref("RhythmPlan"),
        lines=(line,),
        estimated_duration={"value": 2, "rate_num": 1},
    )
    repository = FakeArtifactRepository()
    report_ref = service(repository).review_lines(
        **common(),
        line_set=lines,
        line_set_ref=ref("NarrationLineSet"),
        dialogue_by_beat={line.beat_id: ("你站住!",)},
    )
    assert report_ref.artifact_type == "NarrationPlanningReport"
    payload = repository.committed[-1].payload
    assert payload is not None
    assert payload["findings"][0]["code"] == "dialogue-repetition"


class FakeNarrationSource:
    def __init__(self, current: NarrationLineSet) -> None:
        self._current = current

    def load(self, line_set_ref: ArtifactRef) -> NarrationLineSet:
        return self._current


def test_replace_lines_commits_successor_line_set() -> None:
    line_id = uuid4()
    line = NarrationLine(
        line_id=line_id,
        beat_id=uuid4(),
        text="他推开门",
        function="bridge",
        story_refs=(uuid4(),),
        evidence_refs=(uuid4(),),
        target_duration={"value": 2, "rate_num": 1},
        dialogue_relationship="bridge",
    )
    current = NarrationLineSet(
        creative_brief_ref=ref("CreativeBrief"),
        rhythm_plan_ref=ref("RhythmPlan"),
        lines=(line,),
        estimated_duration={"value": 2, "rate_num": 1},
    )
    repository = FakeArtifactRepository()
    updated_ref, updated = service(repository).replace_lines(
        **common(),
        source=FakeNarrationSource(current),
        current_ref=ref("NarrationLineSet"),
        replacements={line_id: line.model_copy(update={"text": "他轻轻推开门"})},
    )
    assert updated.lines[0].text == "他轻轻推开门"
    assert repository.committed[-1].artifact_type == "NarrationLineSet"
    assert updated_ref.checksum is not None
