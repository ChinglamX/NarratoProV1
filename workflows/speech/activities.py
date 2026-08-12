"""Speech Activity; file/network/database I/O stays outside Workflow history."""

import asyncio
from uuid import UUID

from temporalio import activity

from apps.services.provider_invocation import ProviderInvocationService
from apps.services.speech_observation import SpeechObservationService
from packages.artifacts import LocalObjectStore
from packages.contracts import ArtifactRef, ProviderInvocationRequest
from packages.foundation.settings import get_settings
from packages.persistence.database import create_database_engine
from packages.providers import InvocationPolicy
from packages.providers.speech import FunASRHttpProvider
from workflows.project.models import ArtifactPointer
from workflows.speech.models import SpeechActivityResult, SpeechWorkflowInput


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


def _process(request: SpeechWorkflowInput) -> SpeechActivityResult:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    store = LocalObjectStore(settings.object_store_root)
    try:
        provider = FunASRHttpProvider(
            base_url=request.provider_base_url,
            model=request.provider_model,
        )
        invocation = ProviderInvocationRequest.model_validate(
            {
                "capability": "asr",
                "inputs": [_ref(request.source_audio)],
                "config_ref": _ref(request.config),
                "resource_profile_ref": _ref(request.resource_profile),
                "idempotency_key": f"speech:{request.run_id}:{request.source_audio.artifact_id}",
                "timeout_ms": 7_200_000,
                "parameters": {"audio_path": request.local_audio_path},
            }
        )
        raw_ref, _ = ProviderInvocationService(engine=engine, object_store=store).invoke_and_record(
            provider=provider,
            request=invocation,
            policy=InvocationPolicy(request.allow_research, False, "CN", 0, 8 * 1024**3, 0),
            raw_artifact_id=UUID(request.raw_artifact_id),
            project_id=UUID(request.project_id),
            run_id=UUID(request.run_id),
            trace_id=request.trace_id,
            rights_class="internal-observation",
        )
        observation = SpeechObservationService(
            engine=engine, object_store=store
        ).normalize_and_commit(
            observation_id=UUID(request.observation_artifact_id),
            project_id=UUID(request.project_id),
            run_id=UUID(request.run_id),
            source_audio_ref=_ref(request.source_audio),
            raw_response_ref=raw_ref,
            config_ref=_ref(request.config),
            resource_profile_ref=_ref(request.resource_profile),
            trace_id=request.trace_id,
            rights_class="internal-observation",
        )
        return SpeechActivityResult(_pointer(raw_ref), _pointer(observation))
    finally:
        engine.dispose()


@activity.defn
async def process_speech_activity(request: SpeechWorkflowInput) -> SpeechActivityResult:
    activity.heartbeat({"stage": "speech", "trace_id": request.trace_id})
    return await asyncio.to_thread(_process, request)
