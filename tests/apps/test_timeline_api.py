from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

import apps.services.timeline_editing as editing_module
from apps.api import timelines as api
from apps.services.timeline_editing import TimelineEditingService
from packages.contracts import ArtifactRef
from packages.persistence.timeline_repository import TimelineSnapshot
from packages.production.real_preview import PartialPreviewResult
from tests.timeline.fixtures import artifact_ref, item, patch, timeline


@contextmanager
def _fake_transaction(_engine: object):
    yield object()


class FakeRepository:
    def __init__(self, snapshots: dict[int, TimelineSnapshot], approved: int | None = None) -> None:
        self.snapshots = snapshots
        self.active_version = max(snapshots) if snapshots else 1
        self.approved = approved
        self.commits: list[dict] = []
        self.navigations: list[dict] = []

    def lock_and_load(self, _conn, *, artifact_id, base_version):
        from packages.persistence.timeline_repository import TimelineStorageConflict

        if base_version not in self.snapshots:
            raise TimelineStorageConflict("base version unavailable")
        return self.snapshots[base_version], self.snapshots[self.active_version]

    def commit(
        self, _conn, *, artifact_id, current, payload, checksum, patch_id, rebased, trace_id
    ):
        next_version = self.active_version + 1
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
        from packages.persistence.timeline_repository import TimelineStorageConflict

        if target_version not in self.snapshots:
            raise TimelineStorageConflict("target version does not exist")
        if expected_version != self.active_version:
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
        versions = sorted(self.snapshots, reverse=True)[:limit]
        return [self.snapshots[v] for v in versions]

    def get_active_version(self, _conn, *, artifact_id):
        return self.active_version

    def approved_intent_version(self, _conn, *, artifact_id):
        return self.approved


def _snapshot(tl, version: int = 1) -> TimelineSnapshot:
    return TimelineSnapshot(
        version=version,
        payload=tl.model_dump(mode="json"),
        schema_version="1.0.0",
        run_id=uuid4(),
        variant_id=None,
        producer={"kind": "test"},
        rights_class="internal",
    )


def _request(repository: FakeRepository) -> SimpleNamespace:
    return SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                database_engine=object(),
                timeline_repository=repository,
                timeline_editing_service=TimelineEditingService(
                    engine=object(), repository=repository
                ),
            )
        )
    )


@pytest.fixture(autouse=True)
def _patch_transactions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api, "transaction", _fake_transaction)
    monkeypatch.setattr(editing_module, "transaction", _fake_transaction)


def _patch_for(tl, target_item, timeline_id):
    p = patch(target_item, "set_parameter", {"key": "crop", "value": "center"})
    return p.model_copy(
        update={
            "base_timeline": ArtifactRef.model_validate(
                artifact_ref("MasterTimeline") | {"artifact_id": timeline_id}
            )
        }
    )


def _timeline_with_snapshots() -> tuple[object, FakeRepository]:
    tl = timeline(item(start=0, duration=25), item(start=25, duration=25))
    return tl, FakeRepository({1: _snapshot(tl, 1)})


def test_timeline_api_applies_valid_semantic_patch(monkeypatch: pytest.MonkeyPatch) -> None:
    value = timeline()
    target = value.tracks[0].items[0]
    timeline_id = uuid4()
    candidate = patch(target, "set_parameter", {"key": "crop", "value": "center"})
    candidate = candidate.model_copy(
        update={
            "base_timeline": ArtifactRef.model_validate(
                artifact_ref("MasterTimeline") | {"artifact_id": timeline_id}
            )
        }
    )
    snapshot = _snapshot(value, 1)
    repository = FakeRepository({1: snapshot})
    request = _request(repository)

    @contextmanager
    def fake_transaction(_engine: object):
        yield object()

    monkeypatch.setattr(api, "transaction", fake_transaction)
    response = api.apply_timeline_patch(  # type: ignore[arg-type]
        timeline_id, candidate, request, "editor", "a" * 32
    )
    assert response["version"] == 2 and response["rebased"] is False
    assert repository.commits[0]["artifact_id"] == timeline_id


def test_timeline_api_requires_editor_role() -> None:
    with pytest.raises(HTTPException) as captured:
        api.apply_timeline_patch(  # type: ignore[arg-type]
            uuid4(), patch(item(), "remove", {}), SimpleNamespace(), "viewer"
        )
    assert captured.value.status_code == 403


def test_timeline_api_patch_blocked_on_approved_intent() -> None:
    tl = timeline()
    timeline_id = uuid4()
    candidate = _patch_for(tl, tl.tracks[0].items[0], timeline_id)
    repository = FakeRepository({1: _snapshot(tl, 1)}, approved=1)
    request = _request(repository)
    with pytest.raises(HTTPException) as captured:
        api.apply_timeline_patch(  # type: ignore[arg-type]
            timeline_id, candidate, request, "editor", "a" * 32
        )
    assert captured.value.status_code == 409
    assert captured.value.detail["code"] == "timeline_conflict"
    assert repository.commits == []


