"""TimelineAssemblyService tests: multi-track assembly and fail-closed conflicts."""

from types import SimpleNamespace
from uuid import uuid4

from apps.services.timeline_assembly import AssemblyArtifactIds, TimelineAssemblyService
from packages.contracts import ActorRef, ArtifactEnvelope, ArtifactRef, RationalTime
from packages.contracts.timeline_intent import (
    AudioIntent,
    ClipCandidate,
    ClipSelection,
    ClipSelectionPlan,
    NarrationLine,
    NarrationLineSet,
    SubtitleIntent,
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


def candidate(beat_id, *, duration: int = 5) -> ClipCandidate:
    return ClipCandidate(
        candidate_id=uuid4(),
        beat_id=beat_id,
        source_ref=ref("SourceMedia"),
        source_range={
            "start": {"value": 0, "rate_num": 1},
            "duration": {"value": duration, "rate_num": 1},
        },
        story_refs=(uuid4(),),
        evidence_refs=(uuid4(),),
        quality={},
        continuity_features={},
        reframe_feasible=True,
        rights_allowed=True,
        score_components={"evidence": 0.9},
    )


def selections(chosen: ClipCandidate) -> ClipSelectionPlan:
    return ClipSelectionPlan(
        candidate_set_ref=ref("ClipCandidateSet"),
        selections=(
            ClipSelection(
                beat_id=chosen.beat_id,
                candidate_id=chosen.candidate_id,
                selected_range=chosen.source_range,
                rationale="grounded",
            ),
        ),
    )


def narration(chosen: ClipCandidate) -> NarrationLineSet:
    line = NarrationLine(
        line_id=uuid4(),
        beat_id=chosen.beat_id,
        text="他推开门",
        function="bridge",
        story_refs=chosen.story_refs,
        evidence_refs=chosen.evidence_refs,
        target_duration={"value": 5, "rate_num": 1},
        dialogue_relationship="bridge",
    )
    return NarrationLineSet(
        creative_brief_ref=ref("CreativeBrief"),
        rhythm_plan_ref=ref("RhythmPlan"),
        lines=(line,),
        estimated_duration={"value": 5, "rate_num": 1},
    )


def audio(chosen: ClipCandidate) -> tuple[AudioIntent, ...]:
    return (
        AudioIntent(
            intent_id=uuid4(),
            role="original",
            timeline_range={
                "start": {"value": 0, "rate_num": 1},
                "duration": {"value": 5, "rate_num": 1},
            },
            source_ref=chosen.source_ref,
            source_range=chosen.source_range,
        ),
    )


def subtitles(narration_lines: NarrationLineSet) -> tuple[SubtitleIntent, ...]:
    line = narration_lines.lines[0]
    return (
        SubtitleIntent(
            intent_id=uuid4(),
            line_id=line.line_id,
            timeline_range={
                "start": {"value": 0, "rate_num": 1},
                "duration": {"value": 5, "rate_num": 1},
            },
            text=line.text,
            style_ref=ref("ConfigArtifact"),
            safe_area={"x": 0.1, "y": 0.72, "width": 0.8, "height": 0.18},
            evidence_refs=line.evidence_refs,
        ),
    )


def service(repository: FakeArtifactRepository) -> TimelineAssemblyService:
    return TimelineAssemblyService(repository)


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


def test_assembly_commits_master_timeline_and_report() -> None:
    chosen = candidate(uuid4())
    lines = narration(chosen)
    repository = FakeArtifactRepository()
    outcome = service(repository).assemble(
        **common(),
        timeline_id=uuid4(),
        selections=selections(chosen),
        candidates=(chosen,),
        narration=lines,
        audio_intents=audio(chosen),
        subtitle_intents=subtitles(lines),
        overlay_intents=(),
        dependencies=(ref("CreativeBrief"),),
        duration=RationalTime(value=5, rate_num=1),
        ids=AssemblyArtifactIds(),
    )
    assert not outcome.blocked and outcome.master_timeline_ref is not None
    types = {envelope.artifact_type for envelope in repository.committed}
    assert {"MasterTimeline", "TimelineAssemblyReport"} <= types


def test_duration_mismatch_fails_closed_with_report_only() -> None:
    chosen = candidate(uuid4(), duration=3)
    lines = narration(chosen)
    repository = FakeArtifactRepository()
    outcome = service(repository).assemble(
        **common(),
        timeline_id=uuid4(),
        selections=selections(chosen),
        candidates=(chosen,),
        narration=lines,
        audio_intents=(),
        subtitle_intents=(),
        overlay_intents=(),
        dependencies=(),
        duration=RationalTime(value=5, rate_num=1),
        ids=AssemblyArtifactIds(),
    )
    assert outcome.blocked and outcome.master_timeline_ref is None
    assert outcome.conflict_codes == ("video-duration-mismatch",)
    types = {envelope.artifact_type for envelope in repository.committed}
    assert types == {"TimelineAssemblyReport"}
