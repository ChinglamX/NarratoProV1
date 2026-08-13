"""Media persistence extensions introduced by E05."""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

# E05 media tables use their own metadata so the immutable baseline v0001
# snapshot (used by migration 0001) is never mutated at runtime. Fresh
# deployments therefore get media tables exclusively from revision 0002, and
# existing deployments keep their applied 0001/0002 history intact.
# `packages.persistence.schema` still exposes the table for repositories.
media_metadata = MetaData()

media_ingest_identity = Table(
    "ingest_identity",
    media_metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("project_id", UUID(as_uuid=True), ForeignKey("core.project.id"), nullable=False),
    Column("source_checksum", String(72), nullable=False),
    Column("profile_version", String(128), nullable=False),
    Column("role", String(128), nullable=False),
    # Allocated before the artifact reservation transaction; repository validation
    # prevents dangling identities from being returned as committed artifacts.
    Column("artifact_id", UUID(as_uuid=True)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("project_id", "source_checksum", "profile_version", "role"),
    schema="media",
)
