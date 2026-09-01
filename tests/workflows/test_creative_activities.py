"""Creative Timeline activity orchestration tests with mocked storage boundaries."""

from types import SimpleNamespace
from uuid import uuid4

from workflows.project.models import ArtifactPointer
from workflows.timeline import creative_activities as module
from workflows.timeline.creative_models import (
    AssemblyActivityRequest,
    ClipQuerySpec,
    NarrationReviewActivityRequest,
    PlanningIdSpec,
    VisualPlanningActivityRequest,
)


def pointer(artifact_id=None, kind="MasterTimeline", version=1) -> ArtifactPointer:
    return ArtifactPointer(
        artifact_id=artifact_id or str(uuid4()), version=version, artifact_type=kind
    )


def test_query_specs_build_grounded_retrieval_queries() -> None:
    beat_id, story_id, character_id = (uuid4() for _ in range(3))
    queries = module._query_specs(
        (
            ClipQuerySpec(
                beat_id=str(beat_id),
                story_refs=(str(story_id),),
                required_character_refs=(str(character_id),),
                routes=("evidence", "semantic"),
                top_k_per_route=5,
            ),
        )
    )
    assert queries[0].beat_id == beat_id
    assert queries[0].required_character_refs == (character_id,)
    assert [route.value for route in queries[0].routes] == ["evidence", "semantic"]


def test_planning_ids_convert_spec_fields() -> None:
    candidate_id, selection_id, continuity_id, report_id = (uuid4() for _ in range(4))
    ids = module._planning_ids(
        PlanningIdSpec(
            candidate_set_id=str(candidate_id),
            selection_plan_id=str(selection_id),
            continuity_report_id=str(continuity_id),
            visual_report_id=str(report_id),
        )
    )
    assert ids.candidate_set_id == candidate_id
    assert ids.visual_report_id == report_id


def test_ref_pointer_round_trip_preserves_identity() -> None:
    value = pointer(kind="ClipCandidateSet")
    reference = module._ref(value)
    restored = module._pointer(reference)
    assert restored.artifact_id == value.artifact_id
    assert restored.artifact_type == "ClipCandidateSet"
    assert restored.version == 1


def test_common_uses_system_actor_and_typed_ids() -> None:
    request = VisualPlanningActivityRequest(
        run_id=str(uuid4()),
        project_id=str(uuid4()),
        trace_id="a" * 32,
        resource_profile=pointer(kind="ConfigArtifact"),
        beat_graph=pointer(kind="NarrativeBeatGraph"),
        candidate_sets=(),
        queries=(),
    )
    common = module._common(request)
    assert common["actor"].kind == "system"
    assert common["trace_id"] == request.trace_id
    assert common["variant_id"] is None


def test_review_narration_sync_orchestrates_review_and_report(monkeypatch) -> None:
    line_set_id = uuid4()
    report_id = uuid4()
    connection = SimpleNamespace()

    captured = {}

    def fake_run_activity(handler):
        captured["connection"] = handler(connection)
        return captured["connection"]

    monkeypatch.setattr(module, "_run_activity", fake_run_activity)

    class FakeRepository:
        def __init__(self) -> None:
            self.committed = []

        def get_version(self, _connection, reference):
            from packages.contracts.timeline_intent import NarrationLineSet

            if reference.artifact_type == "NarrationPlanningReport":
                return {
                    "payload_json": {"findings": [], "evidence_coverage": 1.0},
                }
            return {
                "payload_json": NarrationLineSet(
                    creative_brief_ref=module._ref(pointer(kind="CreativeBrief")),
                    rhythm_plan_ref=module._ref(pointer(kind="RhythmPlan")),
                    lines=(),
                    estimated_duration={"value": 0, "rate_num": 1},
                ).model_dump(mode="json")
            }

        def reserve(self, _connection, **_kwargs):
            pass

        def commit_version(self, _connection, envelope, **_kwargs):
            self.committed.append(envelope)
            return envelope.as_ref()

    repository = FakeRepository()
    monkeypatch.setattr(module, "ArtifactRepository", lambda: repository)

    class FakeRhythmService:
        def __init__(self, _repository: object) -> None:
            pass

        def review_lines(self, connection, **kwargs):
            captured["kwargs"] = kwargs
            return module._ref(pointer(artifact_id=str(report_id), kind="NarrationPlanningReport"))

    monkeypatch.setattr(module, "RhythmPlanningService", FakeRhythmService)
    request = NarrationReviewActivityRequest(
        run_id=str(uuid4()),
        project_id=str(uuid4()),
        trace_id="b" * 32,
        resource_profile=pointer(kind="ConfigArtifact"),
        line_set=pointer(artifact_id=str(line_set_id), kind="NarrationLineSet"),
        report_id=str(report_id),
        dialogue_by_beat={},
    )
    result = module._review_narration_sync(request)
    assert result.report.artifact_id == str(report_id)
    assert captured["kwargs"]["line_set_ref"].artifact_id == line_set_id
    assert result.blocker_codes == ()


