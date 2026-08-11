"""Add concurrent media ingest identity registry."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_e05_media_identity"
down_revision: str | None = "0001_e02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS media")
    op.create_table(
        "ingest_identity",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_checksum", sa.String(72), nullable=False),
        sa.Column("profile_version", sa.String(128), nullable=False),
        sa.Column("role", sa.String(128), nullable=False),
        sa.Column("artifact_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["project_id"], ["core.project.id"]),
        sa.UniqueConstraint("project_id", "source_checksum", "profile_version", "role"),
        schema="media",
    )


def downgrade() -> None:
    op.drop_table("ingest_identity", schema="media")
