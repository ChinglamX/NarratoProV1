# ruff: noqa: RUF001 - fixtures intentionally contain Chinese punctuation.

from pathlib import Path
from uuid import uuid4

import pytest

from packages.contracts import ArtifactRef
from packages.intelligence.story_brief import StoryClaim, build_story_brief, parse_srt


def _ref(kind: str) -> ArtifactRef:
    return ArtifactRef.model_validate({"artifact_id": uuid4(), "version": 1, "artifact_type": kind})


def test_story_brief_requires_exact_transcript_excerpt(tmp_path: Path) -> None:
    transcript = tmp_path / "episode.srt"
    transcript.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\n三十万，这两样我都要了。\n",
        encoding="utf-8",
    )
    cues = parse_srt(transcript)
    graph = build_story_brief(
        fact_ref=_ref("FactSet"),
        transcript_ref=_ref("SpeechObservation"),
        cues=cues,
        claims=(
            StoryClaim(
                claim_id="sale",
                description="买家以三十万购买两样货物。",
                cue_ids=(1,),
                excerpts=("三十万，这两样我都要了",),
            ),
        ),
        unresolved=("货物具体名称仅凭本段对白无法确认。",),
    )
    assert graph.events[0].confidence.status.value == "unavailable"
    assert graph.events[0].evidence[0].excerpt == "三十万，这两样我都要了"
    assert len(graph.unresolved_questions) == 1


def test_story_brief_rejects_absent_excerpt(tmp_path: Path) -> None:
    transcript = tmp_path / "episode.srt"
    transcript.write_text("1\n00:00:01,000 --> 00:00:03,000\n三十万成交。\n", encoding="utf-8")
    with pytest.raises(ValueError, match="excerpt is absent"):
        build_story_brief(
            fact_ref=_ref("FactSet"),
            transcript_ref=_ref("SpeechObservation"),
            cues=parse_srt(transcript),
            claims=(
                StoryClaim(
                    claim_id="invented",
                    description="买家支付五十万。",
                    cue_ids=(1,),
                    excerpts=("五十万",),
                ),
            ),
            unresolved=(),
        )