def test_assemble_sync_passes_projected_intents_to_service(monkeypatch) -> None:
    beat_id, evidence_id = uuid4(), uuid4()
    timeline_id = uuid4()
    selection_ref = pointer(kind="ClipSelectionPlan")
    connection = SimpleNamespace()

    def fake_run_activity(handler):
        return handler(connection)

    monkeypatch.setattr(module, "_run_activity", fake_run_activity)

    from packages.contracts.timeline_intent import (
        ClipCandidate,
        ClipCandidateSet,
        ClipSelection,
        ClipSelectionPlan,
        NarrationLine,
        NarrationLineSet,
    )

    chosen = ClipCandidate(
        candidate_id=uuid4(),
        beat_id=beat_id,
        source_ref=module._ref(pointer(kind="SourceMedia")),
        source_range={
            "start": {"value": 0, "rate_num": 1},
            "duration": {"value": 5, "rate_num": 1},
        },
        story_refs=(uuid4(),),
        evidence_refs=(evidence_id,),
        quality={},
        continuity_features={},
        reframe_feasible=True,
        rights_allowed=True,
        score_components={"evidence": 1.0},
    )
    candidate_set_payload = ClipCandidateSet(
        beat_graph_ref=module._ref(pointer(kind="NarrativeBeatGraph")), candidates=(chosen,)
    ).model_dump(mode="json")
    selection_payload = ClipSelectionPlan(
        candidate_set_ref=module._ref(pointer(kind="ClipCandidateSet")),
        selections=(
            ClipSelection(
                beat_id=beat_id,
                candidate_id=chosen.candidate_id,
                selected_range=chosen.source_range,
                rationale="grounded",
            ),
        ),
    ).model_dump(mode="json")
    line = NarrationLine(
        line_id=uuid4(),
        beat_id=beat_id,
        text="他推开门",
        function="bridge",
        story_refs=chosen.story_refs,
        evidence_refs=(evidence_id,),
        target_duration={"value": 5, "rate_num": 1},
        dialogue_relationship="bridge",
    )
    line_set_payload = NarrationLineSet(
        creative_brief_ref=module._ref(pointer(kind="CreativeBrief")),
        rhythm_plan_ref=module._ref(pointer(kind="RhythmPlan")),
        lines=(line,),
        estimated_duration={"value": 5, "rate_num": 1},
    ).model_dump(mode="json")

    class FakeRepository:
        def get_version(self, _connection, reference):
            if reference.artifact_type == "ClipSelectionPlan":
                return {"payload_json": selection_payload}
            if reference.artifact_type == "ClipCandidateSet":
                return {"payload_json": candidate_set_payload}
            if reference.artifact_type == "NarrationLineSet":
                return {"payload_json": line_set_payload}
            raise AssertionError(f"unexpected artifact read: {reference.artifact_type}")

    monkeypatch.setattr(module, "ArtifactRepository", lambda: FakeRepository())
    captured = {}

    class FakeAssemblyService:
        def __init__(self, _repository: object) -> None:
            pass

        def assemble(self, connection, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                master_timeline_ref=module._ref(
                    pointer(artifact_id=str(timeline_id), kind="MasterTimeline")
                ),
                assembly_report_ref=module._ref(pointer(kind="TimelineAssemblyReport")),
                blocked=False,
                conflict_codes=(),
            )

    monkeypatch.setattr(module, "TimelineAssemblyService", FakeAssemblyService)
    request = AssemblyActivityRequest(
        run_id=str(uuid4()),
        project_id=str(uuid4()),
        trace_id="c" * 32,
        resource_profile=pointer(kind="ConfigArtifact"),
        selection_plan=selection_ref,
        candidate_sets=(pointer(kind="ClipCandidateSet"),),
        line_set=pointer(kind="NarrationLineSet"),
        subtitle_style=pointer(kind="ConfigArtifact"),
        timeline_id=str(timeline_id),
        master_timeline_id=str(uuid4()),
        report_id=str(uuid4()),
    )
    result = module._assemble_sync(request)
    assert not result.blocked and result.master_timeline is not None
    assert len(captured["audio_intents"]) == 1
    assert len(captured["subtitle_intents"]) == 1
    assert captured["subtitle_intents"][0].text == "他推开门"
    assert captured["duration"].value == 5
