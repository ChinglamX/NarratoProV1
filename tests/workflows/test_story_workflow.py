from pathlib import Path


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
