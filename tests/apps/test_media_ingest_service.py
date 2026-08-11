from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path
from types import MethodType
from uuid import uuid4

import pytest

from apps.services.media_ingest import MediaIngestService
from packages.contracts import ArtifactRef, MediaTechnicalMetadata, RightsMetadata
from packages.providers.media.ffmpeg import DerivativeOutputs, ProbeResult, SourceTimeMap
from packages.providers.media.scenes import SceneBoundary


def _technical(*, audio: bool = True) -> MediaTechnicalMetadata:
    return MediaTechnicalMetadata.model_validate(
        {
            "duration": {"value": 2_000_000, "rate_num": 1_000_000},
            "start_time": {"value": 0, "rate_num": 1_000_000},
            "format_name": "mp4",
            "mime_type": "video/mp4",
            "byte_size": 10,
            "video_streams": [
                {
                    "stream_index": 0,
                    "codec": "h264",
                    "width": 640,
                    "height": 360,
                    "pixel_format": "yuv420p",
                    "time_base_num": 1,
                    "time_base_den": 30,
                    "frame_rate_num": 30,
                    "frame_rate_den": 1,
                }
            ],
            "audio_streams": (
                [{"stream_index": 1, "codec": "aac", "sample_rate": 48000, "channels": 2}]
                if audio
                else []
            ),
        }
    )


class FakeProvider:
    def probe(self, _path: Path) -> ProbeResult:
        return ProbeResult(_technical(), {"format": {"duration": "2"}}, "ffprobe test")

    def derive(self, _source: Path, output: Path, _probe: ProbeResult) -> DerivativeOutputs:
        proxy, audio = output / "proxy.mp4", output / "audio.wav"
        frames = output / "frames"
        frames.mkdir()
        frame = frames / "frame_00001.jpg"
        for path in (proxy, audio, frame):
            path.write_bytes(b"derived")
        return DerivativeOutputs(
            proxy,
            audio,
            frames,
            (frame,),
            SourceTimeMap(Fraction(0), Fraction(0), Fraction(1), Fraction(1, 30)),
            "ffmpeg test",
        )


def test_media_ingest_orchestrates_contracts_and_reuses_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    service = MediaIngestService(engine=object(), object_store=object(), provider=FakeProvider())  # type: ignore[arg-type]
    identities: dict[str, object] = {}

    def identity(_self: object, **values: object) -> tuple[object, bool]:
        role = str(values["role"])
        reused = role in identities
        identities.setdefault(role, uuid4())
        return identities[role], reused

    def store(_self: object, _path: Path, **_values: object) -> tuple[str, str, object]:
        return "object://test", "sha256:" + "a" * 64, uuid4()

    def commit(_self: object, **values: object) -> tuple[ArtifactRef, bool]:
        return (
            ArtifactRef.model_validate(
                {
                    "artifact_id": values["artifact_id"],
                    "version": 1,
                    "artifact_type": values["artifact_type"],
                    "checksum": values["checksum"],
                }
            ),
            False,
        )

    service._identity = MethodType(identity, service)  # type: ignore[method-assign]
    service._store_file = MethodType(store, service)  # type: ignore[method-assign]
    service._commit_payload = MethodType(commit, service)  # type: ignore[method-assign]
    monkeypatch.setattr(
        "apps.services.media_ingest.detect_scenes",
        lambda _path: (SceneBoundary(Fraction(0), Fraction(2), 0, 60),),
    )
    profile = ArtifactRef.model_validate(
        {"artifact_id": uuid4(), "version": 1, "artifact_type": "ConfigArtifact"}
    )
    result = service.ingest(
        project_id=uuid4(),
        run_id=uuid4(),
        source_path=source,
        rights=RightsMetadata(status="unknown", source="test", checked_at=datetime.now(UTC)),
        profile_ref=profile,
        profile_version="test-v1",
        trace_id="a" * 32,
    )
    assert result.audio is not None and result.derivative_count == 5
    assert result.scene_shot_catalog.artifact_type == "SceneShotCatalog"


def test_media_ingest_rejects_missing_source(tmp_path: Path) -> None:
    service = MediaIngestService(engine=object(), object_store=object(), provider=FakeProvider())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="regular file"):
        service.ingest(
            project_id=uuid4(),
            run_id=uuid4(),
            source_path=tmp_path / "missing.mp4",
            rights=RightsMetadata(status="unknown", checked_at=datetime.now(UTC)),
            profile_ref=ArtifactRef.model_validate(
                {"artifact_id": uuid4(), "version": 1, "artifact_type": "ConfigArtifact"}
            ),
            profile_version="test-v1",
            trace_id="a" * 32,
        )
