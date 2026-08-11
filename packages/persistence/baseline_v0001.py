"""Immutable SQLAlchemy metadata snapshot for migration revision 0001_e02."""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
metadata = MetaData(naming_convention=NAMING_CONVENTION)

project = Table(
    "project",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("name", String(512), nullable=False),
    Column("state", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("row_version", BigInteger, nullable=False, server_default="1"),
    CheckConstraint("row_version >= 1", name="positive_row_version"),
    schema="core",
)

run = Table(
    "run",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("project_id", UUID(as_uuid=True), ForeignKey("core.project.id"), nullable=False),
    Column("workflow_id", String(255), nullable=False, unique=True),
    Column("state", String(32), nullable=False),
    Column("automation_policy_snapshot", JSONB, nullable=False),
    Column("resource_profile_snapshot", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("started_at", DateTime(timezone=True)),
    Column("finished_at", DateTime(timezone=True)),
    Column("row_version", BigInteger, nullable=False, server_default="1"),
    CheckConstraint("row_version >= 1", name="positive_row_version"),
    schema="core",
)

variant = Table(
    "variant",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("project_id", UUID(as_uuid=True), ForeignKey("core.project.id"), nullable=False),
    Column("strategy_artifact_id", UUID(as_uuid=True)),
    Column("state", String(32), nullable=False),
    Column("label", String(255)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    schema="core",
)

artifact = Table(
    "artifact",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("project_id", UUID(as_uuid=True), ForeignKey("core.project.id"), nullable=False),
    Column("artifact_type", String(128), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    schema="artifact",
)

blob = Table(
    "blob",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("uri", Text, nullable=False, unique=True),
    Column("checksum", String(72), nullable=False),
    Column("size_bytes", BigInteger, nullable=False),
    Column("content_type", String(255), nullable=False),
    Column("storage_class", String(64), nullable=False),
    Column("state", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("checksum", "size_bytes"),
    CheckConstraint("size_bytes >= 0", name="non_negative_size"),
    schema="artifact",
)

artifact_version = Table(
    "artifact_version",
    metadata,
    Column("artifact_id", UUID(as_uuid=True), ForeignKey("artifact.artifact.id"), primary_key=True),
    Column("version", Integer, primary_key=True),
    Column("schema_version", String(32), nullable=False),
    Column("run_id", UUID(as_uuid=True), ForeignKey("core.run.id"), nullable=False),
    Column("variant_id", UUID(as_uuid=True), ForeignKey("core.variant.id")),
    Column("state", String(32), nullable=False),
    Column("payload_json", JSONB),
    Column("blob_id", UUID(as_uuid=True), ForeignKey("artifact.blob.id")),
    Column("checksum", String(72), nullable=False),
    Column("producer_json", JSONB, nullable=False),
    Column("rights_class", String(255), nullable=False),
    Column("trace_id", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("artifact_id", "checksum"),
    CheckConstraint("version >= 1", name="positive_version"),
    CheckConstraint("payload_json IS NOT NULL OR blob_id IS NOT NULL", name="payload_or_blob"),
    schema="artifact",
)

artifact_state_transition = Table(
    "state_transition",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("artifact_id", UUID(as_uuid=True), nullable=False),
    Column("version", Integer, nullable=False),
    Column("from_state", String(32), nullable=False),
    Column("to_state", String(32), nullable=False),
    Column("reason", Text, nullable=False),
    Column("trace_id", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    ForeignKeyConstraint(
        ["artifact_id", "version"],
        ["artifact.artifact_version.artifact_id", "artifact.artifact_version.version"],
    ),
    schema="artifact",
)

active_pointer = Table(
    "active_pointer",
    metadata,
    Column("artifact_id", UUID(as_uuid=True), ForeignKey("artifact.artifact.id"), primary_key=True),
    Column("version", Integer, nullable=False),
    Column("row_version", BigInteger, nullable=False, server_default="1"),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    ForeignKeyConstraint(
        ["artifact_id", "version"],
        ["artifact.artifact_version.artifact_id", "artifact.artifact_version.version"],
    ),
    schema="artifact",
)

dependency = Table(
    "dependency",
    metadata,
    Column("upstream_artifact_id", UUID(as_uuid=True), primary_key=True),
    Column("upstream_version", Integer, primary_key=True),
    Column("downstream_artifact_id", UUID(as_uuid=True), primary_key=True),
    Column("downstream_version", Integer, primary_key=True),
    Column("dependency_type", String(32), primary_key=True),
    Column("invalidation_rule", String(255), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    ForeignKeyConstraint(
        ["upstream_artifact_id", "upstream_version"],
        ["artifact.artifact_version.artifact_id", "artifact.artifact_version.version"],
    ),
    ForeignKeyConstraint(
        ["downstream_artifact_id", "downstream_version"],
        ["artifact.artifact_version.artifact_id", "artifact.artifact_version.version"],
    ),
    CheckConstraint("upstream_artifact_id <> downstream_artifact_id", name="no_self_dependency"),
    schema="artifact",
)

invalidation_decision = Table(
    "invalidation_decision",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("project_id", UUID(as_uuid=True), ForeignKey("core.project.id"), nullable=False),
    Column("root_ref", JSONB, nullable=False),
    Column("affected_refs", JSONB, nullable=False),
    Column("graph_version", BigInteger, nullable=False),
    Column("change_set", JSONB, nullable=False),
    Column("trace_id", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    schema="artifact",
)

command = Table(
    "command",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("idempotency_key", String(255), nullable=False, unique=True),
    Column("command_type", String(255), nullable=False),
    Column("project_id", UUID(as_uuid=True), ForeignKey("core.project.id")),
    Column("request_json", JSONB, nullable=False),
    Column("request_checksum", String(72), nullable=False),
    Column("state", String(32), nullable=False),
    Column("workflow_id", String(255)),
    Column("response_json", JSONB),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("completed_at", DateTime(timezone=True)),
    schema="workflow",
)

stage_execution = Table(
    "stage_execution",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("run_id", UUID(as_uuid=True), ForeignKey("core.run.id"), nullable=False),
    Column("stage", String(128), nullable=False),
    Column("execution_key", String(255), nullable=False, unique=True),
    Column("attempt", Integer, nullable=False),
    Column("state", String(32), nullable=False),
    Column("input_refs", JSONB, nullable=False),
    Column("output_refs", JSONB, nullable=False),
    Column("error_json", JSONB),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    schema="workflow",
)

review_request = Table(
    "review_request",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("project_id", UUID(as_uuid=True), ForeignKey("core.project.id"), nullable=False),
    Column("workflow_id", String(255), nullable=False),
    Column("gate", String(32), nullable=False),
    Column("target_ref", JSONB, nullable=False),
    Column("state", String(32), nullable=False),
    Column("policy_snapshot", JSONB, nullable=False),
    Column("deadline", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    schema="review",
)

review_decision = Table(
    "decision",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("request_id", UUID(as_uuid=True), ForeignKey("review.review_request.id"), unique=True),
    Column("decision", String(32), nullable=False),
    Column("reviewer_json", JSONB, nullable=False),
    Column("reasons", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    schema="review",
)

correction = Table(
    "correction",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("project_id", UUID(as_uuid=True), ForeignKey("core.project.id"), nullable=False),
    Column("run_id", UUID(as_uuid=True), ForeignKey("core.run.id"), nullable=False),
    Column("before_ref", JSONB, nullable=False),
    Column("after_ref", JSONB, nullable=False),
    Column("semantic_operation", JSONB, nullable=False),
    Column("before_value", JSONB, nullable=False),
    Column("after_value", JSONB, nullable=False),
    Column("reason", Text, nullable=False),
    Column("reviewer_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    schema="review",
)

automation_policy = Table(
    "automation_policy",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("version", Integer, primary_key=True),
    Column("scope_json", JSONB, nullable=False),
    Column("policy_json", JSONB, nullable=False),
    Column("state", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    schema="policy",
)

resource_profile = Table(
    "resource_profile",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("version", Integer, primary_key=True),
    Column("profile_json", JSONB, nullable=False),
    Column("state", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    schema="policy",
)

config_snapshot = Table(
    "config_snapshot",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("project_id", UUID(as_uuid=True), ForeignKey("core.project.id"), nullable=False),
    Column("schema_version", String(32), nullable=False),
    Column("config_json", JSONB, nullable=False),
    Column("checksum", String(72), nullable=False),
    Column("state", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("project_id", "checksum"),
    schema="policy",
)

asset_rights = Table(
    "asset_rights",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("project_id", UUID(as_uuid=True), ForeignKey("core.project.id"), nullable=False),
    Column("asset_ref", JSONB, nullable=False),
    Column("rights_json", JSONB, nullable=False),
    Column("state", String(32), nullable=False),
    Column("valid_until", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    schema="rights",
)

rights_manifest = Table(
    "rights_manifest",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("project_id", UUID(as_uuid=True), ForeignKey("core.project.id"), nullable=False),
    Column("version", Integer, primary_key=True),
    Column("manifest_json", JSONB, nullable=False),
    Column("checksum", String(72), nullable=False),
    Column("state", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("project_id", "checksum"),
    schema="rights",
)

publication_pointer = Table(
    "publication_pointer",
    metadata,
    Column("project_id", UUID(as_uuid=True), ForeignKey("core.project.id"), primary_key=True),
    Column("registry_type", String(64), primary_key=True),
    Column("registry_id", UUID(as_uuid=True), nullable=False),
    Column("version", Integer, nullable=False),
    Column("row_version", BigInteger, nullable=False, server_default="1"),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("version >= 1", name="positive_version"),
    schema="policy",
)

audit_event = Table(
    "audit_event",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("project_id", UUID(as_uuid=True), ForeignKey("core.project.id")),
    Column("event_type", String(255), nullable=False),
    Column("actor_json", JSONB, nullable=False),
    Column("target_ref", JSONB),
    Column("payload_json", JSONB, nullable=False),
    Column("trace_id", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    schema="audit",
)

outbox_event = Table(
    "outbox_event",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("aggregate_id", String(255), nullable=False),
    Column("event_type", String(255), nullable=False),
    Column("payload_json", JSONB, nullable=False),
    Column("trace_id", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("published_at", DateTime(timezone=True)),
    Column("attempts", Integer, nullable=False, server_default="0"),
    CheckConstraint("attempts >= 0", name="non_negative_attempts"),
    schema="audit",
)

Index("ix_artifact_version_run_state", artifact_version.c.run_id, artifact_version.c.state)
Index(
    "ix_artifact_dependency_downstream",
    dependency.c.downstream_artifact_id,
    dependency.c.downstream_version,
)
Index("ix_review_request_workflow_state", review_request.c.workflow_id, review_request.c.state)
Index(
    "ix_stage_execution_run_stage_state",
    stage_execution.c.run_id,
    stage_execution.c.stage,
    stage_execution.c.state,
)
Index("ix_audit_event_project_created", audit_event.c.project_id, audit_event.c.created_at)
