from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from packages.artifacts import BlobMetadata
from packages.persistence.blob_repository import (
    BlobCommitConflict,
    BlobRepository,
    RegisteredBlob,
)


def test_commit_is_idempotent_for_existing_committed_blob() -> None:
    metadata = BlobMetadata("local-object://objects/sha256/abc", "sha256:" + "a" * 64, 3)
    registered = RegisteredBlob(uuid4(), metadata, "committed")
    store = MagicMock()
    store.head.return_value = metadata
    assert BlobRepository().commit(MagicMock(), store, registered) == registered
    store.commit.assert_not_called()


def test_commit_rejects_drifted_existing_blob() -> None:
    metadata = BlobMetadata("local-object://objects/sha256/abc", "sha256:" + "a" * 64, 3)
    registered = RegisteredBlob(uuid4(), metadata, "committed")
    store = MagicMock()
    store.head.return_value = BlobMetadata(metadata.uri, "sha256:" + "b" * 64, 3)
    with pytest.raises(BlobCommitConflict, match="no longer matches"):
        BlobRepository().commit(MagicMock(), store, registered)
