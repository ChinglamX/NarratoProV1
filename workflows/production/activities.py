"""E10 planning activities: mix plan, subtitle cues, ASS render (persisted)."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import Connection
from temporalio import activity

from apps.services.media_production import MediaProductionService
from packages.artifacts import LocalObjectStore
from packages.contracts import ActorRef, ArtifactRef, MasterTimeline
from packages.contracts.media_production import SubtitleCue, SubtitleCueSet
from packages.contracts.timeline_intent import NarrationLineSet
from packages.foundation.settings import get_settings
from packages.persistence.artifact_repository import ArtifactRepository
from packages.persistence.artifact_writer import commit_contract_artifact
from packages.persistence.database import create_database_engine
from packages.production.ass_renderer import render_ass_content
from packages.production.mix_planning import plan_mix_stems
from workflows.project.models import ArtifactPointer

ACTOR = ActorRef.model_validate({"kind": "human", "id": "e10-planning"})
T = TypeVar("T", bound=BaseModel)
U = TypeVar("U")


@dataclass(frozen=True)
class PlanMixInput:
    project_id: str
    run_id: str
    trace_id: str
    timeline: ArtifactPointer
    narration_source: ArtifactPointer  # voice asset when TTS exists, else narration line set
    style_profile: ArtifactPointer
    resource_profile: ArtifactPointer
    mix_plan_id: str | None = None
    target_loudness_lufs: float = -14.0
    true_peak_ceiling_dbtp: float = -1.0


@dataclass(frozen=True)
class BuildSubtitleInput:
    project_id: str
    run_id: str
    trace_id: str
    narration_line_set: ArtifactPointer
    style_profile: ArtifactPointer
    resource_profile: ArtifactPointer
    cue_set_id: str | None = None


@dataclass(frozen=True)
class RenderAssInput:
    project_id: str
    run_id: str
    trace_id: str
    cue_set: ArtifactPointer
    libass_profile: ArtifactPointer
    resource_profile: ArtifactPointer
    ass_artifact_id: str | None = None


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


def _load(
    repository: ArtifactRepository,
    connection: Connection,
    pointer: ArtifactPointer,
    model: type,
) -> Any:
    payload = repository.get_version(connection, _ref(pointer))["payload_json"]
    return model.model_validate(payload)  # type: ignore[attr-defined]


def _run_activity(handler: Callable[[Connection], U]) -> U:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    try:
        with engine.begin() as connection:
            return handler(connection)
    finally:
        engine.dispose()


def _build_cues_from_narration(narration: NarrationLineSet) -> tuple[SubtitleCue, ...]:
    from packages.contracts import TimeRange

    cues: list[SubtitleCue] = []
    cursor = 0.0
    for line in narration.lines:
        duration = float(line.target_duration.seconds)
        cues.append(
            SubtitleCue(
                cue_id=uuid4(),
                line_id=line.line_id,
                timeline_range=TimeRange.model_validate(
                    {
                        "start": {"value": round(cursor * 1_000_000), "rate_num": 1_000_000},
                        "duration": {"value": round(duration * 1_000_000), "rate_num": 1_000_000},
                    }
                ),
                text=line.text,
                style_ref="primary",
                safe_area={"y": 0.8, "height": 0.14},
            )
        )
        cursor += duration
    return tuple(cues)


@activity.defn
async def plan_mix_activity(request: PlanMixInput) -> ArtifactPointer:  # pragma: no cover
    activity.heartbeat({"stage": "e10-plan-mix", "trace_id": request.trace_id})

    def work(connection: Connection) -> ArtifactPointer:
        repository = ArtifactRepository()
        timeline: MasterTimeline = _load(repository, connection, request.timeline, MasterTimeline)
        service = MediaProductionService(
            artifacts=repository, store=LocalObjectStore(get_settings().object_store_root)
        )
        mix_plan = plan_mix_stems(
            timeline,
            conformed_timeline_ref=_ref(request.timeline),
            narration_source_ref=_ref(request.narration_source),
            target_loudness_lufs=request.target_loudness_lufs,
            true_peak_ceiling_dbtp=request.true_peak_ceiling_dbtp,
            measurement_profile_ref=_ref(request.style_profile),
        )
        mix_ref = service.persist_mix_plan(
            connection,
            mix_plan=mix_plan,
            project_id=UUID(request.project_id),
            run_id=UUID(request.run_id),
            variant_id=None,
            trace_id=request.trace_id,
            actor=ACTOR,
            resource_profile_ref=_ref(request.resource_profile),
            inputs=(_ref(request.timeline),),
            rights_class="internal-planning",
            mix_plan_id=UUID(request.mix_plan_id) if request.mix_plan_id else None,
        )
        return _pointer(mix_ref)

    return await asyncio.to_thread(lambda: _run_activity(work))


@activity.defn
async def build_subtitle_activity(
    request: BuildSubtitleInput,
) -> ArtifactPointer:  # pragma: no cover
    activity.heartbeat({"stage": "e10-build-subtitle", "trace_id": request.trace_id})

    def work(connection: Connection) -> ArtifactPointer:
        repository = ArtifactRepository()
        narration: NarrationLineSet = _load(
            repository, connection, request.narration_line_set, NarrationLineSet
        )
        cue_set = SubtitleCueSet(
            alignment_ref=_ref(request.narration_line_set),
            cues=_build_cues_from_narration(narration),
            style_profile_ref=_ref(request.style_profile),
        )
        cue_ref = commit_contract_artifact(
            connection,
            repository,
            artifact_id=UUID(request.cue_set_id) if request.cue_set_id else uuid4(),
            artifact_type="SubtitleCueSet",
            payload=cue_set,
            project_id=UUID(request.project_id),
            run_id=UUID(request.run_id),
            variant_id=None,
            trace_id=request.trace_id,
            actor=ACTOR,
            producer_module="e10-planning",
            module_version="v1",
            resource_profile_ref=_ref(request.resource_profile),
            rights_class="internal-planning",
            inputs=(_ref(request.narration_line_set),),
        )
        return _pointer(cue_ref)

    return await asyncio.to_thread(lambda: _run_activity(work))


@activity.defn
async def render_ass_activity(request: RenderAssInput) -> ArtifactPointer:  # pragma: no cover
    activity.heartbeat({"stage": "e10-render-ass", "trace_id": request.trace_id})

    def work(connection: Connection) -> ArtifactPointer:
        repository = ArtifactRepository()
        cue_set: SubtitleCueSet = _load(repository, connection, request.cue_set, SubtitleCueSet)
        service = MediaProductionService(
            artifacts=repository, store=LocalObjectStore(get_settings().object_store_root)
        )
        ass_ref = service.persist_ass_artifact(
            connection,
            ass_content=render_ass_content(cue_set),
            subtitle_cue_set_ref=_ref(request.cue_set),
            libass_profile_ref=_ref(request.libass_profile),
            project_id=UUID(request.project_id),
            run_id=UUID(request.run_id),
            variant_id=None,
            trace_id=request.trace_id,
            actor=ACTOR,
            resource_profile_ref=_ref(request.resource_profile),
            rights_class="internal-planning",
            ass_artifact_id=UUID(request.ass_artifact_id) if request.ass_artifact_id else None,
        )
        return _pointer(ass_ref)

    return await asyncio.to_thread(lambda: _run_activity(work))