def test_timeline_api_undo_redo_and_jump() -> None:
    tl, repository = _timeline_with_snapshots()
    timeline_id = tl.timeline_id
    request = _request(repository)
    api.apply_timeline_patch(  # type: ignore[arg-type]
        timeline_id,
        _patch_for(tl, tl.tracks[0].items[0], timeline_id),
        request,
        "editor",
        "a" * 32,
    )
    response = api.undo_timeline(timeline_id, request, "editor", "a" * 32)  # type: ignore[arg-type]
    assert response["version"] == 1
    response = api.redo_timeline(timeline_id, request, "editor", "a" * 32)  # type: ignore[arg-type]
    assert response["version"] == 2
    response = api.jump_timeline(  # type: ignore[arg-type]
        timeline_id, SimpleNamespace(version=1), request, "editor", "a" * 32
    )
    assert response["version"] == 1
    assert repository.navigations[0]["to"] == 1


def test_timeline_api_undo_at_v1_returns_409() -> None:
    tl, repository = _timeline_with_snapshots()
    request = _request(repository)
    with pytest.raises(HTTPException) as captured:
        api.undo_timeline(tl.timeline_id, request, "editor", "a" * 32)  # type: ignore[arg-type]
    assert captured.value.status_code == 409


def test_timeline_api_jump_missing_version_returns_409() -> None:
    tl, repository = _timeline_with_snapshots()
    request = _request(repository)
    with pytest.raises(HTTPException) as captured:
        api.jump_timeline(  # type: ignore[arg-type]
            tl.timeline_id, SimpleNamespace(version=99), request, "editor", "a" * 32
        )
    assert captured.value.status_code == 409


def test_timeline_api_versions_and_diff() -> None:
    tl, repository = _timeline_with_snapshots()
    timeline_id = tl.timeline_id
    request = _request(repository)
    api.apply_timeline_patch(  # type: ignore[arg-type]
        timeline_id,
        _patch_for(tl, tl.tracks[0].items[0], timeline_id),
        request,
        "editor",
        "a" * 32,
    )
    response = api.list_timeline_versions(timeline_id, request, limit=10, include_changes=True)
    assert response["count"] == 2
    assert response["versions"][0]["version"] == 2
    diff = api.diff_timeline_versions(timeline_id, request, from_version=1, to_version=2)
    assert len(diff["changes"]) == 1
    current = api.get_current_timeline(timeline_id, request)
    assert current["timeline_id"] == str(timeline_id)


def test_timeline_api_diff_missing_version_returns_404() -> None:
    tl, repository = _timeline_with_snapshots()
    request = _request(repository)
    with pytest.raises(HTTPException) as captured:
        api.diff_timeline_versions(tl.timeline_id, request, from_version=1, to_version=99)
    assert captured.value.status_code == 404


def test_timeline_api_preview_partial_renders_changed_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tl, repository = _timeline_with_snapshots()
    timeline_id = tl.timeline_id
    request = _request(repository)
    api.apply_timeline_patch(  # type: ignore[arg-type]
        timeline_id,
        _patch_for(tl, tl.tracks[0].items[0], timeline_id),
        request,
        "editor",
        "a" * 32,
    )
    monkeypatch.setattr(api, "_resolve_source_paths", lambda *_a, **_k: {})
    rendered: list[tuple[object, ...]] = []

    def fake_render(timeline, sources, output_path, **kwargs):
        rendered.append((timeline, sources, output_path, kwargs))
        return PartialPreviewResult(
            output_path=Path("/tmp/out.mp4"),
            subtitle_path=Path("/tmp/out.ass"),
            original_start=kwargs["time_range"][0],
            original_end=kwargs["time_range"][1],
            duration_seconds=1.0,
            clip_count=1,
            ffmpeg_version="test",
        )

    monkeypatch.setattr(api, "render_partial_preview", fake_render)
    response = api.render_timeline_partial_preview(  # type: ignore[arg-type]
        timeline_id,
        SimpleNamespace(from_version=1, to_version=2),
        request,
        "editor",
    )
    assert response["to_version"] == 2
    assert response["output_path"] == "/tmp/out.mp4"
    assert response["changed_ranges"]
    assert len(rendered) == 1


def test_timeline_api_preview_requires_editor_role() -> None:
    tl, repository = _timeline_with_snapshots()
    request = _request(repository)
    with pytest.raises(HTTPException) as captured:
        api.render_timeline_partial_preview(  # type: ignore[arg-type]
            tl.timeline_id, SimpleNamespace(from_version=1, to_version=2), request, "viewer"
        )
    assert captured.value.status_code == 403


def test_timeline_api_preview_identical_versions_returns_409() -> None:
    tl, repository = _timeline_with_snapshots()
    request = _request(repository)
    with pytest.raises(HTTPException) as captured:
        api.render_timeline_partial_preview(  # type: ignore[arg-type]
            tl.timeline_id, SimpleNamespace(from_version=1, to_version=1), request, "editor"
        )
    assert captured.value.status_code == 409
    assert captured.value.detail["code"] == "no_changes"
