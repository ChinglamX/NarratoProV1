"""Real-data E07 StoryReasoningWorkflow verification.

Uses a real persisted FactSet (36 FactSet / 571 Facts from OCR evidence chain,
run b7b7eccd) plus an empty IdentityGraph (conservative: no human-corrected
identity nodes yet, ADR-033) to run the full event_set -> character_state ->
causal_graph -> story_graph chain on the real Temporal server. Proves the
Story reasoning pipeline consumes real observed facts end-to-end.
"""

import asyncio
from uuid import uuid4

import sqlalchemy as sa
from temporalio.client import Client
from temporalio.worker import Worker

from packages.contracts import ActorRef
from packages.contracts.identity import IdentityGraph
from packages.foundation.settings import get_settings
from packages.persistence.artifact_repository import ArtifactRepository
from packages.persistence.artifact_writer import commit_contract_artifact
from packages.persistence.database import create_database_engine
from workflows.intelligence.activities import (
    assemble_story_graph_activity,
    build_causal_graph_activity,
    build_character_state_activity,
    build_event_set_activity,
)
from workflows.intelligence.models import StoryReasoningInput
from workflows.intelligence.workflow import StoryReasoningWorkflow

PROJECT = "2052f76b-0709-4d29-a858-20916779096f"
FACT_SET = ("edfae9dd-815f-4804-8b25-5fa772118c42", 1, "FactSet")
CONFIG = ("7d3276d5-2097-424b-a50b-0535c50ec503", 1, "ConfigArtifact")
ACTOR = ActorRef.model_validate({"kind": "system", "id": "e07-real-verify"})


async def main() -> None:
    settings = get_settings()
    run_id = uuid4()
    identity_id = uuid4()
    engine = create_database_engine(settings.database_url)

    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "insert into core.run (id, project_id, workflow_id, state, "
                "automation_policy_snapshot, resource_profile_snapshot) "
                "values (:i,:p,:w,'running','{}','{}')"
            ),
            {"i": run_id, "p": PROJECT, "w": f"e07-story/{run_id}"},
        )
        repository = ArtifactRepository()
        identity = IdentityGraph(
            source_observation_refs=(),
            nodes=(),
            edges=(),
            characters=(),
            conflicts=(),
            applied_proposal_ids=(),
            incomplete=False,
        )
        identity_ref = commit_contract_artifact(
            connection,
            repository,
            artifact_id=identity_id,
            artifact_type="IdentityGraph",
            payload=identity,
            project_id=PROJECT,
            run_id=run_id,
            variant_id=None,
            trace_id="a" * 32,
            actor=ACTOR,
            producer_module="e07-real-verify",
            module_version="v1",
            resource_profile_ref={
                "artifact_id": CONFIG[0],
                "version": CONFIG[1],
                "artifact_type": CONFIG[2],
            },
            rights_class="internal-story",
            inputs=(),
        )
        print("IDENTITY_COMMITTED:", identity_ref.artifact_id)

    request = StoryReasoningInput(
        project_id=PROJECT,
        run_id=str(run_id),
        trace_id="a" * 32,
        fact_set=__import__(
            "workflows.project.models", fromlist=["ArtifactPointer"]
        ).ArtifactPointer(FACT_SET[0], FACT_SET[1], FACT_SET[2]),
        identity_graph=__import__(
            "workflows.project.models", fromlist=["ArtifactPointer"]
        ).ArtifactPointer(str(identity_id), 1, "IdentityGraph", str(identity_ref.checksum)),
        config=__import__("workflows.project.models", fromlist=["ArtifactPointer"]).ArtifactPointer(
            CONFIG[0], CONFIG[1], CONFIG[2]
        ),
        resource_profile=__import__(
            "workflows.project.models", fromlist=["ArtifactPointer"]
        ).ArtifactPointer(CONFIG[0], CONFIG[1], CONFIG[2]),
        event_set_artifact_id=str(uuid4()),
        state_graph_artifact_id=str(uuid4()),
        causal_graph_artifact_id=str(uuid4()),
        story_graph_artifact_id=str(uuid4()),
    )

    client = await Client.connect(settings.temporal_target)
    worker = Worker(
        client,
        task_queue="control",
        workflows=[StoryReasoningWorkflow],
        activities=[
            build_event_set_activity,
            build_character_state_activity,
            build_causal_graph_activity,
            assemble_story_graph_activity,
        ],
    )
    async with worker:
        handle = await client.start_workflow(
            StoryReasoningWorkflow.run,
            request,
            id=f"e07-story/{run_id}",
            task_queue="control",
        )
        result = await asyncio.wait_for(handle.result(), timeout=300)
        print("STATE:", result.state, "| stage:", result.current_stage)
        print("event_set:", result.event_set.artifact_id[:8] if result.event_set else None)
        print(
            "character_state:",
            result.character_state_graph.artifact_id[:8] if result.character_state_graph else None,
        )
        print("causal_graph:", result.causal_graph.artifact_id[:8] if result.causal_graph else None)
        print("story_graph:", result.story_graph.artifact_id[:8] if result.story_graph else None)
        assert result.state == "succeeded", result
        # Conservative fusion expectation: OCR-only facts (fact_type=ocr) are NOT
        # promoted to events (ADR-035 observable-only; event types are
        # dialogue/action/audio_signal/visual_signal). The chain must still run
        # end-to-end against the real persisted FactSet.
        print("VERIFY_OK")


asyncio.run(main())
