import json
import re
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.contracts import ArtifactRef
from packages.contracts import artifact_catalog as artifact_catalog_module
from packages.contracts import registry as registry_module
from packages.contracts.artifact_catalog import ARTIFACT_TYPE_SPECS, ArtifactTypeSpec
from packages.contracts.registry import (
    REGISTRY_VERSION,
    artifact_registry_breaking_changes,
    artifact_registry_document,
    breaking_changes,
    generated_outputs,
    json_schema_document,
    openapi_document,
    registry_history_errors,
)


def _design_catalog() -> dict[str, tuple[str, str]]:
    text = Path("design/implementation/05_SCHEMA_AND_ARTIFACT_CATALOG.md").read_text()
    section = text.split("## 4. Canonical Artifact Catalog", 1)[1].split("\n---\n", 1)[0]
    result: dict[str, tuple[str, str]] = {}
    for line in section.splitlines():
        if not re.match(r"^\| [A-Za-z]", line):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells[0] == "Domain":
            continue
        domain, names, owner_expression = cells[:3]
        primary_owner = owner_expression.split("/", 1)[0]
        for name in (item.strip() for item in names.split("/")):
            assert name not in result, f"duplicate design artifact type: {name}"
            result[name] = (domain, primary_owner)
    return result


def test_artifact_registry_matches_design_catalog_and_real_owners() -> None:
    code_catalog = {spec.name: (spec.domain, spec.owner) for spec in ARTIFACT_TYPE_SPECS}
    assert code_catalog == _design_catalog()
    for spec in ARTIFACT_TYPE_SPECS:
        assert (Path("packages") / spec.owner).is_dir()


def test_duplicate_artifact_type_names_fail_registry_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    duplicate = ArtifactTypeSpec(name="StoryGraph", domain="Story", owner="intelligence")
    monkeypatch.setattr(
        artifact_catalog_module,
        "ARTIFACT_TYPE_SPECS",
        (*ARTIFACT_TYPE_SPECS, duplicate),
    )
    with pytest.raises(ValueError, match="duplicate artifact types"):
        artifact_catalog_module.validate_artifact_catalog()


def test_artifact_ref_rejects_unknown_type() -> None:
    with pytest.raises(ValidationError, match="unknown artifact_type"):
        ArtifactRef(artifact_id=uuid4(), version=1, artifact_type="UnregisteredArtifact")


def test_artifact_type_registry_is_embedded_in_cross_language_schema() -> None:
    artifact_type_schema = openapi_document()["components"]["schemas"]["ArtifactRef"]["properties"][
        "artifact_type"
    ]
    assert set(artifact_type_schema["enum"]) == {spec.name for spec in ARTIFACT_TYPE_SPECS}


def test_all_openapi_references_resolve_and_schema_names_are_unique() -> None:
    schemas = openapi_document()["components"]["schemas"]
    assert len(schemas) == len(set(schemas))
    serialized = json.dumps(schemas)
    references = set(re.findall(r'#/components/schemas/([^"/]+)', serialized))
    assert references <= set(schemas)


def test_generated_outputs_match_committed_registry() -> None:
    for path, expected in generated_outputs(Path.cwd()).items():
        assert path.read_text(encoding="utf-8") == expected, f"stale generated file: {path}"
    generated_types = generated_outputs(Path.cwd())[
        Path.cwd() / "apps" / "review_web" / "src" / "generated" / "contracts.generated.ts"
    ]
    assert "export type JsonValue = null | boolean | number | string" in generated_types
    assert '"StoryGraph"' in generated_types


def test_compatible_optional_field_and_enum_addition_are_allowed() -> None:
    previous = json_schema_document()
    current = deepcopy(previous)
    current["$defs"]["ActorRef"]["properties"]["display_name"] = {"type": "string"}
    current["$defs"]["ActorKind"]["enum"].append("service")
    assert breaking_changes(previous, current) == []


def test_removed_schema_new_required_field_and_narrowed_enum_are_breaking() -> None:
    previous = json_schema_document()
    current = deepcopy(previous)
    del current["$defs"]["TimeRange"]
    current["$defs"]["ActorRef"]["properties"]["display_name"] = {"type": "string"}
    current["$defs"]["ActorRef"]["required"].append("display_name")
    current["$defs"]["ActorKind"]["enum"].remove("system")
    changes = breaking_changes(previous, current)
    assert "removed schema: TimeRange" in changes
    assert "new required field: ActorRef.display_name" in changes
    assert "removed enum value: ActorKind.system" in changes


def test_artifact_removal_and_owner_change_are_breaking() -> None:
    previous = artifact_registry_document()
    current = deepcopy(previous)
    current["artifact_types"] = current["artifact_types"][1:]
    current["artifact_types"][0]["owner"] = "control"
    assert artifact_registry_breaking_changes(previous, current)


def test_registry_version_and_openapi_version_are_identical() -> None:
    assert openapi_document()["info"]["version"] == REGISTRY_VERSION
    assert artifact_registry_document()["registry_version"] == REGISTRY_VERSION
    assert registry_history_errors(Path.cwd()) == []


def _write_registry_version(root: Path, version: str, schema: dict, artifacts: dict) -> None:
    version_dir = root / "generated" / "contracts" / "versions" / version
    version_dir.mkdir(parents=True)
    (version_dir / "json-schema.json").write_text(json.dumps(schema))
    (version_dir / "artifact-types.json").write_text(json.dumps(artifacts))


def test_breaking_history_requires_major_version_bump(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_schema = json_schema_document()
    broken_schema = deepcopy(original_schema)
    del broken_schema["$defs"]["TimeRange"]
    artifacts = artifact_registry_document()
    _write_registry_version(tmp_path, "1.0.0", original_schema, artifacts)
    _write_registry_version(tmp_path, "1.1.0", broken_schema, artifacts)
    monkeypatch.setattr(registry_module, "REGISTRY_VERSION", "1.1.0")
    assert any("major version bump" in error for error in registry_history_errors(tmp_path))


def test_breaking_history_is_allowed_after_major_version_bump(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_schema = json_schema_document()
    broken_schema = deepcopy(original_schema)
    del broken_schema["$defs"]["TimeRange"]
    artifacts = artifact_registry_document()
    _write_registry_version(tmp_path, "1.0.0", original_schema, artifacts)
    _write_registry_version(tmp_path, "2.0.0", broken_schema, artifacts)
    monkeypatch.setattr(registry_module, "REGISTRY_VERSION", "2.0.0")
    assert registry_history_errors(tmp_path) == []
