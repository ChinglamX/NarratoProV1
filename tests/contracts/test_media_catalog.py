from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.contracts import (
    EpisodeCatalog,
    FrameSamplePlan,
    MediaAsset,
    MediaTechnicalMetadata,
    SceneShotCatalog,
)


def ref(kind: str) -> dict[str, object]:
    return {"artifact_id": uuid4(), "version": 1, "artifact_type": kind}


def time(value: int) -> dict[str, int]:
    return {"value": value, "rate_num": 25, "rate_den": 1}


def technical(**overrides: object) -> MediaTechnicalMetadata:
    values: dict[str, object] = {
        "duration": time(250),
        "start_time": time(0),
        "format_name": "mov-mp4",
        "mime_type": "video/mp4",
        "byte_size": 1000,
        "video_streams": [
            {
                "stream_index": 0,
                "codec": "h264",
                "width": 1920,
                "height": 1080,
                "pixel_format": "yuv420p",
                "time_base_num": 1,
                "time_base_den": 25,
                "frame_rate_num": 25,
                "frame_rate_den": 1,
            }
        ],
    }
    values.update(overrides)
    return MediaTechnicalMetadata.model_validate(values)


def shadow_confidence() -> dict[str, object]:
    return {
        "score": 0.8,
        "status": "shadow",
        "method": "scene-score",
        "applicable_scope": "scene:v1",
        "risk_class": "low",
    }


def test_media_asset_source_and_derived_lineage() -> None:
    source = MediaAsset.model_validate(
        {
            "asset_id": uuid4(),
            "role": "source",
            "uri": "object://source/video.mp4",
            "checksum": "sha256:" + "a" * 64,
            "technical": technical(),
            "rights": {"status": "unknown", "checked_at": datetime(2026, 8, 12, tzinfo=UTC)},
        }
    )
    assert MediaAsset.model_validate_json(source.canonical_json()) == source
    with pytest.raises(ValidationError, match="derived media requires"):
        MediaAsset.model_validate({**source.model_dump(), "asset_id": uuid4(), "role": "proxy"})


def test_media_technical_metadata_rejects_partial_rate_and_duplicate_streams() -> None:
    with pytest.raises(ValidationError, match="appear together"):
        technical(
            video_streams=[{**technical().video_streams[0].model_dump(), "frame_rate_den": None}]
        )
    with pytest.raises(ValidationError, match="stream indexes"):
        technical(
            audio_streams=[{"stream_index": 0, "codec": "aac", "sample_rate": 48000, "channels": 2}]
        )


def test_episode_scene_shot_and_frame_plan_contracts() -> None:
    series_id = uuid4()
    episode = {
        "episode_id": uuid4(),
        "series_id": series_id,
        "sequence": 1,
        "title": "第一集",
        "source_media_ref": ref("SourceMedia"),
    }
    catalog = EpisodeCatalog.model_validate({"series_id": series_id, "episodes": [episode]})
    assert catalog.episodes[0].sequence == 1
    with pytest.raises(ValidationError, match="unique"):
        EpisodeCatalog.model_validate({"series_id": series_id, "episodes": [episode, episode]})

    source = ref("SourceMedia")
    scene = {
        "segment_id": uuid4(),
        "kind": "scene",
        "source": source,
        "source_range": {"start": time(0), "duration": time(25)},
        "detector": {
            "provider": "local",
            "implementation": "pyscene",
            "version": "1",
            "license": "bsd",
        },
        "confidence": shadow_confidence(),
        "status": "detected",
    }
    assert (
        len(SceneShotCatalog.model_validate({"source": source, "segments": [scene]}).segments) == 1
    )
    with pytest.raises(ValidationError, match="scene cannot"):
        SceneShotCatalog.model_validate(
            {"source": source, "segments": [{**scene, "parent_scene_id": uuid4()}]}
        )

    plan = FrameSamplePlan.model_validate(
        {
            "source": source,
            "purpose": "ocr",
            "profile_ref": ref("ConfigArtifact"),
            "samples": [{"sample_id": uuid4(), "source_time": time(10), "reason": "text-change"}],
        }
    )
    assert FrameSamplePlan.model_validate_json(plan.canonical_json()) == plan
