from io import BytesIO
from uuid import uuid4

import pytest

from packages.artifacts import ChecksumMismatch, InvalidObjectUri, LocalObjectStore


def test_stage_commit_read_and_content_dedup(tmp_path) -> None:
    store = LocalObjectStore(tmp_path / "objects")
    staged = store.stage(uuid4(), "probe-1", BytesIO(b"same-content"))
    committed = store.commit(staged.uri, staged.checksum)
    assert committed.uri.startswith("local-object://objects/sha256/")
    assert store.open(committed.uri).read() == b"same-content"
    duplicate = store.stage(uuid4(), "probe-2", BytesIO(b"same-content"))
    assert store.commit(duplicate.uri, duplicate.checksum) == committed


def test_checksum_mismatch_preserves_staged_blob(tmp_path) -> None:
    store = LocalObjectStore(tmp_path / "objects")
    staged = store.stage(uuid4(), "probe", BytesIO(b"content"))
    with pytest.raises(ChecksumMismatch):
        store.commit(staged.uri, "sha256:" + "0" * 64)
    assert store.head(staged.uri) == staged


def test_path_traversal_and_committed_delete_fail_closed(tmp_path) -> None:
    store = LocalObjectStore(tmp_path / "objects")
    with pytest.raises(InvalidObjectUri):
        store.head("local-object://../../secret")
    staged = store.stage(uuid4(), "probe", BytesIO(b"content"))
    committed = store.commit(staged.uri, staged.checksum)
    with pytest.raises(InvalidObjectUri, match="staged"):
        store.delete_staged(committed.uri)


def test_delete_staged_is_idempotent_and_activity_id_is_safe(tmp_path) -> None:
    store = LocalObjectStore(tmp_path / "objects")
    staged = store.stage(uuid4(), "probe", BytesIO(b"content"))
    store.delete_staged(staged.uri)
    store.delete_staged(staged.uri)
    with pytest.raises(InvalidObjectUri, match="activity_id"):
        store.stage(uuid4(), "../escape", BytesIO(b"content"))
