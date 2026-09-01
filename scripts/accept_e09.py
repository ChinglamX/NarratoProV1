"""E09 real-data candidate-to-demo certification driver (fail-closed evidence).

Runs the CreativeTimelineWorkflow against the real media already ingested in
the local dev database (SourceMedia 8a0ce63f..., SceneShotCatalog 6ea1ed5f...
with 17 real PySceneDetect shots over a 105.667s source). It builds real input
artifacts (ResourceProfile/CreativeBrief/NarrativeBeatGraph/ClipCandidateSet/
NarrationLineSet/SubtitleStyle), pre-allocates output identities, drives the
workflow through visual→rhythm→narration→assembly→media preview with a worker
restart mid-run, replays the recorded history, and stops at the mandatory
human timeline checkpoint.

The final approve is a human decision. ``--auto-approve`` exists only for
machine acceptance of the engineering path (accept_e03/e04 precedent); the
default run stops at ``awaiting_review`` and prints the certification
evidence for human review.

Story/evidence references are deterministic placeholders (no real StoryGraph
exists locally); this keeps E09's real-data blockers open and is reported as
such. Narration text is a factual draft for human approval, not machine
fabrication.
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
from workflows.project.models import ArtifactPointer, ReviewSignal
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

ACTOR = ActorRef.model_validate({"kind": "human", "id": "e09-certification"})


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
    """Load real shot boundaries (start/duration seconds) from the catalog."""
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


def _build_beats(shots: list[dict[str, float]]) -> list[NarrativeBeat]:
    """Group real shots into four beats by timeline position (Hook/Context/Escalation/Payoff).

    Each beat maps to exactly one representative real shot so the assembled
    timeline duration (sum of selected clip durations) equals the narration
    duration (sum of beat durations).
    """
    beat_shot = [0, 5, 11, 15]  # representative shots, spread across the source
    beats: list[NarrativeBeat] = []
    for index, (shot_index, function) in enumerate(
        zip(
            beat_shot,
            [BeatFunction.HOOK, BeatFunction.CONTEXT, BeatFunction.ESCALATION, BeatFunction.PAYOFF],
            strict=True,
        )
    ):
        duration = shots[shot_index]["duration"]
        # Deterministic v4 placeholder story refs (no real StoryGraph exists
        # locally; E09 real-data blockers stay open and this is reported).
        story_ref = UUID(bytes=sha256(f"e09-cert-story:{index}".encode()).digest()[:16], version=4)
        beats.append(
            NarrativeBeat.model_validate(
                {
                    "beat_id": str(uuid4()),
                    "function": function.value,
                    "story_refs": [str(story_ref)],
                    "target_duration": _rational(duration),
                    "minimum_duration": _rational(min(duration * 0.6, duration)),
                    "maximum_duration": _rational(max(duration * 1.1, duration)),
                    "required_information": [f"beat-{index + 1}-grounding"],
                    "emotional_intent": {"tension": 0.2 + 0.2 * index},
                    "locked": False,
                }
            )
        )
    return beats


def _build_candidates(
    shots: list[dict[str, float]], beats: list[NarrativeBeat]
) -> list[ClipCandidate]:
    """One real candidate per beat, grounded in the beat's representative shot."""
    beat_shot = [0, 5, 11, 15]
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
    return candidates


def _build_narration(
    beats: list[NarrativeBeat],
    creative_brief_ref: ArtifactRef,
) -> NarrationLineSet:
    """Factual narration draft over the four beats (human approval required)."""
    texts = [
        "山神印觉醒，满山风月尽归一人。",
        "身怀山神印的少年初入宗门，被视作异类。",
        "宗门大比将至，山神印之力引来觊觎与杀机。",
        "山门之上，少年直面宿命一战，风月相随。",
    ]
    lines: list[NarrationLine] = []
    for beat, text in zip(beats, texts, strict=True):
        duration = beat.target_duration.seconds
        story_ref = beat.story_refs[0]
        lines.append(
            NarrationLine.model_validate(
                {
                    "line_id": str(uuid4()),
                    "beat_id": str(beat.beat_id),
                    "text": text,
                    "function": beat.function.value,
                    "story_refs": [str(story_ref)],
                    "evidence_refs": [str(story_ref)],
                    "target_duration": _rational(duration),
                    "dialogue_relationship": DialogueRelationship.NONE.value,
                    "rhetorical": False,
                    "locked": False,
                }
            )
        )
    return NarrationLineSet.model_validate(
        {
            "creative_brief_ref": creative_brief_ref,
            "rhythm_plan_ref": _ref(uuid4(), "RhythmPlan"),
            "lines": [line.model_dump(mode="json") for line in lines],
            "estimated_duration": _rational(sum(beat.target_duration.seconds for beat in beats)),
        }
    )


