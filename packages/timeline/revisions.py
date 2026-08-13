"""In-memory revision history with undo/redo for precise timeline editing.

This module is pure and persistence-agnostic: it maintains an immutable chain
of timeline versions and a cursor. The editing service persists versions
through ``TimelineRepository``; this module only governs session-level
navigation and patch application semantics.

Design rules:
- Every version is an immutable ``MasterTimeline`` snapshot.
- ``apply_patch`` creates a new version and truncates redo history.
- ``undo``/``redo`` only move the cursor; they never mutate or delete versions.
- A fresh patch after undo discards the redo branch (standard editor semantics).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import UUID

from packages.contracts import MasterTimeline, TimelinePatch
from packages.timeline.patches import (
    TimelineChange,
    TimelinePatchConflict,
    apply_patch,
    semantic_diff,
)


class RevisionHistoryError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RevisionEntry:
    """One immutable version in the editing history."""

    version: int
    timeline: MasterTimeline
    patch_id: UUID | None = None
    changes: tuple[TimelineChange, ...] = ()
    label: str = ""


@dataclass
class RevisionHistory:
    """Append-only version chain with a movable cursor.

    The chain is zero-indexed internally; ``version`` on each entry is the
    external timeline version number (1-based, matching ``TimelineRepository``).
    """

    _entries: list[RevisionEntry] = field(default_factory=list)
    _cursor: int = -1

    @property
    def current(self) -> RevisionEntry:
        if self._cursor < 0:
            raise RevisionHistoryError("revision history is empty")
        return self._entries[self._cursor]

    @property
    def current_version(self) -> int:
        return self.current.version

    @property
    def current_timeline(self) -> MasterTimeline:
        return self.current.timeline

    @property
    def can_undo(self) -> bool:
        return self._cursor > 0

    @property
    def can_redo(self) -> bool:
        return self._cursor < len(self._entries) - 1

    @property
    def entries(self) -> tuple[RevisionEntry, ...]:
        return tuple(self._entries)

    @property
    def cursor_index(self) -> int:
        return self._cursor

    def initialize(self, timeline: MasterTimeline, *, version: int = 1) -> None:
        """Seed the history with a baseline timeline. Must be called first."""
        if self._entries:
            raise RevisionHistoryError("revision history already initialized")
        self._entries.append(
            RevisionEntry(version=version, timeline=timeline, label="baseline")
        )
        self._cursor = 0

    def undo(self) -> RevisionEntry:
        """Move cursor one step back. Raises if at baseline."""
        if not self.can_undo:
            raise RevisionHistoryError("cannot undo: already at earliest version")
        self._cursor -= 1
        return self._entries[self._cursor]

    def redo(self) -> RevisionEntry:
        """Move cursor one step forward. Raises if at latest."""
        if not self.can_redo:
            raise RevisionHistoryError("cannot redo: already at latest version")
        self._cursor += 1
        return self._entries[self._cursor]

    def apply_patch(
        self,
        patch: TimelinePatch,
        *,
        label: str = "",
    ) -> RevisionEntry:
        """Apply a patch on top of the current version.

        Truncates any redo history (entries after the cursor) before appending,
        matching standard editor behaviour.
        """
        if not self._entries:
            raise RevisionHistoryError("cannot patch: history is empty")
        current = self._entries[self._cursor]
        try:
            patched = apply_patch(current.timeline, patch)
        except TimelinePatchConflict as error:
            raise RevisionHistoryError(str(error)) from error
        changes = semantic_diff(current.timeline, patched)
        next_version = current.version + 1
        entry = RevisionEntry(
            version=next_version,
            timeline=patched,
            patch_id=patch.patch_id,
            changes=changes,
            label=label,
        )
        # Truncate redo branch
        del self._entries[self._cursor + 1 :]
        self._entries.append(entry)
        self._cursor = len(self._entries) - 1
        return entry

    def jump_to(self, version: int) -> RevisionEntry:
        """Move cursor to a specific version number. Does not truncate history."""
        for index, entry in enumerate(self._entries):
            if entry.version == version:
                self._cursor = index
                return entry
        raise RevisionHistoryError(f"version {version} not found in history")

    def diff(
        self, from_version: int, to_version: int
    ) -> tuple[TimelineChange, ...]:
        """Compute semantic diff between two versions in the history."""
        from_entry = self._find(from_version)
        to_entry = self._find(to_version)
        return semantic_diff(from_entry.timeline, to_entry.timeline)

    def changed_ranges(
        self, from_version: int, to_version: int
    ) -> tuple[tuple[float, float], ...]:
        """Return merged timeline time ranges affected by changes.

        Used by partial preview to determine which segments need re-render.
        Overlapping or adjacent ranges are merged.
        """
        from_entry = self._find(from_version)
        to_entry = self._find(to_version)
        old_items = {
            item.item_id: item
            for track in from_entry.timeline.tracks
            for item in track.items
        }
        ranges: list[tuple[float, float]] = []
        for track in to_entry.timeline.tracks:
            for item in track.items:
                old = old_items.get(item.item_id)
                if old is None or old != item:
                    start = float(item.timeline_range.start.seconds)
                    end = start + float(item.timeline_range.duration.seconds)
                    ranges.append((start, end))
        if not ranges:
            return ()
        ranges.sort()
        merged: list[tuple[float, float]] = [ranges[0]]
        for start, end in ranges[1:]:
            last_start, last_end = merged[-1]
            if start <= last_end:
                merged[-1] = (last_start, max(last_end, end))
            else:
                merged.append((start, end))
        return tuple(merged)

    def _find(self, version: int) -> RevisionEntry:
        for entry in self._entries:
            if entry.version == version:
                return entry
        raise RevisionHistoryError(f"version {version} not found in history")


def build_history_from_versions(
    timelines: Sequence[MasterTimeline],
    *,
    start_version: int = 1,
) -> RevisionHistory:
    """Convenience: build a history from an ordered list of timeline snapshots."""
    if not timelines:
        raise RevisionHistoryError("cannot build history from empty timeline list")
    history = RevisionHistory()
    history.initialize(timelines[0], version=start_version)
    for timeline in timelines[1:]:
        changes = semantic_diff(history.current_timeline, timeline)
        next_version = history.current_version + 1
        entry = RevisionEntry(
            version=next_version,
            timeline=timeline,
            changes=changes,
            label="imported",
        )
        history._entries.append(entry)
        history._cursor += 1
    return history
