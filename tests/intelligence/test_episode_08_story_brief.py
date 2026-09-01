import json
from pathlib import Path
from uuid import uuid4

from packages.contracts import ArtifactRef
from packages.intelligence.story_brief import StoryClaim, build_story_brief, parse_srt

ROOT = Path(__file__).resolve().parents[2]


def _ref(kind: str) -> ArtifactRef:
    return ArtifactRef.model_validate({"artifact_id": uuid4(), "version": 1, "artifact_type": kind})


def test_episode_08_claims_remain_exactly_grounded() -> None:
    config_path = ROOT / "product/episode_08_story_brief_validation.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    transcript = (config_path.parent / config["transcript"]).resolve()
    claims = tuple(StoryClaim(**item) for item in config["claims"])

    graph = build_story_brief(
        fact_ref=_ref("FactSet"),
        transcript_ref=_ref("SpeechObservation"),
        cues=parse_srt(transcript),
        claims=claims,
        unresolved=tuple(config["unresolved"]),
    )

    assert len(graph.events) == 3
    assert all(event.confidence.status.value == "unavailable" for event in graph.events)
    assert all(event.evidence for event in graph.events)
    assert len(graph.unresolved_questions) == 2