def _commit_inputs(
    connection: object,
    repository: ArtifactRepository,
    *,
    run_id: UUID,
    trace_id: str,
    project_id: UUID,
    beats: list[NarrativeBeat],
    candidates: list[ClipCandidate],
) -> dict[str, ArtifactPointer]:
    """Commit every real input artifact with deterministic checksums."""
    resource_profile_id = uuid4()
    brief_id = uuid4()
    beat_graph_id = uuid4()
    candidate_set_id = uuid4()
    line_set_id = uuid4()
    subtitle_style_id = uuid4()

    def commit(artifact_id: UUID, artifact_type: str, payload: object) -> ArtifactRef:
        return commit_contract_artifact(
            connection,
            repository,
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            payload=payload,
            project_id=project_id,
            run_id=run_id,
            variant_id=None,
            trace_id=trace_id,
            actor=ACTOR,
            producer_module="scripts.accept_e09",
            module_version="1.0.0",
            resource_profile_ref=_ref(resource_profile_id, "ResourceProfile"),
            rights_class="internal",
        )

    commit(
        resource_profile_id,
        "ResourceProfile",
        {"profile": "local-acceptance", "cost_budget_cents": 0},
    )
    brief_ref = commit(
        brief_id,
        "CreativeBrief",
        {
            "title": "山神印觉醒 - E09 real-data certification",
            "target_duration_seconds": round(
                float(sum(beat.target_duration.seconds for beat in beats)), 6
            ),
        },
    )
    commit(
        beat_graph_id,
        "NarrativeBeatGraph",
        NarrativeBeatGraph.model_validate(
            {
                "creative_brief_ref": brief_ref,
                "beats": [beat.model_dump(mode="json") for beat in beats],
                "target_duration": _rational(sum(beat.target_duration.seconds for beat in beats)),
            }
        ),
    )
    commit(
        candidate_set_id,
        "ClipCandidateSet",
        ClipCandidateSet.model_validate(
            {
                "beat_graph_ref": _ref(beat_graph_id, "NarrativeBeatGraph"),
                "candidates": [candidate.model_dump(mode="json") for candidate in candidates],
            }
        ),
    )
    commit(
        line_set_id,
        "NarrationLineSet",
        _build_narration(beats, brief_ref),
    )
    commit(
        subtitle_style_id,
        "SubtitleCueSet",
        {"style": "default", "safe_area": {"y": 0.8, "height": 0.15}},
    )

    return {
        "resource_profile": _pointer(resource_profile_id, "ResourceProfile"),
        "creative_brief": _pointer(brief_id, "CreativeBrief"),
        "beat_graph": _pointer(beat_graph_id, "NarrativeBeatGraph"),
        "candidate_set": _pointer(candidate_set_id, "ClipCandidateSet"),
        "line_set": _pointer(line_set_id, "NarrationLineSet"),
        "subtitle_style": _pointer(subtitle_style_id, "SubtitleCueSet"),
    }


