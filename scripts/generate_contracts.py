#!/usr/bin/env python3
"""Generate or verify the versioned contract registry outputs."""

from __future__ import annotations

import argparse
from pathlib import Path

from packages.contracts.registry import REGISTRY_VERSION, generated_outputs, registry_history_errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    stale: list[str] = []
    immutable_prefix = root / "generated" / "contracts" / "versions" / REGISTRY_VERSION
    for path, content in generated_outputs(root).items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(str(path.relative_to(root)))
            continue
        if path.is_relative_to(immutable_prefix) and path.exists():
            if path.read_text(encoding="utf-8") != content:
                print(f"refusing to overwrite immutable registry version: {path.relative_to(root)}")
                return 1
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    if stale:
        print("contract registry outputs are missing or stale:")
        print("\n".join(f"- {path}" for path in stale))
        return 1
    history_errors = registry_history_errors(root)
    if history_errors:
        print("contract registry version history is invalid:")
        print("\n".join(f"- {error}" for error in history_errors))
        return 1
    print("contract registry outputs: ok" if args.check else "contract registry generated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
