"""Build the Gate-1/2-approved second-source product candidate."""

# ruff: noqa: RUF001 - narration copy intentionally uses Chinese punctuation

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess  # nosec B404
import wave
from pathlib import Path
from typing import cast
from uuid import NAMESPACE_URL, UUID, uuid5

import httpx

from packages.contracts import RationalTime, TimeRange
from packages.production.director_provenance import (
    AgentRole,
    DecisionRecord,
    ProductionRunProvenance,
    TaskType,
)
from packages.timeline.narration_anchor import (
    NarrationAnchorRequest,
    VisualEventAnchor,
    plan_narration_anchors,
)

SOURCE = Path(
    "data/local/object_store/objects/sha256/dc/"
    "dc1b3d78bf10230f7e26606f2744d985d84e59a0635ec936f7b7af9d0b82a99d"
)
REFERENCE_AUDIO = Path("/Users/chinglam/Desktop/ref_7_clean.wav")
OUTPUT_DIR = Path("outputs/m5_second_source/candidate_v1")
TTS_URL = "http://127.0.0.1:8081/tts"

SEGMENTS: tuple[tuple[float, float], ...] = (
    (56.50, 4.00),
    (0.00, 4.00),
    (22.00, 4.50),
    (29.54, 4.50),
    (43.33, 4.00),
    (61.79, 4.50),
    (74.96, 4.50),
)
SEGMENT_SOURCES: tuple[Path, ...] = tuple(SOURCE for _ in SEGMENTS)
LINES: tuple[str, ...] = (
    "狼群封死退路，妹妹已无处可逃。",
    "几分钟前，她还被困在悬崖边。",
    "兄妹刚脱险，就挖到五十年份的野山参。",
    "卖掉它，妹妹的大学学费就有了。",
    "可狼群突然出现，再次把他们逼入绝境。",
    "为护住妹妹，他第一次用山神之力驱兽。",
    "群狼低头退去，他才明白，整座山都在回应自己。",
)
NARRATION_CUES: tuple[tuple[float, float, str], ...] = tuple(
    (
        sum(duration for _, duration in SEGMENTS[:index]),
        duration,
        LINES[index],
    )
    for index, (_, duration) in enumerate(SEGMENTS)
)
OUTPUT_FILENAME = "candidate_v1.mp4"
ANCHOR_CONFIG: dict[str, object] | None = None
PROVENANCE_CONFIG: dict[str, object] | None = None
ANCHOR_PLAN_MANIFEST: dict[str, object] | None = None
TTS_PARAMETERS = {
    "infer_mode": "普通推理",
    "do_sample": "false",
    "num_beams": "3",
    "repetition_penalty": "10.0",
}


