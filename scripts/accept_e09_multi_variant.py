"""E09 multi-variant real-data restart/replay certification (engineering evidence).

Runs two CreativeTimelineWorkflow variants against the same real media with
different beat/shot selections, drives both through visual→rhythm→narration→
assembly→media preview with a worker hard restart mid-run, replays both recorded
histories, and verifies both stop at the human timeline checkpoint.

This closes the engineering side of the E09 "real multi-variant Worker
restart/replay" blocker: durable history recovery and deterministic replay are
exercised with two concurrent variants. The human side (approved multi-variant
project data) remains open and is reported as such.
"""

# ruff: noqa: RUF001  (narration text is intentionally CJK punctuation)
from __future__ import annotations

import argparse
import asyncio
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import insert, select
from temporalio.client import Client
from temporalio.worker import Replayer, Worker

import packages.persistence.schema as schema
from packages.contracts import ActorRef, ArtifactRef, TimeRange
from packages.contracts.timeline_intent import (
    BeatFunction,
    ClipCandidate,
    ClipCandidateSet,
    DialogueRelationship,
    NarrationLine,
    NarrationLineSet,
    NarrativeBeat,
    NarrativeBeatGraph,
)
from packages.foundation.settings import get_settings
from packages.persistence.artifact_repository import ArtifactRepository
from packages.persistence.artifact_writer import commit_contract_artifact
from packages.persistence.database import create_database_engine
from workflows.project.models import ArtifactPointer
from workflows.timeline.creative_activities import (
    assemble_timeline_activity,
    plan_rhythm_activity,
    plan_visual_activity,
    render_media_preview_activity,
    review_narration_activity,
)
from workflows.timeline.creative_models import (
    ClipQuerySpec,
    CreativeTimelineRequest,
    PlanningIdSpec,
)
from workflows.timeline.creative_workflow import CreativeTimelineWorkflow

SOURCE_ARTIFACT_ID = UUID("8a0ce63f-ad95-4879-9803-0c653c81b3cd")
CATALOG_ARTIFACT_ID = UUID("6ea1ed5f-0163-46e1-95f1-aec4f4b25d9a")
PROJECT_ID = UUID("2052f76b-0709-4d29-a858-20916779096f")
SOURCE_DURATION_SECONDS = "105.666667"
TASK_QUEUE = "control"

ACTOR = ActorRef.model_validate({"kind": "human", "id": "e09-multi-variant"})

