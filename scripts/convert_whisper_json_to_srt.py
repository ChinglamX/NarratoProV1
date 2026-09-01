#!/usr/bin/env python3
"""Convert whisper.cpp full JSON outputs into episode-numbered SRT files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    sources = sorted(
        args.input_dir.glob("*.wav.json"),
        key=lambda path: int(path.name.split(".", 1)[0]),
    )
    if not sources:
        raise ValueError("no whisper.cpp *.wav.json files found")
    for source in sources:
        episode = int(source.name.split(".", 1)[0])
        payload = json.loads(source.read_text(encoding="utf-8"))
        segments: list[dict[str, Any]] = payload["transcription"]
        blocks = []
        for index, segment in enumerate(segments, 1):
            timestamps = segment["timestamps"]
            blocks.append(
                f"{index}\n{timestamps['from']} --> {timestamps['to']}\n"
                f"{str(segment['text']).strip()}"
            )
        target = args.output_dir / f"episode_{episode:02d}.srt"
        target.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    print(f"converted {len(sources)} transcripts to {args.output_dir}")


if __name__ == "__main__":
    main()
