from uuid import uuid4

from apps.api.commands import _checksum
from apps.api.corrections import OperationBody, PatchBody, _operations


def test_command_checksum_is_canonical() -> None:
    assert _checksum({"a": 1, "b": 2}) == _checksum({"b": 2, "a": 1})
    assert _checksum({"a": 1}).startswith("sha256:")


def test_correction_operation_body_serializes_for_repository() -> None:
    body = PatchBody(
        project_id=uuid4(),
        run_id=uuid4(),
        base_version=1,
        operations=[OperationBody(operation="replace", path=["title"], value="new")],
        reason="fix",
    )
    assert _operations(body) == [{"operation": "replace", "path": ["title"], "value": "new"}]
