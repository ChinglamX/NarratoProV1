from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.contracts import SpeechObservation


def ref(kind: str) -> dict[str, object]:
    return {"artifact_id": uuid4(), "version": 1, "artifact_type": kind}


def provider() -> dict[str, object]:
    return {
        "provider": "funasr",
        "implementation": "http",
        "version": "1",
        "license": "MIT-code",
    }


def time_range(start: int, duration: int) -> dict[str, object]:
    return {
        "start": {"value": start, "rate_num": 1000},
        "duration": {"value": duration, "rate_num": 1000},
    }


def unavailable_confidence() -> dict[str, object]:
    return {
        "score": None,
        "status": "unavailable",
        "method": "none",
        "applicable_scope": "speech:v1",
        "risk_class": "high",
    }


def test_speech_observation_separates_cluster_from_character_and_validates_tokens() -> None:
    value = SpeechObservation.model_validate(
        {
            "source_audio_ref": ref("AudioStem"),
            "raw_response_ref": ref("RawProviderResponse"),
            "provider": provider(),
            "vad_segments": [{"segment_id": uuid4(), "source_range": time_range(0, 2000)}],
            "transcripts": [
                {
                    "segment_id": uuid4(),
                    "source_range": time_range(0, 2000),
                    "raw_text": "你好",
                    "normalized_text": "你好",
                    "speaker_cluster_id": "speaker-0",
                    "tokens": [
                        {
                            "token_id": uuid4(),
                            "text": "你好",
                            "source_range": time_range(100, 500),
                            "granularity": "word",
                            "estimated_error_ms": 200,
                            "confidence": unavailable_confidence(),
                        }
                    ],
                    "confidence": unavailable_confidence(),
                }
            ],
            "speakers": [],
            "status": "complete",
        }
    )
    assert value.transcripts[0].speaker_cluster_id == "speaker-0"
    invalid = value.model_dump(mode="json")
    invalid["transcripts"][0]["tokens"][0]["source_range"] = time_range(3000, 100)
    with pytest.raises(ValidationError, match="inside transcript"):
        SpeechObservation.model_validate(invalid)


def test_unavailable_speech_cannot_claim_transcript() -> None:
    with pytest.raises(ValidationError, match="requires reasons"):
        SpeechObservation.model_validate(
            {
                "source_audio_ref": ref("AudioStem"),
                "raw_response_ref": ref("RawProviderResponse"),
                "provider": provider(),
                "vad_segments": [],
                "transcripts": [],
                "status": "unavailable",
            }
        )
