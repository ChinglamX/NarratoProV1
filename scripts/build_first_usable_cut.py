"""Build the product-control First Usable Cut from the approved E09 preview.

This is an inspectable product proof, not an E11 qualification shortcut.  It
generates one WAV per narration line, places each line at the approved beat
start, ducks the existing preview audio, and muxes the mixed audio with the
already-rendered E09 video/subtitle preview.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess  # nosec B404
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from packages.contracts import ArtifactRef, ProviderCapability, ProviderInvocationRequest
from packages.providers.speech.indextts import IndexTTSProvider

LINES = (
    (0.0, "少年被困山林，却在绝境中唤醒了山神印。"),  # noqa: RUF001
    (3.5, "所有人只看见他的狼狈，没人知道群山正在回应他。"),  # noqa: RUF001
    (8.0, "初入宗门，他因这股陌生力量被视作异类。"),  # noqa: RUF001
    (13.583333, "直到血脉显现，望守山人的传承终于重见天日。"),  # noqa: RUF001
    (18.2, "宗门大比将至，这份力量也引来了觊觎。"),  # noqa: RUF001
    (22.3, "他越接近真相，暗处的杀机就逼得越紧。"),  # noqa: RUF001
    (26.208333, "而爷爷留下的笔记，将指向他必须面对的宿命。"),  # noqa: RUF001
)


def _config_ref() -> ArtifactRef:
    return ArtifactRef.model_validate(
        {
            "artifact_id": "00000000-0000-4000-8000-000000000058",
            "version": 1,
            "artifact_type": "ConfigArtifact",
        }
    )


def _duration(path: Path) -> float:
    result = subprocess.run(  # nosec B603 B607
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def _synthesize(output_dir: Path) -> list[dict[str, object]]:
    provider = IndexTTSProvider()
    reference = _config_ref()
    results: list[dict[str, object]] = []
    for index, (start, text) in enumerate(LINES, 1):
        path = output_dir / f"narration_{index:02d}.wav"
        if path.is_file() and path.stat().st_size > 44:
            payload = path.read_bytes()
        else:
            if not provider.health():
                raise RuntimeError("IndexTTS is not healthy and narration audio is missing")
            text_key = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
            request = ProviderInvocationRequest(
                capability=ProviderCapability.TTS,
                inputs=(reference,),
                config_ref=reference,
                resource_profile_ref=reference,
                idempotency_key=f"first-cut-line-{index}-{text_key}",
                timeout_ms=600_000,
                parameters={"text": text},
            )
            raw = provider.infer(request)
            payload = raw.payload
            path.write_bytes(payload)
        results.append(
            {
                "line": index,
                "text": text,
                "timeline_start_seconds": start,
                "actual_duration_seconds": round(_duration(path), 3),
                "path": str(path.resolve()),
                "checksum": "sha256:" + hashlib.sha256(payload).hexdigest(),
            }
        )
    return results


def _caption_images(output_dir: Path) -> list[Path]:
    font = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 40)
    paths = []
    for index, (_start, text) in enumerate(LINES, 1):
        image = Image.new("RGBA", (720, 1280), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        rows: list[str] = []
        current = ""
        for character in text:
            candidate = current + character
            if current and draw.textlength(candidate, font=font) > 620:
                rows.append(current)
                current = character
            else:
                current = candidate
        if current:
            rows.append(current)
        caption = "\n".join(rows)
        bbox = draw.multiline_textbbox(
            (0, 0), caption, font=font, spacing=8, align="center", stroke_width=2
        )
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        x = max(28, (720 - width) // 2)
        y = 1010
        draw.rounded_rectangle(
            (x - 18, y - 12, x + width + 18, y + height + 14),
            radius=12,
            fill=(0, 0, 0, 155),
        )
        draw.multiline_text(
            (x, y),
            caption,
            font=font,
            fill=(255, 242, 185, 255),
            spacing=8,
            align="center",
            stroke_width=2,
            stroke_fill=(0, 0, 0, 255),
        )
        path = output_dir / f"caption_{index:02d}.png"
        image.save(path)
        paths.append(path)
    return paths


def _ass_timestamp(seconds: float) -> str:
    centiseconds = round(seconds * 100)
    hours, remainder = divmod(centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    whole_seconds, fraction = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{fraction:02d}"


def _write_ass(path: Path, duration: float) -> None:
    events = []
    for index, (start, text) in enumerate(LINES):
        end = LINES[index + 1][0] if index + 1 < len(LINES) else duration
        events.append(
            f"Dialogue: 0,{_ass_timestamp(start)},{_ass_timestamp(end)},Default,,0,0,0,,{text}"
        )
    path.write_text(
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
                "Style: Default,Heiti SC,40,&H00B9F2FF,&H000000FF,&H00000000,"
                "&H80000000,0,0,0,0,100,100,0,0,3,2,0,2,40,40,102,1",
                "",
                "[Events]",
                "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
                *events,
                "",
            ]
        ),
        encoding="utf-8",
    )


def _mix(preview: Path, lines: list[dict[str, object]], output: Path) -> None:
    command = ["ffmpeg", "-y", "-i", str(preview)]
    for line in lines:
        command.extend(["-i", str(line["path"])])
    captions = _caption_images(output.parent)
    for caption in captions:
        command.extend(["-loop", "1", "-i", str(caption)])
    filters = ["[0:a]volume=0.32[original]"]
    narration_labels = []
    for index, line in enumerate(lines, 1):
        delay_ms = round(float(line["timeline_start_seconds"]) * 1000)
        label = f"n{index}"
        filters.append(f"[{index}:a]adelay={delay_ms}:all=1,volume=1.0[{label}]")
        narration_labels.append(f"[{label}]")
    filters.append(
        "[original]"
        + "".join(narration_labels)
        + f"amix=inputs={len(lines) + 1}:duration=longest:normalize=0,"
        "alimiter=limit=0.95[mix]"
    )
    beat_ends = [
        LINES[index + 1][0] if index + 1 < len(LINES) else 30.25 for index in range(len(LINES))
    ]
    video_label = "0:v"
    for index, ((start, _text), end) in enumerate(zip(LINES, beat_ends, strict=True), 1):
        output_label = f"v{index}"
        caption_index = len(lines) + index
        filters.append(
            f"[{video_label}][{caption_index}:v]overlay=0:0:"
            f"enable='between(t,{start:.6f},{end:.6f})'[{output_label}]"
        )
        video_label = output_label
    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            f"[{video_label}]",
            "-map",
            "[mix]",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-t",
            f"{_duration(preview):.6f}",
            str(output),
        ]
    )
    subprocess.run(command, check=True)  # nosec B603


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", type=Path, required=True)
    parser.add_argument("--ass", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/first_usable_cut"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    lines = _synthesize(args.output_dir)
    copied_ass = args.output_dir / "first_usable_cut.ass"
    _write_ass(copied_ass, _duration(args.preview))
    output = args.output_dir / "first_usable_cut.mp4"
    _mix(args.preview, lines, output)
    manifest = {
        "status": "product_proof_pending_human_review",
        "source_preview": str(args.preview.resolve()),
        "source_preview_ass": str(args.ass.resolve()),
        "subtitle_source": str(copied_ass.resolve()),
        "subtitle_note": (
            "narration ASS regenerated from the current lines; captions rendered as "
            "deterministic PNG overlays; "
            "source subtitles remain inherited from E09 preview"
        ),
        "narration_lines": lines,
        "mix": {"original_gain": 0.32, "narration_gain": 1.0, "limiter": 0.95},
        "output": str(output.resolve()),
        "duration_seconds": round(_duration(output), 3),
        "checksum": "sha256:" + hashlib.sha256(output.read_bytes()).hexdigest(),
        "limitations": [
            "product proof uses the E09 preview's already-rendered subtitles",
            "no BGM or SFX",
            "not an E11 production qualification artifact",
        ],
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
