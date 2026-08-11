"""Concurrent identity allocation for idempotent media ingest products."""

from uuid import UUID, uuid4

from sqlalchemy import Connection, and_, select, update
from sqlalchemy.dialects.postgresql import insert

import packages.persistence.schema as schema


class MediaIdentityRepository:
    def resolve(
        self,
        connection: Connection,
        *,
        project_id: UUID,
        source_checksum: str,
        profile_version: str,
        role: str,
    ) -> tuple[UUID, bool]:
        candidate = uuid4()
        inserted = connection.scalar(
            insert(schema.media_ingest_identity)
            .values(
                id=uuid4(),
                project_id=project_id,
                source_checksum=source_checksum,
                profile_version=profile_version,
                role=role,
            )
            .on_conflict_do_nothing(
                index_elements=["project_id", "source_checksum", "profile_version", "role"]
            )
            .returning(schema.media_ingest_identity.c.id)
        )
        identity = connection.execute(
            select(
                schema.media_ingest_identity.c.id,
                schema.media_ingest_identity.c.artifact_id,
            ).where(
                and_(
                    schema.media_ingest_identity.c.project_id == project_id,
                    schema.media_ingest_identity.c.source_checksum == source_checksum,
                    schema.media_ingest_identity.c.profile_version == profile_version,
                    schema.media_ingest_identity.c.role == role,
                )
            )
        ).one()
        if identity.artifact_id is not None:
            return identity.artifact_id, True
        claimed = connection.scalar(
            update(schema.media_ingest_identity)
            .where(
                and_(
                    schema.media_ingest_identity.c.id == identity.id,
                    schema.media_ingest_identity.c.artifact_id.is_(None),
                )
            )
            .values(artifact_id=candidate)
            .returning(schema.media_ingest_identity.c.artifact_id)
        )
        if claimed is not None:
            return claimed, inserted is None
        resolved = connection.scalar(
            select(schema.media_ingest_identity.c.artifact_id).where(
                schema.media_ingest_identity.c.id == identity.id
            )
        )
        if resolved is None:
            raise RuntimeError("media identity allocation failed")
        return resolved, True
