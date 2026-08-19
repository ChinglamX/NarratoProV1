from __future__ import annotations

import json
from pathlib import Path

from scripts.personal_cut import _load_config, _source_ingest_pairs, inspect


def test_multi_source_entry_reports_completed_canonical_slice(tmp_path: Path) -> None:
    sources = (tmp_path / "7.mp4", tmp_path / "8.mp4")
    ingests = (tmp_path / "ingest_7.json", tmp_path / "ingest_8.json")
    for source, ingest in zip(sources, ingests, strict=True):
        source.write_bytes(b"source")
        ingest.write_text(
            json.dumps({"artifacts": {"source": {"artifact_id": source.stem}}}),
            encoding="utf-8",
        )
    wav = tmp_path / "line.wav"
    ass = tmp_path / "candidate.ass"
    wav.write_bytes(b"wav")
    ass.write_text("ass", encoding="utf-8")
    candidate = tmp_path / "manifest.json"
    candidate.write_text(
        json.dumps(
            {
                "segments": [{"source_path": str(item)} for item in sources],
                "narration_lines": [{"path": str(wav)}],
                "ass": str(ass),
            }
        ),
        encoding="utf-8",
    )
    canonical = tmp_path / "canonical.mp4"
    canonical.write_bytes(b"canonical")
    acceptance = tmp_path / "acceptance.json"
    acceptance.write_text(
        json.dumps({"render_result": {"passed": True, "blocked_codes": []}}),
        encoding="utf-8",
    )
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "project_name": "multi-source",
                "usage_scope": "internal-preview",
                "rights_confirmed": True,
                "gate_1_story_approved": True,
                "gate_2_strategy_approved": True,
                "reference_audio": str(wav),
                "segments": [
                    {
                        "source_path": str(source),
                        "source_start_seconds": 0,
                        "duration_seconds": 2,
                    }
                    for source in sources
                ],
                "ingest_manifests": [str(item) for item in ingests],
                "candidate_manifest": str(candidate),
                "canonical_output": str(canonical),
                "acceptance_manifest": str(acceptance),
            }
        ),
        encoding="utf-8",
    )

    config = _load_config(config_path)
    results = inspect(config)

    assert _source_ingest_pairs(config) == tuple(zip(sources, ingests, strict=True))
    assert [(item.stage, item.status) for item in results] == [
        ("01-rights-and-human-gates", "passed"),
        ("02-media-ingest", "passed"),
        ("03-approved-cut-parts", "passed"),
        ("04-runtime", "passed"),
        ("05-canonical-render-and-qc", "passed"),
        ("06-human-release", "skipped"),
    ]
