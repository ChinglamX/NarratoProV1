"""Tests for TimelineEditingService."""

from __future__ import annotations

from contextlib import contextmanager
from uuid import uuid4

import pytest

import apps.services.timeline_editing as editing_module
from apps.services.timeline_editing import (
    NavigationResult,
    PatchResult,
    TimelineEditingError,
    TimelineEditingService,
)
from packages.contracts import ArtifactRef, MasterTimeline
from packages.persistence.timeline_repository import TimelineSnapshot
from tests.timeline.fixtures import artifact_ref, item, patch, timeline


@contextmanager
def _fake_transaction(_engine: object):
    yield object()


class FakeRepository:
    def __init__(self, snapshots: dict[int, TimelineSnapshot]) -> None:
        self.snapshots = snapshots
        self.active_version = max(snapshots.keys()) if snapshots else 1
        self.commits: list[dict] = []
        self.navigations: list[dict] = []

    def lock_and_load(self, _conn, *, artifact_id, base_version):
        if base_version not in self.snapshots:
            from packages.persistence.timeline_repository import TimelineStorageConflict

            raise TimelineStorageConflict("base version unavailable")
        return self.snapshots[base_version], self.snapshots[self.active_version]

    def commit(
        self, _conn, *, artifact_id, current, payload, checksum, patch_id, rebased, trace_id
    ):
        next_version = current.version + 1
        self.commits.append(
            {
                "artifact_id": artifact_id,
                "version": next_version,
                "payload": payload,
                "checksum": checksum,
                "patch_id": patch_id,
                "rebased": rebased,
                "trace_id": trace_id,
            }
        )
        self.snapshots[next_version] = TimelineSnapshot(
            next_version,
            payload,
            current.schema_version,
            current.run_id,
            current.variant_id,
            {"kind": "timeline_patch", "patch_id": str(patch_id)},
            current.rights_class,
        )
        self.active_version = next_version
        return next_version

    def set_active_version(
        self, _conn, *, artifact_id, target_version, expected_version, trace_id, reason
    ):
        if target_version not in self.snapshots:
            from packages.persistence.timeline_repository import TimelineStorageConflict

            raise TimelineStorageConflict("target version does not exist")
        if expected_version != self.active_version:
            from packages.persistence.timeline_repository import TimelineStorageConflict

            raise TimelineStorageConflict("CAS failed")
        self.navigations.append(
            {
                "artifact_id": artifact_id,
                "from": expected_version,
                "to": target_version,
                "reason": reason,
            }
        )
        self.active_version = target_version
        return target_version

    def list_versions(self, _conn, *, artifact_id, limit=100):
        versions = sorted(self.snapshots.keys(), reverse=True)[:limit]
        return [self.snapshots[v] for v in versions]

    def get_active_version(self, _conn, *, artifact_id):
        return self.active_version


def _make_snapshot(tl: MasterTimeline, version: int = 1) -> TimelineSnapshot:
    return TimelineSnapshot(
        version=version,
        payload=tl.model_dump(mode="json"),
        schema_version="1.0.0",
        run_id=uuid4(),
        variant_id=None,
        producer={"kind": "test"},
        rights_class="internal",
    )


def _make_service(tl: MasterTimeline) -> tuple[TimelineEditingService, FakeRepository]:
    snapshot = _make_snapshot(tl, version=1)
    repo = FakeRepository({1: snapshot})
    service = TimelineEditingService(engine=object(), repository=repo)
    return service, repo


