"""E04 real PostgreSQL semantic concurrency, OTIO and FFmpeg acceptance."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import insert
from temporalio.client import Client
from temporalio.worker import Worker

import packages.persistence.schema as schema
from apps.api.main import create_app
from packages.contracts import ArtifactRef, MasterTimeline
from packages.foundation.settings import get_settings
from packages.persistence.database import create_database_engine
from packages.production import render_fake_preview
from packages.timeline import compile_render_plan, export_otio, import_otio
from workflows.project.models import ArtifactPointer, ReviewSignal
from workflows.timeline import (
    PreviewWorkflowInput,
    TimelinePreviewWorkflow,
    render_preview_activity,
)

DATABASE_URL = (
    "postgresql+psycopg://narratopro:replace-with-a-local-secret@127.0.0.1:5432/"
    "narratopro_e02_acceptance"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _ref(kind: str, artifact_id: UUID | None = None, version: int = 1) -> dict[str, object]:
    return {
        "artifact_id": str(artifact_id or uuid4()),
        "version": version,
        "artifact_type": kind,
    }


def _time(value: int) -> dict[str, int]:
    return {"value": value, "rate_num": 25}


def _timeline() -> MasterTimeline:
    items = []
    for start in (0, 50):
        items.append(
            {
                "item_id": uuid4(),
                "item_version": 1,
                "item_type": "clip",
                "timeline_range": {"start": _time(start), "duration": _time(50)},
                "source_ref": _ref("SourceMedia"),
                "source_range": {"start": _time(0), "duration": _time(50)},
            }
        )
    return MasterTimeline.model_validate(
        {
            "timeline_id": uuid4(),
            "lifecycle": "draft",
            "rate_num": 25,
            "global_start": _time(0),
            "duration": _time(100),
            "tracks": [{"track_id": uuid4(), "kind": "video", "order": 0, "items": items}],
            "metadata_namespace_version": "1.0.0",
        }
    )


def _patch(timeline_id: UUID, item_id: UUID, *, key: str, value: object) -> dict[str, object]:
    return {
        "patch_id": str(uuid4()),
        "base_timeline": _ref("MasterTimeline", timeline_id),
        "operations": [
            {
                "operation_id": str(uuid4()),
                "op": "set_parameter",
                "target_item_id": str(item_id),
                "expected_item_version": 1,
                "payload": {"key": key, "value": value},
            }
        ],
        "author": {"kind": "human", "id": "editor"},
        "reason": "E04 concurrency acceptance",
    }


async def _accept_preview_workflow(
    *,
    project_id: UUID,
    run_id: UUID,
    artifact_id: UUID,
    timeline_version: int,
    timeline_checksum: str,
    output_path: Path,
) -> str:
    client = await Client.connect("127.0.0.1:7233")
    task_queue = f"e04-preview-{run_id}"
    workflow_id = f"e04-preview/{run_id}"
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=[TimelinePreviewWorkflow],
        activities=[render_preview_activity],
    ):
        handle = await client.start_workflow(
            TimelinePreviewWorkflow.run,
            PreviewWorkflowInput(
                run_id=str(run_id),
                project_id=str(project_id),
                trace_id="b" * 32,
                timeline=ArtifactPointer(
                    str(artifact_id), timeline_version, "MasterTimeline", timeline_checksum
                ),
                profile=ArtifactPointer(str(uuid4()), 1, "ConfigArtifact"),
                output_path=str(output_path),
            ),
            id=workflow_id,
            task_queue=task_queue,
        )
        for _ in range(200):
            status = await handle.query(TimelinePreviewWorkflow.status)
            if status is not None and status.state == "awaiting_review":
                break
            await asyncio.sleep(0.05)
        else:
            raise RuntimeError("preview workflow did not reach human checkpoint")
        await handle.signal(
            TimelinePreviewWorkflow.submit_review,
            ReviewSignal(f"review:{run_id}:timeline-preview", 1, "approve"),
        )
        result = await handle.result()
        require(
            result.state == "succeeded" and result.preview is not None, "preview workflow failed"
        )
        return result.preview.artifact_id


def main() -> None:
    engine = create_database_engine(DATABASE_URL)
    app = create_app()
    app.state.database_engine.dispose()
    app.state.database_engine = engine
    os.environ["NARRATOPRO_DATABASE_URL"] = DATABASE_URL
    get_settings.cache_clear()
    client = TestClient(app)
    project_id, run_id, artifact_id = uuid4(), uuid4(), uuid4()
    value = _timeline()
    with engine.begin() as connection:
        connection.execute(
            insert(schema.project).values(id=project_id, name="E04 acceptance", state="active")
        )
        connection.execute(
            insert(schema.run).values(
                id=run_id,
                project_id=project_id,
                workflow_id=f"e04/{run_id}",
                state="running",
                automation_policy_snapshot={"level": "L1"},
                resource_profile_snapshot={"queue": "cpu"},
            )
        )
        connection.execute(
            insert(schema.artifact).values(
                id=artifact_id, project_id=project_id, artifact_type="MasterTimeline"
            )
        )
        connection.execute(
            insert(schema.artifact_version).values(
                artifact_id=artifact_id,
                version=1,
                schema_version="1.0.0",
                run_id=run_id,
                state="committed",
                payload_json=value.model_dump(mode="json"),
                checksum="sha256:" + "7" * 64,
                producer_json={"kind": "acceptance"},
                rights_class="acceptance-only",
                trace_id="b" * 32,
            )
        )
        connection.execute(insert(schema.active_pointer).values(artifact_id=artifact_id, version=1))

    first_id = value.tracks[0].items[0].item_id
    second_id = value.tracks[0].items[1].item_id
    headers = {"X-Actor-Roles": "editor", "X-Trace-Id": "b" * 32}
    first = client.post(
        f"/v1/timelines/{artifact_id}/patches",
        json=_patch(artifact_id, first_id, key="crop", value="center"),
        headers=headers,
    )
    require(first.status_code == 201 and first.json()["version"] == 2, "first patch failed")
    disjoint = client.post(
        f"/v1/timelines/{artifact_id}/patches",
        json=_patch(artifact_id, second_id, key="gain", value=-3),
        headers=headers,
    )
    require(
        disjoint.status_code == 201
        and disjoint.json()["version"] == 3
        and disjoint.json()["rebased"],
        "disjoint semantic rebase failed",
    )
    conflicting = client.post(
        f"/v1/timelines/{artifact_id}/patches",
        json=_patch(artifact_id, first_id, key="crop", value="left"),
        headers=headers,
    )
    require(conflicting.status_code == 409, "same-item conflict was not rejected")

    otio_payload, export_loss = export_otio(value)
    restored, import_loss = import_otio(otio_payload)
    require(export_loss.lossless and import_loss.lossless and restored == value, "OTIO loss")
    compiled_ref = ArtifactRef.model_validate(_ref("MasterTimeline", artifact_id))
    profile_ref = ArtifactRef.model_validate(_ref("ConfigArtifact"))
    plan = compile_render_plan(
        value,
        timeline_ref=compiled_ref,
        profile_ref=profile_ref,
        toolchain_version="ffmpeg-8.1.2",
    )
    with TemporaryDirectory() as temporary:
        preview = render_fake_preview(value, Path(temporary) / "preview.mp4")
        require(preview.output_path.stat().st_size > 0, "preview output is empty")
        require(preview.subtitle_path.exists(), "ASS sidecar is missing")
        require(
            preview.video_codec == "h264"
            and preview.audio_codec == "aac"
            and (preview.width, preview.height) == (720, 1280),
            "preview QC failed",
        )
        preview_artifact_id = asyncio.run(
            _accept_preview_workflow(
                project_id=project_id,
                run_id=run_id,
                artifact_id=artifact_id,
                timeline_version=3,
                timeline_checksum=disjoint.json()["checksum"],
                output_path=Path(temporary) / "workflow-preview.mp4",
            )
        )
    print(
        json.dumps(
            {
                "ffmpeg_version": preview.ffmpeg_version.split()[2],
                "otio_round_trip": True,
                "preview_qc": True,
                "preview_artifact_id": preview_artifact_id,
                "preview_workflow": True,
                "render_plan_checksum": plan.checksum,
                "same_item_conflict": True,
                "semantic_rebase": True,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
