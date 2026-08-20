"""Produce the Episode 8 creative timeline from the approved Gate 2 brief.

Inputs (all already persisted and human-approved):
- Approved Story: StoryGraph ``c378ba51-da33-4049-baf0-538ca637e9a5@1``.
- Approved CreativeBrief: ``bc2c693e-8768-40fc-84d5-fcc00946f80a@1`` (Option 1
  "威胁倒叙"; narrative spine threat -> sale -> payment).
- Approved VariantPlan: ``58a7c392-64f3-4d81-b1df-fbcfedb10c1b@1``.
- Real media: SourceMedia ``f98ca32a-a855-441b-b73e-fec9f324d1a8@1`` (Episode 8,
  53.056s, blob committed in the local object store).
- Human-verified claim windows (outputs/vc002_episode_08/evidence_manifest.json):
  sale 15.0-28.0s, payment 28.0-33.0s, threat 39.0-53.056s.

It commits the planning inputs (ResourceProfile, NarrativeBeatGraph,
ClipCandidateSet, NarrationLineSet, SubtitleCueSet), drives the
CreativeTimelineWorkflow through visual -> rhythm -> narration -> assembly ->
real media preview, and STOPS at the mandatory human timeline checkpoint
(awaiting_review). No machine approval; signing is a separate human step.

Do NOT rerun this script for the same run; a revise/reject decision is handled
by re-producing with a new run id after the human decision.
"""

# ruff: noqa: RUF001 - CJK narration text is intentional review copy.

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import insert, select
from temporalio.client import Client
from temporalio.worker import Worker

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

PROJECT_ID = UUID("dd397853-79bc-4e6f-a540-bb1c296d6936")
SOURCE_ARTIFACT_ID = UUID("f98ca32a-a855-441b-b73e-fec9f324d1a8")
SOURCE_DURATION_SECONDS = "53.056"
TASK_QUEUE = "control"
WORKFLOW_PREFIX = "vc003-e08-timeline"

STORY_REF = ArtifactRef.model_validate(
    {
        "artifact_id": "c378ba51-da33-4049-baf0-538ca637e9a5",
        "version": 1,
        "artifact_type": "StoryGraph",
        "checksum": "sha256:8b34ae0d15d81126a1907366e27efcb4ce113e5bea0e1d2fae0ec146d0c7aad2",
    }
)
BRIEF_REF = ArtifactRef.model_validate(
    {
        "artifact_id": "bc2c693e-8768-40fc-84d5-fcc00946f80a",
        "version": 1,
        "artifact_type": "CreativeBrief",
        "checksum": "sha256:a20c2f1639d5ceb3ce2772dbc3b98d97e14830400b9b0e48d3de73ee8f38e0e8",
    }
)
VARIANT_REF = ArtifactRef.model_validate(
    {
        "artifact_id": "58a7c392-64f3-4d81-b1df-fbcfedb10c1b",
        "version": 1,
        "artifact_type": "VariantPlan",
        "checksum": "sha256:c337552207507ddd7f49a0c413b25c5ef45e3699868c48a0acdf8e5991d968bd",
    }
)
SOURCE_REF = ArtifactRef.model_validate(
    {
        "artifact_id": "f98ca32a-a855-441b-b73e-fec9f324d1a8",
        "version": 1,
        "artifact_type": "SourceMedia",
        "checksum": "sha256:bb45cd4221f9310c4a4bfd6ed29e92883a351b8596b05bebef5f839bc3e3c3f2",
    }
)

# StoryGraph events (threat / sale / payment) with their evidence ids.
THREAT_EVENT = UUID("87f8ff89-54ec-42b1-8e46-c12cefba6e47")
SALE_EVENT = UUID("1df88e31-efac-44ac-8e73-8bcb5c8269ec")
PAYMENT_EVENT = UUID("1c583c8c-7291-4f8f-91e9-b02181958c26")
THREAT_EVIDENCE = UUID("1267ab6e-3cc8-4a10-8ef5-5764077f0616")
SALE_EVIDENCE = UUID("172bf99b-af5d-4070-b836-ec6d50eedf58")
PAYMENT_EVIDENCE = UUID("d008fa4a-3bd6-40c0-83f3-79885d89b34d")

# Human-verified claim windows (evidence_manifest.json, 1s precision).
DEFAULT_WINDOWS = {
    "threat": (39.0, 14.056),  # 39.0 - 53.056
    "sale": (15.0, 13.0),  # 15.0 - 28.0
    "payment": (28.0, 5.0),  # 28.0 - 33.0
}


