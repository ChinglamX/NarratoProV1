from pathlib import Path
from uuid import uuid4

import pytest

from workflows.intelligence import workflow as story_workflow
from workflows.intelligence.models import (
    StoryReasoningInput,
    StoryStageResult,
)
from workflows.project.models import ArtifactPointer


def test_story_workflow_keeps_typed_stages_and_pointer_payloads() -> None:
    source = Path("workflows/intelligence/workflow.py").read_text()
    order = [
        "build_event_set_activity",
        "build_character_state_activity",
        "build_causal_graph_activity",
        "assemble_story_graph_activity",
    ]
    positions = [source.rfind(name) for name in order]
    assert positions == sorted(positions)
    models = Path("workflows/intelligence/models.py").read_text()
    assert "ArtifactPointer" in models
    assert "FactSet" not in models and "StoryGraph" not in models


@pytest.mark.anyio
async def test_story_workflow_runs_all_typed_stages(monkeypatch: pytest.MonkeyPatch) -> None:
    outputs = iter(
        ArtifactPointer(str(uuid4()), 1, kind)
        for kind in ("EventSet", "CharacterStateGraph", "CausalGraph", "StoryGraph")
    )

    async def execute(*_args, **_kwargs):
        return StoryStageResult(next(outputs))

    monkeypatch.setattr(story_workflow.workflow, "execute_activity", execute)

    def pointer(kind: str) -> ArtifactPointer:
        return ArtifactPointer(str(uuid4()), 1, kind)

    request = StoryReasoningInput(
        project_id=str(uuid4()),
        run_id=str(uuid4()),
        trace_id="a" * 32,
        fact_set=pointer("FactSet"),
        identity_graph=pointer("IdentityGraph"),
        config=pointer("ConfigArtifact"),
        resource_profile=pointer("ResourceProfile"),
        event_set_artifact_id=str(uuid4()),
        state_graph_artifact_id=str(uuid4()),
        causal_graph_artifact_id=str(uuid4()),
        story_graph_artifact_id=str(uuid4()),
    )
    instance = story_workflow.StoryReasoningWorkflow()
    result = await instance.run(request)
    assert result.state == "succeeded" and result.current_stage == "complete"
    assert result.event_set and result.character_state_graph
    assert result.causal_graph and result.story_graph
    assert instance.status() is result
