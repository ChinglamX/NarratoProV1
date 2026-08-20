"""Materialize and approve the exact Episode 8 VC-002 Gate 1 package."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID, uuid4

from packages.contracts import (
    ActorRef,
    ArtifactRef,
    CausalGraph,
    CharacterStateGraph,
    EntailmentStatus,
    EventCandidate,
    EventSet,
    FactSet,
    IdentityGraph,
    StoryGraph,
    StoryReviewPackage,
)
from packages.foundation.settings import get_settings
from packages.persistence import ArtifactRepository
from packages.persistence.artifact_writer import commit_contract_artifact
from packages.persistence.database import create_database_engine
from packages.persistence.review_repository import ReviewRepository

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = UUID("dd397853-79bc-4e6f-a540-bb1c296d6936")
RUN_ID = UUID("136b8fe5-180a-4159-8097-5f688e155305")
TRACE_ID = "8e002000000000000000000000000002"
STORY_REF = ArtifactRef.model_validate(
    {
        "artifact_id": "c378ba51-da33-4049-baf0-538ca637e9a5",
        "version": 1,
        "artifact_type": "StoryGraph",
        "checksum": "sha256:8b34ae0d15d81126a1907366e27efcb4ce113e5bea0e1d2fae0ec146d0c7aad2",
    }
)
FACT_REF = ArtifactRef.model_validate(
    {
        "artifact_id": "17140235-dc00-4851-b3c1-5d819290fe9f",
        "version": 1,
        "artifact_type": "FactSet",
        "checksum": "sha256:220ed1b89a7d6e6032c0a989b57b8990871ddb85e6c25a09349897a060eed776",
    }
)
SPEECH_REF = ArtifactRef.model_validate(
    {
        "artifact_id": "d54f3bb7-ff62-4ee0-824c-f0126328ba24",
        "version": 1,
        "artifact_type": "SpeechObservation",
        "checksum": "sha256:a989cfb5304a8dde24c8a75622eeed18c8c67d1f195ecda17b4e80cf11cce0a6",
    }
)


def main() -> int:
    engine = create_database_engine(get_settings().database_url)
    artifacts, reviews = ArtifactRepository(), ReviewRepository()
    actor = ActorRef.model_validate({"kind": "human", "id": "project-owner"})
    profile_ref = ArtifactRef.model_validate(
        {"artifact_id": uuid4(), "version": 1, "artifact_type": "ConfigArtifact"}
    )
    with engine.connect() as connection:
        story_row = artifacts.get_version(connection, STORY_REF)
        fact_row = artifacts.get_version(connection, FACT_REF)
    if story_row["checksum"] != str(STORY_REF.checksum):
        raise RuntimeError("Gate 1 StoryGraph checksum drift")
    story = StoryGraph.model_validate(story_row["payload_json"])
    facts = FactSet.model_validate(fact_row["payload_json"])
    if not facts.facts:
        raise RuntimeError("Gate 1 requires at least one persisted Fact")

    identity_id, event_id, state_id, causal_id, config_id = (uuid4() for _ in range(5))
    review_id = uuid4()
    with engine.begin() as connection:
        identity_ref = commit_contract_artifact(
            connection,
            artifacts,
            artifact_id=identity_id,
            artifact_type="IdentityGraph",
            payload=IdentityGraph(
                source_observation_refs=(SPEECH_REF,), nodes=(), edges=(), characters=()
            ),
            project_id=PROJECT_ID,
            run_id=RUN_ID,
            variant_id=None,
            trace_id=TRACE_ID,
            actor=actor,
            producer_module="vc002-human-reviewed-story-boundary",
            module_version="1.0.0",
            resource_profile_ref=profile_ref,
            rights_class="internal-only",
            inputs=(SPEECH_REF,),
            schema_version="1.8.0",
        )
        event_ref_placeholder = ArtifactRef.model_validate(
            {"artifact_id": event_id, "version": 1, "artifact_type": "EventSet"}
        )
        candidates_list: list[EventCandidate] = []
        for event in story.events:
            if event.source_range is None:
                raise RuntimeError("Gate 1 event is missing its source range")
            candidates_list.append(
                EventCandidate(
                    candidate_id=uuid4(),
                    source_fact_ids=(facts.facts[0].fact_id,),
                    description=event.description,
                    source_range=event.source_range,
                    evidence=event.evidence,
                    confidence=event.confidence,
                    entailment=EntailmentStatus.SUPPORTED,
                )
            )
        candidates = tuple(candidates_list)
        event_ref = commit_contract_artifact(
            connection,
            artifacts,
            artifact_id=event_id,
            artifact_type="EventSet",
            payload=EventSet(
                source_fact_ref=FACT_REF,
                candidates=candidates,
                events=story.events,
            ),
            project_id=PROJECT_ID,
            run_id=RUN_ID,
            variant_id=None,
            trace_id=TRACE_ID,
            actor=actor,
            producer_module="vc002-human-reviewed-event-boundary",
            module_version="1.0.0",
            resource_profile_ref=profile_ref,
            rights_class="internal-only",
            inputs=(FACT_REF,),
            schema_version="2.0.0",
        )
        if event_ref != event_ref_placeholder.model_copy(update={"checksum": event_ref.checksum}):
            raise RuntimeError("EventSet identity changed during commit")
        state_ref = commit_contract_artifact(
            connection,
            artifacts,
            artifact_id=state_id,
            artifact_type="CharacterStateGraph",
            payload=CharacterStateGraph(source_event_ref=event_ref, states=()),
            project_id=PROJECT_ID,
            run_id=RUN_ID,
            variant_id=None,
            trace_id=TRACE_ID,
            actor=actor,
            producer_module="vc002-no-character-state-claims",
            module_version="1.0.0",
            resource_profile_ref=profile_ref,
            rights_class="internal-only",
            inputs=(event_ref,),
            schema_version="2.0.0",
        )
        causal_ref = commit_contract_artifact(
            connection,
            artifacts,
            artifact_id=causal_id,
            artifact_type="CausalGraph",
            payload=CausalGraph(source_event_ref=event_ref, edges=()),
            project_id=PROJECT_ID,
            run_id=RUN_ID,
            variant_id=None,
            trace_id=TRACE_ID,
            actor=actor,
            producer_module="vc002-no-causal-edge-claims",
            module_version="1.0.0",
            resource_profile_ref=profile_ref,
            rights_class="internal-only",
            inputs=(event_ref,),
            schema_version="2.0.0",
        )
        config_ref = commit_contract_artifact(
            connection,
            artifacts,
            artifact_id=config_id,
            artifact_type="ConfigArtifact",
            payload={
                "scope": "vc002-episode-08-factual-summary-only",
                "automation_level": "L1",
                "confidence": "unavailable",
                "not_proven": [
                    "canonical-character-identity",
                    "causal-story-arc",
                    "generalized-story-understanding",
                ],
            },
            project_id=PROJECT_ID,
            run_id=RUN_ID,
            variant_id=None,
            trace_id=TRACE_ID,
            actor=actor,
            producer_module="vc002-gate1-scope",
            module_version="1.0.0",
            resource_profile_ref=profile_ref,
            rights_class="internal-only",
            inputs=(STORY_REF,),
            schema_version="1.0.0",
        )
        package = StoryReviewPackage(
            fact_ref=FACT_REF,
            identity_ref=identity_ref,
            event_set_ref=event_ref,
            character_state_ref=state_ref,
            causal_graph_ref=causal_ref,
            story_graph_ref=STORY_REF,
            config_refs=(config_ref,),
            unresolved_count=len(story.unresolved_questions),
            incomplete=False,
        )
        reviews.create_request(
            connection,
            review_id=review_id,
            project_id=PROJECT_ID,
            workflow_id=f"vc002-gate1/{review_id}",
            gate="story",
            target_ref=STORY_REF.model_dump(mode="json"),
            policy_snapshot={
                "automation_level": "L1",
                "story_review_package": package.model_dump(mode="json"),
            },
        )
        decision = reviews.decide(
            connection,
            review_id=review_id,
            expected_target_version=1,
            decision="approve",
            reviewer_snapshot={
                "actor_id": "project-owner",
                "roles": ["reviewer"],
                "service_account": False,
            },
            reasons=[
                {
                    "code": "project-owner-approved-gate-1",
                    "detail": (
                        "User explicitly approved Gate 1 after factual and corrected "
                        "evidence review."
                    ),
                }
            ],
            trace_id=TRACE_ID,
        )
        approved = reviews.approved_story(connection, project_id=PROJECT_ID)
        if (
            approved is None
            or str(approved["artifact_id"]) != str(STORY_REF.artifact_id)
            or approved["version"] != STORY_REF.version
            or approved["artifact_type"] != STORY_REF.artifact_type
        ):
            raise RuntimeError("approved Story publication pointer mismatch")

    result = {
        "review_id": str(review_id),
        "decision_id": str(decision.decision_id),
        "decision": "approve",
        "approved_story_ref": STORY_REF.model_dump(mode="json", exclude_none=True),
        "review_package": package.model_dump(mode="json"),
        "scope": "Episode 8 factual summary only",
    }
    output = ROOT / "outputs/vc002_episode_08/gate1_approval.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
