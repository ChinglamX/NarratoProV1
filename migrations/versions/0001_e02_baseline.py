"""E02 production metadata baseline.

Revision ID: 0001_e02
Revises: None
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from packages.persistence.baseline_v0001 import metadata as baseline_metadata

revision: str = "0001_e02"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMAS = ("core", "artifact", "workflow", "review", "policy", "rights", "audit")


def upgrade() -> None:
    bind = op.get_bind()
    for schema in SCHEMAS:
        op.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
    baseline_metadata.create_all(bind=bind, checkfirst=False)


def downgrade() -> None:
    bind = op.get_bind()
    baseline_metadata.drop_all(bind=bind, checkfirst=True)
    for schema in reversed(SCHEMAS):
        op.execute(f'DROP SCHEMA IF EXISTS "{schema}"')
