"""Deterministic semantic patches and dry-run impact planning."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal


class PatchConflict(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SemanticOperation:
    operation: Literal["add", "replace", "remove"]
    path: tuple[str, ...]
    value: Any = None


@dataclass(frozen=True, slots=True)
class PatchImpact:
    result: dict[str, Any]
    changed_paths: tuple[str, ...]
    downstream_refs: tuple[str, ...]


def preview_patch(
    source: dict[str, Any],
    operations: tuple[SemanticOperation, ...],
    *,
    downstream_refs: tuple[str, ...] = (),
) -> PatchImpact:
    result = deepcopy(source)
    changed: list[str] = []
    for operation in operations:
        if not operation.path:
            raise PatchConflict("root replacement is prohibited")
        cursor: dict[str, Any] = result
        for segment in operation.path[:-1]:
            child = cursor.get(segment)
            if not isinstance(child, dict):
                raise PatchConflict(f"path does not exist: {'/'.join(operation.path)}")
            cursor = child
        leaf = operation.path[-1]
        exists = leaf in cursor
        if operation.operation in {"replace", "remove"} and not exists:
            raise PatchConflict(f"path does not exist: {'/'.join(operation.path)}")
        if operation.operation == "add" and exists:
            raise PatchConflict(f"path already exists: {'/'.join(operation.path)}")
        if operation.operation == "remove":
            del cursor[leaf]
        else:
            cursor[leaf] = deepcopy(operation.value)
        changed.append("/" + "/".join(operation.path))
    return PatchImpact(result, tuple(changed), downstream_refs)