def _request(
    run_id: UUID,
    project_id: UUID,
    pointers: dict[str, ArtifactPointer],
    beats: list[NarrativeBeat],
) -> CreativeTimelineRequest:
    planning = PlanningIdSpec(
        candidate_set_id=str(uuid4()),
        selection_plan_id=str(uuid4()),
        continuity_report_id=str(uuid4()),
        visual_report_id=str(uuid4()),
    )
    return CreativeTimelineRequest(
        run_id=str(run_id),
        project_id=str(project_id),
        trace_id="a" * 32,
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
        output_path=str(Path(get_settings().temp_root) / f"e09-cert-{run_id}-preview.mp4"),
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
        print(
            f"  ... state={status.state if status else 'unknown'} "
            f"stages={dict(status.stage_states) if status else {}}"
        )
        await asyncio.sleep(2.0)
        elapsed += 2.0
    raise AssertionError(f"workflow did not reach {states}")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--auto-approve", action="store_true", help="machine-acceptance approve")
    args = parser.parse_args()

    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    trace_id = uuid4().hex
    run_id = uuid4()
    workflow_id = f"e09-cert/{run_id}"

    with engine.begin() as connection:
        connection.execute(
            insert(schema.run).values(
                id=run_id,
                project_id=PROJECT_ID,
                workflow_id=workflow_id,
                state="running",
                automation_policy_snapshot={},
                resource_profile_snapshot={},
            )
        )
        repository = ArtifactRepository()
        shots = _load_catalog_shots(connection)
        beats = _build_beats(shots)
        candidates = _build_candidates(shots, beats)
        pointers = _commit_inputs(
            connection,
            repository,
            run_id=run_id,
            trace_id=trace_id,
            project_id=PROJECT_ID,
            beats=beats,
            candidates=candidates,
        )
        request = _request(run_id, PROJECT_ID, pointers, beats)

    print("== E09 real-data certification ==")
    print(f"run_id={run_id}  source={SOURCE_ARTIFACT_ID}  shots={len(shots)}")
    print("input artifacts:")
    for name, pointer in pointers.items():
        print(f"  {name}: {pointer.artifact_id} v{pointer.version}")

    client = await Client.connect(settings.temporal_target)

    # First worker span: run until the timeline checkpoint, then stop for a
    # hard restart (durability evidence: Temporal keeps the workflow alive).
    worker = _worker(client)
    async with worker:
        handle = await client.start_workflow(
            CreativeTimelineWorkflow.run,
            request,
            id=workflow_id,
            task_queue=TASK_QUEUE,
        )
        status = await _wait_for_state(handle, {"awaiting_review", "blocked"})
        print(f"== reached {status.state} (stages={dict(status.stage_states)}) ==")
        require(status.state == "awaiting_review", f"workflow blocked: {status.blocked_codes}")
    print("== worker stopped (hard restart) ==")

    # Second worker span: workflow must resume from durable history.
    async with _worker(client):
        status = await _wait_for_state(handle, {"awaiting_review", "blocked", "succeeded"})
        print(f"== after restart state={status.state} ==")
        require(status.state == "awaiting_review", "workflow did not resume at checkpoint")

        # Deterministic replay of the recorded history.
        history = await handle.fetch_history()
        replay = await Replayer(workflows=[CreativeTimelineWorkflow]).replay_workflow(history)
        require(replay.replay_failure is None, f"history replay failed: {replay.replay_failure}")

        print("== checkpoint evidence ==")
        for name, pointer in sorted(status.artifacts.items()):
            print(f"  artifact[{name}] = {pointer.artifact_id} v{pointer.version}")
        print("  review_id =", status.active_review_id)
        print("  replay: PASS")

        if not args.auto_approve:
            print("== STOPPED at human timeline checkpoint ==")
            print("review the preview + shot timecode map, then re-run with --auto-approve")
            return

        signal = ReviewSignal(
            review_id=status.active_review_id or f"review:{run_id}:timeline",
            target_version=1,
            decision="approve",
        )
        await handle.signal(CreativeTimelineWorkflow.submit_review_decision, signal)
        status = await _wait_for_state(handle, {"succeeded", "blocked"}, timeout_seconds=1800.0)
        require(status.state == "succeeded", f"approval did not succeed: {status.blocked_codes}")

        preview_ref = status.artifacts.get("preview")
        require(preview_ref is not None, "preview artifact missing")
        output_path = Path(request.output_path)
        require(output_path.is_file(), f"preview file missing: {output_path}")
        print("== SUCCEEDED ==")
        print(f"  preview = {output_path} ({output_path.stat().st_size} bytes)")
        print(f"  subtitle = {output_path.with_suffix('.ass')}")
        print(f"  checksum(s) committed by ArtifactRepository; workflow_id={workflow_id}")

    print("== timecode map for human craft review (beat -> real shot ranges) ==")
    for beat, shot_index in zip(beats, [0, 5, 11, 15], strict=True):
        start = shots[shot_index]["start"]
        end = start + shots[shot_index]["duration"]
        print(
            f"  {beat.function.value:<10} {start:7.2f}s - {end:7.2f}s  "
            f"(source shot #{shot_index}, {end - start:.2f}s)"
        )


if __name__ == "__main__":
    asyncio.run(main())
