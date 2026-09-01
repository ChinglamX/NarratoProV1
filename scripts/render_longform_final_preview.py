#!/usr/bin/env python3
"""Conform narration/subtitles into the canonical timeline and render a final preview."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess  # nosec B404
import wave
from array import array
from pathlib import Path
from typing import Any
from uuid import UUID

from packages.contracts import (
    ArtifactRef,
    MasterTimeline,
    RationalTime,
    TimelineItem,
    TimelineTrack,
    TimeRange,
)
from packages.contracts.media_production import SubtitleCue, SubtitleCueSet
from packages.contracts.timeline import TimelineItemType, TimelineLifecycle, TimelineTrackKind
from packages.production.ass_renderer import SubtitleStyle, render_ass_content
from packages.production.technical_qc import technical_qc

FFMPEG_FULL = Path("/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg")
FFMPEG = str(FFMPEG_FULL) if FFMPEG_FULL.is_file() else "ffmpeg"
FFPROBE_FULL = Path("/opt/homebrew/opt/ffmpeg-full/bin/ffprobe")
FFPROBE = str(FFPROBE_FULL) if FFPROBE_FULL.is_file() else "ffprobe"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-preview", type=Path, required=True)
    parser.add_argument("--source-timeline", type=Path, required=True)
    parser.add_argument("--narration-manifest", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--output-name", default="longform_final_preview.mp4")
    return parser.parse_args()


def _uuid(key: str) -> UUID:
    raw = bytearray(hashlib.sha256(key.encode()).digest()[:16])
    raw[6] = (raw[6] & 0x0F) | 0x40
    raw[8] = (raw[8] & 0x3F) | 0x80
    return UUID(bytes=bytes(raw))


def _ref(kind: str, key: str) -> ArtifactRef:
    return ArtifactRef.model_validate(
        {"artifact_id": _uuid(key), "version": 1, "artifact_type": kind}
    )


def _time(seconds: float) -> RationalTime:
    return RationalTime(value=round(seconds * 1_000_000), rate_num=1_000_000)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _duration(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / handle.getframerate()


def _window_correlation(
    first_path: Path, second_path: Path, *, start_seconds: float, duration_seconds: float
) -> float:
    samples: list[array[int]] = []
    for path in (first_path, second_path):
        with wave.open(str(path), "rb") as handle:
            if handle.getsampwidth() != 2 or handle.getnchannels() != 2:
                raise ValueError("narration mix QC requires stereo PCM16 WAV inputs")
            handle.setpos(round(start_seconds * handle.getframerate()))
            raw = handle.readframes(round(duration_seconds * handle.getframerate()))
            values = array("h")
            values.frombytes(raw)
            samples.append(values)
    first, second = samples
    count = min(len(first), len(second))
    numerator = sum(first[index] * second[index] for index in range(count))
    first_energy = sum(first[index] * first[index] for index in range(count))
    second_energy = sum(second[index] * second[index] for index in range(count))
    denominator = math.sqrt(first_energy * second_energy)
    return numerator / denominator if denominator else 0.0


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True)  # nosec B603


def _loudness(path: Path) -> tuple[float, float]:
    result = subprocess.run(  # nosec B603
        [
            FFMPEG,
            "-hide_banner",
            "-i",
            str(path),
            "-filter_complex",
            "ebur128=peak=true",
            "-f",
            "null",
            "-",  # nosec B607
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    values = [float(value) for value in re.findall(r"I:\s*(-?[\d.]+)\s*LUFS", result.stderr)]
    peaks = [float(value) for value in re.findall(r"Peak:\s*(-?[\d.]+)\s*dBFS", result.stderr)]
    return values[-1], peaks[-1]


def _probe(path: Path) -> dict[str, Any]:
    result = subprocess.run(  # nosec B603
        [FFPROBE, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    payload: dict[str, Any] = json.loads(result.stdout)
    return payload


def main() -> None:
    args = _parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(args.narration_manifest.read_text(encoding="utf-8"))
    anchors = json.loads(args.anchors.read_text(encoding="utf-8"))
    if anchors["blocked"]:
        raise ValueError("narration anchors are blocked")
    line_by_id = {str(line["line_id"]): line for line in manifest["lines"]}
    anchor_by_id = {str(item["line_id"]): item for item in anchors["decisions"]}
    if line_by_id.keys() != anchor_by_id.keys():
        raise ValueError("narration manifest and anchor decisions do not match")

    aligned = args.output_dir / "narration_aligned.wav"
    inputs: list[str] = []
    filters: list[str] = []
    labels: list[str] = []
    ordered = sorted(anchor_by_id.values(), key=lambda item: float(item["start_seconds"]))
    for index, anchor in enumerate(ordered):
        line = line_by_id[str(anchor["line_id"])]
        wav_path = Path(str(line["wav_path"]))
        inputs.extend(["-i", str(wav_path)])
        delay_ms = round(float(anchor["start_seconds"]) * 1000)
        filters.append(f"[{index}:a]aresample=48000,adelay={delay_ms}:all=1[n{index}]")
        labels.append(f"[n{index}]")
    filters.append(
        f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest:normalize=0,"
        "apad=whole_dur=240[narration]"
    )
    _run(
        [
            FFMPEG,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            *inputs,
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[narration]",
            "-t",
            "240",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(aligned),
        ]
    )

    alignment_ref = _ref("AlignmentArtifact", "longform:shanshen:alignment:v1")
    style_ref = _ref("ConfigArtifact", "longform:subtitle-style:v1")
    cues = tuple(
        SubtitleCue(
            cue_id=_uuid(f"subtitle:{anchor['line_id']}"),
            line_id=_uuid(f"narration:{anchor['line_id']}"),
            timeline_range=TimeRange(
                start=_time(float(anchor["start_seconds"])),
                duration=_time(float(anchor["duration_seconds"])),
            ),
            text=str(line_by_id[str(anchor["line_id"])]["text"]),
            style_ref="longform-narration-v1",
            safe_area={"x": 0.08, "y": 0.77, "width": 0.84, "height": 0.14},
        )
        for anchor in ordered
    )
    cue_set = SubtitleCueSet(
        alignment_ref=alignment_ref,
        cues=cues,
        style_profile_ref=style_ref,
    )
    ass_path = args.output_dir / "narration.ass"
    ass_path.write_text(
        render_ass_content(
            cue_set,
            style=SubtitleStyle(
                font_name="Heiti SC",
                font_size=43,
                bold=True,
                outline=4,
                max_chars_per_line=14,
            ),
        ),
        encoding="utf-8",
    )

    source_timeline = MasterTimeline.model_validate_json(
        args.source_timeline.read_text(encoding="utf-8")
    )
    narration_items: list[TimelineItem] = []
    subtitle_items: list[TimelineItem] = []
    for anchor, cue in zip(ordered, cues, strict=True):
        line = line_by_id[str(anchor["line_id"])]
        wav = Path(str(line["wav_path"]))
        wav_ref = _ref("VoiceAsset", f"voice:{line['wav_sha256']}")
        timeline_range = cue.timeline_range
        narration_items.append(
            TimelineItem(
                item_id=_uuid(f"timeline:narration:{anchor['line_id']}"),
                item_version=1,
                item_type=TimelineItemType.CLIP,
                timeline_range=timeline_range,
                source_ref=wav_ref,
                source_range=TimeRange(start=_time(0), duration=_time(_duration(wav))),
                parameters={
                    "text": line["text"],
                    "line_id": anchor["line_id"],
                    "intent_state": "measured-and-conformed",
                    "gain_db": 0.0,
                },
                evidence_refs=tuple(_uuid(f"story:{event}") for event in line["event_refs"]),
                generation_dependencies=(alignment_ref,),
                locked=True,
            )
        )
        subtitle_items.append(
            TimelineItem(
                item_id=_uuid(f"timeline:subtitle:{anchor['line_id']}"),
                item_version=1,
                item_type=TimelineItemType.TEXT,
                timeline_range=timeline_range,
                content_ref=str(anchor["line_id"]),
                parameters={
                    "text": line["text"],
                    "style_ref": "longform-narration-v1",
                    "intent_state": "rendered-ass",
                },
                evidence_refs=tuple(_uuid(f"story:{event}") for event in line["event_refs"]),
                generation_dependencies=(alignment_ref, style_ref),
                locked=True,
            )
        )
    conformed = source_timeline.model_copy(
        update={
            "lifecycle": TimelineLifecycle.CONFORMED,
            "tracks": (
                *source_timeline.tracks,
                TimelineTrack(
                    track_id=_uuid("track:longform:narration"),
                    kind=TimelineTrackKind.NARRATION,
                    order=2,
                    items=tuple(narration_items),
                ),
                TimelineTrack(
                    track_id=_uuid("track:longform:subtitle"),
                    kind=TimelineTrackKind.SUBTITLE,
                    order=5,
                    items=tuple(subtitle_items),
                ),
            ),
            "dependencies": (*source_timeline.dependencies, alignment_ref, style_ref),
            "metadata_namespace_version": "longform-v1",
        }
    )
    # Revalidate after model_copy because pydantic intentionally skips validators there.
    conformed = MasterTimeline.model_validate(conformed.model_dump(mode="json"))
    (args.output_dir / "master_timeline_conformed.json").write_text(
        conformed.model_dump_json(indent=2), encoding="utf-8"
    )

    mixed = args.output_dir / "mixed_audio.wav"
    _run(
        [
            FFMPEG,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(args.source_preview),
            "-i",
            str(aligned),
            "-filter_complex",
            "[0:a]aresample=48000[original];"
            "[1:a]aresample=48000,asplit=2[narr_sidechain][narr_mix];"
            "[original][narr_sidechain]"
            "sidechaincompress=threshold=0.018:ratio=8:attack=20:release=320[ducked];"
            "[ducked][narr_mix]amix=inputs=2:duration=first:normalize=0,"
            "loudnorm=I=-14:TP=-1.5:LRA=7,aresample=48000,"
            "asetpts=PTS-STARTPTS[mix]",
            "-map",
            "[mix]",
            "-t",
            "240",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(mixed),
        ]
    )
    padded_mix = args.output_dir / "mixed_audio_padded.wav"
    _run(
        [
            FFMPEG,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(mixed),
            "-af",
            "apad",
            "-t",
            "240",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(padded_mix),
        ]
    )
    padded_mix.replace(mixed)
    output_video = args.output_dir / args.output_name
    subtitle_filter = f"subtitles=filename='{ass_path}'"
    _run(
        [
            FFMPEG,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(args.source_preview),
            "-i",
            str(mixed),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-vf",
            subtitle_filter,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-t",
            "240",
            "-movflags",
            "+faststart",
            str(output_video),
        ]
    )

    probe = _probe(output_video)
    video = next(item for item in probe["streams"] if item["codec_type"] == "video")
    audio = next(item for item in probe["streams"] if item["codec_type"] == "audio")
    raw_duration = float(probe["format"]["duration"])
    video_duration = float(video["duration"])
    audio_duration = float(audio["duration"])
    av_sync_compliant = (
        abs(video_duration - 240.0) <= 1 / 25
        and abs(audio_duration - 240.0) <= 1 / 25
        and abs(video_duration - audio_duration) <= 1 / 25
    )
    lufs, peak = _loudness(mixed)
    narration_correlations = [
        _window_correlation(
            aligned,
            mixed,
            start_seconds=float(item["start_seconds"]),
            duration_seconds=float(item["duration_seconds"]),
        )
        for item in ordered
    ]
    minimum_narration_correlation = min(narration_correlations)
    measured: dict[str, int | float | str] = {
        "width": int(video["width"]),
        "height": int(video["height"]),
        "video_codec": str(video["codec_name"]),
        "audio_codec": str(audio["codec_name"]),
        "audio_sample_rate": int(audio["sample_rate"]),
        "duration_class": "3-5min" if 180 <= raw_duration <= 300 else "outside-3-5min",
        "loudness_compliant": str(-16.0 <= lufs <= -12.0).lower(),
        "true_peak_compliant": str(peak <= -1.0).lower(),
        "av_sync_compliant": str(av_sync_compliant).lower(),
        "narration_mix_compliant": str(minimum_narration_correlation >= 0.15).lower(),
    }
    required: dict[str, int | float | str] = {
        "width": 720,
        "height": 1280,
        "video_codec": "h264",
        "audio_codec": "aac",
        "audio_sample_rate": 48000,
        "duration_class": "3-5min",
        "loudness_compliant": "true",
        "true_peak_compliant": "true",
        "av_sync_compliant": "true",
        "narration_mix_compliant": "true",
    }
    candidate_ref = _ref("FinalCandidate", f"final:{_sha256(output_video)}")
    qc = technical_qc(
        candidate_ref=candidate_ref,
        profile_ref=_ref("ConfigArtifact", "internal-vertical-720x1280-v1"),
        measured=measured,
        required=required,
    )
    report = {
        "release_boundary": "internal-preview-only",
        "release_gate": "not_requested-human-release-required",
        "output_path": str(output_video.resolve()),
        "output_sha256": _sha256(output_video),
        "measured": measured,
        "duration_seconds": raw_duration,
        "integrated_loudness_lufs": lufs,
        "true_peak_dbtp": peak,
        "minimum_narration_mix_correlation": minimum_narration_correlation,
        "narration_mix_correlations": narration_correlations,
        "technical_qc": qc.model_dump(mode="json"),
        "narration_line_count": len(ordered),
        "narration_duration_seconds": sum(float(item["duration_seconds"]) for item in ordered),
        "canonical_timeline": str((args.output_dir / "master_timeline_conformed.json").resolve()),
        "subtitle_ass": str(ass_path.resolve()),
    }
    (args.output_dir / "render_and_qc_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
