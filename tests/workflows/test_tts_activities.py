"""E10/K01 voice synthesis: pure _synthesize_takes tests (no DB)."""

from __future__ import annotations

import wave
from io import BytesIO
from uuid import uuid4

import pytest

from packages.contracts import ArtifactRef
from packages.contracts.media_production import TakeDisposition
from packages.contracts.timeline_intent import NarrationLine, NarrationLineSet
from workflows.production.tts_activities import (
    _concatenate_wavs,
    _synthesize_one,
    _synthesize_takes,
    _wav_duration,
)


def _ref(kind: str = "ConfigArtifact") -> ArtifactRef:
    return ArtifactRef.model_validate(
        {"artifact_id": str(uuid4()), "version": 1, "artifact_type": kind}
    )


def _narration(n_lines: int = 2) -> NarrationLineSet:
    lines = tuple(
        NarrationLine(
            line_id=uuid4(),
            beat_id=uuid4(),
            text=f"解说第{index}句",
            function="bridge",
            story_refs=(uuid4(),),
            evidence_refs=(uuid4(),),
            target_duration={"value": 3_000_000, "rate_num": 1_000_000},
            dialogue_relationship="bridge",
        )
        for index in range(n_lines)
    )
    return NarrationLineSet(
        creative_brief_ref=_ref("CreativeBrief"),
        rhythm_plan_ref=_ref("RhythmPlan"),
        lines=lines,
        estimated_duration={"value": 6_000_000, "rate_num": 1_000_000},
    )


def _wav_payload(*, frames: int = 24_000, rate: int = 24_000) -> bytes:
    output = BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(rate)
        target.writeframes(b"\x00\x00" * frames)
    return output.getvalue()


class _Raw:
    payload = _wav_payload()


class _OkProvider:
    def infer(self, request: object) -> _Raw:
        return _Raw()


class _FailingProvider:
    def infer(self, request: object) -> _Raw:
        raise RuntimeError("synthesis failed")


def test_synthesize_one_returns_wav_and_checksum() -> None:
    wav, digest = _synthesize_one("你好", _OkProvider(), _ref())
    assert wav == _Raw.payload
    assert digest.startswith("sha256:")


def test_wav_measurement_and_concatenation_use_real_frames() -> None:
    combined = _concatenate_wavs([_wav_payload(frames=12_000), _wav_payload(frames=24_000)])
    assert _wav_duration(combined).seconds == 1.5


def test_concatenation_rejects_empty_or_mismatched_wavs() -> None:
    with pytest.raises(ValueError, match="at least one"):
        _concatenate_wavs([])
    with pytest.raises(ValueError, match="formats do not match"):
        _concatenate_wavs([_wav_payload(rate=24_000), _wav_payload(rate=16_000)])


def test_synthesize_takes_all_selected_on_success() -> None:
    narration = _narration(2)
    takes, selected, failed, wavs = _synthesize_takes(narration, _OkProvider(), _ref(), uuid4())
    assert len(takes) == 2
    assert all(t.disposition is TakeDisposition.SELECTED for t in takes)
    assert len(selected) == 2
    assert selected == [take.take_id for take in takes]
    assert all(take.duration is not None and take.duration.seconds == 1 for take in takes)
    assert failed == 0
    assert len(wavs) == 2


def test_synthesize_takes_marks_unavailable_on_failure() -> None:
    narration = _narration(2)
    takes, selected, failed, wavs = _synthesize_takes(
        narration, _FailingProvider(), _ref(), uuid4()
    )
    assert len(takes) == 2
    assert all(t.disposition is TakeDisposition.UNAVAILABLE for t in takes)
    assert selected == []
    assert failed == 2
    assert wavs == {}


def test_synthesize_takes_empty_narration() -> None:
    takes, selected, failed, _wavs = _synthesize_takes(
        _narration(0), _OkProvider(), _ref(), uuid4()
    )
    assert takes == []
    assert selected == []
    assert failed == 0
