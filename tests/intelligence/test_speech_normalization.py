from uuid import uuid4

from packages.contracts import ArtifactRef, ProviderIdentity
from packages.intelligence.speech import (
    detect_transcript_conflicts,
    normalize_funasr_response,
    normalize_text,
)


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=kind)


def provider() -> ProviderIdentity:
    return ProviderIdentity(
        provider="funasr", implementation="http", version="1", license="MIT-code"
    )


def test_funasr_response_normalizes_segments_tokens_and_shadow_confidence() -> None:
    result = normalize_funasr_response(
        {
            "language": "zh-CN",
            "segments": [
                {
                    "start": 1.0,
                    "end": 2.0,
                    "text": " 我  不答应 ",
                    "confidence": 0.7,
                    "words": [
                        {"start": 1.1, "end": 1.3, "word": "我", "probability": 0.8},
                        {"start": 1.4, "end": 1.8, "word": "不答应", "probability": 0.6},
                    ],
                }
            ],
        },
        source_audio_ref=ref("AudioStem"),
        raw_response_ref=ref("RawProviderResponse"),
        provider=provider(),
    )
    assert result.status == "complete"
    assert result.transcripts[0].normalized_text == "我 不答应"
    assert result.transcripts[0].confidence.status == "shadow"
    assert len(result.transcripts[0].tokens) == 2


def test_missing_timestamps_is_explicit_unavailable() -> None:
    result = normalize_funasr_response(
        {"text": "hello"},
        source_audio_ref=ref("AudioStem"),
        raw_response_ref=ref("RawProviderResponse"),
        provider=provider(),
    )
    assert result.status == "unavailable"
    assert result.unavailable_reasons == ("missing_segment_timestamps",)
    assert normalize_text(" a   b ") == "a b"


def test_critical_negation_conflict_is_exposed_not_resolved() -> None:
    first_ref = ref("SpeechObservation")
    second_ref = ref("SpeechObservation")
    first = normalize_funasr_response(
        {"segments": [{"start": 0, "end": 1, "text": "我不答应"}]},
        source_audio_ref=ref("AudioStem"),
        raw_response_ref=ref("RawProviderResponse"),
        provider=provider(),
    ).transcripts[0]
    second = normalize_funasr_response(
        {"segments": [{"start": 0, "end": 1, "text": "我答应"}]},
        source_audio_ref=ref("AudioStem"),
        raw_response_ref=ref("RawProviderResponse"),
        provider=provider(),
    ).transcripts[0]
    conflicts = detect_transcript_conflicts(first, second, left_ref=first_ref, right_ref=second_ref)
    assert conflicts[0].conflict_type == "critical-transcript-disagreement"
    assert "negation" in conflicts[0].detail
