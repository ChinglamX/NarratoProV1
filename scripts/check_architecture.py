#!/usr/bin/env python3
"""Fail when a package imports a layer that is forbidden by the domain DAG."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

ALLOWED: dict[str, frozenset[str]] = {
    "foundation": frozenset(),
    "contracts": frozenset({"foundation"}),
    "artifacts": frozenset({"foundation", "contracts"}),
    "persistence": frozenset({"foundation", "contracts", "artifacts"}),
    "control": frozenset({"foundation", "contracts", "artifacts"}),
    "intelligence": frozenset({"foundation", "contracts", "artifacts"}),
    "strategy": frozenset({"foundation", "contracts", "artifacts", "intelligence"}),
    "timeline": frozenset({"foundation", "contracts", "artifacts", "strategy"}),
    "production": frozenset({"foundation", "contracts", "artifacts", "timeline"}),
    "evaluation": frozenset({"foundation", "contracts", "artifacts"}),
    "providers": frozenset({"foundation", "contracts"}),
    "observability": frozenset({"foundation", "contracts"}),
    "testing": frozenset({"foundation", "contracts"}),
}


def imported_package(node: ast.AST) -> str | None:
    names: list[str] = []
    if isinstance(node, ast.Import):
        names = [alias.name for alias in node.names]
    elif isinstance(node, ast.ImportFrom) and node.module:
        names = [node.module]
    for name in names:
        parts = name.split(".")
        if len(parts) >= 2 and parts[0] == "packages":
            return parts[1]
    return None


def violations(root: Path) -> list[str]:
    errors: list[str] = []
    package_root = root / "packages"
    for source in package_root.glob("*/*.py"):
        owner = source.parent.name
        if owner not in ALLOWED:
            continue
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            target = imported_package(node)
            if target and target != owner and target not in ALLOWED[owner]:
                line = getattr(node, "lineno", 0)
                errors.append(f"{source.relative_to(root)}:{line}: {owner} -> {target} forbidden")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args()
    errors = violations(args.root.resolve())
    if errors:
        print("\n".join(errors))
        return 1
    print("architecture dependency check: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
