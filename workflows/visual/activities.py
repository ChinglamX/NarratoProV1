"""Visual Activity; model/file/database I/O stays out of Workflow history."""

import asyncio
from uuid import UUID

from temporalio import activity

from apps.services.provider_invocation import ProviderInvocationService
from apps.services.visual_observation import VisualObservationService
from packages.artifacts import LocalObjectStore
from packages.contracts import ArtifactRef, ProviderInvocationRequest
from packages.foundation.settings import get_settings
from packages.persistence.database import create_database_engine
from packages.providers import InvocationPolicy
from packages.providers.visual import OpenCVContourProvider
from workflows.project.models import ArtifactPointer
from workflows.visual.models import VisualActivityResult, VisualWorkflowInput


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


def _process(request: VisualWorkflowInput) -> VisualActivityResult:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    store = LocalObjectStore(settings.object_store_root)
    try:
        provider = OpenCVContourProvider()
        invocation = ProviderInvocationRequest.model_validate(
            {
                "capability": "detection",
                "inputs": [_ref(request.frame)],
                "config_ref": _ref(request.config),
                "resource_profile_ref": _ref(request.resource_profile),
                "idempotency_key": f"visual:{request.run_id}:{request.frame.artifact_id}",
                "timeout_ms": 600_000,
                "parameters": {"frame_path": request.local_frame_path},
            }
        )
        raw_ref, _ = ProviderInvocationService(engine=engine, object_store=store).invoke_and_record(
            provider=provider,
            request=invocation,
            policy=InvocationPolicy(
                request.allow_research,
                False,
                "CN",
                0,
                2 * 1024**3,
                0,
            ),
            raw_artifact_id=UUID(request.raw_artifact_id),
            project_id=UUID(request.project_id),
            run_id=UUID(request.run_id),
            trace_id=request.trace_id,
            rights_class="internal-observation",
        )
        observation = VisualObservationService(
            engine=engine, object_store=store
        ).normalize_and_commit(
            observation_id=UUID(request.observation_artifact_id),
            project_id=UUID(request.project_id),
            run_id=UUID(request.run_id),
            source_ref=_ref(request.source),
            frame_plan_ref=_ref(request.frame_plan),
            raw_response_ref=raw_ref,
            frame_evidence={
                "frame_ref": _ref(request.frame),
                "sample_id": UUID(request.frame.artifact_id),
                "source_time": {
                    "value": request.source_time_value,
                    "rate_num": request.source_time_rate_num,
                },
            },
            config_ref=_ref(request.config),
            resource_profile_ref=_ref(request.resource_profile),
            trace_id=request.trace_id,
            rights_class="internal-observation",
        )
        return VisualActivityResult(_pointer(raw_ref), _pointer(observation))
    finally:
        engine.dispose()


@activity.defn
async def process_visual_activity(request: VisualWorkflowInput) -> VisualActivityResult:
    activity.heartbeat({"stage": "visual", "trace_id": request.trace_id})
    return await asyncio.to_thread(_process, request)
