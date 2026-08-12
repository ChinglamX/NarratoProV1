from uuid import uuid4

import pytest

from packages.contracts import ArtifactRef
from packages.contracts.timeline_intent import (
    NarrationLine,
    NarrationLineSet,
    NarrativeBeat,
    NarrativeBeatGraph,
)
from packages.timeline.rhythm_narration import (
    allocate_rhythm,
    replace_lines_in_scope,
    review_narration,
)


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=kind)


def t(value: int) -> dict[str, int]:
    return {"value": value, "rate_num": 1}


def test_budget_reconciles_and_impossible_budget_conflicts() -> None:
    beat = NarrativeBeat(
        beat_id=uuid4(),
        function="hook",
        story_refs=(uuid4(),),
        target_duration=t(5),
        minimum_duration=t(3),
        maximum_duration=t(7),
        required_information=("conflict",),
        emotional_intent={},
    )
    graph = NarrativeBeatGraph(
        creative_brief_ref=ref("CreativeBrief"), beats=(beat,), target_duration=t(5)
    )
    plan, conflict = allocate_rhythm(
        beat_graph_ref=ref("NarrativeBeatGraph"),
        selection_plan_ref=ref("PatchProposal"),
        graph=graph,
    )
    assert plan and not conflict and plan.target_duration.seconds == 5


def test_narration_blocks_repetition_and_preserves_locks() -> None:
    beat_id, line_id = uuid4(), uuid4()
    line = NarrationLine(
        line_id=line_id,
        beat_id=beat_id,
        text="你站住",
        function="bridge",
        story_refs=(uuid4(),),
        evidence_refs=(uuid4(),),
        target_duration=t(2),
        dialogue_relationship="none",
        locked=True,
    )
    lines = NarrationLineSet(
        creative_brief_ref=ref("CreativeBrief"),
        rhythm_plan_ref=ref("PatchProposal"),
        lines=(line,),
        estimated_duration=t(2),
    )
    report = review_narration(
        line_set_ref=ref("NarrationLineSet"), lines=lines, dialogue_by_beat={beat_id: ("你站住!",)}
    )
    assert report.findings[0].code == "dialogue-repetition" and report.evidence_coverage == 1
    with pytest.raises(ValueError, match="locked"):
        replace_lines_in_scope(lines, {line_id: line.model_copy(update={"text": "换句话"})})