@pytest.fixture(autouse=True)
def _patch_transaction(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(editing_module, "transaction", _fake_transaction)


class TestApplyPatch:
    def test_apply_patch_creates_new_version(self):
        tl = timeline(item(start=0, duration=25), item(start=25, duration=25))
        service, repo = _make_service(tl)
        target = tl.tracks[0].items[0]
        p = patch(target, "set_parameter", {"key": "crop", "value": "center"})
        p = p.model_copy(
            update={
                "base_timeline": ArtifactRef.model_validate(
                    artifact_ref("MasterTimeline") | {"artifact_id": tl.timeline_id}
                )
            }
        )
        result = service.apply_patch(timeline_id=tl.timeline_id, patch=p, trace_id="test")
        assert isinstance(result, PatchResult)
        assert result.version == 2
        assert result.rebased is False
        assert len(result.changes) == 1
        assert len(repo.commits) == 1

    def test_apply_patch_wrong_artifact_raises(self):
        tl = timeline()
        service, _ = _make_service(tl)
        target = tl.tracks[0].items[0]
        p = patch(target, "remove", {})
        with pytest.raises(TimelineEditingError, match="does not match"):
            service.apply_patch(timeline_id=uuid4(), patch=p, trace_id="test")

    def test_apply_patch_stale_version_raises(self):
        tl = timeline(item(start=0, duration=25), item(start=25, duration=25))
        service, _ = _make_service(tl)
        target = tl.tracks[0].items[0]
        # Use a patch with expected_item_version that doesn't match
        p = patch(target, "set_parameter", {"key": "x", "value": 1})
        p = p.model_copy(
            update={
                "operations": [
                    p.operations[0].model_copy(
                        update={"expected_item_version": target.item_version + 99}
                    )
                ]
            }
        )
        p = p.model_copy(
            update={
                "base_timeline": ArtifactRef.model_validate(
                    artifact_ref("MasterTimeline") | {"artifact_id": tl.timeline_id}
                )
            }
        )
        with pytest.raises(TimelineEditingError):
            service.apply_patch(timeline_id=tl.timeline_id, patch=p, trace_id="test")


class TestUndoRedo:
    def test_undo_moves_to_previous_version(self):
        tl = timeline(item(start=0, duration=25), item(start=25, duration=25))
        service, repo = _make_service(tl)
        # Create v2
        target = tl.tracks[0].items[0]
        p = patch(target, "set_parameter", {"key": "x", "value": 1})
        p = p.model_copy(
            update={
                "base_timeline": ArtifactRef.model_validate(
                    artifact_ref("MasterTimeline") | {"artifact_id": tl.timeline_id}
                )
            }
        )
        service.apply_patch(timeline_id=tl.timeline_id, patch=p, trace_id="test")
        assert repo.active_version == 2
        result = service.undo(timeline_id=tl.timeline_id, trace_id="test")
        assert isinstance(result, NavigationResult)
        assert result.version == 1
        assert result.previous_version == 2
        assert repo.active_version == 1

    def test_undo_at_v1_raises(self):
        tl = timeline()
        service, _ = _make_service(tl)
        with pytest.raises(TimelineEditingError, match="cannot undo"):
            service.undo(timeline_id=tl.timeline_id, trace_id="test")

    def test_redo_moves_to_next_version(self):
        tl = timeline(item(start=0, duration=25), item(start=25, duration=25))
        service, repo = _make_service(tl)
        target = tl.tracks[0].items[0]
        p = patch(target, "set_parameter", {"key": "x", "value": 1})
        p = p.model_copy(
            update={
                "base_timeline": ArtifactRef.model_validate(
                    artifact_ref("MasterTimeline") | {"artifact_id": tl.timeline_id}
                )
            }
        )
        service.apply_patch(timeline_id=tl.timeline_id, patch=p, trace_id="test")
        service.undo(timeline_id=tl.timeline_id, trace_id="test")
        assert repo.active_version == 1
        result = service.redo(timeline_id=tl.timeline_id, trace_id="test")
        assert result.version == 2
        assert repo.active_version == 2

    def test_redo_at_latest_raises(self):
        tl = timeline()
        service, _ = _make_service(tl)
        with pytest.raises(TimelineEditingError, match="cannot redo"):
            service.redo(timeline_id=tl.timeline_id, trace_id="test")

    def test_jump_to_version(self):
        tl = timeline(item(start=0, duration=25), item(start=25, duration=25))
        service, repo = _make_service(tl)
        target = tl.tracks[0].items[0]
        p = patch(target, "set_parameter", {"key": "x", "value": 1})
        p = p.model_copy(
            update={
                "base_timeline": ArtifactRef.model_validate(
                    artifact_ref("MasterTimeline") | {"artifact_id": tl.timeline_id}
                )
            }
        )
        service.apply_patch(timeline_id=tl.timeline_id, patch=p, trace_id="test")
        result = service.jump_to_version(
            timeline_id=tl.timeline_id, target_version=1, trace_id="test"
        )
        assert result.version == 1
        assert repo.active_version == 1

    def test_jump_to_same_version_is_noop(self):
        tl = timeline()
        service, repo = _make_service(tl)
        result = service.jump_to_version(
            timeline_id=tl.timeline_id, target_version=1, trace_id="test"
        )
        assert result.reason == "no-op"
        assert len(repo.navigations) == 0


class TestListVersions:
    def test_list_versions_returns_all(self):
        tl = timeline(item(start=0, duration=25), item(start=25, duration=25))
        service, _repo = _make_service(tl)
        target = tl.tracks[0].items[0]
        p = patch(target, "set_parameter", {"key": "x", "value": 1})
        p = p.model_copy(
            update={
                "base_timeline": ArtifactRef.model_validate(
                    artifact_ref("MasterTimeline") | {"artifact_id": tl.timeline_id}
                )
            }
        )
        service.apply_patch(timeline_id=tl.timeline_id, patch=p, trace_id="test")
        versions = service.list_versions(timeline_id=tl.timeline_id)
        assert len(versions) == 2
        # Newest first
        assert versions[0].version == 2
        assert versions[1].version == 1

    def test_list_versions_without_changes(self):
        tl = timeline()
        service, _ = _make_service(tl)
        versions = service.list_versions(timeline_id=tl.timeline_id, include_changes=False)
        assert len(versions) == 1
        assert versions[0].changes is None


class TestDiffVersions:
    def test_diff_returns_changes(self):
        tl = timeline(item(start=0, duration=25), item(start=25, duration=25))
        service, _ = _make_service(tl)
        target = tl.tracks[0].items[0]
        p = patch(target, "set_parameter", {"key": "x", "value": 1})
        p = p.model_copy(
            update={
                "base_timeline": ArtifactRef.model_validate(
                    artifact_ref("MasterTimeline") | {"artifact_id": tl.timeline_id}
                )
            }
        )
        service.apply_patch(timeline_id=tl.timeline_id, patch=p, trace_id="test")
        changes = service.diff_versions(timeline_id=tl.timeline_id, from_version=1, to_version=2)
        assert len(changes) == 1
        assert changes[0].change == "modified"

    def test_diff_nonexistent_version_raises(self):
        tl = timeline()
        service, _ = _make_service(tl)
        with pytest.raises(TimelineEditingError, match="not found"):
            service.diff_versions(timeline_id=tl.timeline_id, from_version=1, to_version=99)


class TestGetCurrent:
    def test_get_current_returns_active_timeline(self):
        tl = timeline()
        service, _ = _make_service(tl)
        current = service.get_current(timeline_id=tl.timeline_id)
        assert current.timeline_id == tl.timeline_id
