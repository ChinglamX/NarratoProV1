"""E10/K01 voice synthesis: pure _synthesize_takes tests (no DB)."""

from __future__ import annotations

from uuid import uuid4

from packages.contracts import ArtifactRef
from packages.contracts.media_production import TakeDisposition
from packages.contracts.timeline_intent import NarrationLine, NarrationLineSet
from workflows.production.tts_activities import _synthesize_one, _synthesize_takes


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


class _Raw:
    payload = b"RIFF\x00\x00WAVEfmt"


class _OkProvider:
    def infer(self, request: object) -> _Raw:
        return _Raw()


class _FailingProvider:
    def infer(self, request: object) -> _Raw:
        raise RuntimeError("synthesis failed")


def test_synthesize_one_returns_wav_and_checksum() -> None:
    wav, digest = _synthesize_one("你好", _OkProvider(), _ref())
    assert wav == b"RIFF\x00\x00WAVEfmt"
    assert digest.startswith("sha256:")


def test_synthesize_takes_all_selected_on_success() -> None:
    narration = _narration(2)
    takes, selected, failed, wavs = _synthesize_takes(narration, _OkProvider(), _ref(), uuid4())
    assert len(takes) == 2
    assert all(t.disposition is TakeDisposition.SELECTED for t in takes)
    assert len(selected) == 2
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
