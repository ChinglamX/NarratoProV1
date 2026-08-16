"""E10/K02 voice take selection unit tests (provider-neutral pure function)."""

from uuid import uuid4

import pytest

from packages.contracts import ArtifactRef
from packages.contracts.media_production import TakeDisposition, VoiceTake
from packages.contracts.timeline_intent import NarrationLine, NarrationLineSet
from packages.production.take_selection import SelectTakeConflict, select_best_takes

VOICE = ArtifactRef(artifact_id=uuid4(), version=1, artifact_type="ConfigArtifact")
NLS_REF = ArtifactRef(artifact_id=uuid4(), version=1, artifact_type="NarrationLineSet")


def _ref() -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type="VoiceTakeSet")


def _line(line_id, target_us: int) -> NarrationLine:
    return NarrationLine(
        line_id=line_id,
        beat_id=uuid4(),
        text=f"line {line_id}",
        function="bridge",
        story_refs=(uuid4(),),
        evidence_refs=(uuid4(),),
        target_duration={"value": target_us, "rate_num": 1_000_000},
        dialogue_relationship="bridge",
    )


def _take(
    line_id,
    duration_us: int,
    *,
    qc: tuple[str, ...] = (),
    pron: tuple[str, ...] = (),
    no_audio: bool = False,
) -> VoiceTake:
    return VoiceTake(
        take_id=uuid4(),
        narration_line_id=line_id,
        raw_response_ref=_ref(),
        audio_blob_ref=None if no_audio else f"blob:{uuid4()}",
        duration={"value": duration_us, "rate_num": 1_000_000},
        provider_id="tts",
        provider_version="v1",
        voice_id="zh-female-1",
        pronunciation_findings=pron,
        qc_findings=qc,
        disposition=TakeDisposition.CANDIDATE,
        estimated_cost_micros=100,
    )


def _narration(lines: tuple[NarrationLine, ...]) -> NarrationLineSet:
    return NarrationLineSet(
        creative_brief_ref=ArtifactRef(
            artifact_id=uuid4(), version=1, artifact_type="CreativeBrief"
        ),
        rhythm_plan_ref=ArtifactRef(artifact_id=uuid4(), version=1, artifact_type="RhythmPlan"),
        lines=lines,
        estimated_duration={"value": 1, "rate_num": 1},
    )


def test_selects_closest_duration() -> None:
    line_id = uuid4()
    narration = _narration((_line(line_id, 5_000_000),))
    takes = (
        _take(line_id, 4_000_000),
        _take(line_id, 5_200_000),
        _take(line_id, 9_000_000),
    )
    result = select_best_takes(
        narration=narration,
        narration_line_set_ref=NLS_REF,
        takes=takes,
        voice_profile_ref=VOICE,
    )
    selected = [t for t in result.takes if t.disposition is TakeDisposition.SELECTED]
    assert len(selected) == 1
    assert selected[0].duration.value == 5_200_000  # closest to 5.0s target
    rejected = [t for t in result.takes if t.disposition is TakeDisposition.REJECTED]
    assert len(rejected) == 2
    assert not result.incomplete


def test_rejects_takes_with_qc_or_pronunciation_findings() -> None:
    line_id = uuid4()
    narration = _narration((_line(line_id, 5_000_000),))
    takes = (
        _take(line_id, 5_000_000, qc=("clipped",)),
        _take(line_id, 4_800_000, pron=("mispronounced-name",)),
        _take(line_id, 5_100_000),
    )
    result = select_best_takes(
        narration=narration,
        narration_line_set_ref=NLS_REF,
        takes=takes,
        voice_profile_ref=VOICE,
    )
    selected = [t for t in result.takes if t.disposition is TakeDisposition.SELECTED]
    assert len(selected) == 1
    assert selected[0].duration.value == 5_100_000
    assert not result.incomplete


def test_unavailable_when_no_eligible_take() -> None:
    line_id = uuid4()
    narration = _narration((_line(line_id, 5_000_000),))
    takes = (_take(line_id, 5_000_000, qc=("clipped",)),)
    result = select_best_takes(
        narration=narration,
        narration_line_set_ref=NLS_REF,
        takes=takes,
        voice_profile_ref=VOICE,
    )
    assert not [t for t in result.takes if t.disposition is TakeDisposition.SELECTED]
    assert result.incomplete


def test_unavailable_when_take_has_no_audio() -> None:
    line_id = uuid4()
    narration = _narration((_line(line_id, 5_000_000),))
    takes = (_take(line_id, 5_000_000, no_audio=True),)
    result = select_best_takes(
        narration=narration,
        narration_line_set_ref=NLS_REF,
        takes=takes,
        voice_profile_ref=VOICE,
    )
    assert not [t for t in result.takes if t.disposition is TakeDisposition.SELECTED]
    assert result.incomplete


def test_ignores_non_candidate_takes() -> None:
    line_id = uuid4()
    narration = _narration((_line(line_id, 5_000_000),))
    preselected = _take(line_id, 5_000_000).model_copy(
        update={"disposition": TakeDisposition.SELECTED}
    )
    result = select_best_takes(
        narration=narration,
        narration_line_set_ref=NLS_REF,
        takes=(preselected,),
        voice_profile_ref=VOICE,
    )
    # Preselected take is kept as-is; no line left incomplete.
    kept = [t for t in result.takes if t.disposition is TakeDisposition.SELECTED]
    assert len(kept) == 1
    assert not result.incomplete


def test_rejects_empty_narration() -> None:
    with pytest.raises(SelectTakeConflict, match="empty"):
        select_best_takes(
            narration=_narration(()),
            narration_line_set_ref=NLS_REF,
            takes=(),
            voice_profile_ref=VOICE,
        )


def test_deterministic_tie_break() -> None:
    line_id = uuid4()
    narration = _narration((_line(line_id, 5_000_000),))
    takes = (
        _take(line_id, 5_000_000),
        _take(line_id, 5_000_000),
    )
    first = select_best_takes(
        narration=narration,
        narration_line_set_ref=NLS_REF,
        takes=takes,
        voice_profile_ref=VOICE,
    )
    second = select_best_takes(
        narration=narration,
        narration_line_set_ref=NLS_REF,
        takes=takes,
        voice_profile_ref=VOICE,
    )
    a = next(t for t in first.takes if t.disposition is TakeDisposition.SELECTED)
    b = next(t for t in second.takes if t.disposition is TakeDisposition.SELECTED)
    assert a.take_id == b.take_id
