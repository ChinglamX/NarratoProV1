"""Partial preview tests: changed-range computation and real media rendering."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from packages.contracts import MasterTimeline
from packages.production.real_preview import (
    compute_changed_ranges,
    render_partial_preview,
)
from packages.timeline import apply_patch
from tests.timeline.fixtures import item, patch, timeline

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe required for media tests",
)


def _patched(before: MasterTimeline, payload: dict[str, object]) -> MasterTimeline:
    target = before.tracks[0].items[0]
    p = patch(target, "set_parameter", payload)
    return apply_patch(before, p)


def _patched_all(before: MasterTimeline, payload: dict[str, object]) -> MasterTimeline:
    """Apply the same parameter change to every item in the video track."""
    result = before
    for target in result.tracks[0].items:
        p = patch(target, "set_parameter", payload)
        result = apply_patch(result, p)
    return result


class TestComputeChangedRanges:
    def test_returns_range_of_modified_item(self) -> None:
        before = timeline(item(start=0, duration=25), item(start=25, duration=25))
        after = _patched(before, {"key": "crop", "value": "center"})
        ranges = compute_changed_ranges(before, after)
        assert ranges == ((0.0, 1.0),)

    def test_merges_close_ranges(self) -> None:
        # Two modified items 0-1s and 1.5-2.5s: gap 0.5s <= merge_gap 1.0
        before = timeline(item(start=0, duration=25), item(start=38, duration=25))
        after = _patched_all(before, {"key": "crop", "value": "center"})
        ranges = compute_changed_ranges(before, after)
        assert len(ranges) == 1
        assert ranges[0][0] == 0.0

    def test_keeps_distant_ranges_separate(self) -> None:
        # Items 0-1s and 3-4s: gap 2s > merge_gap 1.0
        before = timeline(item(start=0, duration=25), item(start=75, duration=25))
        after = _patched_all(before, {"key": "crop", "value": "center"})
        ranges = compute_changed_ranges(before, after)
        assert len(ranges) == 2

    def test_identical_timelines_have_no_ranges(self) -> None:
        before = timeline(item(start=0, duration=25))
        assert compute_changed_ranges(before, before) == ()


class TestRenderPartialPreview:
    def test_renders_overlapping_segment(self, tmp_path: Path) -> None:
        source = tmp_path / "source.mp4"
        subprocess.run(  # nosec B603
            [
                shutil.which("ffmpeg") or "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=red:s=320x180:r=20:d=2",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(source),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        tl = timeline(item(start=0, duration=25), item(start=25, duration=25))
        source_ref = tl.tracks[0].items[0].source_ref
        assert source_ref is not None
        output = tmp_path / "partial.mp4"
        result = render_partial_preview(
            tl,
            {source_ref.artifact_id: source},
            output,
            time_range=(0.0, 0.5),
        )
        assert output.is_file()
        assert result.duration_seconds == 0.5
        assert result.clip_count == 1
        assert result.subtitle_path.is_file()

    def test_rejects_range_without_video_items(self, tmp_path: Path) -> None:
        from packages.production.real_preview import PreviewRenderError

        tl = timeline(item(start=0, duration=25))
        source_ref = tl.tracks[0].items[0].source_ref
        assert source_ref is not None
        with pytest.raises(PreviewRenderError, match="no video items overlap"):
            render_partial_preview(
                tl,
                {source_ref.artifact_id: tmp_path / "missing.mp4"},
                tmp_path / "out.mp4",
                time_range=(10.0, 11.0),
            )
