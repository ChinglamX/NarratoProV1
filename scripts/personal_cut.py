"""Transparent, resumable personal entry point for an approved short-drama cut."""

# ruff: noqa: RUF001 - user-facing Chinese messages intentionally use CJK punctuation

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import subprocess  # nosec B404
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CutSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_start_seconds: float = Field(ge=0)
    duration_seconds: float = Field(gt=0, le=30)
    narration: str | None = Field(default=None, min_length=1, max_length=500)
    source_path: Path | None = None


class PersonalCutConfig(BaseModel):
    """User-editable boundary for the current M5 validation scope."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    project_name: str = Field(min_length=1, max_length=120)
    usage_scope: Literal["internal-preview"]
    rights_confirmed: bool
    gate_1_story_approved: bool
    gate_2_strategy_approved: bool
    source_path: Path | None = None
    reference_audio: Path
    segments: tuple[CutSegment, ...] = Field(min_length=1, max_length=20)
    ingest_manifest: Path | None = None
    ingest_manifests: tuple[Path, ...] = ()
    candidate_manifest: Path
    canonical_output: Path
    acceptance_manifest: Path
    candidate_filename: str | None = None
    rights: str | None = None
    gate_1: str | None = None
    gate_2: str | None = None
    visual_events: tuple[dict[str, object], ...] = ()
    narration_anchors: tuple[dict[str, object], ...] = ()
    run_provenance: dict[str, object] | None = None

    @model_validator(mode="after")
    def enforce_human_and_rights_boundary(self) -> PersonalCutConfig:
        if not self.rights_confirmed:
            raise ValueError("rights_confirmed must be true for internal processing")
        if not self.gate_1_story_approved or not self.gate_2_strategy_approved:
            raise ValueError("Gate 1 and Gate 2 must be approved before media production")
        manifests = self.ingest_manifests or (
            (self.ingest_manifest,) if self.ingest_manifest is not None else ()
        )
        if not manifests:
            raise ValueError("ingest_manifest or ingest_manifests is required")
        sources = {
            segment.source_path for segment in self.segments if segment.source_path is not None
        }
        if self.source_path is not None:
            sources.add(self.source_path)
        if len(sources) != len(manifests):
            raise ValueError("each source requires exactly one ingest manifest")
        return self


class StageResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: str
    status: Literal["passed", "ready", "skipped", "failed"]
    explanation: str
    inspectable_output: str | None = None


def _load_config(path: Path) -> PersonalCutConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    config = PersonalCutConfig.model_validate(raw)
    base = path.parent.resolve()
    updates = {}
    for name in (
        "candidate_manifest",
        "canonical_output",
        "acceptance_manifest",
        "reference_audio",
    ):
        value = getattr(config, name)
        updates[name] = value if value.is_absolute() else base / value
    if config.source_path is not None:
        updates["source_path"] = (
            config.source_path if config.source_path.is_absolute() else base / config.source_path
        )
    if config.ingest_manifest is not None:
        updates["ingest_manifest"] = (
            config.ingest_manifest
            if config.ingest_manifest.is_absolute()
            else base / config.ingest_manifest
        )
    updates["ingest_manifests"] = tuple(
        item if item.is_absolute() else base / item for item in config.ingest_manifests
    )
    updates["segments"] = tuple(
        segment.model_copy(
            update={
                "source_path": (
                    segment.source_path
                    if segment.source_path is None or segment.source_path.is_absolute()
                    else base / segment.source_path
                )
            }
        )
        for segment in config.segments
    )
    return config.model_copy(update=updates)


def _source_ingest_pairs(config: PersonalCutConfig) -> tuple[tuple[Path, Path], ...]:
    manifests = config.ingest_manifests or (
        (config.ingest_manifest,) if config.ingest_manifest is not None else ()
    )
    sources = tuple(
        dict.fromkeys(
            segment.source_path for segment in config.segments if segment.source_path is not None
        )
    )
    if not sources and config.source_path is not None:
        sources = (config.source_path,)
    return tuple(zip(sources, manifests, strict=True))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _port_ready(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def inspect(config: PersonalCutConfig) -> list[StageResult]:
    results = [
        StageResult(
            stage="01-rights-and-human-gates",
            status="passed",
            explanation="仅限内部预览；Gate 1 剧情与 Gate 2 策略均已人工批准。",
        )
    ]
    source_ingests = _source_ingest_pairs(config)
    missing_ingests = [
        (source, manifest) for source, manifest in source_ingests if not manifest.is_file()
    ]
    if missing_ingests:
        sources_exist = all(source.is_file() for source, _ in missing_ingests)
        return [
            *results,
            StageResult(
                stage="02-media-ingest",
                status="ready" if sources_exist else "failed",
                explanation=(
                    f"{len(missing_ingests)} 个素材文件存在，可以执行导入。"
                    if sources_exist
                    else "至少一个源视频不存在，请检查 segments.source_path。"
                ),
                inspectable_output=", ".join(str(item[1]) for item in missing_ingests),
            ),
        ]
    ingests = [json.loads(manifest.read_text(encoding="utf-8")) for _, manifest in source_ingests]
    source_refs_ok = all(ingest.get("artifacts", {}).get("source") for ingest in ingests)
    results.append(
        StageResult(
            stage="02-media-ingest",
            status="passed" if source_refs_ok else "failed",
            explanation=(
                f"{len(ingests)} 个素材和权利快照均可追踪。"
                if source_refs_ok
                else "至少一个导入清单缺少 SourceMedia。"
            ),
            inspectable_output=", ".join(str(item[1]) for item in source_ingests),
        )
    )
    if not config.candidate_manifest.is_file():
        return [
            *results,
            StageResult(
                stage="03-approved-cut-parts",
                status="ready" if config.reference_audio.is_file() else "failed",
                explanation=(
                    "镜头与解说配置完整，可以生成配音、字幕和候选片。"
                    if config.reference_audio.is_file()
                    else "参考声音文件不存在，请检查 reference_audio。"
                ),
                inspectable_output=str(config.candidate_manifest),
            ),
        ]
    candidate = json.loads(config.candidate_manifest.read_text(encoding="utf-8"))
    lines = candidate.get("narration_lines", [])
    wavs_ok = bool(lines) and all(Path(str(line.get("path", ""))).is_file() for line in lines)
    parts_ok = (
        bool(candidate.get("segments"))
        and wavs_ok
        and Path(str(candidate.get("ass", ""))).is_file()
    )
    results.append(
        StageResult(
            stage="03-approved-cut-parts",
            status="passed" if parts_ok else "failed",
            explanation=(
                f"{len(lines)} 段解说、镜头表、WAV 和 ASS 均可单独查看。"
                if parts_ok
                else "候选清单中的镜头、WAV 或 ASS 不完整。"
            ),
            inspectable_output=str(config.candidate_manifest),
        )
    )
    canonical_files_present = (
        config.canonical_output.is_file() and config.acceptance_manifest.is_file()
    )
    runtime_ok = _port_ready("127.0.0.1", 7233)
    runtime_status: Literal["passed", "ready", "skipped", "failed"]
    if canonical_files_present:
        runtime_status = "skipped"
        runtime_explanation = "canonical 已完成，本次检查无需连接 Temporal。"
    elif runtime_ok:
        runtime_status = "passed"
        runtime_explanation = "Temporal 可连接；canonical 渲染可执行。"
    else:
        runtime_status = "failed"
        runtime_explanation = "Temporal 端口 7233 不可连接；续跑前请启动基础设施和 Worker。"
    results.append(
        StageResult(
            stage="04-runtime",
            status=runtime_status,
            explanation=runtime_explanation,
        )
    )
    canonical_ok = canonical_files_present
    if canonical_ok:
        acceptance = json.loads(config.acceptance_manifest.read_text(encoding="utf-8"))
        render = acceptance.get("render_result", {})
        canonical_ok = render.get("passed") is True and not render.get("blocked_codes")
    results.append(
        StageResult(
            stage="05-canonical-render-and-qc",
            status="passed" if canonical_ok else "ready",
            explanation=(
                "canonical 成片存在，Temporal Render 与 Technical QC 已通过。"
                if canonical_ok
                else "前置项满足后可执行 canonical 渲染；失败可从本阶段重试。"
            ),
            inspectable_output=str(config.canonical_output),
        )
    )
    results.append(
        StageResult(
            stage="06-human-release",
            status="skipped",
            explanation="Gate 3 未执行；本入口不会公开发布。",
        )
    )
    return results


def _write_status(config_path: Path, config: PersonalCutConfig, results: list[StageResult]) -> Path:
    target = config.acceptance_manifest.parent / "personal_cut_status.json"
    payload = {
        "schema_version": "1.0",
        "project_name": config.project_name,
        "updated_at": datetime.now(UTC).isoformat(),
        "config": str(config_path.resolve()),
        "overall_status": (
            "passed"
            if all(item.status in {"passed", "skipped"} for item in results)
            else "attention-required"
        ),
        "stages": [item.model_dump(mode="json") for item in results],
        "canonical_checksum": _sha256(config.canonical_output)
        if config.canonical_output.is_file()
        else None,
        "release_gate_3": "not-executed",
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def _print_results(results: list[StageResult]) -> None:
    labels = {"passed": "通过", "ready": "待执行", "skipped": "未执行", "failed": "失败"}
    for item in results:
        print(f"[{labels[item.status]}] {item.stage}: {item.explanation}")
        if item.inspectable_output:
            print(f"         产物: {item.inspectable_output}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True, help="单份 JSON 项目配置")
    parser.add_argument("--run", action="store_true", help="执行未完成的 canonical 渲染阶段")
    args = parser.parse_args()
    try:
        config = _load_config(args.config)
        if args.run:
            for source_path, ingest_manifest in _source_ingest_pairs(config):
                if ingest_manifest.is_file():
                    continue
                subprocess.run(  # nosec B603
                    [
                        str(Path(".venv/bin/python").resolve()),
                        str(Path("scripts/ingest_m5_second_source.py").resolve()),
                        "--source",
                        str(source_path),
                        "--output",
                        str(ingest_manifest),
                        "--project-name",
                        f"{config.project_name} — {source_path.stem}",
                    ],
                    check=True,
                )
        if args.run and not config.candidate_manifest.is_file():
            subprocess.run(  # nosec B603
                [
                    str(Path(".venv/bin/python").resolve()),
                    str(Path("scripts/build_m5_second_cut.py").resolve()),
                    "--personal-config",
                    str(args.config.resolve()),
                ],
                check=True,
            )
        results = inspect(config)
        blocking = any(item.status == "failed" for item in results)
        canonical_done = any(
            item.stage == "05-canonical-render-and-qc" and item.status == "passed"
            for item in results
        )
        if args.run and not blocking and not canonical_done:
            subprocess.run(  # nosec B603
                [
                    str(Path(".venv/bin/python").resolve()),
                    str(Path("scripts/accept_first_usable_cut_canonical.py").resolve()),
                    "--personal-config",
                    str(args.config.resolve()),
                ],
                check=True,
            )
            results = inspect(config)
        _print_results(results)
        status_path = _write_status(args.config, config, results)
        print(f"\n状态文件: {status_path}")
        return 1 if any(item.status == "failed" for item in results) else 0
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"[失败] 配置或执行错误: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
