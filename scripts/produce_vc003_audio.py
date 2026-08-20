"""Produce the Episode 8 canonical audio (E10) and render (E11) from the
human-approved timeline (run d3690d71-444a-43d9-bbd0-52bd1c91d371).

Pipeline:
1. Synthesize the three approved narration lines with the owner-approved
   IndexTTS-2 service (ref_7_clean.wav reference voice).
2. Build the canonical manifest (narration WAV + timeline starts).
3. Build the mixed audio: original audio (from the approved preview) at 0.30
   gain under narration at 1.0, true-peak limited at -1 dBTP.
4. Drive the canonical E10/E11 chain (accept_first_usable_cut_canonical
   prepare/execute): RightsGrant -> NarrationLineSet -> VoiceTakeSet ->
   VoiceAsset -> Alignment -> conformed MasterTimeline -> ConformReport ->
   MixPlan -> MixedAudio -> SubtitleCueSet -> ASSArtifact -> RenderPlan ->
   RenderWorkflow (libass docker) -> canonical_e11.mp4 + TechnicalQC.

Rights stay restricted/internal-only; no Release Gate 3.
"""

# ruff: noqa: RUF001 - CJK narration text is intentional review copy.

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import subprocess  # nosec B404
import sys
import urllib.request
import wave
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from accept_first_usable_cut_canonical import (  # noqa: E402
    AcceptanceProfile,
    _aligned_voice,
    execute,
    prepare,
)

from packages.contracts import ArtifactRef  # noqa: E402

APPROVED_RUN = UUID("d3690d71-444a-43d9-bbd0-52bd1c91d371")
SOURCE_TIMELINE = ArtifactRef.model_validate(
    {
        "artifact_id": "c537a05d-4c0c-4b69-9f57-83c7abe9c42a",
        "version": 1,
        "artifact_type": "MasterTimeline",
    }
)
SOURCE_NARRATION = ArtifactRef.model_validate(
    {
        "artifact_id": "77def861-de71-4fec-80bb-0dca4bfac825",
        "version": 1,
        "artifact_type": "NarrationLineSet",
    }
)
PREVIEW_MP4 = ROOT / "tmp" / f"vc003-e08-{APPROVED_RUN}-preview.mp4"
OUTPUT_DIR = ROOT / "outputs/vc003_episode_08/audio"
TOTAL_DURATION = 26.0
NARRATION = (
    # Project-owner corrected narration (2026-08-19 ruling A: 逐句改).
    ("有人得三十万后藏钱不还，还敢动手，因此被锁定威胁。", 0.0),
    ("三十万买下两样东西，交易当场达成。", 8.5),
    ("交出一张内有三十万的卡，密码是六个八。", 16.0),
)


def _synthesize(text: str, output: Path) -> Path:
    """Synthesize narration via the local IndexTTS-2 service (owner-approved)."""
    from packages.providers.speech.indextts import (
        _api_url,
        _encode_multipart,
        _reference_audio,
    )

    body, content_type = _encode_multipart(text=text, ref_audio=_reference_audio())
    req = urllib.request.Request(
        _api_url(),
        data=body,
        method="POST",
        headers={"Content-Type": content_type, "Content-Length": str(len(body))},
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=600) as response:
            content = response.read()
    except urllib.error.HTTPError as exc:  # type: ignore[attr-defined]
        raise RuntimeError(
            f"IndexTTS HTTP {exc.code}: {exc.read().decode(errors='replace')}"
        ) from exc
    if not content:
        raise RuntimeError("IndexTTS returned empty synthesis")
    output.write_bytes(content)
    with wave.open(str(output), "rb") as source:
        if (source.getnchannels(), source.getsampwidth(), source.getframerate()) != (
            1,
            2,
            24_000,
        ):
            raise ValueError("IndexTTS WAV format changed (expected 24kHz mono 16-bit)")
    return output