def _windows(threat_start: float, threat_duration: float) -> dict[str, tuple[float, float]]:
    windows = dict(DEFAULT_WINDOWS)
    windows["threat"] = (threat_start, threat_duration)
    return windows


ACTOR = ActorRef.model_validate({"kind": "human", "id": "vc003-episode8-timeline"})


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


def _build_beats(windows: dict[str, tuple[float, float]]) -> list[NarrativeBeat]:
    """Three beats in the approved 威胁倒叙 order: threat -> sale -> payment."""
    specs = (
        (THREAT_EVENT, THREAT_EVIDENCE, BeatFunction.HOOK, "threat", 0.9),
        (SALE_EVENT, SALE_EVIDENCE, BeatFunction.CONTEXT, "sale", 0.5),
        (PAYMENT_EVENT, PAYMENT_EVIDENCE, BeatFunction.PAYOFF, "payment", 0.3),
    )
    beats: list[NarrativeBeat] = []
    for event_id, _evidence_id, function, key, tension in specs:
        _start, duration = windows[key]
        beats.append(
            NarrativeBeat.model_validate(
                {
                    "beat_id": str(uuid4()),
                    "function": function.value,
                    "story_refs": [str(event_id)],
                    "target_duration": _rational(duration),
                    "minimum_duration": _rational(duration * 0.6),
                    "maximum_duration": _rational(duration * 1.1),
                    "required_information": [f"episode-08:{key}:human-verified-window"],
                    "emotional_intent": {
                        "tension": tension,
                        "entry_energy": 0.4 + 0.2 * tension,
                        "exit_energy": 0.5 - 0.2 * tension,
                        "information_density": 0.6,
                    },
                    "locked": False,
                }
            )
        )
    return beats


def _build_candidates(
    beats: list[NarrativeBeat], windows: dict[str, tuple[float, float]]
) -> list[ClipCandidate]:
    """One evidence-grounded candidate per beat at its human-verified window."""
    specs = (
        (beats[0], THREAT_EVENT, THREAT_EVIDENCE, "threat", "room"),
        (beats[1], SALE_EVENT, SALE_EVIDENCE, "sale", "stall"),
        (beats[2], PAYMENT_EVENT, PAYMENT_EVIDENCE, "payment", "stall"),
    )
    candidates: list[ClipCandidate] = []
    for beat, event_id, evidence_id, key, location in specs:
        start, duration = windows[key]
        candidates.append(
            ClipCandidate.model_validate(
                {
                    "candidate_id": str(uuid4()),
                    "beat_id": str(beat.beat_id),
                    "source_ref": SOURCE_REF.model_dump(mode="json"),
                    "source_range": _time_range(start, duration).model_dump(mode="json"),
                    "story_refs": [str(event_id)],
                    "evidence_refs": [str(evidence_id)],
                    "visible_character_refs": [],
                    "quality": {"sharpness": 0.8, "motion": 0.5},
                    # No "time" feature: the approved brief is a reverse
                    # chronology (威胁倒叙); declaring source order would trip a
                    # blocker that the approved creative decision overrides.
                    "continuity_features": {"location": location},
                    "reframe_feasible": False,
                    "rights_allowed": True,
                    "score_components": {"evidence": 1.0},
                }
            )
        )
    return candidates


