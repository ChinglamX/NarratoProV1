from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import pytest

from packages.production import fake_preview
from packages.production.fake_preview import PreviewRenderError, _ass_timestamp
from tests.timeline.fixtures import item, timeline


def test_ass_timestamp_is_stable() -> None:
    assert _ass_timestamp(Fraction(125, 100)) == "0:00:01.25"


def test_renderer_fails_when_tools_are_unavailable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(fake_preview.shutil, "which", lambda _name: None)
    with pytest.raises(PreviewRenderError, match="required"):
        fake_preview.render_fake_preview(timeline(), tmp_path / "preview.mp4")


def test_renderer_compiles_safe_ffmpeg_argv_and_qc(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    commands: list[list[str]] = []

    def run(command: list[str], **_kwargs: object) -> SimpleNamespace:
        commands.append(command)
        if "-show_entries" in command:
            return SimpleNamespace(
                stdout=(
                    '{"streams":[{"codec_type":"video","codec_name":"h264",'
                    '"width":720,"height":1280},{"codec_type":"audio",'
                    '"codec_name":"aac"}],"format":{"duration":"4.0"}}'
                )
            )
        if "-version" in command:
            return SimpleNamespace(stdout="ffmpeg version 8.1.2\n")
        return SimpleNamespace(stdout="")

    monkeypatch.setattr(fake_preview.shutil, "which", lambda name: f"/safe/{name}")
    monkeypatch.setattr(fake_preview.subprocess, "run", run)
    result = fake_preview.render_fake_preview(timeline(), tmp_path / "preview.mp4")
    assert result.subtitle_path.exists()
    assert result.video_codec == "h264" and result.audio_codec == "aac"
    assert result.ffmpeg_version == "ffmpeg version 8.1.2"
    assert all(isinstance(command, list) for command in commands)


def test_renderer_rejects_non_render_ready_timeline(tmp_path: Path) -> None:
    invalid = timeline(item(start=25), item(start=0))
    with pytest.raises(PreviewRenderError, match="not render-ready"):
        fake_preview.render_fake_preview(invalid, tmp_path / "preview.mp4")
