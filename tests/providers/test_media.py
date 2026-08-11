from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import pytest

from packages.providers.media.ffmpeg import FFmpegMediaProvider, MediaProviderError, SourceTimeMap
from packages.providers.media.scenes import detect_scenes


def test_source_time_map_round_trip_is_exact() -> None:
    mapping = SourceTimeMap(Fraction(3, 2), Fraction(0), Fraction(1), Fraction(1, 30))
    source = Fraction(47, 10)
    assert mapping.proxy_to_source(mapping.source_to_proxy(source)) == source


def test_probe_rejects_corrupt_media(tmp_path: Path) -> None:
    broken = tmp_path / "broken.mp4"
    broken.write_bytes(b"not-media")
    with pytest.raises(MediaProviderError):
        FFmpegMediaProvider().probe(broken)


def test_scene_boundaries_use_rational_framerate(monkeypatch: pytest.MonkeyPatch) -> None:
    point = lambda frame: SimpleNamespace(frame_num=frame, framerate=29.97)  # noqa: E731
    monkeypatch.setattr(
        "packages.providers.media.scenes.detect", lambda *_a, **_k: [(point(3), point(6))]
    )
    result = detect_scenes(Path("fixture.mp4"))
    assert result[0].start_seconds == Fraction(100, 999)


def test_ffmpeg_provider_normalizes_probe_and_builds_derivatives(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    raw = {
        "format": {"duration": "2.5", "start_time": "0.5", "format_name": "mov,mp4"},
        "streams": [
            {
                "index": 0,
                "codec_type": "video",
                "codec_name": "h264",
                "width": 640,
                "height": 360,
                "pix_fmt": "yuv420p",
                "avg_frame_rate": "30000/1001",
                "r_frame_rate": "30/1",
                "time_base": "1/90000",
                "tags": {"rotate": "90"},
            },
            {
                "index": 1,
                "codec_type": "audio",
                "codec_name": "aac",
                "sample_rate": "48000",
                "channels": 2,
                "channel_layout": "stereo",
            },
        ],
    }

    def fake_run(command: list[str], **_kwargs: object) -> SimpleNamespace:
        if "-show_format" in command:
            import json

            return SimpleNamespace(stdout=json.dumps(raw))
        if command[-1].endswith(".part"):
            Path(command[-1]).write_bytes(b"derived")
        if "frame_%05d.jpg" in command[-1]:
            Path(command[-1].replace("%05d", "00001")).write_bytes(b"frame")
        return SimpleNamespace(stdout="ffmpeg version test")

    monkeypatch.setattr("packages.providers.media.ffmpeg.subprocess.run", fake_run)
    provider = FFmpegMediaProvider(ffprobe="ffprobe", ffmpeg="ffmpeg")
    probe = provider.probe(source)
    assert probe.technical.video_streams[0].variable_frame_rate
    assert probe.technical.video_streams[0].rotation_degrees == 90
    derived = provider.derive(source, tmp_path / "out", probe)
    assert derived.proxy_path.is_file() and derived.audio_path is not None
    assert len(derived.frame_paths) == 1


def test_probe_accepts_audio_only_and_rejects_empty_streams(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    source = tmp_path / "audio.wav"
    source.write_bytes(b"audio")
    responses = iter(
        [
            {
                "format": {"duration": "1"},
                "streams": [
                    {
                        "index": 0,
                        "codec_type": "audio",
                        "codec_name": "pcm_s16le",
                        "sample_rate": "16000",
                        "channels": 1,
                    }
                ],
            },
            {"format": {"duration": "1"}, "streams": []},
        ]
    )

    def fake_run(command: list[str], **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            stdout=json.dumps(next(responses)) if "-show_format" in command else "version"
        )

    monkeypatch.setattr("packages.providers.media.ffmpeg.subprocess.run", fake_run)
    provider = FFmpegMediaProvider(ffprobe="ffprobe", ffmpeg="ffmpeg")
    assert provider.probe(source).technical.audio_streams
    with pytest.raises(MediaProviderError):
        provider.probe(source)
