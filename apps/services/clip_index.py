"""Persistence-backed :class:`ClipIndexPort` adapter over committed candidate sets.

The semantic visual provider is not production-admitted (E09 blocker), so the
retrieval boundary for L1 planning reads *human-approved* ``ClipCandidateSet``
artifacts and applies deterministic, evidence-grounded routing. Adapters never
own selection policy; :func:`packages.timeline.visual_planning.retrieve_candidates`
still rejects mismatched or ungrounded results.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from fractions import Fraction
from typing import Any
from uuid import UUID

from sqlalchemy import Connection

from packages.contracts import ArtifactRef
from packages.contracts.timeline_intent import (
    ClipCandidate,
    ClipCandidateSet,
    ClipRetrievalQuery,
    RetrievalRoute,
)
from packages.persistence.artifact_repository import ArtifactNotFound, ArtifactRepository

ROUTE_SCORE_COMPONENTS: dict[RetrievalRoute, str] = {
    RetrievalRoute.EVIDENCE: "evidence",
    RetrievalRoute.CHARACTER: "character",
    RetrievalRoute.NEIGHBORHOOD: "continuity",
    RetrievalRoute.SEMANTIC: "semantic",
    RetrievalRoute.HUMAN_PIN: "human_pin",
}


class ClipIndexUnavailable(RuntimeError):
    pass


class PersistenceClipIndex:
    """Deterministic adapter over exact-version ``ClipCandidateSet`` artifacts."""

    def __init__(
        self,
        repository: ArtifactRepository,
        connection: Connection,
        candidate_set_refs: Sequence[ArtifactRef],
        *,
        source_duration_by_ref: Mapping[UUID, Fraction] | None = None,
    ) -> None:
        self._candidates = self._load(repository, connection, candidate_set_refs)
        self._source_duration_by_ref = source_duration_by_ref or {}

    def _load(
        self,
        repository: ArtifactRepository,
        connection: Connection,
        candidate_set_refs: Sequence[ArtifactRef],
    ) -> tuple[ClipCandidate, ...]:
        merged: dict[UUID, ClipCandidate] = {}
        for reference in candidate_set_refs:
            if reference.artifact_type != "ClipCandidateSet":
                raise ClipIndexUnavailable(
                    f"clip index requires ClipCandidateSet refs, got {reference.artifact_type}"
                )
            try:
                row = repository.get_version(connection, reference)
            except ArtifactNotFound as error:
                raise ClipIndexUnavailable(str(error)) from error
            payload: Any = row.get("payload_json")
            if not isinstance(payload, dict):
                raise ClipIndexUnavailable("clip candidate set payload is unavailable")
            candidate_set = ClipCandidateSet.model_validate(payload)
            for candidate in candidate_set.candidates:
                merged.setdefault(candidate.candidate_id, candidate)
        return tuple(merged.values())

    def _admissible(self, query: ClipRetrievalQuery) -> list[ClipCandidate]:
        matched = []
        for candidate in self._candidates:
            if candidate.beat_id != query.beat_id:
                continue
            if not set(candidate.story_refs).intersection(query.story_refs):
                continue
            if query.required_character_refs and not set(query.required_character_refs).issubset(
                candidate.visible_character_refs
            ):
                continue
            known_duration = self._source_duration_by_ref.get(candidate.source_ref.artifact_id)
            if known_duration is not None and candidate.source_range.end_seconds > known_duration:
                continue
            matched.append(candidate)
        return matched

    def retrieve(self, query: ClipRetrievalQuery) -> Sequence[ClipCandidate]:
        merged: dict[UUID, ClipCandidate] = {}
        for route in query.routes:
            component = ROUTE_SCORE_COMPONENTS[route]
            ranked = sorted(
                self._admissible(query),
                key=lambda item: (
                    -item.score_components.get(component, 0.0),
                    str(item.candidate_id),
                ),
            )
            for candidate in ranked[: query.top_k_per_route]:
                merged.setdefault(candidate.candidate_id, candidate)
        return tuple(sorted(merged.values(), key=lambda item: str(item.candidate_id)))