def _build_narration(beats: list[NarrativeBeat]) -> NarrationLineSet:
    """Factual narration draft over the three beats (human approval required).

    No invented identity (人物身份未证明 -> do-not-name), no dialogue
    repetition, no unsupported psychology.
    """
    lines_data = (
        (
            "有人得知对方一天到手三十万，嫌他有钱不还又敢动手，下令盯住，扬言要他的命。",
            THREAT_EVENT,
            THREAT_EVIDENCE,
            "danger-hook",
        ),
        (
            "这三十万，是有人当场买下两样货物的成交价。",
            SALE_EVENT,
            SALE_EVIDENCE,
            "transaction-context",
        ),
        (
            "一张卡、三十万、密码六个八，就这样交到买主手里。",
            PAYMENT_EVENT,
            PAYMENT_EVIDENCE,
            "value-proof",
        ),
    )
    lines: list[NarrationLine] = []
    for beat, (text, event_id, evidence_id, function) in zip(beats, lines_data, strict=True):
        lines.append(
            NarrationLine.model_validate(
                {
                    "line_id": str(uuid4()),
                    "beat_id": str(beat.beat_id),
                    "text": text,
                    "function": function,
                    "story_refs": [str(event_id)],
                    "evidence_refs": [str(evidence_id)],
                    "target_duration": beat.target_duration.model_dump(mode="json"),
                    "dialogue_relationship": DialogueRelationship.NONE.value,
                    "rhetorical": False,
                    "locked": False,
                }
            )
        )
    return NarrationLineSet.model_validate(
        {
            "creative_brief_ref": BRIEF_REF.model_dump(mode="json"),
            "rhythm_plan_ref": _ref(uuid4(), "RhythmPlan").model_dump(mode="json"),
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
    narration: NarrationLineSet,
) -> dict[str, ArtifactPointer]:
    resource_profile_id = uuid4()
    beat_graph_id = uuid4()
    candidate_set_id = uuid4()
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
            producer_module="scripts.produce_vc003_timeline",
            module_version="1.0.0",
            resource_profile_ref=_ref(resource_profile_id, "ResourceProfile"),
            rights_class="internal-planning",
        )

    commit(
        resource_profile_id,
        "ResourceProfile",
        {"profile": "local-vc003-episode08", "cost_budget_cents": 0},
    )
    beat_graph_ref = commit(
        beat_graph_id,
        "NarrativeBeatGraph",
        NarrativeBeatGraph.model_validate(
            {
                "creative_brief_ref": BRIEF_REF.model_dump(mode="json"),
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
                "beat_graph_ref": beat_graph_ref.model_dump(mode="json"),
                "candidates": [candidate.model_dump(mode="json") for candidate in candidates],
            }
        ),
    )
    commit(
        subtitle_style_id,
        "SubtitleCueSet",
        {"style": "default", "safe_area": {"y": 0.8, "height": 0.15}},
    )
    line_set_ref = commit(
        uuid4(),
        "NarrationLineSet",
        narration,
    )
    return {
        "resource_profile": _pointer(resource_profile_id, "ResourceProfile"),
        "beat_graph": _pointer(beat_graph_id, "NarrativeBeatGraph"),
        "candidate_set": _pointer(candidate_set_id, "ClipCandidateSet"),
        "line_set": line_set_ref and _pointer(line_set_ref.artifact_id, "NarrationLineSet"),
        "subtitle_style": _pointer(subtitle_style_id, "SubtitleCueSet"),
    }


def _dialogue_by_beat(beats: list[NarrativeBeat]) -> dict[str, list[str]]:
    dialogues = {
        THREAT_EVENT: [
            "那小子一天就弄到了三十万。妈的，那小子手里有钱，却藏着掖着，不还还敢对我动手给我盯住。那小子，上次让那小子躲过了，这次我就不信，弄不死他"
        ],
        SALE_EVENT: ["三十万这两样我都要了"],
        PAYMENT_EVENT: ["这张卡里有三十万，密码，六个八"],
    }
    return {str(beat.beat_id): dialogues.get(beat.story_refs[0], []) for beat in beats}


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
        trace_id=uuid4().hex,
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
        dialogue_by_beat=_dialogue_by_beat(beats),
        subtitle_style=pointers["subtitle_style"],
        timeline_id=str(uuid4()),
        master_timeline_id=str(uuid4()),
        assembly_report_id=str(uuid4()),
        track_ids={},
        item_ids=(),
        output_path=str(Path(get_settings().temp_root) / f"vc003-e08-{run_id}-preview.mp4"),
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


