"""E09 J04 application service: compile creative intents into one Master Timeline.

Orchestrates :func:`assemble_multitrack_timeline` and persists the single
canonical ``MasterTimeline`` plus its ``TimelineAssemblyReport`` with exact
dependencies. Blocking conflicts keep the outcome fail-closed: no Master
Timeline artifact is committed, only the explanatory report.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from sqlalchemy import Connection

from packages.contracts import ActorRef, ArtifactRef, RationalTime
from packages.contracts.timeline import TimelineTrackKind
from packages.contracts.timeline_intent import (
    AudioIntent,
    AudioIntentRole,
    ClipCandidate,
    ClipSelectionPlan,
    NarrationLineSet,
    OverlayIntent,
    SubtitleIntent,
)
from packages.observability import MetricPoint
from packages.persistence.artifact_repository import ArtifactRepository
from packages.persistence.artifact_writer import commit_contract_artifact
from packages.timeline.multitrack import assemble_multitrack_timeline


class TimelineAssemblyError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AssemblyArtifactIds:
    """Pre-allocated identities make assembly activities replay-deterministic."""

    master_timeline_id: UUID | None = None
    assembly_report_id: UUID | None = None
    track_ids: Mapping[str, UUID] = field(default_factory=dict)
    item_ids: Sequence[UUID] = ()


@dataclass(frozen=True, slots=True)
class AssemblyOutcome:
    master_timeline_ref: ArtifactRef | None
    assembly_report_ref: ArtifactRef
    blocked: bool
    conflict_codes: tuple[str, ...]
    metrics: tuple[MetricPoint, ...]


_AUDIO_ROLE_KIND = {
    AudioIntentRole.ORIGINAL: TimelineTrackKind.ORIGINAL_AUDIO,
    AudioIntentRole.NARRATION: TimelineTrackKind.NARRATION,
    AudioIntentRole.BGM: TimelineTrackKind.BGM,
    AudioIntentRole.SFX: TimelineTrackKind.SFX,
}


def _used_track_kinds(
    selections: ClipSelectionPlan,
    narration: NarrationLineSet,
    audio_intents: Sequence[AudioIntent],
    subtitle_intents: Sequence[SubtitleIntent],
    overlay_intents: Sequence[OverlayIntent],
) -> list[TimelineTrackKind]:
    kinds = [TimelineTrackKind.VIDEO]
    if narration.lines:
        kinds.append(TimelineTrackKind.NARRATION)
    for intent in audio_intents:
        kind = _AUDIO_ROLE_KIND[intent.role]
        if kind not in kinds:
            kinds.append(kind)
    if subtitle_intents:
        kinds.append(TimelineTrackKind.SUBTITLE)
    if overlay_intents:
        kinds.append(TimelineTrackKind.OVERLAY)
    return kinds


def _item_count(
    selections: ClipSelectionPlan,
    narration: NarrationLineSet,
    audio_intents: Sequence[AudioIntent],
    subtitle_intents: Sequence[SubtitleIntent],
    overlay_intents: Sequence[OverlayIntent],
) -> int:
    return (
        len(selections.selections)
        + len(narration.lines)
        + len(audio_intents)
        + len(subtitle_intents)
        + len(overlay_intents)
    )


class TimelineAssemblyService:
    def __init__(self, artifacts: ArtifactRepository) -> None:
        self._artifacts = artifacts

    def assemble(
        self,
        connection: Connection,
        *,
        project_id: UUID,
        run_id: UUID,
        variant_id: UUID | None,
        trace_id: str,
        actor: ActorRef,
        resource_profile_ref: ArtifactRef,
        timeline_id: UUID,
        selections: ClipSelectionPlan,
        candidates: Sequence[ClipCandidate],
        narration: NarrationLineSet,
        audio_intents: Sequence[AudioIntent],
        subtitle_intents: Sequence[SubtitleIntent],
        overlay_intents: Sequence[OverlayIntent],
        dependencies: tuple[ArtifactRef, ...],
        duration: RationalTime,
        ids: AssemblyArtifactIds | None = None,
        revision_budget: int = 3,
    ) -> AssemblyOutcome:
        ids = ids or AssemblyArtifactIds()
        kinds = _used_track_kinds(
            selections, narration, audio_intents, subtitle_intents, overlay_intents
        )
        track_ids = {kind: ids.track_ids.get(kind.value, uuid4()) for kind in kinds}
        expected_items = _item_count(
            selections, narration, audio_intents, subtitle_intents, overlay_intents
        )
        if ids.item_ids:
            if len(ids.item_ids) != expected_items:
                raise TimelineAssemblyError("preallocated item ID count mismatch")
            item_ids = tuple(ids.item_ids)
        else:
            item_ids = tuple(uuid4() for _ in range(expected_items))

        timeline, report = assemble_multitrack_timeline(
            timeline_id=timeline_id,
            selections=selections,
            candidates=candidates,
            narration=narration,
            audio_intents=audio_intents,
            subtitle_intents=subtitle_intents,
            overlay_intents=overlay_intents,
            dependencies=dependencies,
            track_ids=track_ids,
            item_ids=item_ids,
            duration=duration,
            revision_budget=revision_budget,
        )
        master_timeline_id = ids.master_timeline_id or uuid4()
        assembly_report_id = ids.assembly_report_id or uuid4()
        if timeline is not None:
            master_timeline_ref = commit_contract_artifact(
                connection,
                self._artifacts,
                artifact_id=master_timeline_id,
                artifact_type="MasterTimeline",
                payload=timeline,
                project_id=project_id,
                run_id=run_id,
                variant_id=variant_id,
                trace_id=trace_id,
                actor=actor,
                producer_module="timeline-assembly",
                module_version="e09-j04-v1",
                resource_profile_ref=resource_profile_ref,
                rights_class="internal-planning",
                inputs=dependencies,
            )
            report = report.model_copy(update={"timeline_ref": master_timeline_ref})
            report_ref = commit_contract_artifact(
                connection,
                self._artifacts,
                artifact_id=assembly_report_id,
                artifact_type="TimelineAssemblyReport",
                payload=report,
                project_id=project_id,
                run_id=run_id,
                variant_id=variant_id,
                trace_id=trace_id,
                actor=actor,
                producer_module="timeline-assembly",
                module_version="e09-j04-v1",
                resource_profile_ref=resource_profile_ref,
                rights_class="internal-planning",
                inputs=(master_timeline_ref,),
            )
        else:
            master_timeline_ref = None
            report_ref = commit_contract_artifact(
                connection,
                self._artifacts,
                artifact_id=assembly_report_id,
                artifact_type="TimelineAssemblyReport",
                payload=report,
                project_id=project_id,
                run_id=run_id,
                variant_id=variant_id,
                trace_id=trace_id,
                actor=actor,
                producer_module="timeline-assembly",
                module_version="e09-j04-v1",
                resource_profile_ref=resource_profile_ref,
                rights_class="internal-planning",
                inputs=dependencies,
            )
        blocked = timeline is None
        return AssemblyOutcome(
            master_timeline_ref=master_timeline_ref,
            assembly_report_ref=report_ref,
            blocked=blocked,
            conflict_codes=tuple(
                conflict.code for conflict in report.conflicts if conflict.blocker
            ),
            metrics=(
                MetricPoint(
                    name="timeline_assembly",
                    value=1,
                    labels={"stage": "assembly", "state": "blocked" if blocked else "succeeded"},
                ),
            ),
        )
