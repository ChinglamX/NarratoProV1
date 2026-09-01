#!/usr/bin/env python3
"""Thin CLI over the existing NarratoPro core for long-form planning checkpoints."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.longform.clip_planning import CandidateShot, plan_chapter_clips  # noqa: E402
from packages.longform.inventory import build_media_inventory  # noqa: E402
from packages.longform.narration_planning import (  # noqa: E402
    NarrationTextDraft,
    preflight_narration_drafts,
)
from packages.longform.planning import (  # noqa: E402
    Chapter,
    ChapterBlueprint,
    ChapterFunction,
    build_chapter_blueprint,
    propose_marketing_arcs,
    select_default_arc,
)
from packages.longform.story_index import (  # noqa: E402
    EventFunction,
    SeriesEvent,
    SeriesEvidence,
    build_series_story_index,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    inventory = commands.add_parser("inventory", help="build a read-only media inventory")
    inventory.add_argument("source_root", type=Path)
    inventory.add_argument("--output", type=Path, required=True)

    plan = commands.add_parser("plan", help="build story index, arcs and chapter blueprints")
    plan.add_argument("events", type=Path, help="evidence-grounded series events JSON")
    plan.add_argument("--output-dir", type=Path, required=True)
    plan.add_argument("--target-seconds", type=float, default=240.0)
    plan.add_argument(
        "--hook-event-ref",
        help="evidence-grounded event to use as the cold-open hook in the recommended arc",
    )

    coverage = commands.add_parser("coverage", help="validate shot coverage for one blueprint")
    coverage.add_argument("blueprint", type=Path)
    coverage.add_argument("shots", type=Path)
    coverage.add_argument("--output", type=Path, required=True)

    narration = commands.add_parser(
        "narration-preflight", help="validate evidence-grounded narration before TTS"
    )
    narration.add_argument("drafts", type=Path)
    narration.add_argument("story_index", type=Path)
    narration.add_argument("blueprints", type=Path)
    narration.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "inventory":
        result = build_media_inventory(args.source_root)
        _write(args.output, json.loads(result.to_json()))
        print(f"inventory: {len(result.files)} videos / {len(result.series)} groups")
        print(f"output: {args.output.resolve()}")
        return 0
    if args.command == "plan":
        return _plan(args.events, args.output_dir, args.target_seconds, args.hook_event_ref)
    if args.command == "coverage":
        return _coverage(args.blueprint, args.shots, args.output)
    if args.command == "narration-preflight":
        return _narration_preflight(args.drafts, args.story_index, args.blueprints, args.output)
    raise AssertionError(f"unhandled command: {args.command}")


def _plan(
    events_path: Path,
    output_dir: Path,
    target_seconds: float,
    hook_event_ref: str | None = None,
) -> int:
    payload = json.loads(events_path.read_text(encoding="utf-8"))
    index = build_series_story_index(
        series_id=str(payload["series_id"]),
        events=tuple(_event(item) for item in payload["events"]),
        unresolved=tuple(str(item) for item in payload.get("unresolved", [])),
    )
    if index.blocked:
        raise SystemExit("story index blocked: no complete conflict→escalation→payoff chain")
    arcs = propose_marketing_arcs(index)
    if not arcs:
        raise SystemExit("marketing planning blocked: no evidence-grounded arc")
    recommendation = select_default_arc(index, arcs)
    blueprints = tuple(
        build_chapter_blueprint(
            index=index,
            arc=arc,
            target_seconds=target_seconds,
            hook_event_ref=(hook_event_ref if arc.arc_id == recommendation.arc.arc_id else None),
        )
        for arc in arcs
    )
    if all(blueprint.blocked for blueprint in blueprints):
        raise SystemExit("chapter planning blocked: every candidate lacks required structure")
    output_dir.mkdir(parents=True, exist_ok=True)
    _write(output_dir / "series_story_index.json", asdict(index))
    _write(output_dir / "marketing_arc_candidates.json", [asdict(item) for item in arcs])
    _write(output_dir / "chapter_blueprints.json", [asdict(item) for item in blueprints])
    _write(
        output_dir / "planning_summary.json",
        _summary(index, arcs, blueprints, recommendation),
    )
    print(f"story index: {len(index.events)} events / {len(index.conflicts)} conflicts")
    print(f"marketing arcs: {len(arcs)}")
    print(f"output: {output_dir.resolve()}")
    return 0


def _event(raw: dict[str, Any]) -> SeriesEvent:
    return SeriesEvent(
        event_id=str(raw["event_id"]),
        episode=int(raw["episode"]),
        order_in_episode=int(raw["order_in_episode"]),
        description=str(raw["description"]),
        function=EventFunction(str(raw["function"])),
        character_refs=tuple(str(item) for item in raw.get("character_refs", [])),
        evidence=tuple(_evidence(item) for item in raw["evidence"]),
        causes=tuple(str(item) for item in raw.get("causes", [])),
        importance=int(raw.get("importance", 3)),
        visual_payoff=int(raw.get("visual_payoff", 0)),
        original_audio_value=int(raw.get("original_audio_value", 0)),
    )


def _coverage(blueprint_path: Path, shots_path: Path, output: Path) -> int:
    raw_blueprint = json.loads(blueprint_path.read_text(encoding="utf-8"))
    if isinstance(raw_blueprint, list):
        raw_blueprint = raw_blueprint[0]
    blueprint = ChapterBlueprint(
        arc_id=str(raw_blueprint["arc_id"]),
        target_seconds=float(raw_blueprint["target_seconds"]),
        chapters=tuple(_chapter(item) for item in raw_blueprint["chapters"]),
        findings=tuple(str(item) for item in raw_blueprint.get("findings", [])),
    )
    raw_shots = json.loads(shots_path.read_text(encoding="utf-8"))
    shots = tuple(_shot(item) for item in raw_shots)
    result = plan_chapter_clips(blueprint=blueprint, shots=shots)
    _write(output, asdict(result))
    status = "blocked" if result.blocked else "ready"
    print(f"clip coverage: {result.selected_seconds:.3f}/{result.target_seconds:.3f}s ({status})")
    print(f"output: {output.resolve()}")
    return 2 if result.blocked else 0


def _narration_preflight(
    drafts_path: Path, story_path: Path, blueprints_path: Path, output: Path
) -> int:
    raw_drafts = json.loads(drafts_path.read_text(encoding="utf-8"))
    raw_story = json.loads(story_path.read_text(encoding="utf-8"))
    raw_blueprints = json.loads(blueprints_path.read_text(encoding="utf-8"))
    index = build_series_story_index(
        series_id=str(raw_story["series_id"]),
        events=tuple(_event(item) for item in raw_story["events"]),
        unresolved=tuple(str(item) for item in raw_story.get("unresolved", [])),
    )
    result = preflight_narration_drafts(
        drafts=tuple(
            NarrationTextDraft(
                line_id=str(item["line_id"]),
                chapter_id=str(item["chapter_id"]),
                text=str(item["text"]),
                event_refs=tuple(str(ref) for ref in item["event_refs"]),
                rhetorical=bool(item.get("rhetorical", False)),
            )
            for item in raw_drafts["lines"]
        ),
        story_index=index,
        blueprint=_chapter_blueprint(raw_blueprints[0]),
    )
    _write(output, asdict(result))
    status = "blocked" if result.blocked else "ready-for-tts"
    print(f"narration preflight: {result.estimated_duration_seconds:.3f}s ({status})")
    print(f"output: {output.resolve()}")
    return 2 if result.blocked else 0


def _chapter_blueprint(raw: dict[str, Any]) -> ChapterBlueprint:
    return ChapterBlueprint(
        arc_id=str(raw["arc_id"]),
        target_seconds=float(raw["target_seconds"]),
        chapters=tuple(_chapter(item) for item in raw["chapters"]),
        findings=tuple(str(item) for item in raw.get("findings", [])),
    )


def _chapter(raw: dict[str, Any]) -> Chapter:
    return Chapter(
        chapter_id=str(raw["chapter_id"]),
        function=ChapterFunction(str(raw["function"])),
        event_refs=tuple(str(item) for item in raw["event_refs"]),
        target_seconds=float(raw["target_seconds"]),
        narration_budget_seconds=float(raw["narration_budget_seconds"]),
        protects_original_audio=bool(raw["protects_original_audio"]),
    )


def _shot(raw: dict[str, Any]) -> CandidateShot:
    return CandidateShot(
        shot_id=str(raw["shot_id"]),
        source_path=str(raw["source_path"]),
        episode=int(raw["episode"]),
        start_seconds=float(raw["start_seconds"]),
        duration_seconds=float(raw["duration_seconds"]),
        event_refs=tuple(str(item) for item in raw["event_refs"]),
        visual_score=float(raw.get("visual_score", 0.5)),
        continuity_group=(
            str(raw["continuity_group"]) if raw.get("continuity_group") is not None else None
        ),
        contains_protected_audio=bool(raw.get("contains_protected_audio", False)),
    )


def _evidence(raw: dict[str, Any]) -> SeriesEvidence:
    return SeriesEvidence(
        evidence_id=str(raw["evidence_id"]),
        episode=int(raw["episode"]),
        start_seconds=float(raw["start_seconds"]),
        end_seconds=float(raw["end_seconds"]),
        kind=str(raw["kind"]),
        excerpt=str(raw["excerpt"]) if raw.get("excerpt") is not None else None,
    )


def _summary(
    index: Any,
    arcs: tuple[Any, ...],
    blueprints: tuple[Any, ...],
    recommendation: Any,
) -> dict[str, Any]:
    return {
        "series_id": index.series_id,
        "episode_count": index.episode_count,
        "event_count": len(index.events),
        "conflict_count": len(index.conflicts),
        "unresolved": list(index.unresolved),
        "recommended_arc_id": recommendation.arc.arc_id,
        "recommendation_reasons": list(recommendation.reason_codes),
        "candidates": [
            {
                "arc_id": arc.arc_id,
                "label": arc.label,
                "risk_codes": list(arc.risk_codes),
                "target_seconds": blueprint.target_seconds,
                "chapter_count": len(blueprint.chapters),
                "findings": list(blueprint.findings),
            }
            for arc, blueprint in zip(arcs, blueprints, strict=True)
        ],
        "status": "planning-ready",
        "release_boundary": "internal-preview-only",
    }


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
