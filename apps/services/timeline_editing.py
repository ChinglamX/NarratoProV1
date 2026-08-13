"""Precise timeline editing service: patch, undo, redo, version navigation.

Wraps the deterministic patch engine and persistence layer with a clean
service boundary. Every mutating operation runs inside a database transaction
and emits an outbox event through the repository.

This service is stateless: each call reloads the current state from storage.
Undo/redo are implemented by moving the active version pointer, not by
deleting or rewriting history.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any
from uuid import UUID

from sqlalchemy import Engine

from packages.contracts import MasterTimeline, TimelinePatch
from packages.persistence.database import transaction
from packages.persistence.timeline_repository import (
    TimelineRepository,
    TimelineStorageConflict,
)
from packages.timeline.patches import (
    TimelineChange,
    TimelinePatchConflict,
    apply_patch,
    can_rebase,
    semantic_diff,
)
from packages.timeline.validator import validate_timeline


class TimelineEditingError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PatchResult:
    timeline_id: UUID
    version: int
    checksum: str
    rebased: bool
    changes: tuple[TimelineChange, ...]


@dataclass(frozen=True, slots=True)
class NavigationResult:
    timeline_id: UUID
    version: int
    previous_version: int
    reason: str


@dataclass(frozen=True, slots=True)
class VersionSummary:
    version: int
    producer: dict[str, Any]
    changes: tuple[TimelineChange, ...] | None = None


class TimelineEditingService:
    """Application service for precise multi-track timeline editing."""

    def __init__(
        self,
        engine: Engine,
        repository: TimelineRepository | None = None,
    ) -> None:
        self._engine = engine
        self._repository = repository or TimelineRepository()

    def apply_patch(
        self,
        *,
        timeline_id: UUID,
        patch: TimelinePatch,
        trace_id: str,
    ) -> PatchResult:
        """Apply a semantic patch and commit a new timeline version.

        Supports optimistic concurrency: if the base version is not current,
        the patch is rebased onto the current version when safe (no overlapping
        item changes).
        """
        if patch.base_timeline.artifact_id != timeline_id:
            raise TimelineEditingError("patch base does not match timeline identity")
        try:
            with transaction(self._engine) as connection:
                base_snapshot, current_snapshot = self._repository.lock_and_load(
                    connection,
                    artifact_id=timeline_id,
                    base_version=patch.base_timeline.version,
                )
                approved = self._repository.approved_intent_version(
                    connection, artifact_id=timeline_id
                )
                if approved is not None and approved == current_snapshot.version:
                    raise TimelineEditingError(
                        "active version is the approved timeline intent; "
                        "edits require a new review cycle"
                    )
                base = MasterTimeline.model_validate(base_snapshot.payload)
                current = MasterTimeline.model_validate(current_snapshot.payload)
                rebased = base_snapshot.version != current_snapshot.version
                if rebased and not can_rebase(patch, semantic_diff(base, current)):
                    raise TimelineEditingError(
                        "concurrent patch touches the same items; rebase rejected"
                    )
                candidate = apply_patch(current, patch)
                validation = validate_timeline(candidate)
                if not validation.render_ready:
                    raise TimelineEditingError(f"timeline validation failed: {validation.issues}")
                changes = semantic_diff(current, candidate)
                payload = candidate.model_dump(mode="json")
                checksum = _payload_checksum(payload)
                version = self._repository.commit(
                    connection,
                    artifact_id=timeline_id,
                    current=current_snapshot,
                    payload=payload,
                    checksum=checksum,
                    patch_id=patch.patch_id,
                    rebased=rebased,
                    trace_id=trace_id,
                )
        except (TimelinePatchConflict, TimelineStorageConflict) as error:
            raise TimelineEditingError(str(error)) from error
        return PatchResult(
            timeline_id=timeline_id,
            version=version,
            checksum=checksum,
            rebased=rebased,
            changes=changes,
        )

    def undo(
        self,
        *,
        timeline_id: UUID,
        trace_id: str,
        reason: str = "undo",
    ) -> NavigationResult:
        """Navigate to the previous version. Raises if at version 1."""
        try:
            with transaction(self._engine) as connection:
                current_version = self._repository.get_active_version(
                    connection, artifact_id=timeline_id
                )
                if current_version <= 1:
                    raise TimelineEditingError("cannot undo: already at earliest version")
                target = current_version - 1
                self._repository.set_active_version(
                    connection,
                    artifact_id=timeline_id,
                    target_version=target,
                    expected_version=current_version,
                    trace_id=trace_id,
                    reason=reason,
                )
        except TimelineStorageConflict as error:
            raise TimelineEditingError(str(error)) from error
        return NavigationResult(
            timeline_id=timeline_id,
            version=target,
            previous_version=current_version,
            reason=reason,
        )

    def redo(
        self,
        *,
        timeline_id: UUID,
        trace_id: str,
        reason: str = "redo",
    ) -> NavigationResult:
        """Navigate to the next version. Raises if at latest."""
        try:
            with transaction(self._engine) as connection:
                current_version = self._repository.get_active_version(
                    connection, artifact_id=timeline_id
                )
                versions = self._repository.list_versions(
                    connection, artifact_id=timeline_id, limit=2
                )
                latest = max(v.version for v in versions) if versions else current_version
                if current_version >= latest:
                    raise TimelineEditingError("cannot redo: already at latest version")
                target = current_version + 1
                self._repository.set_active_version(
                    connection,
                    artifact_id=timeline_id,
                    target_version=target,
                    expected_version=current_version,
                    trace_id=trace_id,
                    reason=reason,
                )
        except TimelineStorageConflict as error:
            raise TimelineEditingError(str(error)) from error
        return NavigationResult(
            timeline_id=timeline_id,
            version=target,
            previous_version=current_version,
            reason=reason,
        )

    def jump_to_version(
        self,
        *,
        timeline_id: UUID,
        target_version: int,
        trace_id: str,
        reason: str = "jump",
    ) -> NavigationResult:
        """Navigate to any existing version by number."""
        try:
            with transaction(self._engine) as connection:
                current_version = self._repository.get_active_version(
                    connection, artifact_id=timeline_id
                )
                if target_version == current_version:
                    return NavigationResult(
                        timeline_id=timeline_id,
                        version=target_version,
                        previous_version=current_version,
                        reason="no-op",
                    )
                self._repository.set_active_version(
                    connection,
                    artifact_id=timeline_id,
                    target_version=target_version,
                    expected_version=current_version,
                    trace_id=trace_id,
                    reason=reason,
                )
        except TimelineStorageConflict as error:
            raise TimelineEditingError(str(error)) from error
        return NavigationResult(
            timeline_id=timeline_id,
            version=target_version,
            previous_version=current_version,
            reason=reason,
        )

    def get_current(self, *, timeline_id: UUID) -> MasterTimeline:
        """Load the currently active timeline."""
        with transaction(self._engine) as connection:
            current_version = self._repository.get_active_version(
                connection, artifact_id=timeline_id
            )
            snapshots = self._repository.list_versions(connection, artifact_id=timeline_id, limit=1)
            # list_versions is newest-first; find the active one
            for snapshot in snapshots:
                if snapshot.version == current_version:
                    return MasterTimeline.model_validate(snapshot.payload)
            # If not in the first page, load via lock_and_load with base=current
            _, current = self._repository.lock_and_load(
                connection,
                artifact_id=timeline_id,
                base_version=current_version,
            )
            return MasterTimeline.model_validate(current.payload)

    def get_version(self, *, timeline_id: UUID, version: int) -> MasterTimeline:
        """Load a specific timeline version by number."""
        try:
            with transaction(self._engine) as connection:
                base_snapshot, _current = self._repository.lock_and_load(
                    connection,
                    artifact_id=timeline_id,
                    base_version=version,
                )
                return MasterTimeline.model_validate(base_snapshot.payload)
        except TimelineStorageConflict as error:
            raise TimelineEditingError(str(error)) from error

    def list_versions(
        self,
        *,
        timeline_id: UUID,
        limit: int = 100,
        include_changes: bool = True,
    ) -> tuple[VersionSummary, ...]:
        """List timeline versions newest-first, optionally with semantic diffs."""
        with transaction(self._engine) as connection:
            snapshots = self._repository.list_versions(
                connection, artifact_id=timeline_id, limit=limit
            )
        if not include_changes or len(snapshots) < 2:
            return tuple(
                VersionSummary(
                    version=s.version,
                    producer=s.producer,
                    changes=None,
                )
                for s in snapshots
            )
        # Compute diffs between consecutive versions (oldest → newest direction)
        ordered = sorted(snapshots, key=lambda s: s.version)
        result: list[VersionSummary] = []
        for i, snapshot in enumerate(ordered):
            changes: tuple[TimelineChange, ...] | None = None
            if i > 0:
                prev = MasterTimeline.model_validate(ordered[i - 1].payload)
                curr = MasterTimeline.model_validate(snapshot.payload)
                changes = semantic_diff(prev, curr)
            result.append(
                VersionSummary(
                    version=snapshot.version,
                    producer=snapshot.producer,
                    changes=changes,
                )
            )
        return tuple(reversed(result))

    def diff_versions(
        self,
        *,
        timeline_id: UUID,
        from_version: int,
        to_version: int,
    ) -> tuple[TimelineChange, ...]:
        """Compute semantic diff between two timeline versions."""
        with transaction(self._engine) as connection:
            snapshots = {
                s.version: s
                for s in self._repository.list_versions(
                    connection, artifact_id=timeline_id, limit=200
                )
            }
        if from_version not in snapshots or to_version not in snapshots:
            raise TimelineEditingError(f"version {from_version} or {to_version} not found")
        from_timeline = MasterTimeline.model_validate(snapshots[from_version].payload)
        to_timeline = MasterTimeline.model_validate(snapshots[to_version].payload)
        return semantic_diff(from_timeline, to_timeline)


def _payload_checksum(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return "sha256:" + sha256(encoded).hexdigest()
