from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from packages.persistence.media_repository import MediaIdentityRepository


def test_media_identity_migration_is_versioned_and_reversible() -> None:
    migration = Path("migrations/versions/0002_e05_media_identity.py").read_text()
    assert 'down_revision: str | None = "0001_e02"' in migration
    assert 'project_id", "source_checksum", "profile_version", "role' in migration
    assert "def downgrade()" in migration


class FakeResult:
    def __init__(self, row: object) -> None:
        self.row = row

    def one(self) -> object:
        return self.row


class FakeConnection:
    def __init__(self, scalars: list[object], row: object) -> None:
        self.scalars = iter(scalars)
        self.row = row

    def scalar(self, _statement: object) -> object:
        return next(self.scalars)

    def execute(self, _statement: object) -> FakeResult:
        return FakeResult(self.row)


def test_media_identity_repository_allocates_uuid4() -> None:
    row = SimpleNamespace(id=uuid4(), artifact_id=None)
    claimed = uuid4()
    connection = FakeConnection([uuid4(), claimed], row)
    artifact_id, reused = MediaIdentityRepository().resolve(  # type: ignore[arg-type]
        connection,
        project_id=uuid4(),
        source_checksum="sha256:" + "a" * 64,
        profile_version="v1",
        role="proxy",
    )
    assert artifact_id == claimed and artifact_id.version == 4 and not reused


def test_media_identity_repository_reuses_existing_artifact() -> None:
    existing = uuid4()
    row = SimpleNamespace(id=uuid4(), artifact_id=existing)
    connection = FakeConnection([None], row)
    artifact_id, reused = MediaIdentityRepository().resolve(  # type: ignore[arg-type]
        connection,
        project_id=uuid4(),
        source_checksum="sha256:" + "b" * 64,
        profile_version="v1",
        role="source",
    )
    assert artifact_id == existing and reused
