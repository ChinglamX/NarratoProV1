"""FunASR/OpenAI-style response normalization into canonical Speech observations."""

from __future__ import annotations

import re
from fractions import Fraction
from typing import Any
from uuid import uuid4

from packages.contracts import (
    ArtifactRef,
    ProviderIdentity,
    SpeechConflict,
    SpeechObservation,
    TranscriptSegment,
)

_CRITICAL_PATTERNS: dict[str, re.Pattern[str]] = {
    "negation": re.compile(r"不|没|无|未|别|莫|否"),
    "number": re.compile(r"\d+(?:\.\d+)?|[零一二三四五六七八九十百千万亿两]+"),
    "money": re.compile(r"(?:元|块|万|亿|美元|人民币)"),
    "time": re.compile(r"(?:年|月|日|天|时|点|分|秒|小时|分钟)"),
}


def _time_range(start_seconds: float, end_seconds: float) -> dict[str, object]:
    start = Fraction(str(start_seconds))
    end = Fraction(str(end_seconds))
    if end <= start:
        raise ValueError("provider timestamp range must be positive")
    return {
        "start": {"value": round(float(start) * 1_000_000), "rate_num": 1_000_000},
        "duration": {
            "value": round(float(end - start) * 1_000_000),
            "rate_num": 1_000_000,
        },
    }


def _confidence(score: float | None, scope: str) -> dict[str, object]:
    if score is None:
        return {
            "score": None,
            "status": "unavailable",
            "method": "provider-score-unavailable",
            "applicable_scope": scope,
            "risk_class": "high",
        }
    return {
        "score": min(1.0, max(0.0, score)),
        "status": "shadow",
        "method": "provider-score-uncalibrated",
        "applicable_scope": scope,
        "risk_class": "high",
        "supporting_factors": [
            {
                "code": "provider_score",
                "description": "Uncalibrated score reported by the speech provider",
                "value": score,
            }
        ],
    }


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def detect_transcript_conflicts(
    left: TranscriptSegment,
    right: TranscriptSegment,
    *,
    left_ref: ArtifactRef,
    right_ref: ArtifactRef,
) -> tuple[SpeechConflict, ...]:
    """Expose critical semantic disagreements without attempting to resolve them."""

    overlap_start = max(left.source_range.start.seconds, right.source_range.start.seconds)
    overlap_end = min(left.source_range.end_seconds, right.source_range.end_seconds)
    if overlap_end <= overlap_start:
        return ()
    disagreements = [
        name
        for name, pattern in _CRITICAL_PATTERNS.items()
        if pattern.findall(left.normalized_text) != pattern.findall(right.normalized_text)
    ]
    if not disagreements:
        return ()
    source_range = _time_range(float(overlap_start), float(overlap_end))
    return (
        SpeechConflict.model_validate(
            {
                "conflict_id": uuid4(),
                "conflict_type": "critical-transcript-disagreement",
                "source_range": source_range,
                "candidate_refs": [left_ref, right_ref],
                "detail": "Critical categories differ: " + ", ".join(disagreements),
            }
        ),
    )


def normalize_funasr_response(
    raw: dict[str, Any],
    *,
    source_audio_ref: ArtifactRef,
    raw_response_ref: ArtifactRef,
    provider: ProviderIdentity,
) -> SpeechObservation:
    raw_segments = raw.get("segments")
    if not isinstance(raw_segments, list):
        text = raw.get("text")
        duration = raw.get("duration")
        if isinstance(text, str) and text.strip() and isinstance(duration, (int, float)):
            raw_segments = [{"start": 0.0, "end": float(duration), "text": text}]
        else:
            return SpeechObservation.model_validate(
                {
                    "source_audio_ref": source_audio_ref,
                    "raw_response_ref": raw_response_ref,
                    "provider": provider,
                    "vad_segments": [],
                    "transcripts": [],
                    "status": "unavailable",
                    "unavailable_reasons": ["missing_segment_timestamps"],
                }
            )
    vad_segments: list[dict[str, object]] = []
    transcripts: list[dict[str, object]] = []
    speaker_ranges: dict[str, list[dict[str, object]]] = {}
    for segment in raw_segments:
        if not isinstance(segment, dict):
            raise ValueError("provider segment must be an object")
        start = float(segment["start"])
        end = float(segment["end"])
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        source_range = _time_range(start, end)
        vad_segments.append(
            {
                "segment_id": uuid4(),
                "source_range": source_range,
                "speech_probability": segment.get("speech_probability"),
            }
        )
        words = segment.get("words", [])
        tokens = []
        if isinstance(words, list):
            for word in words:
                if not isinstance(word, dict) or not str(word.get("word", "")).strip():
                    continue
                tokens.append(
                    {
                        "token_id": uuid4(),
                        "text": str(word["word"]).strip(),
                        "source_range": _time_range(float(word["start"]), float(word["end"])),
                        "granularity": "word",
                        "estimated_error_ms": int(word.get("estimated_error_ms", 200)),
                        "confidence": _confidence(
                            float(word["probability"]) if "probability" in word else None,
                            "speech-token:v1",
                        ),
                    }
                )
        score = float(segment["confidence"]) if "confidence" in segment else None
        transcripts.append(
            {
                "segment_id": uuid4(),
                "source_range": source_range,
                "raw_text": text,
                "normalized_text": normalize_text(text),
                "language": raw.get("language"),
                "tokens": tokens,
                "speaker_cluster_id": segment.get("speaker"),
                "confidence": _confidence(score, "speech-segment:v1"),
            }
        )
        speaker = segment.get("speaker")
        if isinstance(speaker, str) and speaker:
            speaker_ranges.setdefault(speaker, []).append(source_range)
    status = "complete" if transcripts else "unavailable"
    speakers = [
        {
            "observation_id": uuid4(),
            "cluster_id": cluster,
            "source_ranges": ranges,
            "provider": provider,
            "confidence": _confidence(None, "speaker-cluster:v1"),
        }
        for cluster, ranges in sorted(speaker_ranges.items())
    ]
    return SpeechObservation.model_validate(
        {
            "source_audio_ref": source_audio_ref,
            "raw_response_ref": raw_response_ref,
            "provider": provider,
            "vad_segments": vad_segments,
            "transcripts": transcripts,
            "speakers": speakers,
            "status": status,
            "unavailable_reasons": [] if transcripts else ["empty_transcript"],
        }
    )
