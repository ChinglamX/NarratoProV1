from uuid import uuid4

from packages.contracts import ArtifactRef, RationalTime
from packages.contracts.timeline import TimelineTrackKind
from packages.contracts.timeline_intent import (
    AudioIntent,
    ClipCandidate,
    ClipSelection,
    ClipSelectionPlan,
    NarrationLine,
    NarrationLineSet,
    OverlayIntent,
    SubtitleIntent,
)
from packages.timeline.multitrack import assemble_multitrack_timeline


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=kind)


def t(value: int) -> dict[str, int]:
    return {"value": value, "rate_num": 1}


def test_all_creative_intents_share_one_master_timeline() -> None:
    beat_id, line_id, evidence_id = uuid4(), uuid4(), uuid4()
    source = ref("SourceMedia")
    candidate = ClipCandidate(
        candidate_id=uuid4(),
        beat_id=beat_id,
        source_ref=source,
        source_range={"start": t(10), "duration": t(5)},
        story_refs=(uuid4(),),
        evidence_refs=(evidence_id,),
        quality={},
        continuity_features={},
        reframe_feasible=True,
        rights_allowed=True,
        score_components={"relevance": 1.0},
    )
    selections = ClipSelectionPlan(
        candidate_set_ref=ref("ClipCandidateSet"),
        selections=(
            ClipSelection(
                beat_id=beat_id,
                candidate_id=candidate.candidate_id,
                selected_range=candidate.source_range,
                rationale="grounded",
            ),
        ),
    )
    line = NarrationLine(
        line_id=line_id,
        beat_id=beat_id,
        text="他赶在风雨前回了家",
        function="bridge",
        story_refs=candidate.story_refs,
        evidence_refs=(evidence_id,),
        target_duration=t(5),
        dialogue_relationship="bridge",
    )
    narration = NarrationLineSet(
        creative_brief_ref=ref("CreativeBrief"),
        rhythm_plan_ref=ref("PatchProposal"),
        lines=(line,),
        estimated_duration=t(5),
    )
    audio = (
        AudioIntent(
            intent_id=uuid4(),
            role="original",
            timeline_range={"start": t(0), "duration": t(5)},
            source_ref=source,
        ),
        AudioIntent(
            intent_id=uuid4(),
            role="bgm",
            timeline_range={"start": t(0), "duration": t(5)},
            content_ref="bgm-rural-tension",
            rights_ref=ref("RightsManifest"),
            duck_under_narration=True,
            gain_db=-12,
        ),
    )
    subtitle = SubtitleIntent(
        intent_id=uuid4(),
        line_id=line_id,
        timeline_range={"start": t(0), "duration": t(5)},
        text=line.text,
        style_ref=ref("ConfigArtifact"),
        safe_area={"x": 0.1, "y": 0.72, "width": 0.8, "height": 0.18},
        evidence_refs=(evidence_id,),
    )
    overlay = OverlayIntent(
        intent_id=uuid4(),
        timeline_range={"start": t(0), "duration": t(2)},
        overlay_type="character-card",
        content_ref="protagonist",
        style_ref=ref("ConfigArtifact"),
        safe_area={"x": 0.05, "y": 0.1, "width": 0.4, "height": 0.2},
    )
    kinds = (
        TimelineTrackKind.VIDEO,
        TimelineTrackKind.ORIGINAL_AUDIO,
        TimelineTrackKind.NARRATION,
        TimelineTrackKind.BGM,
        TimelineTrackKind.SUBTITLE,
        TimelineTrackKind.OVERLAY,
    )
    timeline, report = assemble_multitrack_timeline(
        timeline_id=uuid4(),
        selections=selections,
        candidates=(candidate,),
        narration=narration,
        audio_intents=audio,
        subtitle_intents=(subtitle,),
        overlay_intents=(overlay,),
        dependencies=(ref("CreativeBrief"),),
        track_ids={kind: uuid4() for kind in kinds},
        item_ids=tuple(uuid4() for _ in range(6)),
        duration=RationalTime(value=5, rate_num=1),
    )
    assert timeline is not None and not report.conflicts
    assert {track.kind for track in timeline.tracks} == set(kinds)
    narration_item = next(
        track for track in timeline.tracks if track.kind == TimelineTrackKind.NARRATION
    ).items[0]
    assert narration_item.parameters["intent_state"] == "placeholder"
    assert "RenderPlan" in report.invalidated_artifact_types


def test_duration_mismatch_is_blocking_not_silently_reflowed() -> None:
    beat_id = uuid4()
    candidate = ClipCandidate(
        candidate_id=uuid4(),
        beat_id=beat_id,
        source_ref=ref("SourceMedia"),
        source_range={"start": t(0), "duration": t(3)},
        story_refs=(uuid4(),),
        evidence_refs=(uuid4(),),
        quality={},
        continuity_features={},
        reframe_feasible=True,
        rights_allowed=True,
        score_components={"relevance": 1.0},
    )
    selections = ClipSelectionPlan(
        candidate_set_ref=ref("ClipCandidateSet"),
        selections=(
            ClipSelection(
                beat_id=beat_id,
                candidate_id=candidate.candidate_id,
                selected_range=candidate.source_range,
                rationale="grounded",
            ),
        ),
    )
    narration = NarrationLineSet(
        creative_brief_ref=ref("CreativeBrief"),
        rhythm_plan_ref=ref("PatchProposal"),
        lines=(),
        estimated_duration=t(0),
    )
    timeline, report = assemble_multitrack_timeline(
        timeline_id=uuid4(),
        selections=selections,
        candidates=(candidate,),
        narration=narration,
        audio_intents=(),
        subtitle_intents=(),
        overlay_intents=(),
        dependencies=(),
        track_ids={TimelineTrackKind.VIDEO: uuid4()},
        item_ids=(uuid4(),),
        duration=RationalTime(value=5, rate_num=1),
    )
    assert timeline is None and report.conflicts[0].code == "video-duration-mismatch"