def _configure_from_personal_config(path: Path) -> None:
    global SOURCE, REFERENCE_AUDIO, OUTPUT_DIR, SEGMENTS, SEGMENT_SOURCES
    global LINES, NARRATION_CUES, OUTPUT_FILENAME, ANCHOR_CONFIG, PROVENANCE_CONFIG
    raw = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent.resolve()

    def resolve(value: object) -> Path:
        candidate = Path(str(value))
        return candidate if candidate.is_absolute() else (base / candidate).resolve()

    SOURCE = resolve(raw["source_path"])
    REFERENCE_AUDIO = resolve(raw["reference_audio"])
    OUTPUT_DIR = resolve(raw["candidate_manifest"]).parent
    segments = raw.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError("personal config requires segments")
    SEGMENTS = tuple(
        (float(item["source_start_seconds"]), float(item["duration_seconds"])) for item in segments
    )
    SEGMENT_SOURCES = tuple(
        resolve(item.get("source_path", raw["source_path"])) for item in segments
    )
    narration_cues = raw.get("narration_cues")
    narration_anchors = raw.get("narration_anchors")
    if narration_cues is not None and narration_anchors is not None:
        raise ValueError("use narration_cues or narration_anchors, not both")
    if narration_anchors is not None:
        visual_events = raw.get("visual_events")
        if not isinstance(visual_events, list) or not visual_events:
            raise ValueError("narration_anchors requires visual_events")
        if not isinstance(narration_anchors, list) or not narration_anchors:
            raise ValueError("narration_anchors must be a non-empty list")
        total_duration = sum(duration for _, duration in SEGMENTS)
        LINES = tuple(str(item["narration"]) for item in narration_anchors)
        NARRATION_CUES = tuple((0.0, total_duration, text) for text in LINES)
        ANCHOR_CONFIG = {"visual_events": visual_events, "narration_anchors": narration_anchors}
    elif narration_cues is None:
        LINES = tuple(str(item["narration"]) for item in segments)
        NARRATION_CUES = tuple(
            (
                sum(duration for _, duration in SEGMENTS[:index]),
                duration,
                LINES[index],
            )
            for index, (_, duration) in enumerate(SEGMENTS)
        )
    elif isinstance(narration_cues, list) and narration_cues:
        NARRATION_CUES = tuple(
            (
                float(item["timeline_start_seconds"]),
                float(item["slot_duration_seconds"]),
                str(item["narration"]),
            )
            for item in narration_cues
        )
        LINES = tuple(cue[2] for cue in NARRATION_CUES)
    else:
        raise ValueError("narration_cues must be a non-empty list")
    OUTPUT_FILENAME = str(raw.get("candidate_filename", "candidate_v1.mp4"))
    provenance = raw.get("run_provenance")
    if provenance is not None and not isinstance(provenance, dict):
        raise ValueError("run_provenance must be an object")
    PROVENANCE_CONFIG = provenance


