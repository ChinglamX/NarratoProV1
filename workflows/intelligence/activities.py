"""Executable typed Story activities; large payloads stay in Artifact storage."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from hashlib import sha256
from itertools import pairwise
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import Connection
from temporalio import activity

from packages.contracts import (
    ArtifactEnvelope,
    ArtifactRef,
    CausalGraph,
    CharacterStateGraph,
    EventSet,
    FactSet,
    IdentityGraph,
)
from packages.foundation.settings import get_settings
from packages.intelligence.story import assemble_story_graph, build_event_set, retrieve_story_facts
from packages.persistence import ArtifactRepository
from packages.persistence.database import create_database_engine, transaction
from workflows.intelligence.models import StoryReasoningInput, StoryStageResult
from workflows.project.models import ArtifactPointer

ContractT = TypeVar("ContractT", bound=BaseModel)


def _ref(pointer: ArtifactPointer) -> ArtifactRef:
    return ArtifactRef.model_validate(
        {
            "artifact_id": pointer.artifact_id,
            "version": pointer.version,
            "artifact_type": pointer.artifact_type,
            "checksum": pointer.checksum,
        }
    )


def _pointer(reference: ArtifactRef) -> ArtifactPointer:
    return ArtifactPointer(
        str(reference.artifact_id),
        reference.version,
        str(reference.artifact_type),
        str(reference.checksum) if reference.checksum else None,
    )


def _load(
    repository: ArtifactRepository,
    connection: Connection,
    pointer: ArtifactPointer,
    model: type[ContractT],
) -> ContractT:
    row = repository.get_version(connection, _ref(pointer))
    return model.model_validate(row["payload_json"])


def _commit(
    repository: ArtifactRepository,
    connection: Connection,
    *,
    request: StoryReasoningInput,
    artifact_id: str,
    artifact_type: str,
    payload: BaseModel,
    inputs: tuple[ArtifactRef, ...],
) -> ArtifactRef:
    encoded = payload.model_dump_json(exclude_none=False).encode()
    envelope = ArtifactEnvelope.model_validate(
        {
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "schema_version": "2.0.0",
            "version": 1,
            "project_id": request.project_id,
            "run_id": request.run_id,
            "state": "committed",
            "created_at": datetime.now(UTC),
            "created_by": {"kind": "system", "id": "story-reasoner"},
            "inputs": inputs,
            "producer": {
                "module": "story-reasoner",
                "module_version": "1.0.0",
                "config_refs": [_ref(request.config)],
                "resource_profile_ref": _ref(request.resource_profile),
            },
            "checksum": "sha256:" + sha256(encoded).hexdigest(),
            "rights_class": "internal-story",
            "trace_id": request.trace_id,
            "payload": payload.model_dump(mode="json"),
        }
    )
    repository.reserve(
        connection,
        artifact_id=UUID(artifact_id),
        project_id=UUID(request.project_id),
        artifact_type=artifact_type,
    )
    return repository.commit_version(connection, envelope, expected_latest_version=0)


def _run_stage(request: StoryReasoningInput, stage: str) -> StoryStageResult:
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    repository = ArtifactRepository()
    try:
        with engine.connect() as connection:
            facts = _load(repository, connection, request.fact_set, FactSet)
            identity = _load(repository, connection, request.identity_graph, IdentityGraph)
            fact_ref = _ref(request.fact_set)
            payload: BaseModel
            inputs: tuple[ArtifactRef, ...]
            if stage == "event_set":
                payload = build_event_set(fact_ref=fact_ref, facts=retrieve_story_facts(facts))
                output_id, output_type = request.event_set_artifact_id, "EventSet"
                inputs = (fact_ref, _ref(request.identity_graph))
            else:
                event_pointer = ArtifactPointer(request.event_set_artifact_id, 1, "EventSet")
                event_set = _load(repository, connection, event_pointer, EventSet)
                event_ref = _ref(event_pointer)
                if stage == "character_state":
                    payload = CharacterStateGraph(
                        source_event_ref=event_ref,
                        states=(),
                        unresolved_character_ids=tuple(
                            item.character_id for item in identity.characters
                        ),
                    )
                    output_id, output_type = (
                        request.state_graph_artifact_id,
                        "CharacterStateGraph",
                    )
                    inputs = (event_ref, _ref(request.identity_graph))
                elif stage == "causal_graph":
                    event_ids = tuple(item.event_id for item in event_set.events)
                    payload = CausalGraph(
                        source_event_ref=event_ref,
                        edges=(),
                        unresolved_pairs=tuple(pairwise(event_ids)),
                    )
                    output_id, output_type = request.causal_graph_artifact_id, "CausalGraph"
                    inputs = (event_ref,)
                else:
                    payload = assemble_story_graph(
                        fact_ref=fact_ref, identity=identity, event_set=event_set
                    )
                    output_id, output_type = request.story_graph_artifact_id, "StoryGraph"
                    inputs = (
                        fact_ref,
                        _ref(request.identity_graph),
                        event_ref,
                        ArtifactRef.model_validate(
                            {
                                "artifact_id": request.state_graph_artifact_id,
                                "version": 1,
                                "artifact_type": "CharacterStateGraph",
                            }
                        ),
                        ArtifactRef.model_validate(
                            {
                                "artifact_id": request.causal_graph_artifact_id,
                                "version": 1,
                                "artifact_type": "CausalGraph",
                            }
                        ),
                    )
        with transaction(engine) as connection:
            output = _commit(
                repository,
                connection,
                request=request,
                artifact_id=output_id,
                artifact_type=output_type,
                payload=payload,
                inputs=inputs,
            )
        unresolved = len(getattr(payload, "unresolved_pairs", ())) + len(
            getattr(payload, "unresolved_character_ids", ())
        )
        return StoryStageResult(_pointer(output), unresolved)
    finally:
        engine.dispose()


@activity.defn
async def build_event_set_activity(request: StoryReasoningInput) -> StoryStageResult:
    activity.heartbeat({"stage": "event_set", "trace_id": request.trace_id})
    return await asyncio.to_thread(_run_stage, request, "event_set")


@activity.defn
async def build_character_state_activity(request: StoryReasoningInput) -> StoryStageResult:
    activity.heartbeat({"stage": "character_state", "trace_id": request.trace_id})
    return await asyncio.to_thread(_run_stage, request, "character_state")


@activity.defn
async def build_causal_graph_activity(request: StoryReasoningInput) -> StoryStageResult:
    activity.heartbeat({"stage": "causal_graph", "trace_id": request.trace_id})
    return await asyncio.to_thread(_run_stage, request, "causal_graph")


@activity.defn
async def assemble_story_graph_activity(request: StoryReasoningInput) -> StoryStageResult:
    activity.heartbeat({"stage": "story_graph", "trace_id": request.trace_id})
    return await asyncio.to_thread(_run_stage, request, "story_graph")
