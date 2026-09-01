import importlib.util
import json
import wave
from pathlib import Path
from typing import Any


def _load_builder() -> Any:
    path = Path("scripts/build_m5_second_cut.py").resolve()
    spec = importlib.util.spec_from_file_location("series_candidate_builder", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _wav(path: Path, frames: int = 8000) -> None:
    with wave.open(str(path), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(8000)
        target.writeframes(b"\0\0" * frames)


def test_tts_cache_key_is_content_addressed(tmp_path: Path) -> None:
    builder = _load_builder()
    reference = tmp_path / "reference.wav"
    _wav(reference)
    builder.REFERENCE_AUDIO = reference
    first = builder._tts_cache_key("第一句")
    assert first == builder._tts_cache_key("第一句")
    assert first != builder._tts_cache_key("第二句")
    _wav(reference, frames=9000)
    assert first != builder._tts_cache_key("第一句")


def test_legacy_cache_requires_matching_manifest_text_and_checksum(tmp_path: Path) -> None:
    builder = _load_builder()
    builder.OUTPUT_DIR = tmp_path
    output = tmp_path / "narration_01.wav"
    _wav(output)
    checksum = builder._sha256(output)
    (tmp_path / "manifest.json").write_text(
        json.dumps({"narration_lines": [{"index": 1, "text": "原句", "checksum": checksum}]}),
        encoding="utf-8",
    )
    assert builder._legacy_cache_matches(index=1, text="原句", output=output)
    assert not builder._legacy_cache_matches(index=1, text="改句", output=output)


def test_anchor_mode_schedules_from_events_after_measured_tts() -> None:
    builder = _load_builder()
    builder.SEGMENTS = ((0.0, 10.0),)
    builder.ANCHOR_CONFIG = {
        "visual_events": [
            {
                "event_id": "cash-visible",
                "timeline_start_seconds": 4.0,
                "duration_seconds": 3.0,
            }
        ],
        "narration_anchors": [
            {
                "narration": "五十万现金出现",
                "required_event_ids": ["cash-visible"],
                "preferred_delay_seconds": 0.2,
                "post_roll_seconds": 2.0,
            }
        ],
    }
    scheduled = builder._apply_anchor_plan(
        [
            {
                "text": "五十万现金出现",
                "duration_seconds": 2.0,
                "timeline_start_seconds": 0.0,
                "slot_duration_seconds": 10.0,
            }
        ]
    )
    assert scheduled[0]["timeline_start_seconds"] == 4.2
    assert scheduled[0]["anchor_source"] == "tool"
    assert builder.ANCHOR_PLAN_MANIFEST["findings"] == []


def test_manifest_provenance_rejects_role_mismatch(tmp_path: Path) -> None:
    builder = _load_builder()
    builder.OUTPUT_DIR = tmp_path
    builder.PROVENANCE_CONFIG = {
        "task_type": "TYPE_B",
        "active_role": "AI System Engineer",
        "auxiliary_roles": [],
    }
    output = tmp_path / "candidate.mp4"
    output.write_bytes(b"video")
    try:
        builder._provenance_manifest(output)
    except ValueError as exc:
        assert "match the task type" in str(exc)
    else:
        raise AssertionError("role mismatch must fail closed")


def test_anchor_config_cannot_mix_absolute_cues(tmp_path: Path) -> None:
    builder = _load_builder()
    source = tmp_path / "source.mp4"
    reference = tmp_path / "reference.wav"
    source.write_bytes(b"media")
    _wav(reference)
    config = {
        "source_path": str(source),
        "reference_audio": str(reference),
        "candidate_manifest": str(tmp_path / "out" / "manifest.json"),
        "segments": [{"source_start_seconds": 0, "duration_seconds": 3, "narration": "x"}],
        "narration_cues": [
            {
                "timeline_start_seconds": 0,
                "slot_duration_seconds": 3,
                "narration": "x",
            }
        ],
        "visual_events": [{"event_id": "x", "timeline_start_seconds": 0, "duration_seconds": 1}],
        "narration_anchors": [{"narration": "x", "required_event_ids": ["x"]}],
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    try:
        builder._configure_from_personal_config(path)
    except ValueError as exc:
        assert "not both" in str(exc)
    else:
        raise AssertionError("mixed timing modes must fail closed")
