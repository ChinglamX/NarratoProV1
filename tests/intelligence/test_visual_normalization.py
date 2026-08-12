from uuid import UUID, uuid4

from packages.contracts import ArtifactRef, ProviderIdentity
from packages.intelligence.visual import (
    build_shot_tracklets,
    build_text_tracks,
    normalize_visual_response,
)


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=kind)


def provider() -> ProviderIdentity:
    return ProviderIdentity(
        provider="visual-test", implementation="fixture", version="1", license="test-only"
    )


def frame(sample_id: UUID, second: int) -> dict[str, object]:
    return {
        "frame_ref": ref("ProxyMedia"),
        "sample_id": sample_id,
        "source_time": {"value": second, "rate_num": 1},
    }


def test_visual_normalization_keeps_capabilities_separate_and_shadow() -> None:
    sample_id = uuid4()
    result = normalize_visual_response(
        {
            "frames": [
                {
                    "frame": frame(sample_id, 1),
                    "ocr": [
                        {
                            "text": "欠条",
                            "region": {"x_min": 0.1, "y_min": 0.1, "x_max": 0.4, "y_max": 0.2},
                            "kind": "scene_text",
                            "score": 0.9,
                        }
                    ],
                    "detections": [
                        {
                            "label": "person",
                            "region": {"x_min": 0.2, "y_min": 0.1, "x_max": 0.6, "y_max": 0.9},
                            "score": 0.8,
                        }
                    ],
                    "vlm_claims": [
                        {"kind": "visible", "statement": "one person is visible", "score": 0.7}
                    ],
                }
            ],
            "unavailable_capabilities": ["visual_embedding"],
        },
        source_ref=ref("SourceMedia"),
        frame_plan_ref=ref("FrameSamplePlan"),
        raw_response_refs=[ref("RawProviderResponse")],
        provider=provider(),
    )
    assert result.status == "incomplete"
    assert result.ocr[0].kind == "scene_text"
    assert result.detections[0].confidence.status == "shadow"
    assert result.vlm_claims[0].kind == "visible"
    assert build_text_tracks(result.ocr, provider=provider())[0].text == "欠条"


def test_tracklets_are_shot_local_and_source_time_ordered() -> None:
    sample_one, sample_two = uuid4(), uuid4()
    result = normalize_visual_response(
        {
            "frames": [
                {
                    "frame": frame(sample_two, 2),
                    "detections": [
                        {
                            "label": "person",
                            "region": {"x_min": 0.1, "y_min": 0.1, "x_max": 0.5, "y_max": 0.9},
                        }
                    ],
                },
                {
                    "frame": frame(sample_one, 1),
                    "detections": [
                        {
                            "label": "person",
                            "region": {"x_min": 0.12, "y_min": 0.1, "x_max": 0.52, "y_max": 0.9},
                        }
                    ],
                },
            ]
        },
        source_ref=ref("SourceMedia"),
        frame_plan_ref=ref("FrameSamplePlan"),
        raw_response_refs=[ref("RawProviderResponse")],
        provider=provider(),
    )
    tracks = build_shot_tracklets(
        result.detections, shot_ref=ref("SceneShotCatalog"), provider=provider()
    )
    assert len(tracks) == 1
    assert [point.frame.source_time.value for point in tracks[0].points] == [1, 2]