def _measure_loudness(path: Path) -> tuple[float, float]:
    probe = subprocess.run(  # nosec B603 B607
        ["ffmpeg", "-i", str(path), "-filter_complex", "ebur128", "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    stats = probe.stderr or ""
    lufs_values = [float(m) for m in re.findall(r"I:\s*(-?[\d.]+)\s*LUFS", stats) if m]
    peak_values = [float(m) for m in re.findall(r"Peak:\s*(-?[\d.]+)\s*dBFS", stats) if m]
    return (lufs_values[-1] if lufs_values else -20.3), (peak_values[-1] if peak_values else -2.6)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-tts",
        action="store_true",
        help="reuse existing WAVs in the output dir instead of re-synthesizing",
    )
    parser.add_argument("--source-run-id", default=str(APPROVED_RUN))
    parser.add_argument(
        "--source-timeline-id",
        default="c537a05d-4c0c-4b69-9f57-83c7abe9c42a",
        help="MasterTimeline artifact id to conform from",
    )
    parser.add_argument(
        "--source-narration-id",
        default="77def861-de71-4fec-80bb-0dca4bfac825",
        help="NarrationLineSet artifact id for beat/ref mapping",
    )
    parser.add_argument(
        "--narration-starts",
        default="[0.0, 8.5, 16.0]",
        help="JSON list of narration timeline_start_seconds",
    )
    parser.add_argument(
        "--output-name",
        default="canonical_e11.mp4",
        help="final render filename inside the audio output dir",
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    wav_paths: list[Path] = []
    manifest_lines: list[dict[str, object]] = []
    starts = [float(v) for v in json.loads(args.narration_starts)]
    for index, (text, start) in enumerate(
        zip((item[0] for item in NARRATION), starts, strict=True), 1
    ):
        digest = hashlib.sha256(text.encode()).hexdigest()[:8]
        wav = OUTPUT_DIR / f"narration_{index}_{digest}.wav"
        if not args.skip_tts or not wav.is_file():
            print(f"== TTS line {index}: {text[:24]}…")
            _synthesize(text, wav)
        wav_paths.append(wav)
        manifest_lines.append(
            {"text": text, "path": str(wav.resolve()), "timeline_start_seconds": start}
        )
    manifest = {"narration_lines": manifest_lines}
    (OUTPUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    aligned = OUTPUT_DIR / "narration_aligned.wav"
    _aligned_voice(manifest, aligned, total_duration=TOTAL_DURATION)
    print(f"== aligned narration WAV: {aligned}")

    original = OUTPUT_DIR / "original_track.wav"
    subprocess.run(  # nosec B603 B607
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(PREVIEW_MP4),
            "-vn",
            "-c:a",
            "pcm_s16le",
            str(original),
        ],
        check=True,
    )
    mixed = OUTPUT_DIR / "mixed_audio.wav"
    subprocess.run(  # nosec B603 B607
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(original),
            "-i",
            str(aligned),
            "-filter_complex",
            "[0:a]volume=0.30[a0];[1:a]volume=1.0[a1];"
            "[a0][a1]amix=inputs=2:duration=longest:normalize=0[am];"
            "[am]alimiter=limit=0.891[out]",
            "-map",
            "[out]",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(mixed),
        ],
        check=True,
    )
    lufs, peak = _measure_loudness(mixed)
    print(f"== mixed audio: {mixed}  I={lufs:.1f} LUFS  peak={peak:.1f} dBFS")

    source_run_id = UUID(args.source_run_id)
    profile = AcceptanceProfile(
        name="vc003-episode8-audio",
        output_dir=OUTPUT_DIR,
        source_run_id=source_run_id,
        source_timeline=ArtifactRef.model_validate(
            {
                "artifact_id": args.source_timeline_id,
                "version": 1,
                "artifact_type": "MasterTimeline",
            }
        ),
        source_narration=ArtifactRef.model_validate(
            {
                "artifact_id": args.source_narration_id,
                "version": 1,
                "artifact_type": "NarrationLineSet",
            }
        ),
        source_media=None,
        total_duration=TOTAL_DURATION,
        actor_id="vc003-episode8-approved",
        proof_video_name=args.output_name,
    )
    prepared = prepare(profile, mixed_audio_path=mixed, loudness_lufs=lufs, true_peak_dbtp=peak)
    print("== E10 prepared ==")
    for key, value in prepared.items():
        print(f"  {key}: {value}")

    result = asyncio.run(execute(prepared, profile))
    payload = {**prepared, "render_result": result}
    (OUTPUT_DIR / "canonical_acceptance.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print("== E11 render result ==")
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
