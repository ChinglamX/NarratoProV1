"""Real multi-episode ASR baseline (research speech benchmark).

Runs the NarratoPro FunASR local service (paraformer-large, diarization) over
every persisted AudioStem (excluding the already-benchmarked Episode 8), parses
the timed SRT, and writes a corpus-level speech baseline manifest: per episode
segment count, speech coverage, speaker cluster count, and sample dialogue.
This is research evidence for the Speech benchmark admission track; CER still
needs human reference transcripts (owner decision).
"""

from __future__ import annotations

import json
import re
import secrets
import urllib.error
import urllib.request
from pathlib import Path

from sqlalchemy import text

from packages.foundation.settings import get_settings
from packages.persistence.database import create_database_engine

ROOT = Path(__file__).resolve().parents[1]
FUNASR_URL = "http://127.0.0.1:7860"
OUT_DIR = ROOT / "evaluation/evidence/speech_baseline"
SKIP_EP8 = "17457a87-af78-4e40-9093-3fb20ae28333"

SRT_PATTERN = re.compile(
    r"\d+\s*\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\s*\n(.+?)(?=\n\n|\Z)",
    re.DOTALL,
)


def _seconds(timestamp: str) -> float:
    hours, minutes, tail = timestamp.split(":")
    whole, millis = tail.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(whole) + int(millis) / 1000


def _parse_srt(content: str) -> list[dict[str, object]]:
    segments = []
    for start, end, segment_text in SRT_PATTERN.findall(content.strip()):
        speaker = None
        matched = re.match(
            r"说话人([^:\N{FULLWIDTH COLON}]+)[:\N{FULLWIDTH COLON}]\s*(.*)",
            (segment_text or "").strip(),
            re.DOTALL,
        )
        if matched:
            speaker, segment_text = matched.group(1).strip(), matched.group(2).strip()
        segments.append(
            {
                "start_seconds": _seconds(start),
                "end_seconds": _seconds(end),
                "text": segment_text.strip(),
                "speaker": speaker,
            }
        )
    return segments


def _asr(audio: Path) -> str:
    boundary = f"----narratopro-{secrets.token_hex(16)}"
    body = (
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="enable_spk"\r\n\r\ntrue\r\n'
        ).encode()
        + f'--{boundary}\r\nContent-Disposition: form-data; name="hotword"\r\n\r\n\r\n'.encode()
        + f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="audio.wav"\r\n'
        "Content-Type: audio/wav\r\n\r\n".encode()
        + audio.read_bytes()
        + f"\r\n--{boundary}--\r\n".encode()
    )
    request = urllib.request.Request(  # nosec B310
        f"{FUNASR_URL}/asr",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=900) as response:  # nosec B310
            payload = json.loads(response.read())
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"FunASR HTTP {error.code}") from error
    return str(payload.get("srt") or "")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corpus-videos",
        nargs="*",
        default=[],
        help="extra corpus video paths to ASR (server converts internally)",
    )
    args = parser.parse_args()

    if args.corpus_videos:
        entries = _run_extra(args.corpus_videos)
        print(f"== extra baseline: {len(entries)} episodes ==")
        _merge_baseline(entries)
        return 0

    engine = create_database_engine(get_settings().database_url)
    rows = []
    with engine.connect() as connection:
        result = connection.execute(
            text(
                "select a.project_id, av.artifact_id, av.payload_json "
                "from artifact.artifact_version av "
                "join artifact.artifact a on a.id = av.artifact_id "
                "where a.artifact_type = 'AudioStem'"
            )
        )
        for row in result:
            rows.append((row[0], row[1], row[2]))
    engine.dispose()

    entries = []
    for project_id, artifact_id, payload in rows:
        if str(artifact_id) == SKIP_EP8:
            continue
        uri = str(payload.get("uri") or "")
        if not uri.startswith("local-object://"):
            print(f"skip {artifact_id}: not a local blob ({uri})")
            continue
        blob_path = ROOT / "data/local/object_store" / uri.removeprefix("local-object://")
        if not blob_path.is_file():
            print(f"skip {artifact_id}: blob missing at {blob_path}")
            continue
        print(f"== ASR {str(artifact_id)[:8]} (project {str(project_id)[:8]})")
        srt = _asr(blob_path)
        segments = _parse_srt(srt)
        speakers = sorted({s["speaker"] for s in segments if s["speaker"]})
        coverage = round(sum(s["end_seconds"] - s["start_seconds"] for s in segments), 2)
        entries.append(
            {
                "project_id": str(project_id),
                "audio_stem_id": str(artifact_id),
                "segment_count": len(segments),
                "speech_seconds": coverage,
                "speaker_clusters": speakers,
                "sample_segments": [
                    {
                        "t": [round(s["start_seconds"], 2), round(s["end_seconds"], 2)],
                        "text": s["text"],
                    }
                    for s in segments[:4]
                ],
            }
        )
        print(f"  segments={len(segments)} speech={coverage}s speakers={speakers}")
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / f"{artifact_id}.srt").write_text(srt, encoding="utf-8")

    manifest = {
        "scope": "research multi-episode ASR baseline (FunASR paraformer-large, diarization); "
        "no human reference; CER pending",
        "model": "speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        "episodes": entries,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "speech_baseline_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"== baseline: {OUT_DIR}/speech_baseline_manifest.json ==")
    return 0


def _run_extra(video_paths: list[str]) -> list[dict[str, object]]:
    entries = []
    for video in video_paths:
        path = Path(video)
        if not path.is_file():
            print(f"skip missing {video}")
            continue
        print(f"== ASR corpus {path.parent.name}/{path.stem}")
        srt = _asr(path)
        segments = _parse_srt(srt)
        speakers = sorted({s["speaker"] for s in segments if s["speaker"]})
        coverage = round(sum(s["end_seconds"] - s["start_seconds"] for s in segments), 2)
        stem = f"{path.parent.name}_{path.stem}"
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / f"{stem}.srt").write_text(srt, encoding="utf-8")
        entries.append(
            {
                "audio_stem": stem,
                "segment_count": len(segments),
                "speech_seconds": coverage,
                "speaker_clusters": speakers,
            }
        )
        print(f"  segments={len(segments)} speech={coverage}s speakers={speakers}")
    return entries


def _merge_baseline(entries: list[dict[str, object]]) -> None:
    manifest_path = OUT_DIR / "speech_baseline_manifest.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.is_file()
        else {"episodes": []}
    )
    existing = {
        e.get("audio_stem") or e.get("audio_stem_id") or "" for e in manifest.get("episodes", [])
    }
    added = [e for e in entries if e["audio_stem"] not in existing]
    manifest.setdefault("episodes", []).extend(added)
    manifest["scope"] = (
        "research multi-episode ASR baseline (FunASR paraformer-large, diarization); "
        "no human reference; CER pending"
    )
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"== merged baseline: {len(manifest['episodes'])} episodes total ==")


if __name__ == "__main__":
    raise SystemExit(main())
