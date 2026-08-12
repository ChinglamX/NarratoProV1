from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.contracts import StoryReviewPackage


def ref(kind: str) -> dict[str, object]:
    return {"artifact_id": uuid4(), "version": 1, "artifact_type": kind}


def package(**overrides: object) -> StoryReviewPackage:
    values: dict[str, object] = {
        "fact_ref": ref("FactSet"),
        "identity_ref": ref("IdentityGraph"),
        "event_set_ref": ref("EventSet"),
        "character_state_ref": ref("CharacterStateGraph"),
        "causal_graph_ref": ref("CausalGraph"),
        "story_graph_ref": ref("StoryGraph"),
        "config_refs": [ref("ConfigArtifact")],
    }
    values.update(overrides)
    return StoryReviewPackage.model_validate(values)


def test_story_review_freezes_all_exact_inputs() -> None:
    value = package()
    assert value.story_graph_ref.version == 1
    with pytest.raises(ValidationError, match="requires exact config refs"):
        package(config_refs=[])
    with pytest.raises(ValidationError, match="must reference StoryGraph"):
        package(story_graph_ref=ref("FactSet"))
