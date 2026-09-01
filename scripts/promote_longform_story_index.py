#!/usr/bin/env python3
"""Promote a fully reviewed evidence pack into SeriesStoryIndex input JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from packages.longform.story_index import EventFunction, SeriesEvent, SeriesEvidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-pack", type=Path, required=True)
    parser.add_argument("--visual-review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    pack = json.loads(args.evidence_pack.read_text(encoding="utf-8"))
    review = json.loads(args.visual_review.read_text(encoding="utf-8"))
    decisions = {item["event_id"]: item for item in review["decisions"]}
    result_events = []
    for raw in pack["events"]:
        decision = decisions.get(raw["event_id"])
        if decision is None or decision["status"] != "verified_window":
            raise ValueError(f"event is not visually verified: {raw['event_id']}")
        dialogue = raw["dialogue_evidence"]
        start, end = dialogue["start_seconds"], dialogue["end_seconds"]
        function = EventFunction(raw["function"])
        event = SeriesEvent(
            event_id=raw["event_id"],
            episode=raw["episode"],
            order_in_episode=raw["order_in_episode"],
            description=raw["description"],
            function=function,
            character_refs=tuple(raw["character_refs"]),
            evidence=(
                SeriesEvidence(
                    evidence_id=f"dialogue:{raw['source_sha256']}:{raw['event_id']}",
                    episode=raw["episode"],
                    start_seconds=start,
                    end_seconds=end,
                    kind="dialogue",
                    excerpt=dialogue["excerpt"],
                ),
                SeriesEvidence(
                    evidence_id=f"visual-review:{raw['source_sha256']}:{raw['event_id']}",
                    episode=raw["episode"],
                    start_seconds=start,
                    end_seconds=end,
                    kind="visual",
                    excerpt=decision["statement"],
                ),
            ),
            causes=tuple(raw["causes"]),
            importance=_importance(function),
            visual_payoff=_visual_payoff(function),
            original_audio_value=_original_audio_value(function),
        )
        result_events.append(_event_json(event, raw["source_path"], dialogue["precision"]))

    missing = set(decisions) - {event["event_id"] for event in pack["events"]}
    if missing:
        raise ValueError(f"visual review contains unknown events: {', '.join(sorted(missing))}")
    result = {
        "series_id": pack["series_id"],
        "evidence_scope": "current source hashes + literal ASR cues + Codex visual-window review",
        "unresolved": [
            "event ranges are coarse review windows and require shot-boundary refinement",
            "character identities remain temporary until cross-episode identity qualification",
        ],
        "events": result_events,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"promoted story input: {len(result_events)} reviewed events")
    print(f"output: {args.output.resolve()}")
    return 0


def _importance(function: EventFunction) -> int:
    return (
        5 if function in {EventFunction.CONFLICT, EventFunction.CLIMAX, EventFunction.PAYOFF} else 4
    )


def _visual_payoff(function: EventFunction) -> int:
    return 5 if function in {EventFunction.TURN, EventFunction.CLIMAX, EventFunction.PAYOFF} else 4


def _original_audio_value(function: EventFunction) -> int:
    if function in {EventFunction.CONFLICT, EventFunction.CLIMAX}:
        return 5
    return 4 if function is EventFunction.PAYOFF else 2


def _event_json(event: SeriesEvent, source_path: str, precision: str) -> dict[str, object]:
    return {
        "event_id": event.event_id,
        "episode": event.episode,
        "order_in_episode": event.order_in_episode,
        "description": event.description,
        "function": event.function.value,
        "character_refs": list(event.character_refs),
        "evidence": [
            {
                "evidence_id": item.evidence_id,
                "episode": item.episode,
                "start_seconds": item.start_seconds,
                "end_seconds": item.end_seconds,
                "kind": item.kind,
                "excerpt": item.excerpt,
            }
            for item in event.evidence
        ],
        "causes": list(event.causes),
        "importance": event.importance,
        "visual_payoff": event.visual_payoff,
        "original_audio_value": event.original_audio_value,
        "source_path": source_path,
        "range_precision": precision,
    }


if __name__ == "__main__":
    raise SystemExit(main())