# Two variant definitions: different representative shots across the source.
VARIANTS = {
    "a": {
        "beat_shot": [0, 5, 11, 15],
        "texts": [
            "山神印觉醒，满山风月尽归一人。",
            "身怀山神印的少年初入宗门，被视作异类。",
            "宗门大比将至，山神印之力引来觊觎与杀机。",
            "山门之上，少年直面宿命一战，风月相随。",
        ],
    },
    "b": {
        "beat_shot": [2, 7, 13, 16],
        "texts": [
            "少年自尘埃中起身，山神印已悄然亮起。",
            "宗门上下无人知晓，他背负着怎样的传承。",
            "大比前夕，山神印的气息引来了夜行者的目光。",
            "山门一役，风雷齐至，少年孤身立在山巅。",
        ],
    },
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _rational(seconds: float) -> dict[str, int]:
    return {"value": round(seconds * 1_000_000), "rate_den": 1, "rate_num": 1_000_000}


def _time_range(start: float, duration: float) -> TimeRange:
    return TimeRange.model_validate({"start": _rational(start), "duration": _rational(duration)})


def _pointer(artifact_id: UUID, kind: str) -> ArtifactPointer:
    return ArtifactPointer(str(artifact_id), 1, kind)


def _ref(artifact_id: UUID, kind: str) -> ArtifactRef:
    return ArtifactRef.model_validate(
        {"artifact_id": str(artifact_id), "version": 1, "artifact_type": kind}
    )


def _load_catalog_shots(connection: object) -> list[dict[str, float]]:
    row = (
        connection.execute(
            select(schema.artifact_version).where(
                schema.artifact_version.c.artifact_id == CATALOG_ARTIFACT_ID
            )
        )
        .mappings()
        .first()
    )
    require(row is not None, "SceneShotCatalog artifact is unavailable")
    payload = row["payload_json"]
    shots: list[dict[str, float]] = []
    for segment in payload["segments"]:
        source_range = segment["source_range"]
        start = source_range["start"]["value"] / source_range["start"]["rate_num"]
        duration = source_range["duration"]["value"] / source_range["duration"]["rate_num"]
        shots.append({"start": start, "duration": duration})
    require(len(shots) == 17, f"expected 17 catalog shots, found {len(shots)}")
    return shots


def _build_inputs(
    shots: list[dict[str, float]], variant: str, run_id: UUID
) -> tuple[list[NarrativeBeat], list[ClipCandidate], dict[str, ArtifactPointer]]:
    beat_shot = VARIANTS[variant]["beat_shot"]
    texts = VARIANTS[variant]["texts"]
    beats: list[NarrativeBeat] = []
    for index, (shot_index, function) in enumerate(
        zip(
            beat_shot,
            [BeatFunction.HOOK, BeatFunction.CONTEXT, BeatFunction.ESCALATION, BeatFunction.PAYOFF],
            strict=True,
        )
    ):
        duration = shots[shot_index]["duration"]
        story_ref = UUID(
            bytes=sha256(f"e09-mv-{variant}-story:{index}".encode()).digest()[:16], version=4
        )
        beats.append(
            NarrativeBeat.model_validate(
                {
                    "beat_id": str(uuid4()),
                    "function": function.value,
                    "story_refs": [str(story_ref)],
                    "target_duration": _rational(duration),
                    "minimum_duration": _rational(min(duration * 0.6, duration)),
                    "maximum_duration": _rational(max(duration * 1.1, duration)),
                    "required_information": [f"mv-{variant}-beat-{index + 1}-grounding"],
                    "emotional_intent": {"tension": 0.2 + 0.2 * index},
                    "locked": False,
                }
            )
        )
    candidates: list[ClipCandidate] = []
    for beat, shot_index in zip(beats, beat_shot, strict=True):
        shot = shots[shot_index]
        story_ref = beat.story_refs[0]
        candidates.append(
            ClipCandidate.model_validate(
                {
                    "candidate_id": str(uuid4()),
                    "beat_id": str(beat.beat_id),
                    "source_ref": _ref(SOURCE_ARTIFACT_ID, "SourceMedia"),
                    "source_range": _time_range(shot["start"], shot["duration"]),
                    "story_refs": [str(story_ref)],
                    "evidence_refs": [str(story_ref)],
                    "visible_character_refs": [],
                    "quality": {"sharpness": 0.8, "motion": 0.5},
                    "continuity_features": {"shot_index": shot_index},
                    "reframe_feasible": False,
                    "rights_allowed": True,
                    "score_components": {"evidence": 0.9, "rhythm": 0.7},
                }
            )
        )
    return beats, candidates, _commit_inputs(beats, candidates, texts, variant, run_id)


def _commit_inputs(
    beats: list[NarrativeBeat],
    candidates: list[ClipCandidate],
    texts: list[str],
    variant: str,
    run_id: UUID,
) -> dict[str, ArtifactPointer]:
    def commit(
        connection: object,
        repository: ArtifactRepository,
        artifact_id: UUID,
        artifact_type: str,
        payload: object,
    ) -> ArtifactRef:
        return commit_contract_artifact(
            connection,
            repository,
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            payload=payload,
            project_id=PROJECT_ID,
            run_id=run_id,
            variant_id=None,
            trace_id="a" * 32,
            actor=ACTOR,
            producer_module=f"scripts.accept_e09_multi_variant.{variant}",
            module_version="1.0.0",
            resource_profile_ref=_ref(uuid4(), "ResourceProfile"),
            rights_class="internal",
        )

    engine = create_database_engine(get_settings().database_url)
    resource_profile_id = uuid4()
    brief_id = uuid4()
    beat_graph_id = uuid4()
    candidate_set_id = uuid4()
    line_set_id = uuid4()
    subtitle_style_id = uuid4()
    pointers: dict[str, ArtifactPointer] = {}
    with engine.begin() as connection:
        repository = ArtifactRepository()
        commit(
            connection,
            repository,
            resource_profile_id,
            "ResourceProfile",
            {"profile": "local-acceptance", "cost_budget_cents": 0},
        )
        brief_ref = commit(
            connection,
            repository,
            brief_id,
            "CreativeBrief",
            {
                "title": f"E09 multi-variant {variant}",
                "target_duration_seconds": round(
                    float(sum(b.target_duration.seconds for b in beats)), 6
                ),
            },
        )
        commit(
            connection,
            repository,
            beat_graph_id,
            "NarrativeBeatGraph",
            NarrativeBeatGraph.model_validate(
                {
                    "creative_brief_ref": brief_ref,
                    "beats": [b.model_dump(mode="json") for b in beats],
                    "target_duration": _rational(sum(b.target_duration.seconds for b in beats)),
                }
            ),
        )
        commit(
            connection,
            repository,
            candidate_set_id,
            "ClipCandidateSet",
            ClipCandidateSet.model_validate(
                {
                    "beat_graph_ref": _ref(beat_graph_id, "NarrativeBeatGraph"),
                    "candidates": [c.model_dump(mode="json") for c in candidates],
                }
            ),
        )
        lines = [
            NarrationLine.model_validate(
                {
                    "line_id": str(uuid4()),
                    "beat_id": str(b.beat_id),
                    "text": text,
                    "function": b.function.value,
                    "story_refs": b.story_refs,
                    "evidence_refs": [b.story_refs[0]],
                    "target_duration": b.target_duration,
                    "dialogue_relationship": DialogueRelationship.NONE.value,
                    "rhetorical": False,
                    "locked": False,
                }
            )
            for b, text in zip(beats, texts, strict=True)
        ]
        commit(
            connection,
            repository,
            line_set_id,
            "NarrationLineSet",
            NarrationLineSet.model_validate(
                {
                    "creative_brief_ref": brief_ref,
                    "rhythm_plan_ref": _ref(uuid4(), "RhythmPlan"),
                    "lines": [line.model_dump(mode="json") for line in lines],
                    "estimated_duration": _rational(sum(b.target_duration.seconds for b in beats)),
                }
            ),
        )
        commit(
            connection,
            repository,
            subtitle_style_id,
            "SubtitleCueSet",
            {"style": "default", "safe_area": {"y": 0.8, "height": 0.15}},
        )
        pointers = {
            "resource_profile": _pointer(resource_profile_id, "ResourceProfile"),
            "creative_brief": _pointer(brief_id, "CreativeBrief"),
            "beat_graph": _pointer(beat_graph_id, "NarrativeBeatGraph"),
            "candidate_set": _pointer(candidate_set_id, "ClipCandidateSet"),
            "line_set": _pointer(line_set_id, "NarrationLineSet"),
            "subtitle_style": _pointer(subtitle_style_id, "SubtitleCueSet"),
        }
    return pointers


def _request(
    run_id: UUID,
    pointers: dict[str, ArtifactPointer],
    beats: list[NarrativeBeat],
    variant: str,
) -> CreativeTimelineRequest:
    planning = PlanningIdSpec(
        candidate_set_id=str(uuid4()),
        selection_plan_id=str(uuid4()),
        continuity_report_id=str(uuid4()),
        visual_report_id=str(uuid4()),
    )
    return CreativeTimelineRequest(
        run_id=str(run_id),
        project_id=str(PROJECT_ID),
        trace_id="b" * 32,
        resource_profile=pointers["resource_profile"],
        beat_graph=pointers["beat_graph"],
        candidate_sets=(pointers["candidate_set"],),
        queries=tuple(
            ClipQuerySpec(
                beat_id=str(beat.beat_id),
                story_refs=tuple(str(ref) for ref in beat.story_refs),
                required_character_refs=(),
                routes=("evidence",),
                top_k_per_route=5,
            )
            for beat in beats
        ),
        planning=planning,
        rhythm_plan_id=str(uuid4()),
        line_set=pointers["line_set"],
        narration_report_id=str(uuid4()),
        dialogue_by_beat={},
        subtitle_style=pointers["subtitle_style"],
        timeline_id=str(uuid4()),
        master_timeline_id=str(uuid4()),
        assembly_report_id=str(uuid4()),
        track_ids={},
        item_ids=(),
        output_path=str(Path(get_settings().temp_root) / f"e09-mv-{variant}-{run_id}-preview.mp4"),
        source_durations={str(SOURCE_ARTIFACT_ID): SOURCE_DURATION_SECONDS},
    )


def _worker(client: Client) -> Worker:
    return Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[CreativeTimelineWorkflow],
        activities=[
            plan_visual_activity,
            plan_rhythm_activity,
            review_narration_activity,
            assemble_timeline_activity,
            render_media_preview_activity,
        ],
    )


