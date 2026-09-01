#!/usr/bin/env python3
"""Bind event cues to hashed episode media and produce visual review samples."""

from __future__ import annotations

import argparse
import json
import subprocess  # nosec B404 - fixed ffmpeg argv without a shell
from pathlib import Path
from typing import Any

from packages.longform.transcript_localization import localize_cue, parse_srt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--transcript-dir", type=Path, required=True)
    parser.add_argument("--cue-spec", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    cue_spec = json.loads(args.cue_spec.read_text(encoding="utf-8"))
    by_episode = {
        int(Path(item["relative_path"]).stem): item
        for item in inventory["files"]
        if Path(item["relative_path"]).stem.isdigit()
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frame_dir = args.output_dir / "review_frames"
    frame_dir.mkdir(exist_ok=True)
    events: list[dict[str, Any]] = []
    for spec in cue_spec["events"]:
        episode = int(spec["episode"])
        media = by_episode.get(episode)
        if media is None:
            raise ValueError(f"inventory has no numeric episode {episode}")
        transcript_path = args.transcript_dir / f"episode_{episode:02d}.srt"
        if not transcript_path.is_file():
            raise ValueError(f"transcript missing: {transcript_path}")
        localized = localize_cue(
            parse_srt(transcript_path.read_text(encoding="utf-8")), str(spec["cue"])
        )
        samples = []
        for label, timestamp in (
            ("start", localized.start_seconds),
            ("middle", (localized.start_seconds + localized.end_seconds) / 2),
            ("end", max(localized.start_seconds, localized.end_seconds - 0.1)),
        ):
            output = frame_dir / f"{spec['event_id']}-{label}.jpg"
            _extract_frame(Path(media["path"]), timestamp, output)
            samples.append({"time_seconds": round(timestamp, 3), "path": str(output)})
        events.append(
            {
                **{key: value for key, value in spec.items() if key != "cue"},
                "source_path": media["path"],
                "source_sha256": media["sha256"],
                "dialogue_evidence": {
                    "start_seconds": round(localized.start_seconds, 3),
                    "end_seconds": round(localized.end_seconds, 3),
                    "excerpt": localized.excerpt,
                    "precision": localized.precision,
                    "final_cut_boundary_allowed": False,
                },
                "visual_review_samples": samples,
                "visual_status": "pending_review",
            }
        )
    result = {
        "series_id": cue_spec["series_id"],
        "rights_status": inventory["rights_status"],
        "method": "literal ASR cue + coarse interpolation; start/middle/end frame review",
        "limitations": [
            "coarse_interpolated ranges are sampling windows, not final cut boundaries",
            "visual facts remain pending until the review frames are checked",
            "ASR text may contain recognition errors and cannot establish identity alone",
        ],
        "events": events,
    }
    output = args.output_dir / "evidence_pack.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"evidence pack: {len(events)} events / {len(events) * 3} review frames")
    print(f"output: {output.resolve()}")
    return 0


def _extract_frame(source: Path, timestamp: float, output: Path) -> None:
    subprocess.run(  # nosec B603 B607 - fixed ffmpeg argv, no shell execution
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(output),
        ],
        check=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
