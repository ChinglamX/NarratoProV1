#!/usr/bin/env python3
"""Expand reviewed event windows into unique scene-bounded shot candidates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from packages.providers.media.scenes import detect_scenes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-pack", type=Path, required=True)
    parser.add_argument("--series-events", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--context-radius", type=float, default=20.0)
    parser.add_argument("--maximum-shot-seconds", type=float, default=8.0)
    args = parser.parse_args()
    if args.context_radius < 0 or args.maximum_shot_seconds <= 0:
        raise ValueError("shot expansion parameters must be positive")

    pack = json.loads(args.evidence_pack.read_text(encoding="utf-8"))
    story = json.loads(args.series_events.read_text(encoding="utf-8"))
    story_by_id = {event["event_id"]: event for event in story["events"]}
    by_source: dict[str, list[dict[str, Any]]] = {}
    for event in pack["events"]:
        by_source.setdefault(event["source_path"], []).append(event)

    shots: list[dict[str, Any]] = []
    for source_path, events in sorted(by_source.items()):
        source = Path(source_path)
        episode = int(events[0]["episode"])
        scenes = detect_scenes(source)
        for scene_number, scene in enumerate(scenes, 1):
            start, end = float(scene.start_seconds), float(scene.end_seconds)
            midpoint = (start + end) / 2
            event, distance = min(
                ((_event, _distance(midpoint, _event)) for _event in events),
                key=lambda pair: pair[1],
            )
            if distance > args.context_radius:
                continue
            cursor = start
            part = 1
            while cursor < end - 0.05:
                duration = min(args.maximum_shot_seconds, end - cursor)
                if duration < 0.35:
                    break
                story_event = story_by_id[event["event_id"]]
                evidence = event["dialogue_evidence"]
                overlaps_evidence = cursor < float(evidence["end_seconds"]) and (
                    cursor + duration > float(evidence["start_seconds"])
                )
                score = max(0.35, 1.0 - distance / max(args.context_radius * 1.5, 1.0))
                shots.append(
                    {
                        "shot_id": f"e{episode:02d}-s{scene_number:03d}-p{part:02d}",
                        "source_path": source_path,
                        "episode": episode,
                        "start_seconds": round(cursor, 3),
                        "duration_seconds": round(duration, 3),
                        "event_refs": [event["event_id"]],
                        "visual_score": round(score, 3),
                        "continuity_group": f"episode-{episode}:{event['event_id']}",
                        "contains_protected_audio": bool(
                            overlaps_evidence and story_event["original_audio_value"] >= 4
                        ),
                        "grounding": "reviewed-window" if overlaps_evidence else "adjacent-context",
                        "distance_to_evidence_seconds": round(distance, 3),
                    }
                )
                cursor += duration
                part += 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(shots, ensure_ascii=False, indent=2), encoding="utf-8")
    coverage = sum((float(item["duration_seconds"]) for item in shots), start=0.0)
    print(f"shot candidates: {len(shots)} / {coverage:.3f}s unique source coverage")
    print(f"output: {args.output.resolve()}")
    return 0


def _distance(midpoint: float, event: dict[str, Any]) -> float:
    evidence = event["dialogue_evidence"]
    assert isinstance(evidence, dict)  # nosec B101 - internal validated JSON shape
    start, end = float(evidence["start_seconds"]), float(evidence["end_seconds"])
    if start <= midpoint <= end:
        return 0.0
    return min(abs(midpoint - start), abs(midpoint - end))


if __name__ == "__main__":
    raise SystemExit(main())
