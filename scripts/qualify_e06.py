"""Validate and summarize the immutable G05 qualification matrix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from packages.evaluation.qualification import load_qualification, qualification_summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path("evaluation/qualification/e06_g05.json"),
    )
    parser.add_argument("--allow-blocked", action="store_true")
    args = parser.parse_args()
    result = qualification_summary(load_qualification(args.path))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["production_qualified"] or args.allow_blocked else 2


if __name__ == "__main__":
    raise SystemExit(main())
