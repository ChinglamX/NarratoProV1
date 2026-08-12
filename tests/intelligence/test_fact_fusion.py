from uuid import uuid4

import pytest

from packages.contracts import ArtifactRef, SpeechObservation, VisualObservation
from packages.intelligence.facts import fuse_observations


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef.model_validate({"artifact_id": uuid4(), "version": 1, "artifact_type": kind})


def confidence() -> dict[str, object]:
    return {
        "score": 0.8,
        "status": "shadow",
        "method": "test",
        "applicable_scope": "fact:test",
        "risk_class": "high",
    }


def provider() -> dict[str, object]:
    return {
        "provider": "fixture",
        "implementation": "fixture",
        "version": "1",
        "license": "test-only",
    }


def frame() -> dict[str, object]:
    return {
        "frame_ref": ref("ProxyMedia"),
        "sample_id": uuid4(),
        "source_time": {"value": 0, "rate_num": 25},
    }


def test_fusion_keeps_observation_facts_and_disagreement() -> None:
    speech_ref, visual_ref = ref("SpeechObservation"), ref("VisualObservation")
    speech = SpeechObservation.model_validate(
        {
            "source_audio_ref": ref("AudioStem"),
            "raw_response_ref": ref("RawProviderResponse"),
            "provider": provider(),
            "vad_segments": [],
            "transcripts": [
                {
                    "segment_id": uuid4(),
                    "source_range": {
                        "start": {"value": 0, "rate_num": 25},
                        "duration": {"value": 25, "rate_num": 25},
                    },
                    "raw_text": "你回来了",
                    "normalized_text": "你回来了",
                    "speaker_cluster_id": "speaker-1",
                    "confidence": confidence(),
                }
            ],
            "status": "complete",
        }
    )
    visual = VisualObservation.model_validate(
        {
            "source_ref": ref("SourceMedia"),
            "frame_plan_ref": ref("FrameSamplePlan"),
            "raw_response_refs": [ref("RawProviderResponse")],
            "ocr": [
                {
                    "observation_id": uuid4(),
                    "frame": frame(),
                    "text": "你走吧",
                    "region": {"x_min": 0.1, "y_min": 0.7, "x_max": 0.9, "y_max": 0.9},
                    "kind": "burned_in_subtitle",
                    "provider": provider(),
                    "confidence": confidence(),
                }
            ],
            "vlm_claims": [
                {
                    "claim_id": uuid4(),
                    "kind": "inferred",
                    "statement": "他想复仇",
                    "frame_evidence": [frame()],
                    "confidence": confidence(),
                }
            ],
            "status": "complete",
        }
    )
    report = fuse_observations(
        fact_set_ref=ref("FactSet"),
        speech_ref=speech_ref,
        speech=speech,
        visual_ref=visual_ref,
        visual=visual,
    )
    assert {item.fact_type.value for item in report.fact_set.facts} == {"dialogue", "ocr"}
    assert all("复仇" not in str(item.value) for item in report.fact_set.facts)
    assert report.conflicts[0].conflict_type == "asr-ocr-text-disagreement"


def test_unavailable_partition_remains_incomplete() -> None:
    speech = SpeechObservation.model_validate(
        {
            "source_audio_ref": ref("AudioStem"),
            "raw_response_ref": ref("RawProviderResponse"),
            "provider": provider(),
            "vad_segments": [],
            "transcripts": [],
            "status": "unavailable",
            "unavailable_reasons": ["provider-down"],
        }
    )
    report = fuse_observations(
        fact_set_ref=ref("FactSet"),
        speech_ref=ref("SpeechObservation"),
        speech=speech,
    )
    assert report.fact_set.incomplete
    assert report.incomplete_partitions == ("speech",)


def test_fact_fusion_requires_payload_ref_pairs() -> None:
    with pytest.raises(ValueError, match="provided together"):
        fuse_observations(fact_set_ref=ref("FactSet"), speech_ref=ref("SpeechObservation"))
