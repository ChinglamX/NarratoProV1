"""Database side of the staging-to-committed blob protocol."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import Connection, and_, insert, select, update
from sqlalchemy.exc import IntegrityError

import packages.persistence.schema as schema
from packages.artifacts import BlobMetadata, ObjectStore


class BlobCommitConflict(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RegisteredBlob:
    blob_id: UUID
    metadata: BlobMetadata
    state: str


class BlobRepository:
    def register_staged(
        self,
        connection: Connection,
        metadata: BlobMetadata,
        *,
        content_type: str,
        storage_class: str = "standard",
    ) -> RegisteredBlob:
        blob_id = uuid4()
        connection.execute(
            insert(schema.blob).values(
                id=blob_id,
                uri=metadata.uri,
                checksum=metadata.checksum,
                size_bytes=metadata.size_bytes,
                content_type=content_type,
                storage_class=storage_class,
                state="staging",
            )
        )
        return RegisteredBlob(blob_id=blob_id, metadata=metadata, state="staging")

    def register_or_get_staged(
        self,
        connection: Connection,
        metadata: BlobMetadata,
        *,
        content_type: str,
        storage_class: str = "standard",
    ) -> RegisteredBlob:
        try:
            with connection.begin_nested():
                return self.register_staged(
                    connection,
                    metadata,
                    content_type=content_type,
                    storage_class=storage_class,
                )
        except IntegrityError:
            row = (
                connection.execute(
                    select(schema.blob).where(
                        and_(
                            schema.blob.c.checksum == metadata.checksum,
                            schema.blob.c.size_bytes == metadata.size_bytes,
                        )
                    )
                )
                .mappings()
                .one()
            )
            return RegisteredBlob(
                blob_id=row["id"],
                metadata=BlobMetadata(row["uri"], row["checksum"], row["size_bytes"]),
                state=row["state"],
            )

    def commit(
        self,
        connection: Connection,
        object_store: ObjectStore,
        registered: RegisteredBlob,
    ) -> RegisteredBlob:
        committed = object_store.commit(
            registered.metadata.uri,
            registered.metadata.checksum,
        )
        result = connection.execute(
            update(schema.blob)
            .where(
                and_(
                    schema.blob.c.id == registered.blob_id,
                    schema.blob.c.state == "staging",
                    schema.blob.c.checksum == committed.checksum,
                    schema.blob.c.size_bytes == committed.size_bytes,
                )
            )
            .values(uri=committed.uri, state="committed")
        )
        if result.rowcount != 1:
            raise BlobCommitConflict("blob staging row changed before commit")
        return RegisteredBlob(
            blob_id=registered.blob_id,
            metadata=committed,
            state="committed",
        )

    def get(self, connection: Connection, blob_id: UUID) -> RegisteredBlob:
        row = (
            connection.execute(select(schema.blob).where(schema.blob.c.id == blob_id))
            .mappings()
            .first()
        )
        if row is None:
            raise KeyError(str(blob_id))
        return RegisteredBlob(
            blob_id=row["id"],
            metadata=BlobMetadata(
                uri=row["uri"],
                checksum=row["checksum"],
                size_bytes=row["size_bytes"],
            ),
            state=row["state"],
        )