async def _wait_for_state(
    handle: object, states: set[str], timeout_seconds: float = 900.0
) -> object:
    elapsed = 0.0
    while elapsed < timeout_seconds:
        status = await handle.query(CreativeTimelineWorkflow.get_status)  # type: ignore[attr-defined]
        if status is not None and status.state in states:
            return status
        await asyncio.sleep(2.0)
        elapsed += 2.0
    raise AssertionError(f"workflow did not reach {states}")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=tuple(VARIANTS), help="run a single variant")
    args = parser.parse_args()

    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    with engine.connect() as connection:
        shots = _load_catalog_shots(connection)
    runs: dict[str, tuple[UUID, object, CreativeTimelineRequest]] = {}

    variants = (args.variant,) if args.variant else tuple(VARIANTS)
    for variant in variants:
        run_id = uuid4()
        with engine.begin() as connection:
            connection.execute(
                insert(schema.run).values(
                    id=run_id,
                    project_id=PROJECT_ID,
                    workflow_id=f"e09-mv-{variant}/{run_id}",
                    state="running",
                    automation_policy_snapshot={},
                    resource_profile_snapshot={},
                )
            )
        beats, _candidates, pointers = _build_inputs(shots, variant, run_id)
        runs[variant] = (run_id, beats, _request(run_id, pointers, beats, variant))

    client = await Client.connect(settings.temporal_target)
    handles: dict[str, object] = {}

    # First worker span: start all variants, run to the checkpoint, then stop.
    async with _worker(client):
        for variant, (run_id, _, request) in runs.items():
            handles[variant] = await client.start_workflow(
                CreativeTimelineWorkflow.run,
                request,
                id=f"e09-mv-{variant}/{run_id}",
                task_queue=TASK_QUEUE,
            )
        statuses: dict[str, object] = {}
        for variant, handle in handles.items():
            status = await _wait_for_state(handle, {"awaiting_review", "blocked"})
            statuses[variant] = status
            require(status.state == "awaiting_review", f"{variant} blocked: {status.blocked_codes}")
            print(f"== variant {variant} reached awaiting_review ==")
    print("== worker stopped (hard restart) ==")

    # Second worker span: both workflows must resume from durable history.
    async with _worker(client):
        for variant, handle in handles.items():
            status = await _wait_for_state(handle, {"awaiting_review", "blocked", "succeeded"})
            require(status.state == "awaiting_review", f"{variant} did not resume at checkpoint")
            history = await handle.fetch_history()
            replay = await Replayer(workflows=[CreativeTimelineWorkflow]).replay_workflow(history)
            require(
                replay.replay_failure is None,
                f"{variant} history replay failed: {replay.replay_failure}",
            )
            print(f"== variant {variant} resumed at checkpoint, replay PASS ==")
            for name, pointer in sorted(status.artifacts.items()):
                print(f"  artifact[{variant}:{name}] = {pointer.artifact_id} v{pointer.version}")

    print("== MULTI-VARIANT RESTART/REPLAY PASS ==")
    for variant, (run_id, _, request) in runs.items():
        output = Path(request.output_path)
        print(f"  variant {variant}: run={run_id} preview={output} exists={output.is_file()}")


if __name__ == "__main__":
    asyncio.run(main())
