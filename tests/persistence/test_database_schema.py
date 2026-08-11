from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from packages.persistence import metadata, schema


def test_baseline_contains_required_schemas_and_tables() -> None:
    names = {(table.schema, table.name) for table in metadata.tables.values()}
    assert {
        ("core", "project"),
        ("core", "run"),
        ("artifact", "artifact"),
        ("artifact", "artifact_version"),
        ("artifact", "blob"),
        ("artifact", "dependency"),
        ("workflow", "command"),
        ("review", "review_request"),
        ("review", "decision"),
        ("review", "correction"),
        ("policy", "automation_policy"),
        ("audit", "audit_event"),
        ("audit", "outbox_event"),
    } <= names


def test_artifact_version_ddl_has_immutable_identity_and_payload_guards() -> None:
    ddl = str(CreateTable(schema.artifact_version).compile(dialect=postgresql.dialect()))
    assert "PRIMARY KEY (artifact_id, version)" in ddl
    assert "UNIQUE (artifact_id, checksum)" in ddl
    assert "payload_json IS NOT NULL OR blob_id IS NOT NULL" in ddl


def test_dependency_ddl_has_exact_version_fks_and_self_guard() -> None:
    ddl = str(CreateTable(schema.dependency).compile(dialect=postgresql.dialect()))
    assert ddl.count("FOREIGN KEY") == 2
    assert "upstream_artifact_id <> downstream_artifact_id" in ddl


def test_outbox_and_artifact_share_one_metadata_transaction_boundary() -> None:
    assert schema.outbox_event.metadata is schema.artifact_version.metadata
    assert schema.audit_event.metadata is schema.artifact_version.metadata
