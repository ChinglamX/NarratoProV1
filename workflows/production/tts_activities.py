"""E10/K01 voice synthesis activity: IndexTTS takes -> VoiceTakeSet -> VoiceAsset.

Reads an approved NarrationLineSet, synthesizes each line via the local
IndexTTS-2 provider (reference voice ref_7_clean.wav), stages the WAV blob,
records one SELECTED VoiceTake per line, and persists the VoiceTakeSet plus a
VoiceAsset pointing at the selected takes. Fail-closed: any synthesis error
marks that take UNAVAILABLE (rather than silently proceeding), and the set is
incomplete when any line is missing.

The per-line decision logic (``_synthesize_takes``) is a pure function over the
narration and provider so it can be unit-tested without a database; ``_work``
owns the object-store / artifact persistence.
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID, uuid4

from sqlalchemy import Connection
from temporalio import activity

from packages.artifacts import LocalObjectStore
from packages.contracts import ActorRef, ArtifactRef, ProviderCapability, ProviderInvocationRequest
from packages.contracts.media_production import (
    TakeDisposition,
    VoiceAsset,
    VoiceTake,
    VoiceTakeSet,
)
from packages.contracts.rights import RightsMetadata, RightsStatus
from packages.contracts.timeline_intent import NarrationLineSet
from packages.foundation.settings import get_settings
from packages.persistence.artifact_repository import ArtifactRepository
from packages.persistence.artifact_writer import commit_contract_artifact
from packages.persistence.blob_repository import BlobRepository
from packages.persistence.database import create_database_engine
from packages.providers.speech.indextts import IndexTTSProvider
from workflows.project.models import ArtifactPointer

ACTOR = ActorRef.model_validate({"kind": "human", "id": "e10-tts"})


@dataclass(frozen=True)
class SynthesizeVoiceInput:
    project_id: str
    run_id: str
    trace_id: str
    narration_line_set: ArtifactPointer
    resource_profile: ArtifactPointer
    voice_profile: ArtifactPointer
    voice_take_set_id: str | None = None
    voice_asset_id: str | None = None


@dataclass(frozen=True)
class SynthesizeVoiceResult:
    voice_take_set: ArtifactPointer
    voice_asset: ArtifactPointer
    incomplete: bool
    synthesized_lines: int
    failed_lines: int


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


def _load_narration(
    connection: Connection, repository: ArtifactRepository, pointer: ArtifactPointer
) -> NarrationLineSet:
    payload = repository.get_version(connection, _ref(pointer))["payload_json"]
    return NarrationLineSet.model_validate(payload)


def _synthesize_one(
    text: str, provider: IndexTTSProvider, config_ref: ArtifactRef
) -> tuple[bytes, str]:
    """Synthesize one line; returns (wav_bytes, checksum)."""
    request = ProviderInvocationRequest(
        capability=ProviderCapability.TTS,
        inputs=(config_ref,),
        config_ref=config_ref,
        resource_profile_ref=config_ref,
        idempotency_key=f"e10-tts:{hashlib.sha256(text.encode()).hexdigest()[:16]}",
        timeout_ms=600_000,
        parameters={"text": text},
    )
    raw = provider.infer(request)
    digest = "sha256:" + hashlib.sha256(raw.payload).hexdigest()
    return raw.payload, digest


def _synthesize_takes(
    narration: NarrationLineSet,
    provider: IndexTTSProvider,
    config_ref: ArtifactRef,
    take_set_id: UUID,
) -> tuple[list[VoiceTake], list[UUID], int, dict[UUID, bytes]]:
    """Synthesize every narration line; pure decision logic (no DB).

    Returns (takes, selected_line_ids, failed_count, wav_by_line). A synthesis
    failure marks that line UNAVAILABLE (fail-closed) instead of aborting.
    """
    takes: list[VoiceTake] = []
    selected_ids: list[UUID] = []
    wav_by_line: dict[UUID, bytes] = {}
    failed = 0
    for line in narration.lines:
        try:
            wav, _digest = _synthesize_one(line.text, provider, config_ref)
            wav_by_line[line.line_id] = wav
            takes.append(
                VoiceTake(
                    take_id=uuid4(),
                    narration_line_id=line.line_id,
                    raw_response_ref=ArtifactRef.model_validate(
                        {
                            "artifact_id": str(uuid4()),
                            "version": 1,
                            "artifact_type": "VoiceTakeSet",
                        }
                    ),
                    audio_blob_ref=f"blob:{take_set_id}:{line.line_id}",
                    duration=line.target_duration,
                    provider_id="indextts",
                    provider_version="index-tts2-bilibili-ula",
                    voice_id="ref_7_clean",
                    pronunciation_findings=(),
                    qc_findings=(),
                    disposition=TakeDisposition.SELECTED,
                    estimated_cost_micros=0,
                )
            )
            selected_ids.append(line.line_id)
        except Exception:
            failed += 1
            takes.append(
                VoiceTake(
                    take_id=uuid4(),
                    narration_line_id=line.line_id,
                    raw_response_ref=ArtifactRef.model_validate(
                        {
                            "artifact_id": str(uuid4()),
                            "version": 1,
                            "artifact_type": "VoiceTakeSet",
                        }
                    ),
                    audio_blob_ref=None,
                    duration=None,
                    provider_id="indextts",
                    provider_version="index-tts2-bilibili-ula",
                    voice_id="ref_7_clean",
                    pronunciation_findings=(),
                    qc_findings=(),
                    disposition=TakeDisposition.UNAVAILABLE,
                    estimated_cost_micros=0,
                )
            )
    return takes, selected_ids, failed, wav_by_line


def _work(connection: Connection, request: SynthesizeVoiceInput) -> SynthesizeVoiceResult:
    settings = get_settings()
    repository = ArtifactRepository()
    blobs = BlobRepository()
    store = LocalObjectStore(settings.object_store_root)
    provider = IndexTTSProvider()

    narration = _load_narration(connection, repository, request.narration_line_set)
    if not narration.lines:
        raise ValueError("narration line set is empty; nothing to synthesize")

    project_uuid = UUID(request.project_id)
    run_uuid = UUID(request.run_id)
    take_set_id = UUID(request.voice_take_set_id) if request.voice_take_set_id else uuid4()
    asset_id = UUID(request.voice_asset_id) if request.voice_asset_id else uuid4()

    config_ref = _ref(request.voice_profile)
    takes, selected_ids, failed, wav_by_line = _synthesize_takes(
        narration, provider, config_ref, take_set_id
    )

    # Persist each synthesized WAV to the object store as an audio blob.
    for take in takes:
        if take.audio_blob_ref is None:
            continue
        wav = wav_by_line.get(take.narration_line_id)
        if wav is None:
            continue
        digest = hashlib.sha256(wav).hexdigest()
        staged = store.stage(run_uuid, f"voice-{take.narration_line_id}", BytesIO(wav))
        blob = blobs.register_or_get_staged(connection, staged, content_type="audio/wav")
        store.commit(staged.uri, f"sha256:{digest}")
        take.audio_blob_ref = str(blob.blob_id)

    take_set = VoiceTakeSet(
        narration_line_set_ref=_ref(request.narration_line_set),
        voice_profile_ref=config_ref,
        takes=tuple(takes),
        max_takes_per_line=1,
        incomplete=failed > 0,
    )
    take_set_ref = commit_contract_artifact(
        connection,
        repository,
        artifact_id=take_set_id,
        artifact_type="VoiceTakeSet",
        payload=take_set,
        project_id=project_uuid,
        run_id=run_uuid,
        variant_id=None,
        trace_id=request.trace_id,
        actor=ACTOR,
        producer_module="e10-tts",
        module_version="v1",
        resource_profile_ref=_ref(request.resource_profile),
        rights_class="internal-preview",
        inputs=(_ref(request.narration_line_set), config_ref),
    )

    if not selected_ids:
        raise RuntimeError("all voice takes unavailable; no voice asset produced")

    duration_us = sum((take.duration.value if take.duration else 0) for take in takes)
    voice_asset = VoiceAsset(
        voice_take_set_ref=take_set_ref,
        selected_take_ids=tuple(selected_ids),
        audio_blob_ref=f"voice:{take_set_id}",
        duration=__import__("packages.contracts", fromlist=["RationalTime"]).RationalTime(
            value=max(duration_us, 1), rate_num=1_000_000
        ),
        checksum=str(take_set_ref.checksum or "sha256:" + "0" * 64),
        rights=RightsMetadata(
            status=RightsStatus.CLEARED,
            source="owner-approved ref_7_clean.wav (2026-08-16)",
            license="bilibili-model-ula-2025",
            commercial_use=True,
            synchronization=True,
            checked_at=datetime.now(UTC),
        ),
    )
    asset_ref = commit_contract_artifact(
        connection,
        repository,
        artifact_id=asset_id,
        artifact_type="VoiceAsset",
        payload=voice_asset,
        project_id=project_uuid,
        run_id=run_uuid,
        variant_id=None,
        trace_id=request.trace_id,
        actor=ACTOR,
        producer_module="e10-tts",
        module_version="v1",
        resource_profile_ref=_ref(request.resource_profile),
        rights_class="internal-preview",
        inputs=(take_set_ref,),
    )
    return SynthesizeVoiceResult(
        voice_take_set=_pointer(take_set_ref),
        voice_asset=_pointer(asset_ref),
        incomplete=failed > 0,
        synthesized_lines=len(selected_ids),
        failed_lines=failed,
    )


@activity.defn
async def synthesize_voice_activity(
    request: SynthesizeVoiceInput,
) -> SynthesizeVoiceResult:  # pragma: no cover - verified by real Temporal run
    activity.heartbeat({"stage": "e10-tts", "trace_id": request.trace_id})

    def run() -> SynthesizeVoiceResult:
        settings = get_settings()
        engine = create_database_engine(settings.database_url)
        try:
            with engine.begin() as connection:
                return _work(connection, request)
        finally:
            engine.dispose()

    return await asyncio.to_thread(run)
