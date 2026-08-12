#!/usr/bin/env python3
"""Build the versioned E09 demo benchmark artifact."""

from __future__ import annotations

import argparse
from pathlib import Path

from packages.evaluation.timeline_benchmark import extract_demo_benchmark, write_benchmark


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    write_benchmark(extract_demo_benchmark(args.source), args.output)


if __name__ == "__main__":
    main()
