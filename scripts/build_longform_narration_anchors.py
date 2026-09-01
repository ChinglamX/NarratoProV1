#!/usr/bin/env python3
"""Build measured, evidence-gated narration anchors for a longform cut."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

from packages.contracts import RationalTime, TimeRange
from packages.timeline.narration_anchor import (
    NarrationAnchorRequest,
    VisualEventAnchor,
    plan_narration_anchors,
)


def _time(seconds: float) -> RationalTime:
    return RationalTime(value=round(seconds * 1_000_000), rate_num=1_000_000)


def _uuid(key: str) -> UUID:
    raw = bytearray(sha256(key.encode()).digest()[:16])
    raw[6] = (raw[6] & 0x0F) | 0x40
    raw[8] = (raw[8] & 0x3F) | 0x80
    return UUID(bytes=bytes(raw))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected-shots", type=Path, required=True)
    parser.add_argument("--narration-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preferred-delay-seconds", type=float, default=0.25)
    parser.add_argument("--post-roll-seconds", type=float, default=8.0)
    parser.add_argument(
        "--protected-event-id",
        action="append",
        default=[],
        help="event whose original sound must not be covered; may be repeated",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    shots_payload = json.loads(args.selected_shots.read_text(encoding="utf-8"))
    narration = json.loads(args.narration_manifest.read_text(encoding="utf-8"))
    shots: list[dict[str, Any]] = shots_payload["selected"]
    lines: list[dict[str, Any]] = narration["lines"]

    event_spans: dict[str, list[float]] = defaultdict(lambda: [float("inf"), 0.0])
    cursor = 0.0
    for shot in shots:
        start = cursor
        cursor += float(shot["duration_seconds"])
        for event_id in shot["event_refs"]:
            event_spans[str(event_id)][0] = min(event_spans[str(event_id)][0], start)
            event_spans[str(event_id)][1] = max(event_spans[str(event_id)][1], cursor)

    events = tuple(
        VisualEventAnchor(
            event_id=event_id,
            timeline_range=TimeRange(start=_time(span[0]), duration=_time(span[1] - span[0])),
            evidence_refs=(_uuid(f"story:{event_id}"),),
            protects_original_sound=event_id in set(args.protected_event_id),
        )
        for event_id, span in sorted(event_spans.items(), key=lambda item: item[1][0])
    )
    requests = tuple(
        NarrationAnchorRequest(
            line_id=_uuid(f"narration:{line['line_id']}"),
            required_event_ids=tuple(str(value) for value in line["event_refs"]),
            measured_duration=_time(float(line["measured_duration_seconds"])),
            preferred_delay=_time(args.preferred_delay_seconds),
            post_roll=_time(args.post_roll_seconds),
        )
        for line in lines
    )
    plan = plan_narration_anchors(
        requests=requests,
        events=events,
        timeline_duration=_time(cursor),
        maximum_gap=_time(30.0),
    )
    line_by_uuid = {
        str(_uuid(f"narration:{line['line_id']}")): str(line["line_id"]) for line in lines
    }
    output = {
        "schema_version": "1.0",
        "release_boundary": "internal-preview-only",
        "timeline_duration_seconds": cursor,
        "blocked": plan.blocked,
        "events": [
            {
                "event_id": event.event_id,
                "start_seconds": float(event.timeline_range.start.seconds),
                "end_seconds": float(event.timeline_range.end_seconds),
                "protects_original_sound": event.protects_original_sound,
            }
            for event in events
        ],
        "decisions": [
            {
                "line_id": line_by_uuid[str(decision.line_id)],
                "start_seconds": float(decision.timeline_range.start.seconds),
                "duration_seconds": float(decision.timeline_range.duration.seconds),
                "end_seconds": float(decision.timeline_range.end_seconds),
                "earliest_allowed_start_seconds": float(decision.earliest_allowed_start.seconds),
                "latest_end_seconds": float(decision.latest_end.seconds),
                "required_event_ids": list(decision.required_event_ids),
                "source": decision.source.value,
            }
            for decision in plan.decisions
        ],
        "findings": [
            {
                "line_id": line_by_uuid[str(finding.line_id)],
                "code": finding.code,
                "explanation": finding.explanation,
                "blocker": finding.blocker,
            }
            for finding in plan.findings
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if plan.blocked:
        raise SystemExit("narration anchor plan is blocked")
    print(args.output)


if __name__ == "__main__":
    main()
