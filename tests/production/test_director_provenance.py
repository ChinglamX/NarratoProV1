import pytest

from packages.production.director_provenance import (
    AgentRole,
    DecisionRecord,
    ProductionRunProvenance,
    TaskType,
)


def test_role_matches_task_and_decisions_remain_separate() -> None:
    record = ProductionRunProvenance(
        task_type=TaskType.DRAMA_PRODUCTION,
        active_role=AgentRole.DRAMA_PRODUCER,
        auxiliary_roles=(AgentRole.SYSTEM_ENGINEER,),
        director_decisions=(
            DecisionRecord(
                decision_id="ending",
                description="use a closed payoff",
                actor_role=AgentRole.DRAMA_PRODUCER,
                rationale="the reference has no supported next-story visual",
            ),
        ),
        tool_generated_outputs=("candidate.mp4",),
        human_corrections=("remove unsupported suspense",),
        release_gate_status="not_requested",
    )
    payload = record.to_dict()
    assert payload["active_role"] == AgentRole.DRAMA_PRODUCER
    assert payload["director_decisions"][0]["decision_id"] == "ending"


def test_invalid_role_switch_is_rejected() -> None:
    with pytest.raises(ValueError, match="match the task type"):
        ProductionRunProvenance(
            task_type=TaskType.DRAMA_PRODUCTION,
            active_role=AgentRole.SYSTEM_ENGINEER,
            auxiliary_roles=(),
            director_decisions=(),
            tool_generated_outputs=(),
            human_corrections=(),
            release_gate_status="not_requested",
        )
