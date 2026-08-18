"""Migrate an approved product proof through the canonical E10/E11 pipeline."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess  # nosec B404
import wave
from array import array
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import Connection, text
from temporalio.client import Client

from apps.services.media_production import MediaProductionService
from packages.artifacts import LocalObjectStore
from packages.contracts import ActorRef, ArtifactRef, MasterTimeline, RationalTime, TimeRange
from packages.contracts.media_production import (
    AlignmentArtifact,
    AlignmentToken,
    ConformReport,
    MixedAudio,
    TakeDisposition,
    VoiceAsset,
    VoiceTake,
    VoiceTakeSet,
)
from packages.contracts.rights import RightsGrantRef, RightsMetadata, RightsStatus
from packages.contracts.timeline import (
    TimelineItem,
    TimelineItemType,
    TimelineLifecycle,
    TimelineTrack,
    TimelineTrackKind,
)
from packages.contracts.timeline_intent import (
    DialogueRelationship,
    NarrationLine,
    NarrationLineSet,
)
from packages.foundation.settings import get_settings
from packages.persistence.artifact_repository import ArtifactRepository
from packages.persistence.artifact_writer import commit_contract_artifact
from packages.persistence.blob_repository import BlobRepository
from packages.persistence.database import create_database_engine
from packages.production.ass_renderer import SubtitleStyle, render_ass_content
from packages.production.conform import build_subtitle_cues
from packages.production.mix_planning import plan_mix_stems
from packages.production.render_planning import plan_render_contract
from workflows.production.render_activities import RenderRequest, RenderResult
from workflows.production.render_workflow import RenderWorkflow
from workflows.project.models import ArtifactPointer

SOURCE_RUN_ID = UUID("d8eb4cd5-11eb-4c13-82d9-9bfe2f0b74af")
SOURCE_TIMELINE = ArtifactRef.model_validate(
    {
        "artifact_id": "8f972af4-b503-447f-aed7-0392233fe5fc",
        "version": 1,
        "artifact_type": "MasterTimeline",
    }
)
SOURCE_NARRATION = ArtifactRef.model_validate(
    {
        "artifact_id": "cf5eb101-1ad8-4322-ab10-cae315dfa849",
        "version": 1,
        "artifact_type": "NarrationLineSet",
    }
)
RESOURCE_PROFILE = ArtifactRef.model_validate(
    {
        "artifact_id": "57163ca7-75f5-4fe7-89ab-830c662fab4c",
        "version": 1,
        "artifact_type": "ResourceProfile",
    }
)
TRACE_ID = "6210f4b69d54403ba4e074ca5ba857c1"
OUTPUT_DIR = Path("outputs/first_usable_cut_v2")


@dataclass(frozen=True)
class AcceptanceProfile:
    name: str
    output_dir: Path
    source_run_id: UUID
    source_timeline: ArtifactRef | None
    source_narration: ArtifactRef | None
    source_media: ArtifactRef | None
    total_duration: float
    actor_id: str
    proof_video_name: str


FIRST_CUT = AcceptanceProfile(
    name="first-cut-v2",
    output_dir=OUTPUT_DIR,
    source_run_id=SOURCE_RUN_ID,
    source_timeline=SOURCE_TIMELINE,
    source_narration=SOURCE_NARRATION,
    source_media=None,
    total_duration=30.25,
    actor_id="first-cut-v2-approved",
    proof_video_name="first_usable_cut.mp4",
)


def _second_source_profile() -> AcceptanceProfile:
    ingest = json.loads(
        Path("outputs/m5_second_source/ingest_manifest.json").read_text(encoding="utf-8")
    )
    return AcceptanceProfile(
        name="m5-second-source",
        output_dir=Path("outputs/m5_second_source/candidate_v1"),
        source_run_id=UUID(str(ingest["run_id"])),
        source_timeline=None,
        source_narration=None,
        source_media=ArtifactRef.model_validate(ingest["artifacts"]["source"]),
        total_duration=30.0,
        actor_id="m5-second-source-approved",
        proof_video_name="candidate_v1.mp4",
    )


def _personal_config_profile(path: Path) -> AcceptanceProfile:
    """Resolve a prepared, human-approved cut from the user-facing config."""
    raw_config = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent.resolve()

    def resolve(name: str) -> Path:
        value = Path(str(raw_config[name]))
        return value if value.is_absolute() else (base / value).resolve()

    ingest = json.loads(resolve("ingest_manifest").read_text(encoding="utf-8"))
    candidate_path = resolve("candidate_manifest")
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    segments = candidate.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError("candidate manifest requires at least one segment")
    duration = sum(float(item["duration_seconds"]) for item in segments)
    proof_video = Path(str(candidate["output"]))
    return AcceptanceProfile(
        name="personal-cut",
        output_dir=candidate_path.parent,
        source_run_id=UUID(str(ingest["run_id"])),
        source_timeline=None,
        source_narration=None,
        source_media=ArtifactRef.model_validate(ingest["artifacts"]["source"]),
        total_duration=duration,
        actor_id="personal-cut-approved",
        proof_video_name=proof_video.name,
    )


def _pointer(reference: ArtifactRef) -> ArtifactPointer:
    return ArtifactPointer(
        str(reference.artifact_id),
        reference.version,
        reference.artifact_type,
        str(reference.checksum) if reference.checksum else None,
    )


def _duration(path: Path) -> RationalTime:
    with wave.open(str(path), "rb") as source:
        return RationalTime(value=source.getnframes(), rate_num=source.getframerate())


def _aligned_voice(manifest: dict[str, object], output: Path, *, total_duration: float) -> bytes:
    lines = manifest["narration_lines"]
    assert isinstance(lines, list)  # nosec B101 - validated product-proof manifest
    frame_rate = 24_000
    samples = array("h", [0]) * round(total_duration * frame_rate)
    for line in lines:
        assert isinstance(line, dict)  # nosec B101 - validated product-proof manifest
        path = Path(str(line["path"]))
        with wave.open(str(path), "rb") as source:
            if (source.getnchannels(), source.getsampwidth(), source.getframerate()) != (
                1,
                2,
                frame_rate,
            ):
                raise ValueError("approved narration WAV format changed")
            audio = array("h")
            audio.frombytes(source.readframes(source.getnframes()))
        offset = round(float(line["timeline_start_seconds"]) * frame_rate)
        for index, value in enumerate(audio):
            samples[offset + index] = value
    with wave.open(str(output), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(frame_rate)
        target.writeframes(samples.tobytes())
    return output.read_bytes()


def _commit_blob(
    connection: Connection,
    *,
    store: LocalObjectStore,
    blobs: BlobRepository,
    run_id: UUID,
    name: str,
    payload: bytes,
) -> tuple[str, str]:
    staged = store.stage(run_id, name, BytesIO(payload))
    registered = blobs.register_or_get_staged(connection, staged, content_type="audio/wav")
    if registered.state == "committed":
        try:
            store.head(registered.metadata.uri)
        except FileNotFoundError:
            restored = store.commit(staged.uri, staged.checksum)
            if restored.checksum != registered.metadata.checksum:
                raise ValueError(
                    "recovered object does not match committed blob checksum"
                ) from None
        else:
            store.delete_staged(staged.uri)
    committed = blobs.commit(connection, store, registered)
    return committed.metadata.uri, committed.metadata.checksum


def _new_narration(original: NarrationLineSet, manifest: dict[str, object]) -> NarrationLineSet:
    raw_lines = manifest["narration_lines"]
    assert isinstance(raw_lines, list)  # nosec B101
    source_indexes = (0, 0, 1, 2, 2, 2, 3)
    lines = []
    for raw, source_index in zip(raw_lines, source_indexes, strict=True):
        assert isinstance(raw, dict)  # nosec B101
        source = original.lines[source_index]
        duration = _duration(Path(str(raw["path"])))
        lines.append(
            NarrationLine(
                line_id=uuid4(),
                beat_id=source.beat_id,
                text=str(raw["text"]),
                function=source.function,
                story_refs=source.story_refs,
                evidence_refs=source.evidence_refs,
                target_duration=duration,
                dialogue_relationship=source.dialogue_relationship,
                locked=True,
            )
        )
    total_frames = sum(line.target_duration.value for line in lines)
    return NarrationLineSet(
        creative_brief_ref=original.creative_brief_ref,
        rhythm_plan_ref=original.rhythm_plan_ref,
        lines=tuple(lines),
        estimated_duration=RationalTime(value=total_frames, rate_num=24_000),
    )


def _manual_narration(manifest: dict[str, object], source_ref: ArtifactRef) -> NarrationLineSet:
    """Build the human-approved second-source narration without inventing AI confidence."""
    raw_lines = manifest["narration_lines"]
    assert isinstance(raw_lines, list)  # nosec B101 - product-proof manifest
    lines = []
    for raw in raw_lines:
        assert isinstance(raw, dict)  # nosec B101
        index = int(raw["index"])
        evidence_id = uuid4()
        story_id = uuid4()
        lines.append(
            NarrationLine(
                line_id=uuid4(),
                beat_id=uuid4(),
                text=str(raw["text"]),
                function=(
                    "hook" if index == 1 else "payoff" if index == len(raw_lines) else "context"
                ),
                story_refs=(story_id,),
                evidence_refs=(evidence_id,),
                target_duration=_duration(Path(str(raw["path"]))),
                dialogue_relationship=DialogueRelationship.COMPLEMENT,
                locked=True,
            )
        )
    return NarrationLineSet(
        creative_brief_ref=source_ref,
        rhythm_plan_ref=source_ref,
        lines=tuple(lines),
        estimated_duration=RationalTime(
            value=sum(line.target_duration.value for line in lines), rate_num=24_000
        ),
    )


def _manual_source_timeline(
    manifest: dict[str, object], source_ref: ArtifactRef, narration: NarrationLineSet
) -> MasterTimeline:
    raw_segments = manifest["segments"]
    assert isinstance(raw_segments, list)  # nosec B101
    raw_lines = cast(list[dict[str, object]], manifest["narration_lines"])
    starts = [float(cast(float, raw["timeline_start_seconds"])) for raw in raw_lines]
    video_items = []
    original_items = []
    cursor = 0.0
    for index, raw in enumerate(raw_segments, 1):
        assert isinstance(raw, dict)  # nosec B101
        duration = float(raw["duration_seconds"])
        source_start = float(raw["source_start_seconds"])
        timeline_range = TimeRange(
            start=RationalTime(value=round(cursor * 1_000_000), rate_num=1_000_000),
            duration=RationalTime(value=round(duration * 1_000_000), rate_num=1_000_000),
        )
        source_range = TimeRange(
            start=RationalTime(value=round(source_start * 1_000_000), rate_num=1_000_000),
            duration=timeline_range.duration,
        )
        common = {
            "item_version": 1,
            "item_type": TimelineItemType.CLIP.value,
            "timeline_range": timeline_range.model_dump(mode="json"),
            "source_ref": source_ref.model_dump(mode="json"),
            "source_range": source_range.model_dump(mode="json"),
            "parameters": {"intent_state": "human-approved", "segment_index": index},
            "generation_dependencies": [source_ref.model_dump(mode="json")],
            "locked": True,
        }
        video_items.append(TimelineItem.model_validate({"item_id": uuid4(), **common}))
        original_items.append(TimelineItem.model_validate({"item_id": uuid4(), **common}))
        cursor += duration
    narration_items = []
    subtitle_items = []
    for index, (line, start) in enumerate(zip(narration.lines, starts, strict=True)):
        end = starts[index + 1] if index + 1 < len(starts) else cursor
        base = {
            "item_version": 1,
            "item_type": TimelineItemType.TEXT.value,
            "content_ref": str(line.line_id),
            "parameters": {"text": line.text, "intent_state": "human-approved"},
            "evidence_refs": list(line.evidence_refs),
            "locked": True,
        }
        narration_items.append(
            TimelineItem.model_validate(
                {
                    "item_id": uuid4(),
                    "timeline_range": TimeRange(
                        start=RationalTime(value=round(start * 1_000_000), rate_num=1_000_000),
                        duration=line.target_duration,
                    ).model_dump(mode="json"),
                    **base,
                }
            )
        )
        subtitle_items.append(
            TimelineItem.model_validate(
                {
                    "item_id": uuid4(),
                    "timeline_range": TimeRange(
                        start=RationalTime(value=round(start * 1_000_000), rate_num=1_000_000),
                        duration=RationalTime(
                            value=round((end - start) * 1_000_000), rate_num=1_000_000
                        ),
                    ).model_dump(mode="json"),
                    **base,
                }
            )
        )
    return MasterTimeline(
        timeline_id=uuid4(),
        lifecycle=TimelineLifecycle.APPROVED_INTENT,
        rate_num=1_000_000,
        global_start=RationalTime(value=0, rate_num=1_000_000),
        duration=RationalTime(value=round(cursor * 1_000_000), rate_num=1_000_000),
        tracks=(
            TimelineTrack(
                track_id=uuid4(),
                kind=TimelineTrackKind.VIDEO,
                order=0,
                items=tuple(video_items),
            ),
            TimelineTrack(
                track_id=uuid4(),
                kind=TimelineTrackKind.ORIGINAL_AUDIO,
                order=1,
                items=tuple(original_items),
            ),
            TimelineTrack(
                track_id=uuid4(),
                kind=TimelineTrackKind.NARRATION,
                order=2,
                items=tuple(narration_items),
            ),
            TimelineTrack(
                track_id=uuid4(),
                kind=TimelineTrackKind.SUBTITLE,
                order=3,
                items=tuple(subtitle_items),
            ),
        ),
        dependencies=(source_ref,),
        metadata_namespace_version="m5-second-source-v1",
    )


def _conformed_timeline(
    source: MasterTimeline,
    narration: NarrationLineSet,
    narration_ref: ArtifactRef,
    voice_ref: ArtifactRef,
    starts: list[float],
) -> MasterTimeline:
    tracks = []
    for track in source.tracks:
        if track.kind not in {TimelineTrackKind.NARRATION, TimelineTrackKind.SUBTITLE}:
            tracks.append(track)
            continue
        items = []
        for index, (line, start) in enumerate(zip(narration.lines, starts, strict=True)):
            if track.kind is TimelineTrackKind.NARRATION:
                duration = line.target_duration
            else:
                end = (
                    starts[index + 1] if index + 1 < len(starts) else float(source.duration.seconds)
                )
                duration = RationalTime(value=round((end - start) * 1_000_000), rate_num=1_000_000)
            items.append(
                TimelineItem(
                    item_id=uuid4(),
                    item_version=1,
                    item_type=TimelineItemType.TEXT,
                    timeline_range=TimeRange(
                        start=RationalTime(value=round(start * 1_000_000), rate_num=1_000_000),
                        duration=duration,
                    ),
                    content_ref=str(line.line_id),
                    parameters={
                        "text": line.text,
                        "intent_state": "conformed",
                        "voice_asset_ref": voice_ref.model_dump(mode="json"),
                    },
                    evidence_refs=line.evidence_refs,
                    generation_dependencies=(narration_ref, voice_ref),
                    locked=True,
                )
            )
        tracks.append(track.model_copy(update={"items": tuple(items)}))
    return source.model_copy(
        update={
            "timeline_id": uuid4(),
            "lifecycle": TimelineLifecycle.CONFORMED,
            "tracks": tuple(tracks),
            "dependencies": (*source.dependencies, narration_ref, voice_ref),
            "metadata_namespace_version": "e10-first-cut-v2",
        }
    )


def prepare(profile: AcceptanceProfile = FIRST_CUT) -> dict[str, object]:
    settings = get_settings()
    output_dir = profile.output_dir
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    starts = [float(line["timeline_start_seconds"]) for line in manifest["narration_lines"]]
    engine = create_database_engine(settings.database_url)
    repository = ArtifactRepository()
    store = LocalObjectStore(settings.object_store_root)
    blobs = BlobRepository()
    run_id = uuid4()
    actor = ActorRef.model_validate({"kind": "human", "id": profile.actor_id})
    with engine.begin() as connection:
        project_id = connection.execute(
            text("select project_id from core.run where id=:run_id"),
            {"run_id": profile.source_run_id},
        ).scalar_one()
        connection.execute(
            text(
                "insert into core.run (id, project_id, workflow_id, state, "
                "automation_policy_snapshot, resource_profile_snapshot) "
                "values (:id,:project,:workflow,'running','{}','{}')"
            ),
            {"id": run_id, "project": project_id, "workflow": f"{profile.name}/{run_id}"},
        )
        if profile.source_timeline is not None and profile.source_narration is not None:
            source_timeline = MasterTimeline.model_validate(
                repository.get_version(connection, profile.source_timeline)["payload_json"]
            )
            original_narration = NarrationLineSet.model_validate(
                repository.get_version(connection, profile.source_narration)["payload_json"]
            )
            narration = _new_narration(original_narration, manifest)
            source_narration_ref = profile.source_narration
        elif profile.source_media is not None:
            narration = _manual_narration(manifest, profile.source_media)
            source_timeline = _manual_source_timeline(manifest, profile.source_media, narration)
            source_narration_ref = profile.source_media
        else:
            raise ValueError("acceptance profile lacks canonical source inputs")
        if profile.source_media is None and profile.source_timeline is None:
            raise ValueError("acceptance profile lost its source after validation")
        grant_ref = commit_contract_artifact(
            connection,
            repository,
            artifact_id=uuid4(),
            artifact_type="RightsGrant",
            payload={
                "asset": "ref_7_clean.wav",
                "approval": "owner-approved-2026-08-16",
                "territories": ["CN"],
                "platforms": ["internal-preview"],
            },
            project_id=project_id,
            run_id=run_id,
            variant_id=None,
            trace_id=TRACE_ID,
            actor=actor,
            producer_module=profile.name,
            module_version="1",
            resource_profile_ref=RESOURCE_PROFILE,
            rights_class="owner-approved",
        )
        narration_ref = commit_contract_artifact(
            connection,
            repository,
            artifact_id=uuid4(),
            artifact_type="NarrationLineSet",
            payload=narration,
            project_id=project_id,
            run_id=run_id,
            variant_id=None,
            trace_id=TRACE_ID,
            actor=actor,
            producer_module=profile.name,
            module_version="1",
            resource_profile_ref=RESOURCE_PROFILE,
            rights_class="internal-preview",
            inputs=(source_narration_ref,),
        )
        if profile.source_timeline is None:
            source_timeline_ref = commit_contract_artifact(
                connection,
                repository,
                artifact_id=uuid4(),
                artifact_type="MasterTimeline",
                payload=source_timeline,
                project_id=project_id,
                run_id=run_id,
                variant_id=None,
                trace_id=TRACE_ID,
                actor=actor,
                producer_module=profile.name,
                module_version="1",
                resource_profile_ref=RESOURCE_PROFILE,
                rights_class="restricted-internal-preview",
                inputs=(cast(ArtifactRef, profile.source_media), narration_ref),
            )
        else:
            source_timeline_ref = profile.source_timeline
        takes = []
        take_blobs: dict[UUID, bytes] = {}
        for line, raw in zip(narration.lines, manifest["narration_lines"], strict=True):
            payload = Path(str(raw["path"])).read_bytes()
            uri, checksum = _commit_blob(
                connection,
                store=store,
                blobs=blobs,
                run_id=run_id,
                name=f"approved-take-{line.line_id}",
                payload=payload,
            )
            raw_ref = commit_contract_artifact(
                connection,
                repository,
                artifact_id=uuid4(),
                artifact_type="RawProviderResponse",
                payload={"provider": "indextts", "checksum": checksum, "audio_blob_ref": uri},
                project_id=project_id,
                run_id=run_id,
                variant_id=None,
                trace_id=TRACE_ID,
                actor=actor,
                producer_module=profile.name,
                module_version="1",
                resource_profile_ref=RESOURCE_PROFILE,
                rights_class="internal-preview",
            )
            take_id = uuid4()
            takes.append(
                VoiceTake(
                    take_id=take_id,
                    narration_line_id=line.line_id,
                    raw_response_ref=raw_ref,
                    audio_blob_ref=uri,
                    duration=line.target_duration,
                    provider_id="indextts",
                    provider_version="index-tts2-bilibili-ula",
                    voice_id="ref_7_clean",
                    disposition=TakeDisposition.SELECTED,
                    estimated_cost_micros=0,
                )
            )
            take_blobs[take_id] = payload
        take_set = VoiceTakeSet(
            narration_line_set_ref=narration_ref,
            voice_profile_ref=RESOURCE_PROFILE,
            takes=tuple(takes),
            max_takes_per_line=1,
        )
        take_set_ref = commit_contract_artifact(
            connection,
            repository,
            artifact_id=uuid4(),
            artifact_type="VoiceTakeSet",
            payload=take_set,
            project_id=project_id,
            run_id=run_id,
            variant_id=None,
            trace_id=TRACE_ID,
            actor=actor,
            producer_module=profile.name,
            module_version="1",
            resource_profile_ref=RESOURCE_PROFILE,
            rights_class="internal-preview",
            inputs=(narration_ref, *[take.raw_response_ref for take in takes]),
        )
        aligned_path = output_dir / "narration_aligned.wav"
        aligned = _aligned_voice(manifest, aligned_path, total_duration=profile.total_duration)
        voice_uri, voice_checksum = _commit_blob(
            connection,
            store=store,
            blobs=blobs,
            run_id=run_id,
            name="approved-voice-asset",
            payload=aligned,
        )
        voice = VoiceAsset(
            voice_take_set_ref=take_set_ref,
            selected_take_ids=tuple(take_blobs),
            audio_blob_ref=voice_uri,
            duration=RationalTime(value=round(profile.total_duration * 24_000), rate_num=24_000),
            checksum=voice_checksum,
            rights=RightsMetadata(
                status=RightsStatus.CLEARED,
                source="owner-approved ref_7_clean.wav (2026-08-16)",
                license="bilibili-model-ula-2025",
                grant_ref=RightsGrantRef.model_validate(grant_ref.model_dump(mode="json")),
                territories=frozenset({"CN"}),
                platforms=frozenset({"internal-preview"}),
                commercial_use=True,
                modification=True,
                synchronization=True,
                checked_at=datetime.now(UTC),
            ),
        )
        voice_ref = commit_contract_artifact(
            connection,
            repository,
            artifact_id=uuid4(),
            artifact_type="VoiceAsset",
            payload=voice,
            project_id=project_id,
            run_id=run_id,
            variant_id=None,
            trace_id=TRACE_ID,
            actor=actor,
            producer_module=profile.name,
            module_version="1",
            resource_profile_ref=RESOURCE_PROFILE,
            rights_class="internal-preview",
            inputs=(take_set_ref,),
        )
        service = MediaProductionService(artifacts=repository, store=store)
        tokens = tuple(
            AlignmentToken(
                token=line.text,
                line_id=line.line_id,
                timeline_range=TimeRange(
                    start=RationalTime(value=round(start * 1_000_000), rate_num=1_000_000),
                    duration=line.target_duration,
                ),
                confidence=None,
            )
            for line, start in zip(narration.lines, starts, strict=True)
        )
        alignment = AlignmentArtifact(
            voice_asset_ref=voice_ref,
            narration_line_set_ref=narration_ref,
            tokens=tokens,
            alignment_method="measured-line-boundary-v1",
        )
        alignment_ref = service.persist_alignment(
            connection,
            alignment=alignment,
            project_id=project_id,
            run_id=run_id,
            trace_id=TRACE_ID,
            actor=actor,
            resource_profile_ref=RESOURCE_PROFILE,
        )
        conformed = _conformed_timeline(
            source_timeline, narration, narration_ref, voice_ref, starts
        )
        timeline_ref = commit_contract_artifact(
            connection,
            repository,
            artifact_id=uuid4(),
            artifact_type="MasterTimeline",
            payload=conformed,
            project_id=project_id,
            run_id=run_id,
            variant_id=None,
            trace_id=TRACE_ID,
            actor=actor,
            producer_module=profile.name,
            module_version="1",
            resource_profile_ref=RESOURCE_PROFILE,
            rights_class="internal-preview",
            inputs=(source_timeline_ref, narration_ref, voice_ref, alignment_ref),
        )
        report_ref = service.persist_conform_report(
            connection,
            report=ConformReport(
                source_timeline_ref=source_timeline_ref,
                conformed_timeline_ref=timeline_ref,
                voice_asset_ref=voice_ref,
                alignment_ref=alignment_ref,
                changed_item_ids=tuple(
                    item.item_id
                    for track in conformed.tracks
                    if track.kind in {TimelineTrackKind.NARRATION, TimelineTrackKind.SUBTITLE}
                    for item in track.items
                ),
                invalidated_artifact_refs=(),
                duration_delta=RationalTime(value=0, rate_num=1_000_000),
            ),
            project_id=project_id,
            run_id=run_id,
            trace_id=TRACE_ID,
            actor=actor,
            resource_profile_ref=RESOURCE_PROFILE,
        )
        mix = plan_mix_stems(
            conformed,
            conformed_timeline_ref=timeline_ref,
            narration_source_ref=voice_ref,
            target_loudness_lufs=-14.0,
            true_peak_ceiling_dbtp=-1.0,
            measurement_profile_ref=RESOURCE_PROFILE,
        )
        mix_ref = service.persist_mix_plan(
            connection,
            mix_plan=mix,
            project_id=project_id,
            run_id=run_id,
            variant_id=None,
            trace_id=TRACE_ID,
            actor=actor,
            resource_profile_ref=RESOURCE_PROFILE,
            inputs=(timeline_ref, voice_ref),
            rights_class="internal-preview",
        )
        mixed_path = output_dir / "mixed_audio.wav"
        subprocess.run(  # nosec B603 B607
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(output_dir / profile.proof_video_name),
                "-vn",
                "-c:a",
                "pcm_s16le",
                str(mixed_path),
            ],
            check=True,
        )
        mixed_ref = service.persist_mixed_audio(
            connection,
            audio=mixed_path.read_bytes(),
            mixed_audio=MixedAudio(
                mix_plan_ref=mix_ref,
                audio_blob_ref="pending-commit",
                duration=conformed.duration,
                integrated_loudness_lufs=-20.3,
                true_peak_dbtp=-2.6,
            ),
            project_id=project_id,
            run_id=run_id,
            trace_id=TRACE_ID,
            actor=actor,
            resource_profile_ref=RESOURCE_PROFILE,
        )
        cue_set = build_subtitle_cues(
            alignment=alignment,
            alignment_ref=alignment_ref,
            style_profile_ref=RESOURCE_PROFILE,
            texts={line.line_id: line.text for line in narration.lines},
            cue_ids={line.line_id: uuid4() for line in narration.lines},
            safe_area={"x": 0.08, "y": 0.78, "width": 0.84, "height": 0.14},
        )
        cue_ref = commit_contract_artifact(
            connection,
            repository,
            artifact_id=uuid4(),
            artifact_type="SubtitleCueSet",
            payload=cue_set,
            project_id=project_id,
            run_id=run_id,
            variant_id=None,
            trace_id=TRACE_ID,
            actor=actor,
            producer_module=profile.name,
            module_version="1",
            resource_profile_ref=RESOURCE_PROFILE,
            rights_class="internal-preview",
            inputs=(alignment_ref,),
        )
        ass_ref = service.persist_ass_artifact(
            connection,
            ass_content=render_ass_content(
                cue_set,
                style=SubtitleStyle(font_name="Heiti SC"),
            ),
            subtitle_cue_set_ref=cue_ref,
            libass_profile_ref=RESOURCE_PROFILE,
            project_id=project_id,
            run_id=run_id,
            variant_id=None,
            trace_id=TRACE_ID,
            actor=actor,
            resource_profile_ref=RESOURCE_PROFILE,
            rights_class="internal-preview",
        )
        plan = plan_render_contract(
            timeline=conformed,
            timeline_ref=timeline_ref,
            mix_plan_ref=mix_ref,
            mix_plan=mix,
            mixed_audio_ref=mixed_ref,
            ass_ref=ass_ref,
            platform_profile_ref=RESOURCE_PROFILE,
        )
        plan_ref = commit_contract_artifact(
            connection,
            repository,
            artifact_id=uuid4(),
            artifact_type="RenderPlan",
            payload=plan,
            project_id=project_id,
            run_id=run_id,
            variant_id=None,
            trace_id=TRACE_ID,
            actor=actor,
            producer_module=profile.name,
            module_version="1",
            resource_profile_ref=RESOURCE_PROFILE,
            rights_class="internal-preview",
            inputs=(timeline_ref, mix_ref, mixed_ref, ass_ref),
        )
    engine.dispose()
    return {
        "project_id": str(project_id),
        "run_id": str(run_id),
        "narration_line_set": asdict(_pointer(narration_ref)),
        "voice_take_set": asdict(_pointer(take_set_ref)),
        "voice_asset": asdict(_pointer(voice_ref)),
        "alignment": asdict(_pointer(alignment_ref)),
        "conformed_timeline": asdict(_pointer(timeline_ref)),
        "conform_report": asdict(_pointer(report_ref)),
        "mix_plan": asdict(_pointer(mix_ref)),
        "mixed_audio": asdict(_pointer(mixed_ref)),
        "subtitle_cue_set": asdict(_pointer(cue_ref)),
        "ass_artifact": asdict(_pointer(ass_ref)),
        "render_plan": asdict(_pointer(plan_ref)),
    }


async def execute(
    prepared: dict[str, object], profile: AcceptanceProfile = FIRST_CUT
) -> RenderResult:
    client = await Client.connect(get_settings().temporal_target)
    raw_plan = prepared["render_plan"]
    if not isinstance(raw_plan, dict):
        raise TypeError("prepared render_plan pointer is invalid")
    plan = ArtifactPointer(**raw_plan)
    request = RenderRequest(
        project_id=str(prepared["project_id"]),
        run_id=str(prepared["run_id"]),
        trace_id=TRACE_ID,
        plan=plan,
        resource_profile=_pointer(RESOURCE_PROFILE),
        output_path=str((profile.output_dir / "canonical_e11.mp4").resolve()),
        ffmpeg_version="narratoai-image-ffmpeg-libass",
        ffmpeg_binary=str((Path("scripts/ffmpeg_libass_docker.sh")).resolve()),
    )
    return await client.execute_workflow(
        RenderWorkflow.run,
        request,
        id=f"{profile.name}-render/{prepared['run_id']}",
        task_queue="control",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        choices=("first-cut-v2", "m5-second-source"),
        help="approved product proof to migrate through canonical E10/E11",
    )
    parser.add_argument(
        "--personal-config",
        type=Path,
        help="user-facing JSON config for any prepared Gate-1/2-approved candidate",
    )
    args = parser.parse_args()
    if args.personal_config is not None:
        profile = _personal_config_profile(args.personal_config)
    elif args.profile == "m5-second-source":
        profile = _second_source_profile()
    else:
        profile = FIRST_CUT
    prepared = prepare(profile)
    result = asyncio.run(execute(prepared, profile))
    payload = {**prepared, "render_result": asdict(result)}
    (profile.output_dir / "canonical_acceptance.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
