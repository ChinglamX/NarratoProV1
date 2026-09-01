#!/usr/bin/env python3
"""Batch-synthesize evidence-approved longform narration with IndexTTS-2.

This is deliberately a thin production adapter: the official IndexTTS-2
runtime remains external to NarratoPro, is loaded once, and every produced WAV
is recorded with measured duration and voice/model provenance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess  # nosec B404
import sys
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / handle.getframerate()


def _git_revision(runtime_dir: Path) -> str | None:
    result = subprocess.run(  # nosec B603 B607
        ["git", "rev-parse", "HEAD"],
        cwd=runtime_dir,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--drafts", type=Path, required=True)
    parser.add_argument("--voice-reference", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    runtime_dir = args.runtime_dir.resolve()
    model_dir = args.model_dir.resolve()
    voice_reference = args.voice_reference.resolve()
    drafts_path = args.drafts.resolve()
    output_dir = args.output_dir.resolve()
    manifest_path = args.manifest.resolve()
    for required in (runtime_dir, model_dir, voice_reference, drafts_path):
        if not required.exists():
            raise FileNotFoundError(required)

    payload = json.loads(drafts_path.read_text(encoding="utf-8"))
    lines: list[dict[str, Any]] = payload["lines"]
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(runtime_dir))
    previous_cwd = Path.cwd()
    os.chdir(runtime_dir)
    try:
        from indextts.infer_v2 import IndexTTS2  # type: ignore[import-not-found]

        engine = IndexTTS2(
            cfg_path=str(model_dir / "config.yaml"),
            model_dir=str(model_dir),
            use_fp16=False,
            use_cuda_kernel=False,
            use_deepspeed=False,
        )
        synthesized: list[dict[str, Any]] = []
        for index, line in enumerate(lines, start=1):
            line_id = str(line["line_id"])
            wav_path = output_dir / f"{index:02d}_{line_id}.wav"
            engine.infer(
                spk_audio_prompt=str(voice_reference),
                text=str(line["text"]),
                output_path=str(wav_path),
                verbose=False,
            )
            synthesized.append(
                {
                    **line,
                    "wav_path": str(wav_path),
                    "wav_sha256": _sha256(wav_path),
                    "measured_duration_seconds": round(_wav_duration(wav_path), 6),
                }
            )
    finally:
        os.chdir(previous_cwd)

    manifest = {
        "schema_version": "1.0",
        "created_at": datetime.now(UTC).isoformat(),
        "release_boundary": "internal-preview-only",
        "engine": "IndexTTS-2 official runtime",
        "runtime_dir": str(runtime_dir),
        "runtime_revision": _git_revision(runtime_dir),
        "model_dir": str(model_dir),
        "model_config_sha256": _sha256(model_dir / "config.yaml"),
        "voice_reference": str(voice_reference),
        "voice_reference_sha256": _sha256(voice_reference),
        "voice_reference_lineage": (
            "Derivative of prior owner-approved IndexTTS narration WAVs; internal preview use only."
        ),
        "drafts_path": str(drafts_path),
        "drafts_sha256": _sha256(drafts_path),
        "lines": synthesized,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(manifest_path)


if __name__ == "__main__":
    main()