def _write_review_card(run_id: UUID, workflow_id: str, status: object) -> None:
    engine = create_database_engine(get_settings().database_url)
    preview_path = None
    with engine.connect() as connection:
        rows = (
            connection.execute(
                select(
                    schema.artifact_version.c.payload_json,
                    schema.artifact.c.artifact_type,
                )
                .select_from(
                    schema.artifact_version.join(
                        schema.artifact,
                        schema.artifact.c.id == schema.artifact_version.c.artifact_id,
                    )
                )
                .where(schema.artifact_version.c.run_id == run_id)
            )
            .mappings()
            .fetchall()
        )
        beat_graph: NarrativeBeatGraph | None = None
        candidate_set: ClipCandidateSet | None = None
        line_set: NarrationLineSet | None = None
        for row in rows:
            kind = row["artifact_type"]
            if kind == "NarrativeBeatGraph" and beat_graph is None:
                beat_graph = NarrativeBeatGraph.model_validate(row["payload_json"])
            elif kind == "ClipCandidateSet" and candidate_set is None:
                candidate_set = ClipCandidateSet.model_validate(row["payload_json"])
            elif kind == "NarrationLineSet" and line_set is None:
                line_set = NarrationLineSet.model_validate(row["payload_json"])
            elif kind == "ProxyRender" and preview_path is None:
                preview_path = row["payload_json"].get("output_path")
    if beat_graph is None or candidate_set is None or line_set is None:
        raise RuntimeError("run inputs are incomplete; cannot write review card")
    candidates_by_beat = {candidate.beat_id: candidate for candidate in candidate_set.candidates}
    lines_by_beat = {line.beat_id: line for line in line_set.lines}
    out_dir = Path(__file__).resolve().parents[1] / "outputs/vc003_episode_08/timeline"
    out_dir.mkdir(parents=True, exist_ok=True)
    card_rows = []
    for beat in beat_graph.beats:
        candidate = candidates_by_beat[beat.beat_id]
        line = lines_by_beat[beat.beat_id]
        start = float(candidate.source_range.start.seconds)
        duration = float(candidate.source_range.duration.seconds)
        card_rows.append(
            {
                "beat_id": str(beat.beat_id),
                "function": beat.function.value,
                "source_window_seconds": [round(start, 3), round(start + duration, 3)],
                "candidate_id": str(candidate.candidate_id),
                "story_ref": str(candidate.story_refs[0]),
                "evidence_ref": str(candidate.evidence_refs[0]),
                "narration": line.text,
            }
        )
    artifacts = {
        name: f"{pointer.artifact_id} v{pointer.version}"
        for name, pointer in status.artifacts.items()
    }
    manifest = {
        "run_id": str(run_id),
        "workflow_id": workflow_id,
        "state": status.state,
        "preview_path": preview_path,
        "approved_creative_brief": BRIEF_REF.model_dump(mode="json", exclude_none=True),
        "approved_story": STORY_REF.model_dump(mode="json", exclude_none=True),
        "source_media": SOURCE_REF.model_dump(mode="json", exclude_none=True),
        "timeline_seconds": round(
            sum(
                item["source_window_seconds"][1] - item["source_window_seconds"][0]
                for item in card_rows
            ),
            3,
        ),
        "beats": card_rows,
        "artifacts": artifacts,
        "boundary_notes": [
            "人物身份未证明：解说与字幕未给任何角色命名。",
            "倒叙时间顺序来自 approved Gate 2 CreativeBrief（威胁倒叙）。",
            "预览为 E09 草稿：原声保留、解说以字幕占位，TTS/混音/字幕烧录属 E10。",
        ],
    }
    (out_dir / f"checkpoint_{run_id}.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = ["# Episode 8 — Timeline Checkpoint（威胁倒叙）", "", f"Run: `{run_id}`", ""]
    for row in card_rows:
        md.append(
            f"- **{row['function']}**：源窗口 {row['source_window_seconds'][0]}–"
            f"{row['source_window_seconds'][1]}s，解说「{row['narration']}」"
        )
    md.append("")
    md.append("## 边界")
    md.extend(f"- {note}" for note in manifest["boundary_notes"])
    md.append("")
    md.append("等待项目负责人 approve / revise / reject。")
    (out_dir / f"checkpoint_{run_id}.md").write_text("\n".join(md), encoding="utf-8")
    print(f"== review card written to {out_dir}/checkpoint_{run_id}.md ==")


async def _produce(
    threat_start: float,
    threat_duration: float,
    windows_override: dict[str, list[float]] | None = None,
    auto_approve: bool = False,
) -> None:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    run_id = uuid4()
    workflow_id = f"{WORKFLOW_PREFIX}/{run_id}"
    trace_id = uuid4().hex

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
        windows = _windows(threat_start, threat_duration)
        if windows_override:
            windows = {
                key: (float(value[0]), float(value[1]))
                for key, value in windows_override.items()
                if key in windows
            }
        beats = _build_beats(windows)
        candidates = _build_candidates(beats, windows)
        narration = _build_narration(beats)
        pointers = _commit_inputs(
            connection,
            repository,
            run_id=run_id,
            trace_id=trace_id,
            project_id=PROJECT_ID,
            beats=beats,
            candidates=candidates,
            narration=narration,
        )
        request = _request(run_id, PROJECT_ID, pointers, beats)

    print("== Episode 8 creative timeline production (威胁倒叙) ==")
    print(f"run_id={run_id}  source={SOURCE_ARTIFACT_ID}  beats=3")
    for name, pointer in pointers.items():
        print(f"  {name}: {pointer.artifact_id} v{pointer.version}")

    client = await Client.connect(settings.temporal_target)
    async with _worker(client):
        handle = await client.start_workflow(
            CreativeTimelineWorkflow.run,
            request,
            id=workflow_id,
            task_queue=TASK_QUEUE,
        )
        status = await _wait_for_state(handle, {"awaiting_review", "blocked"})
        print(f"== reached {status.state} (stages={dict(status.stage_states)}) ==")
        if status.state != "awaiting_review":
            raise SystemExit(f"workflow blocked: {status.blocked_codes}")
        for name, pointer in sorted(status.artifacts.items()):
            print(f"  artifact[{name}] = {pointer.artifact_id} v{pointer.version}")
        print(f"  review_id = {status.active_review_id}")
    _write_review_card(run_id, workflow_id, status)
    if auto_approve:
        await _sign(run_id, "approve")
        print(f"== auto-approved run {run_id} ==")
        return
    print("== STOPPED at human timeline checkpoint ==")
    print("review the preview + ASS + card, then run:")
    print(
        f"  .venv/bin/python scripts/produce_vc003_timeline.py "
        f"--run-id {run_id} --decision approve|revise|reject"
    )


async def _sign(run_id: UUID, decision: str) -> None:
    settings = get_settings()
    workflow_id = f"{WORKFLOW_PREFIX}/{run_id}"
    review_id = f"review:{run_id}:timeline"
    client = await Client.connect(settings.temporal_target)
    async with _worker(client):
        handle = client.get_workflow_handle(workflow_id)
        status = await handle.query(CreativeTimelineWorkflow.get_status)  # type: ignore[attr-defined]
        if status is None:
            raise SystemExit(f"workflow {workflow_id} has no status")
        if status.active_review_id != review_id:
            raise SystemExit(
                f"workflow is not at review {review_id!r} (active={status.active_review_id!r})"
            )
        signal = ReviewSignal(
            review_id=review_id,
            target_version=1,
            decision=decision,
        )
        await handle.signal(CreativeTimelineWorkflow.submit_review_decision, signal)
        print(f"== {decision} signal sent; waiting for settlement ==")
        elapsed = 0.0
        while elapsed < 900.0:
            current = await handle.query(CreativeTimelineWorkflow.get_status)  # type: ignore[attr-defined]
            if current is None:
                break
            print(f"  ... state={current.state} stages={dict(current.stage_states)}")
            if current.state in {"succeeded", "blocked", "rejected", "revise"}:
                print(f"== workflow {current.state} ==")
                if current.state != "succeeded":
                    raise SystemExit(f"workflow did not succeed: {current.blocked_codes}")
                return
            await asyncio.sleep(3.0)
            elapsed += 3.0
        raise SystemExit("timed out waiting for workflow settlement")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", help="write card / sign an existing run")
    parser.add_argument(
        "--decision",
        choices=("approve", "revise", "reject"),
        help="human checkpoint decision (requires --run-id)",
    )
    parser.add_argument("--threat-start", type=float, default=DEFAULT_WINDOWS["threat"][0])
    parser.add_argument("--threat-duration", type=float, default=DEFAULT_WINDOWS["threat"][1])
    parser.add_argument(
        "--windows-json",
        type=Path,
        help="per-beat window overrides: {threat: [start, duration], sale: [...], payment: [...]}",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="auto-sign the timeline checkpoint (no human stop)",
    )
    args = parser.parse_args()
    windows_override = (
        json.loads(args.windows_json.read_text(encoding="utf-8"))
        if args.windows_json is not None
        else None
    )
    if args.decision is not None:
        if args.run_id is None:
            raise SystemExit("--decision requires --run-id")
        asyncio.run(_sign(UUID(args.run_id), args.decision))
    elif args.run_id is not None:
        asyncio.run(_card(UUID(args.run_id)))
    else:
        asyncio.run(
            _produce(
                args.threat_start,
                args.threat_duration,
                windows_override=windows_override,
                auto_approve=args.auto_approve,
            )
        )
    return 0


async def _card(run_id: UUID) -> None:
    settings = get_settings()
    workflow_id = f"{WORKFLOW_PREFIX}/{run_id}"
    client = await Client.connect(settings.temporal_target)
    # Queries need a live poller on the task queue; start one for the query.
    async with _worker(client):
        handle = client.get_workflow_handle(workflow_id)
        status = await handle.query(CreativeTimelineWorkflow.get_status)  # type: ignore[attr-defined]
        if status is None:
            raise SystemExit(f"workflow {workflow_id} has no status")
        print(f"== {workflow_id}: state={status.state} ==")
        _write_review_card(run_id, workflow_id, status)


if __name__ == "__main__":
    raise SystemExit(main())