def _timestamp(seconds: float) -> str:
    centiseconds = round(seconds * 100)
    hours, remainder = divmod(centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    whole_seconds, fraction = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{fraction:02d}"


def _duration(path: Path) -> float:
    with wave.open(str(path), "rb") as source:
        return source.getnframes() / source.getframerate()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _tts_cache_key(text: str) -> str:
    payload = {
        "text": text,
        "reference_audio_checksum": _sha256(REFERENCE_AUDIO),
        "provider": "indextts-http",
        "provider_endpoint": TTS_URL,
        "parameters": TTS_PARAMETERS,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _legacy_cache_matches(*, index: int, text: str, output: Path) -> bool:
    """Accept a pre-key cache only when its prior manifest proves text and bytes."""
    manifest_path = OUTPUT_DIR / "manifest.json"
    if not output.is_file() or not manifest_path.is_file():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        lines = manifest.get("narration_lines", [])
        line = next(item for item in lines if int(item.get("index", -1)) == index)
    except (OSError, ValueError, TypeError, StopIteration, json.JSONDecodeError):
        return False
    return line.get("text") == text and line.get("checksum") == _sha256(output)


def _synthesize() -> list[dict[str, object]]:
    if not REFERENCE_AUDIO.is_file():
        raise FileNotFoundError(REFERENCE_AUDIO)
    results: list[dict[str, object]] = []
    with httpx.Client(timeout=300) as client:
        for index, (timeline_start, slot_duration, text) in enumerate(NARRATION_CUES, 1):
            output = OUTPUT_DIR / f"narration_{index:02d}.wav"
            cache_metadata = output.with_suffix(".cache.json")
            cache_key = _tts_cache_key(text)
            cached = False
            if output.is_file() and cache_metadata.is_file():
                metadata = json.loads(cache_metadata.read_text(encoding="utf-8"))
                cached = metadata.get("cache_key") == cache_key
            elif _legacy_cache_matches(index=index, text=text, output=output):
                cached = True
                cache_metadata.write_text(
                    json.dumps(
                        {
                            "cache_key": cache_key,
                            "audio_checksum": _sha256(output),
                            "migrated_from_manifest": True,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            if not cached:
                with REFERENCE_AUDIO.open("rb") as prompt:
                    response = client.post(
                        TTS_URL,
                        files={"prompt_audio": (REFERENCE_AUDIO.name, prompt, "audio/wav")},
                        data={"text": text, **TTS_PARAMETERS},
                    )
                response.raise_for_status()
                output.write_bytes(response.content)
                cache_metadata.write_text(
                    json.dumps(
                        {"cache_key": cache_key, "audio_checksum": _sha256(output)},
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            actual_duration = _duration(output)
            if actual_duration > slot_duration + 0.6:
                raise RuntimeError(
                    f"narration {index} is {actual_duration:.3f}s for {slot_duration:.3f}s slot"
                )
            results.append(
                {
                    "index": index,
                    "text": text,
                    "path": str(output.resolve()),
                    "timeline_start_seconds": timeline_start,
                    "duration_seconds": round(actual_duration, 3),
                    "slot_duration_seconds": slot_duration,
                    "checksum": _sha256(output),
                    "cache_key": cache_key,
                    "cache_hit": cached,
                }
            )
    return results


def _apply_anchor_plan(lines: list[dict[str, object]]) -> list[dict[str, object]]:
    global ANCHOR_PLAN_MANIFEST
    if ANCHOR_CONFIG is None:
        return lines
    visual_events = cast(list[dict[str, object]], ANCHOR_CONFIG["visual_events"])
    narration_anchors = cast(list[dict[str, object]], ANCHOR_CONFIG["narration_anchors"])
    events = tuple(
        VisualEventAnchor(
            event_id=str(item["event_id"]),
            timeline_range=TimeRange(
                start=_time(_as_float(item["timeline_start_seconds"])),
                duration=_time(_as_float(item["duration_seconds"])),
            ),
            evidence_refs=(
                UUID(str(item["evidence_ref"]))
                if item.get("evidence_ref")
                else uuid5(NAMESPACE_URL, f"visual-event:{item['event_id']}"),
            ),
            protects_original_sound=bool(item.get("protects_original_sound", False)),
        )
        for item in visual_events
    )
    requests = tuple(
        NarrationAnchorRequest(
            line_id=uuid5(NAMESPACE_URL, f"narration:{index}:{line['text']}"),
            required_event_ids=tuple(
                str(value) for value in _as_list(config["required_event_ids"])
            ),
            measured_duration=_time(_as_float(line["duration_seconds"])),
            preferred_delay=_time(_as_float(config.get("preferred_delay_seconds", 0.2))),
            post_roll=_time(_as_float(config.get("post_roll_seconds", 2.0))),
            manual_start=(
                _time(_as_float(config["manual_start_seconds"]))
                if config.get("manual_start_seconds") is not None
                else None
            ),
            manual_override_reason=(
                str(config["manual_override_reason"])
                if config.get("manual_override_reason")
                else None
            ),
        )
        for index, (line, config) in enumerate(zip(lines, narration_anchors, strict=True), 1)
    )
    plan = plan_narration_anchors(
        requests=requests,
        events=events,
        timeline_duration=_time(sum(duration for _, duration in SEGMENTS)),
    )
    ANCHOR_PLAN_MANIFEST = {
        "decisions": [
            {
                "line_id": str(decision.line_id),
                "timeline_start_seconds": float(decision.timeline_range.start.seconds),
                "duration_seconds": float(decision.timeline_range.duration.seconds),
                "earliest_allowed_start_seconds": float(decision.earliest_allowed_start.seconds),
                "preferred_start_seconds": float(decision.preferred_start.seconds),
                "latest_end_seconds": float(decision.latest_end.seconds),
                "required_event_ids": list(decision.required_event_ids),
                "source": decision.source.value,
                "override_reason": decision.override_reason,
            }
            for decision in plan.decisions
        ],
        "findings": [
            {
                "line_id": str(finding.line_id),
                "code": finding.code,
                "explanation": finding.explanation,
                "blocker": finding.blocker,
            }
            for finding in plan.findings
        ],
    }
    if plan.blocked:
        codes = ", ".join(finding.code for finding in plan.findings if finding.blocker)
        raise RuntimeError(f"narration anchor plan blocked: {codes}")
    by_line = {str(decision.line_id): decision for decision in plan.decisions}
    scheduled: list[dict[str, object]] = []
    for index, line in enumerate(lines, 1):
        line_id = str(uuid5(NAMESPACE_URL, f"narration:{index}:{line['text']}"))
        decision = by_line[line_id]
        scheduled.append(
            {
                **line,
                "line_id": line_id,
                "timeline_start_seconds": float(decision.timeline_range.start.seconds),
                "slot_duration_seconds": float(
                    decision.latest_end.seconds - decision.timeline_range.start.seconds
                ),
                "anchor_source": decision.source.value,
                "required_event_ids": list(decision.required_event_ids),
            }
        )
    return scheduled


def _time(seconds: float) -> RationalTime:
    return RationalTime(value=round(seconds * 1_000_000), rate_num=1_000_000)


def _as_float(value: object) -> float:
    if not isinstance(value, int | float | str):
        raise ValueError(f"expected numeric value, got {type(value).__name__}")
    return float(value)


def _as_list(value: object) -> list[object]:
    if not isinstance(value, list):
        raise ValueError("expected a list")
    return value


def _provenance_manifest(output: Path) -> dict[str, object]:
    raw = PROVENANCE_CONFIG or {}
    task_type = TaskType(str(raw.get("task_type", TaskType.DRAMA_PRODUCTION.value)))
    active_role = AgentRole(str(raw.get("active_role", AgentRole.DRAMA_PRODUCER.value)))
    auxiliary_roles = tuple(
        AgentRole(str(value)) for value in _as_list(raw.get("auxiliary_roles", []))
    )
    decisions = tuple(
        DecisionRecord(
            decision_id=str(item["decision_id"]),
            description=str(item["description"]),
            actor_role=AgentRole(str(item.get("actor_role", active_role.value))),
            rationale=str(item["rationale"]),
            manual_override=bool(item.get("manual_override", False)),
        )
        for item in cast(list[dict[str, object]], raw.get("director_decisions", []))
    )
    record = ProductionRunProvenance(
        task_type=task_type,
        active_role=active_role,
        auxiliary_roles=auxiliary_roles,
        director_decisions=decisions,
        tool_generated_outputs=(
            str(output.resolve()),
            str((OUTPUT_DIR / "candidate.ass").resolve()),
        ),
        human_corrections=tuple(str(value) for value in _as_list(raw.get("human_corrections", []))),
        release_gate_status=str(raw.get("release_gate_status", "not_requested")),
    )
    return record.to_dict()


def _write_ass(lines: list[dict[str, object]]) -> Path:
    events = []
    total_duration = sum(duration for _, duration in SEGMENTS)
    for line in lines:
        start = float(cast(float, line["timeline_start_seconds"]))
        audio_duration = float(cast(float, line["duration_seconds"]))
        end = min(total_duration, start + audio_duration + 0.15)
        text = str(line["text"])
        phrases = [part for part in re.split(r"(?<=[，。！？；])", text) if part]
        total_characters = sum(len(phrase) for phrase in phrases)
        cursor = start
        for phrase_index, phrase in enumerate(phrases):
            phrase_duration = (end - start) * len(phrase) / total_characters
            phrase_end = end if phrase_index == len(phrases) - 1 else cursor + phrase_duration
            wrapped = r"\N".join(
                phrase[offset : offset + 12] for offset in range(0, len(phrase), 12)
            )
            events.append(
                f"Dialogue: 0,{_timestamp(cursor)},{_timestamp(phrase_end)},"
                f"Default,,0,0,100,,{wrapped}"
            )
            cursor = phrase_end
    ass = OUTPUT_DIR / "candidate.ass"
    ass.write_text(
        "\n".join(
            [
                "[Script Info]",
                "ScriptType: v4.00+",
                "PlayResX: 720",
                "PlayResY: 1280",
                "",
                "[V4+ Styles]",
                "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,"
                "OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,"
                "ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,"
                "MarginR,MarginV,Encoding",
                "Style: Default,Heiti SC,48,&H00FFFFFF,&H000000FF,&H00000000,"
                "&H80000000,0,0,0,0,100,100,0,0,1,3,1,2,40,40,100,1",
                "",
                "[Events]",
                "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
                *events,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return ass


def _stage_segments() -> tuple[Path, ...]:
    staged: list[Path] = []
    for index, (source, (start, duration)) in enumerate(
        zip(SEGMENT_SOURCES, SEGMENTS, strict=True), 1
    ):
        output = OUTPUT_DIR / f"source_segment_{index:02d}.mp4"
        if not output.is_file():
            subprocess.run(  # nosec B603 B607
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-ss",
                    f"{start:.3f}",
                    "-t",
                    f"{duration:.3f}",
                    "-i",
                    str(source.resolve()),
                    "-vf",
                    "scale=720:1280:force_original_aspect_ratio=decrease,"
                    "pad=720:1280:(ow-iw)/2:(oh-ih)/2,setsar=1",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-c:a",
                    "aac",
                    str(output.resolve()),
                ],
                check=True,
            )
        staged.append(output)
    return tuple(staged)


def _render(lines: list[dict[str, object]], ass: Path) -> Path:
    output = OUTPUT_DIR / OUTPUT_FILENAME
    staged_sources = _stage_segments()
    command: list[str] = [str(Path("scripts/ffmpeg_libass_docker.sh").resolve()), "-y"]
    for source in staged_sources:
        command += ["-i", str(source.resolve())]
    for line in lines:
        command += ["-i", str(line["path"])]

    filters: list[str] = []
    for index, (_, duration) in enumerate(SEGMENTS):
        filters.append(f"[{index}:v]trim=0:{duration:.3f},setpts=PTS-STARTPTS[v{index}]")
        filters.append(f"[{index}:a]atrim=0:{duration:.3f},asetpts=PTS-STARTPTS[a{index}]")
    filters.append(
        "".join(f"[v{i}]" for i in range(len(SEGMENTS))) + f"concat=n={len(SEGMENTS)}:v=1:a=0[vcat]"
    )
    filters.append(
        "".join(f"[a{i}]" for i in range(len(SEGMENTS)))
        + f"concat=n={len(SEGMENTS)}:v=0:a=1[original]"
    )
    narration_labels: list[str] = []
    for offset, line in enumerate(lines, len(SEGMENTS)):
        delay_ms = round(float(cast(float, line["timeline_start_seconds"])) * 1000)
        label = f"n{offset}"
        filters.append(f"[{offset}:a]adelay={delay_ms}:all=1,volume=1.0[{label}]")
        narration_labels.append(f"[{label}]")
    filters.append(
        "[original]volume=0.30[original_low];[original_low]"
        + "".join(narration_labels)
        + f"amix=inputs={len(lines) + 1}:duration=longest:normalize=0,"
        "alimiter=limit=0.95[mix]"
    )
    filters.append(f"[vcat]subtitles={ass.resolve()}[vout]")
    command += [
        "-filter_complex",
        ";".join(filters),
        "-map",
        "[vout]",
        "-map",
        "[mix]",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-t",
        f"{sum(duration for _, duration in SEGMENTS):.3f}",
        str(output.resolve()),
    ]
    subprocess.run(command, check=True)  # nosec B603
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--personal-config", type=Path)
    args = parser.parse_args()
    if args.personal_config is not None:
        _configure_from_personal_config(args.personal_config.resolve())
    missing_sources = sorted({source for source in SEGMENT_SOURCES if not source.is_file()})
    if missing_sources:
        raise FileNotFoundError(", ".join(str(source) for source in missing_sources))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    lines = _apply_anchor_plan(_synthesize())
    ass = _write_ass(lines)
    output = _render(lines, ass)
    manifest = {
        "source": str(SOURCE.resolve()),
        "sources": sorted({str(source.resolve()) for source in SEGMENT_SOURCES}),
        "rights": "internal-only; no-public-release",
        "gate_1": "approved",
        "gate_2": "approved",
        "segments": [
            {
                "source_path": str(source.resolve()),
                "source_start_seconds": start,
                "duration_seconds": duration,
            }
            for source, (start, duration) in zip(SEGMENT_SOURCES, SEGMENTS, strict=True)
        ],
        "narration_lines": lines,
        "narration_anchor_plan": ANCHOR_PLAN_MANIFEST,
        "run_provenance": _provenance_manifest(output),
        "ass": str(ass.resolve()),
        "output": str(output.resolve()),
        "output_checksum": _sha256(output),
    }
    (OUTPUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
