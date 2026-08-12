"""Media-grounded preview tests: real source files, trim/scale/concat pipeline."""

import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

import pytest

from packages.contracts import ArtifactRef, MasterTimeline, TimelineItem
from packages.contracts.timeline import TimelineTrackKind
from packages.production.real_preview import PreviewRenderError, render_media_preview
from tests.timeline.fixtures import rational


def _make_source(path: Path, color: str, seconds: float = 2.0) -> Path:
    subprocess.run(  # nosec B603
        [
            shutil.which("ffmpeg") or "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s=320x180:r=20:d={seconds}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:sample_rate=44100:duration={seconds}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return path


def _clip_item(
    source_ref: ArtifactRef,
    *,
    source_start: int,
    source_duration: int,
    timeline_start: int,
    timeline_duration: int,
    kind: TimelineTrackKind,
) -> TimelineItem:
    item_type = "clip"
    payload: dict[str, object] = {
        "item_id": uuid4(),
        "item_version": 1,
        "item_type": item_type,
        "timeline_range": {
            "start": rational(timeline_start),
            "duration": rational(timeline_duration),
        },
        "source_ref": source_ref.model_dump(mode="json"),
        "source_range": {
            "start": rational(source_start),
            "duration": rational(source_duration),
        },
    }
    if kind == TimelineTrackKind.SUBTITLE:
        payload = {
            "item_id": uuid4(),
            "item_version": 1,
            "item_type": "text",
            "timeline_range": {
                "start": rational(timeline_start),
                "duration": rational(timeline_duration),
            },
            "parameters": {
                "text": "他推开门",
                "safe_area": {"x": 0.1, "y": 0.72, "width": 0.8, "height": 0.18},
            },
        }
    return TimelineItem.model_validate(payload)


def _timeline(source_a: ArtifactRef, source_b: ArtifactRef) -> MasterTimeline:
    return MasterTimeline.model_validate(
        {
            "timeline_id": uuid4(),
            "lifecycle": "draft",
            "rate_num": 20,
            "global_start": rational(0, 20),
            "duration": rational(20, 20),
            "tracks": [
                {
                    "track_id": uuid4(),
                    "kind": TimelineTrackKind.VIDEO.value,
                    "order": 0,
                    "items": [
                        _clip_item(
                            source_a,
                            source_start=0,
                            source_duration=10,
                            timeline_start=0,
                            timeline_duration=10,
                            kind=TimelineTrackKind.VIDEO,
                        ).model_dump(mode="json"),
                        _clip_item(
                            source_b,
                            source_start=10,
                            source_duration=10,
                            timeline_start=10,
                            timeline_duration=10,
                            kind=TimelineTrackKind.VIDEO,
                        ).model_dump(mode="json"),
                    ],
                },
                {
                    "track_id": uuid4(),
                    "kind": TimelineTrackKind.ORIGINAL_AUDIO.value,
                    "order": 1,
                    "items": [
                        _clip_item(
                            source_a,
                            source_start=0,
                            source_duration=10,
                            timeline_start=0,
                            timeline_duration=10,
                            kind=TimelineTrackKind.ORIGINAL_AUDIO,
                        ).model_dump(mode="json"),
                    ],
                },
                {
                    "track_id": uuid4(),
                    "kind": TimelineTrackKind.SUBTITLE.value,
                    "order": 5,
                    "items": [
                        _clip_item(
                            source_a,
                            source_start=0,
                            source_duration=10,
                            timeline_start=0,
                            timeline_duration=10,
                            kind=TimelineTrackKind.SUBTITLE,
                        ).model_dump(mode="json"),
                    ],
                },
            ],
            "metadata_namespace_version": "e09-j04-v1",
        }
    )


@pytest.fixture
def sources(tmp_path: Path) -> dict[str, object]:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg/ffprobe are required for the media-grounded preview test")
    first = ArtifactRef(artifact_id=uuid4(), version=1, artifact_type="SourceMedia")
    second = ArtifactRef(artifact_id=uuid4(), version=1, artifact_type="SourceMedia")
    path_a = _make_source(tmp_path / "a.mp4", "red")
    path_b = _make_source(tmp_path / "b.mp4", "blue")
    return {
        "first": first,
        "second": second,
        "path_a": path_a,
        "path_b": path_b,
    }


def test_media_preview_compiles_real_sources_with_subtitles(
    sources: dict[str, object], tmp_path: Path
) -> None:
    first = sources["first"]
    second = sources["second"]
    output = tmp_path / "preview" / "preview.mp4"
    result = render_media_preview(
        _timeline(first, second),  # type: ignore[arg-type]
        {first.artifact_id: sources["path_a"], second.artifact_id: sources["path_b"]},  # type: ignore[dict-item]
        output,
    )
    assert result.output_path.is_file()
    assert result.width == 720 and result.height == 1280
    assert result.video_codec == "h264" and result.audio_codec == "aac"
    assert float(result.duration_seconds) == pytest.approx(1.0, abs=0.2)
    subtitle_text = result.subtitle_path.read_text(encoding="utf-8")
    assert "他推开门" in subtitle_text
    assert "Dialogue: 0,0:00:00.00,0:00:00.40" in subtitle_text


def test_media_preview_fails_closed_when_source_missing(
    sources: dict[str, object], tmp_path: Path
) -> None:
    first = sources["first"]
    second = sources["second"]
    with pytest.raises(PreviewRenderError, match="unavailable"):
        render_media_preview(
            _timeline(first, second),  # type: ignore[arg-type]
            {first.artifact_id: sources["path_a"]},  # type: ignore[dict-item]
            tmp_path / "preview.mp4",
        )
