"""Tests for timeline revision history (undo/redo)."""

from __future__ import annotations

import pytest

from packages.timeline.revisions import (
    RevisionHistory,
    RevisionHistoryError,
    build_history_from_versions,
)
from tests.timeline.fixtures import item, patch, timeline


class TestRevisionHistory:
    def test_initialize_sets_baseline(self):
        tl = timeline(item(start=0, duration=25), item(start=25, duration=25))
        history = RevisionHistory()
        history.initialize(tl, version=1)
        assert history.current_version == 1
        assert history.current_timeline == tl
        assert not history.can_undo
        assert not history.can_redo

    def test_initialize_twice_raises(self):
        history = RevisionHistory()
        history.initialize(timeline())
        with pytest.raises(RevisionHistoryError, match="already initialized"):
            history.initialize(timeline())

    def test_apply_patch_creates_new_version(self):
        tl = timeline(item(start=0, duration=25), item(start=25, duration=25))
        history = RevisionHistory()
        history.initialize(tl, version=1)
        target = tl.tracks[0].items[0]
        p = patch(target, "set_parameter", {"key": "crop", "value": "center"})
        entry = history.apply_patch(p, label="set crop")
        assert entry.version == 2
        assert entry.label == "set crop"
        assert len(entry.changes) > 0
        assert history.current_version == 2
        assert history.can_undo
        assert not history.can_redo

    def test_undo_moves_cursor_back(self):
        tl = timeline(item(start=0, duration=25), item(start=25, duration=25))
        history = RevisionHistory()
        history.initialize(tl, version=1)
        target = tl.tracks[0].items[0]
        history.apply_patch(patch(target, "set_parameter", {"key": "x", "value": 1}))
        assert history.current_version == 2
        entry = history.undo()
        assert entry.version == 1
        assert history.current_version == 1
        assert not history.can_undo
        assert history.can_redo

    def test_undo_at_baseline_raises(self):
        history = RevisionHistory()
        history.initialize(timeline())
        with pytest.raises(RevisionHistoryError, match="cannot undo"):
            history.undo()

    def test_redo_moves_cursor_forward(self):
        tl = timeline(item(start=0, duration=25), item(start=25, duration=25))
        history = RevisionHistory()
        history.initialize(tl, version=1)
        target = tl.tracks[0].items[0]
        history.apply_patch(patch(target, "set_parameter", {"key": "x", "value": 1}))
        history.undo()
        assert history.current_version == 1
        entry = history.redo()
        assert entry.version == 2
        assert history.current_version == 2
        assert history.can_undo
        assert not history.can_redo

    def test_redo_at_latest_raises(self):
        history = RevisionHistory()
        history.initialize(timeline())
        with pytest.raises(RevisionHistoryError, match="cannot redo"):
            history.redo()

    def test_new_patch_after_undo_truncates_redo(self):
        tl = timeline(
            item(start=0, duration=25),
            item(start=25, duration=25),
            item(start=50, duration=25),
        )
        history = RevisionHistory()
        history.initialize(tl, version=1)
        history.apply_patch(patch(tl.tracks[0].items[0], "set_parameter", {"key": "a", "value": 1}))
        history.undo()
        assert history.can_redo
        history.apply_patch(
            patch(tl.tracks[0].items[1], "set_parameter", {"key": "b", "value": 2}), label="second"
        )
        assert history.current_version == 2
        assert not history.can_redo
        assert history.can_undo

    def test_jump_to_version(self):
        tl = timeline(
            item(start=0, duration=25),
            item(start=25, duration=25),
            item(start=50, duration=25),
        )
        history = RevisionHistory()
        history.initialize(tl, version=1)
        history.apply_patch(patch(tl.tracks[0].items[0], "set_parameter", {"key": "a", "value": 1}))
        history.apply_patch(
            patch(
                history.current_timeline.tracks[0].items[0],
                "set_parameter",
                {"key": "a", "value": 2},
            )
        )
        assert history.current_version == 3
        entry = history.jump_to(1)
        assert entry.version == 1
        assert history.current_version == 1
        assert history.can_redo

    def test_jump_to_nonexistent_raises(self):
        history = RevisionHistory()
        history.initialize(timeline())
        with pytest.raises(RevisionHistoryError, match="not found"):
            history.jump_to(99)

    def test_diff_between_versions(self):
        tl = timeline(item(start=0, duration=25), item(start=25, duration=25))
        history = RevisionHistory()
        history.initialize(tl, version=1)
        target = tl.tracks[0].items[0]
        history.apply_patch(patch(target, "set_parameter", {"key": "x", "value": 1}))
        changes = history.diff(1, 2)
        assert len(changes) == 1
        assert changes[0].change == "modified"

    def test_changed_ranges_returns_affected_time(self):
        tl = timeline(item(start=0, duration=25), item(start=25, duration=25))
        history = RevisionHistory()
        history.initialize(tl, version=1)
        target = tl.tracks[0].items[0]
        history.apply_patch(patch(target, "set_parameter", {"key": "x", "value": 1}))
        ranges = history.changed_ranges(1, 2)
        assert len(ranges) >= 1
        # First item starts at 0, duration 1.0s (25/25)
        assert ranges[0][0] <= 0.0
        assert ranges[0][1] >= 1.0

    def test_changed_ranges_empty_when_identical(self):
        tl = timeline()
        history = RevisionHistory()
        history.initialize(tl, version=1)
        ranges = history.changed_ranges(1, 1)
        assert ranges == ()

    def test_entries_returns_all_versions(self):
        tl = timeline(
            item(start=0, duration=25),
            item(start=25, duration=25),
            item(start=50, duration=25),
        )
        history = RevisionHistory()
        history.initialize(tl, version=1)
        history.apply_patch(patch(tl.tracks[0].items[0], "set_parameter", {"key": "a", "value": 1}))
        history.apply_patch(
            patch(
                history.current_timeline.tracks[0].items[0],
                "set_parameter",
                {"key": "a", "value": 2},
            )
        )
        entries = history.entries
        assert len(entries) == 3
        assert [e.version for e in entries] == [1, 2, 3]

    def test_empty_history_raises_on_current(self):
        history = RevisionHistory()
        with pytest.raises(RevisionHistoryError, match="empty"):
            _ = history.current

    def test_apply_patch_on_empty_raises(self):
        history = RevisionHistory()
        with pytest.raises(RevisionHistoryError, match="empty"):
            history.apply_patch(patch(item(), "remove", {}))


class TestBuildHistoryFromVersions:
    def test_builds_from_timeline_list(self):
        t1 = timeline(item(start=0, duration=50))
        t2 = timeline(item(start=0, duration=25), item(start=25, duration=25))
        t3 = timeline(item(start=0, duration=25))
        history = build_history_from_versions([t1, t2, t3], start_version=1)
        assert history.current_version == 3
        assert len(history.entries) == 3
        assert history.can_undo
        assert not history.can_redo

    def test_empty_list_raises(self):
        with pytest.raises(RevisionHistoryError, match="empty"):
            build_history_from_versions([])

    def test_single_timeline(self):
        t1 = timeline()
        history = build_history_from_versions([t1])
        assert history.current_version == 1
        assert not history.can_undo
        assert not history.can_redo
