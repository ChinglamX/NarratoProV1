"""E11 render workflow: execute ffmpeg plan and technical QC."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TypeVar
from uuid import UUID, uuid4

from sqlalchemy import Connection
from temporalio import activity

from packages.artifacts import LocalObjectStore
from packages.contracts import ActorRef, ArtifactRef, RenderPlanContract
from packages.foundation.settings import get_settings
from packages.persistence.artifact_repository import ArtifactRepository
from packages.persistence.artifact_writer import commit_contract_artifact
from packages.persistence.database import create_database_engine
from packages.production.render import execute_ffmpeg_plan
from packages.production.render_command import build_render_command, libass_available
from workflows.project.models import ArtifactPointer

ACTOR = ActorRef.model_validate({"kind": "human", "id": "e11-render"})
T = TypeVar("T")


@dataclass(frozen=True)
class RenderRequest:
    project_id: str
    run_id: str
    trace_id: str
    plan: ArtifactPointer
    resource_profile: ArtifactPointer
    output_path: str
    ffmpeg_version: str
    execution_report_id: str | None = None
    qc_report_id: str | None = None


@dataclass(frozen=True)
class RenderResult:
    execution_report: ArtifactPointer
    qc_report: ArtifactPointer
    output_path: str
    passed: bool
    blocked_codes: tuple[str, ...] = ()


def _ref(pointer: ArtifactPointer) -> ArtifactRef:
    return ArtifactRef.model_validate(
        {
            "artifact_id": pointer.artifact_id,
            "version": pointer.version,
            "artifact_type": pointer.artifact_type,
            "checksum": pointer.checksum,
        }
    )


def _pointer(reference: ArtifactRef) -> ArtifactPointer:
    return ArtifactPointer(
        str(reference.artifact_id),
        reference.version,
        reference.artifact_type,
        str(reference.checksum) if reference.checksum else None,
    )


def _run_sync(handler: object) -> object:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    try:
        with engine.begin() as connection:
            return handler(connection)  # type: ignore[operator]
    finally:
        engine.dispose()


def _int_measure(value: object) -> int:
    from typing import Any, cast

    return int(cast(Any, value) or 0)


def _source_paths(
    connection: Connection, repository: ArtifactRepository, plan: RenderPlanContract
) -> dict[str, object]:
    store = LocalObjectStore(get_settings().object_store_root)
    paths: dict[str, object] = {}
    for op in plan.operations:
        if op.operation_type != "trim-clip":
            continue
        source_ref = op.input_refs[0]
        payload = repository.get_version(connection, source_ref)["payload_json"]
        uri = payload.get("uri")
        if uri:
            paths[str(source_ref.artifact_id)] = store.local_path(str(uri))
    return paths


@activity.defn
async def execute_render_activity(
    request: RenderRequest,
) -> object:  # pragma: no cover - verified by real Temporal run
    activity.heartbeat({"stage": "e11-execute", "trace_id": request.trace_id})

    def work(connection: Connection) -> object:
        repository = ArtifactRepository()
        payload = repository.get_version(connection, _ref(request.plan))["payload_json"]
        plan = RenderPlanContract.model_validate(payload)
        if not libass_available():
            # Fail-closed: ASS burn requires a libass-enabled ffmpeg (E11 baseline).
            raise RuntimeError("libass-unavailable: ffmpeg lacks the subtitles filter")
        source_paths = _source_paths(connection, repository, plan)
        command = build_render_command(
            plan=plan,
            source_paths=source_paths,  # type: ignore[arg-type]
            ass_path=None,
            output_path=__import__("pathlib").Path(request.output_path),
        )
        report = execute_ffmpeg_plan(
            plan=plan,
            plan_ref=_ref(request.plan),
            command=command,
            output_path=__import__("pathlib").Path(request.output_path),
            ffmpeg_version=request.ffmpeg_version,
            attempt=1,
            heartbeat=lambda details: activity.heartbeat(details),
        )
        report_ref = commit_contract_artifact(
            connection,
            repository,
            artifact_id=UUID(request.execution_report_id)
            if request.execution_report_id
            else uuid4(),
            artifact_type="RenderExecutionReport",
            payload=report,
            project_id=UUID(request.project_id),
            run_id=UUID(request.run_id),
            variant_id=None,
            trace_id=request.trace_id,
            actor=ACTOR,
            producer_module="e11-render",
            module_version="v1",
            resource_profile_ref=_ref(request.resource_profile),
            rights_class="internal-preview",
            inputs=(_ref(request.plan),),
        )
        return _pointer(report_ref)

    return await asyncio.to_thread(_run_sync, work)


@activity.defn
async def technical_qc_activity(
    request: RenderRequest,
) -> object:  # pragma: no cover - verified by real Temporal run
    activity.heartbeat({"stage": "e11-qc", "trace_id": request.trace_id})

    def work(connection: Connection) -> object:
        import subprocess  # nosec B404

        from packages.contracts.render_release import TechnicalCheck, TechnicalQCReport

        repository = ArtifactRepository()
        probe = subprocess.run(  # nosec B603 B607
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type,width,height",
                "-of",
                "json",
                request.output_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if probe.returncode != 0:
            raise RuntimeError("qc-probe-failed")
        import json

        info = json.loads(probe.stdout)
        duration = float(info.get("format", {}).get("duration", 0))
        video: dict[str, object] = next(
            (stream for stream in info.get("streams", []) if stream.get("codec_type") == "video"),
            {},
        )
        checks = (
            TechnicalCheck(
                check_id="duration-positive",
                status="passed" if duration > 0 else "failed",
                measured={"duration_seconds": duration},
                profile_ref=_ref(request.resource_profile),
                blocker=duration <= 0,
                detail=f"probed duration {duration:.2f}s",
            ),
            TechnicalCheck(
                check_id="video-stream-present",
                status="passed" if video else "failed",
                measured={
                    "width": _int_measure(video.get("width")),
                    "height": _int_measure(video.get("height")),
                },
                profile_ref=_ref(request.resource_profile),
                blocker=not video,
                detail="video stream detected" if video else "no video stream",
            ),
        )
        qc = TechnicalQCReport(
            candidate_ref=_ref(request.plan),
            checks=checks,
            blocker_codes=tuple(c.check_id for c in checks if c.blocker and c.status != "passed"),
            passed=all(c.status == "passed" for c in checks),
        )
        qc_ref = commit_contract_artifact(
            connection,
            repository,
            artifact_id=UUID(request.qc_report_id) if request.qc_report_id else uuid4(),
            artifact_type="TechnicalQCReport",
            payload=qc,
            project_id=UUID(request.project_id),
            run_id=UUID(request.run_id),
            variant_id=None,
            trace_id=request.trace_id,
            actor=ACTOR,
            producer_module="e11-render",
            module_version="v1",
            resource_profile_ref=_ref(request.resource_profile),
            rights_class="internal-preview",
            inputs=(_ref(request.plan),),
        )
        return _pointer(qc_ref)

    return await asyncio.to_thread(_run_sync, work)
