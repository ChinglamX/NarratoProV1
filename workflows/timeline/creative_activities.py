"""Activities for the E09 Creative Timeline workflow.

Each activity is DB-bound synchronous work run through :func:`asyncio.to_thread`;
planning, rhythm, narration review, assembly and the media-grounded preview
each get their own activity. All artifact identities arrive pre-allocated in
the request payloads so retries and replays converge on the same artifacts.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from typing import Any, TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import Connection, and_, select
from temporalio import activity

import packages.persistence.schema as schema
from apps.services.clip_index import PersistenceClipIndex
from apps.services.rhythm_planning import RhythmPlanningService
from apps.services.timeline_assembly import AssemblyArtifactIds, TimelineAssemblyService
from apps.services.timeline_planning import PlanningArtifactIds, TimelinePlanningService
from packages.artifacts.object_store import LocalObjectStore
from packages.contracts import (
    ActorKind,
    ActorRef,
    ArtifactRef,
    ArtifactType,
    Checksum,
    MasterTimeline,
    RationalTime,
)
from packages.contracts.timeline_intent import (
    ClipCandidate,
    ClipCandidateSet,
    ClipRetrievalQuery,
    ClipSelectionPlan,
    NarrationLineSet,
    NarrativeBeatGraph,
    RetrievalRoute,
)
from packages.foundation.settings import get_settings
from packages.persistence.artifact_repository import ArtifactRepository
from packages.persistence.artifact_writer import commit_contract_artifact, payload_checksum
from packages.persistence.database import create_database_engine
from packages.production import render_media_preview
from packages.timeline.intent_projection import (
    _deterministic_uuid4,
    project_original_audio_intents,
    project_subtitle_intents_from_narration,
)
from workflows.project.models import ArtifactPointer
from workflows.timeline.creative_models import (
    AssemblyActivityRequest,
    AssemblyActivityResult,
    ClipQuerySpec,
    MediaPreviewActivityRequest,
    MediaPreviewActivityResult,
    NarrationReviewActivityRequest,
    NarrationReviewActivityResult,
    PlanningIdSpec,
    RhythmPlanningActivityRequest,
    RhythmPlanningActivityResult,
    VisualPlanningActivityRequest,
    VisualPlanningActivityResult,
)

ACTOR = ActorRef(kind=ActorKind.SYSTEM, id="timeline-workflow")


T = TypeVar("T")


def _common(request: Any) -> dict[str, Any]:
    return {
        "project_id": UUID(request.project_id),
        "run_id": UUID(request.run_id),
        "variant_id": None,
        "trace_id": request.trace_id,
        "actor": ACTOR,
        "resource_profile_ref": _ref(request.resource_profile),
    }


def _run_activity(handler: Callable[[Connection], T]) -> T:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    try:
        with engine.begin() as connection:
            return handler(connection)
    finally:
        engine.dispose()


def _report_summary(
    repository: ArtifactRepository, connection: Connection, report_ref: ArtifactRef
) -> tuple[tuple[str, ...], float]:
    payload = repository.get_version(connection, report_ref)["payload_json"]
    blockers = tuple(finding["code"] for finding in payload["findings"] if finding["blocker"])
    return blockers, float(payload["evidence_coverage"])


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
        artifact_id=str(reference.artifact_id),
        version=reference.version,
        artifact_type=reference.artifact_type,
        checksum=str(reference.checksum) if reference.checksum else None,
    )


def _load_contract(
    connection: Connection,
    repository: ArtifactRepository,
    pointer: ArtifactPointer,
    contract: type[BaseModel],
) -> Any:
    row = repository.get_version(connection, _ref(pointer))
    payload = row.get("payload_json")
    if not isinstance(payload, dict):
        raise ValueError(f"{pointer.artifact_type} payload is unavailable")
    return contract.model_validate(payload)


def _query_specs(specs: tuple[ClipQuerySpec, ...]) -> tuple[ClipRetrievalQuery, ...]:
    queries = []
    for spec in specs:
        queries.append(
            ClipRetrievalQuery(
                beat_id=UUID(spec.beat_id),
                story_refs=tuple(UUID(item) for item in spec.story_refs),
                required_character_refs=tuple(UUID(item) for item in spec.required_character_refs),
                routes=tuple(RetrievalRoute(item) for item in spec.routes),
                top_k_per_route=spec.top_k_per_route,
            )
        )
    return tuple(queries)


def _planning_ids(spec: PlanningIdSpec | None) -> PlanningArtifactIds:
    if spec is None:
        return PlanningArtifactIds()
    return PlanningArtifactIds(
        candidate_set_id=UUID(spec.candidate_set_id),
        selection_plan_id=UUID(spec.selection_plan_id),
        continuity_report_id=UUID(spec.continuity_report_id),
        visual_report_id=UUID(spec.visual_report_id),
        crop_path_ids={UUID(key): UUID(value) for key, value in spec.crop_path_ids.items()},
        subtitle_plan_ids={UUID(key): UUID(value) for key, value in spec.subtitle_plan_ids.items()},
    )


def _plan_visual_sync(request: VisualPlanningActivityRequest) -> VisualPlanningActivityResult:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    try:
        with engine.begin() as connection:
            repository = ArtifactRepository()
            beat_graph = _load_contract(
                connection, repository, request.beat_graph, NarrativeBeatGraph
            )
            beat_graph_ref = _ref(request.beat_graph)
            source_durations = {
                UUID(key): Fraction(value) for key, value in request.source_durations.items()
            }
            index = PersistenceClipIndex(
                repository,
                connection,
                tuple(_ref(item) for item in request.candidate_sets),
                source_duration_by_ref=source_durations,
            )
            outcome = TimelinePlanningService(repository).plan_visual(
                connection,
                project_id=UUID(request.project_id),
                run_id=UUID(request.run_id),
                variant_id=None,
                trace_id=request.trace_id,
                actor=ACTOR,
                resource_profile_ref=_ref(request.resource_profile),
                beat_graph=beat_graph,
                beat_graph_ref=beat_graph_ref,
                queries=_query_specs(request.queries),
                index=index,
                ids=_planning_ids(request.ids),
            )
    finally:
        engine.dispose()
    return VisualPlanningActivityResult(
        candidate_set=_pointer(outcome.candidate_set_ref),
        selection_plan=_pointer(outcome.selection_plan_ref),
        continuity_report=_pointer(outcome.continuity_report_ref),
        visual_report=_pointer(outcome.visual_report_ref),
        crop_paths=tuple(_pointer(item) for item in outcome.crop_path_refs),
        subtitle_plans=tuple(_pointer(item) for item in outcome.subtitle_plan_refs),
        incomplete=outcome.incomplete,
    )


@activity.defn
async def plan_visual_activity(
    request: VisualPlanningActivityRequest,
) -> VisualPlanningActivityResult:
    activity.heartbeat({"stage": "visual-planning", "trace_id": request.trace_id})
    return await asyncio.to_thread(_plan_visual_sync, request)


def _plan_rhythm_sync(request: RhythmPlanningActivityRequest) -> RhythmPlanningActivityResult:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    try:
        with engine.begin() as connection:
            repository = ArtifactRepository()
            beat_graph = _load_contract(
                connection, repository, request.beat_graph, NarrativeBeatGraph
            )
            outcome = RhythmPlanningService(repository).plan_rhythm(
                connection,
                project_id=UUID(request.project_id),
                run_id=UUID(request.run_id),
                variant_id=None,
                trace_id=request.trace_id,
                actor=ACTOR,
                resource_profile_ref=_ref(request.resource_profile),
                beat_graph=beat_graph,
                beat_graph_ref=_ref(request.beat_graph),
                selection_plan_ref=_ref(request.selection_plan),
                rhythm_plan_id=UUID(request.rhythm_plan_id),
            )
    finally:
        engine.dispose()
    return RhythmPlanningActivityResult(
        rhythm_plan=_pointer(outcome.rhythm_plan_ref) if outcome.rhythm_plan_ref else None,
        conflict=(
            outcome.duration_conflict.model_dump(mode="json") if outcome.duration_conflict else None
        ),
    )


@activity.defn
async def plan_rhythm_activity(
    request: RhythmPlanningActivityRequest,
) -> RhythmPlanningActivityResult:
    activity.heartbeat({"stage": "rhythm-planning", "trace_id": request.trace_id})
    return await asyncio.to_thread(_plan_rhythm_sync, request)


def _review_narration_sync(
    request: NarrationReviewActivityRequest,
) -> NarrationReviewActivityResult:
    def work(connection: Connection) -> NarrationReviewActivityResult:
        repository = ArtifactRepository()
        line_set = _load_contract(connection, repository, request.line_set, NarrationLineSet)
        report_ref = RhythmPlanningService(repository).review_lines(
            connection,
            **_common(request),
            line_set=line_set,
            line_set_ref=_ref(request.line_set),
            dialogue_by_beat={UUID(key): value for key, value in request.dialogue_by_beat.items()},
            report_id=UUID(request.report_id),
        )
        blockers, coverage = _report_summary(repository, connection, report_ref)
        return NarrationReviewActivityResult(
            report=_pointer(report_ref), blocker_codes=blockers, evidence_coverage=coverage
        )

    return _run_activity(work)


@activity.defn
async def review_narration_activity(
    request: NarrationReviewActivityRequest,
) -> NarrationReviewActivityResult:
    activity.heartbeat({"stage": "narration-review", "trace_id": request.trace_id})
    return await asyncio.to_thread(_review_narration_sync, request)


def _load_assembly_inputs(
    connection: Connection, repository: ArtifactRepository, request: AssemblyActivityRequest
) -> tuple[ClipSelectionPlan, list[ClipCandidate], NarrationLineSet]:
    selections = _load_contract(connection, repository, request.selection_plan, ClipSelectionPlan)
    candidates: list[ClipCandidate] = []
    for pointer in request.candidate_sets:
        candidate_set = _load_contract(connection, repository, pointer, ClipCandidateSet)
        candidates.extend(candidate_set.candidates)
    if request.line_set is None:
        narration = NarrationLineSet(
            creative_brief_ref=_ref(request.selection_plan),
            rhythm_plan_ref=_ref(request.selection_plan),
            lines=(),
            estimated_duration=RationalTime(value=0, rate_num=1),
        )
    else:
        narration = _load_contract(connection, repository, request.line_set, NarrationLineSet)
    return selections, candidates, narration


def _assemble_sync(request: AssemblyActivityRequest) -> AssemblyActivityResult:
    def work(connection: Connection) -> AssemblyActivityResult:
        repository = ArtifactRepository()
        selections, candidates, narration = _load_assembly_inputs(connection, repository, request)
        if request.duration:
            duration = RationalTime.model_validate(request.duration)
        else:
            # Selected clip durations are microsecond-based (rate 1_000_000);
            # keep the same time base so assembled track ranges stay in seconds.
            duration = RationalTime(
                value=sum(s.selected_range.duration.value for s in selections.selections),
                rate_num=1_000_000,
            )
        audio_intents = project_original_audio_intents(selections, candidates)
        subtitle_intents = project_subtitle_intents_from_narration(
            narration, _ref(request.subtitle_style)
        )
        outcome = TimelineAssemblyService(repository).assemble(
            connection,
            **_common(request),
            timeline_id=UUID(request.timeline_id),
            selections=selections,
            candidates=candidates,
            narration=narration,
            audio_intents=audio_intents,
            subtitle_intents=subtitle_intents,
            overlay_intents=(),
            dependencies=(_ref(request.selection_plan),),
            duration=duration,
            ids=AssemblyArtifactIds(
                master_timeline_id=UUID(request.master_timeline_id),
                assembly_report_id=UUID(request.report_id),
                track_ids={key: UUID(value) for key, value in request.track_ids.items()},
                item_ids=tuple(UUID(item) for item in request.item_ids),
            ),
        )
        return AssemblyActivityResult(
            master_timeline=(
                _pointer(outcome.master_timeline_ref) if outcome.master_timeline_ref else None
            ),
            report=_pointer(outcome.assembly_report_ref),
            blocked=outcome.blocked,
            conflict_codes=outcome.conflict_codes,
        )

    return _run_activity(work)


@activity.defn
async def assemble_timeline_activity(
    request: AssemblyActivityRequest,
) -> AssemblyActivityResult:
    activity.heartbeat({"stage": "assembly", "trace_id": request.trace_id})
    return await asyncio.to_thread(_assemble_sync, request)


def _source_paths(
    connection: Connection,
    repository: ArtifactRepository,
    store: LocalObjectStore,
    timeline: MasterTimeline,
) -> dict[UUID, Path]:
    paths: dict[UUID, Path] = {}
    for track in timeline.tracks:
        for item in track.items:
            source_ref = item.source_ref
            if source_ref is None or source_ref.artifact_id in paths:
                continue
            payload = repository.get_version(connection, source_ref)["payload_json"]
            uri = payload.get("uri")
            if not uri:
                raise ValueError("source media payload has no object-store uri")
            paths[source_ref.artifact_id] = store.local_path(str(uri))
    return paths


def _render_media_sync(
    request: MediaPreviewActivityRequest, loop: asyncio.AbstractEventLoop
) -> MediaPreviewActivityResult:
    def heartbeat(done: int, total: int) -> None:
        loop.call_soon_threadsafe(
            activity.heartbeat,
            {"stage": "media-preview", "clip": done, "clips": total},
        )

    def work(connection: Connection) -> MediaPreviewActivityResult:
        repository = ArtifactRepository()
        timeline = _load_contract(connection, repository, request.timeline, MasterTimeline)
        store = LocalObjectStore(get_settings().object_store_root)
        source_paths = _source_paths(connection, repository, store, timeline)
        result = render_media_preview(
            timeline,
            source_paths,
            Path(request.output_path),
            target_width=request.target_width,
            target_height=request.target_height,
            progress=heartbeat,
        )
        media_digest = "sha256:" + sha256(result.output_path.read_bytes()).hexdigest()
        preview_id = _deterministic_uuid4(
            f"proxy-render:{request.timeline.artifact_id}:{request.timeline.version}"
        )
        payload = {
            "kind": "media-grounded",
            "output_path": str(result.output_path),
            "subtitle_path": str(result.subtitle_path),
            "media_checksum": media_digest,
            "qc": {
                "video_codec": result.video_codec,
                "audio_codec": result.audio_codec,
                "width": result.width,
                "height": result.height,
            },
        }
        existing = connection.scalar(
            select(schema.artifact_version.c.checksum).where(
                and_(
                    schema.artifact_version.c.artifact_id == preview_id,
                    schema.artifact_version.c.version == 1,
                )
            )
        )
        if existing is not None and str(existing) != payload_checksum(payload):
            raise ValueError("idempotent preview checksum changed")
        if existing is None:
            commit_contract_artifact(
                connection,
                repository,
                artifact_id=preview_id,
                artifact_type="ProxyRender",
                payload=payload,
                inputs=(_ref(request.timeline),),
                producer_module="timeline-preview",
                module_version="e09-j04-v1",
                rights_class="internal-preview",
                **_common(request),
            )
        return MediaPreviewActivityResult(
            preview=_pointer(
                ArtifactRef(
                    artifact_id=preview_id,
                    version=1,
                    artifact_type=ArtifactType("ProxyRender"),
                    checksum=Checksum(payload_checksum(payload)),
                )
            ),
            subtitle_path=str(result.subtitle_path),
            qc={
                "video_codec": result.video_codec,
                "audio_codec": result.audio_codec,
                "width": result.width,
                "height": result.height,
            },
        )

    return _run_activity(work)


@activity.defn
async def render_media_preview_activity(
    request: MediaPreviewActivityRequest,
) -> MediaPreviewActivityResult:
    activity.heartbeat({"stage": "media-preview", "trace_id": request.trace_id})
    # Rendering runs in a worker thread; activity.heartbeat must be invoked on
    # the event loop, so schedule it via call_soon_threadsafe from the thread.
    loop = asyncio.get_running_loop()
    return await asyncio.to_thread(_render_media_sync, request, loop)
