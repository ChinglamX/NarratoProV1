#!/usr/bin/env python3
"""Validate the repository-owned context and recovery contract."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

REQUIRED_FILES = (
    "README.md",
    "AGENTS.md",
    "PROJECT_INDEX.md",
    "PROJECT_STATE.md",
    "agent/CONTEXT_RECONSTRUCTION_PROTOCOL.md",
    "agent/HANDOFF_TEMPLATE.md",
    "design/implementation/07_EPICS_AND_DELIVERY_SEQUENCE.md",
    "design/implementation/08_INITIAL_IMPLEMENTATION_BACKLOG.md",
)
HANDOFF_FIELDS = (
    "Handoff ID:",
    "Objective:",
    "Active Epic / Backlog ID:",
    "Starting State Version:",
    "Inputs Read:",
    "Files Changed:",
    "Validation Performed:",
    "Workspace State:",
    "Risks / Blockers / Open Decisions:",
    "Next Exact Step:",
    "Project State Update:",
)


@dataclass(frozen=True)
class ContextSnapshot:
    state_version: int
    lifecycle: str
    active_release: str
    active_epics: tuple[str, ...]
    active_tasks: tuple[str, ...]
    risks: tuple[str, ...]


def first_match(pattern: str, text: str, label: str) -> str:
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        raise ValueError(f"PROJECT_STATE missing {label}")
    return match.group(1).strip()


def extract_ids(pattern: str, text: str) -> set[str]:
    return set(re.findall(pattern, text, flags=re.MULTILINE))


def check(root: Path) -> tuple[list[str], ContextSnapshot | None]:
    errors: list[str] = []
    for relative in REQUIRED_FILES:
        path = root / relative
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            errors.append(f"required context file missing or empty: {relative}")
    if errors:
        return errors, None

    index = (root / "PROJECT_INDEX.md").read_text(encoding="utf-8")
    for reference in sorted(set(re.findall(r"`([^`]+\.(?:md|yaml|yml))`", index))):
        if "*" not in reference and not (root / reference).exists():
            errors.append(f"PROJECT_INDEX broken link: {reference}")

    state = (root / "PROJECT_STATE.md").read_text(encoding="utf-8")
    epics = (root / "design/implementation/07_EPICS_AND_DELIVERY_SEQUENCE.md").read_text(
        encoding="utf-8"
    )
    backlog = (root / "design/implementation/08_INITIAL_IMPLEMENTATION_BACKLOG.md").read_text(
        encoding="utf-8"
    )
    try:
        state_version = int(first_match(r"^State Version:\s*(\d+)", state, "State Version"))
        lifecycle = first_match(r"^- Lifecycle：(.+)$", state, "Lifecycle")  # noqa: RUF001
        active_release = first_match(
            r"^- Active Release Slice：(.+?)[。.]?$",  # noqa: RUF001
            state,
            "release",
        )
        active_epic_line = first_match(
            r"^- Active Epics：(.+?)[。.]?$",  # noqa: RUF001
            state,
            "active epics",
        )
        active_task_line = first_match(
            r"^- Active Backlog Entry：(.+?)[。.]?$",  # noqa: RUF001
            state,
            "active backlog",
        )
    except ValueError as exc:
        errors.append(str(exc))
        return errors, None

    known_epics = extract_ids(r"^### (E\d{2})\s+—", epics)
    known_tasks = extract_ids(r"^### ([A-Z]\d{2})\s+", backlog)
    active_epics = tuple(dict.fromkeys(re.findall(r"\bE\d{2}\b", active_epic_line)))
    active_tasks = tuple(dict.fromkeys(re.findall(r"\b[A-Z]\d{2}\b", active_task_line)))
    for epic in active_epics:
        if epic not in known_epics:
            errors.append(f"active Epic not found in catalog: {epic}")
    for task in active_tasks:
        if task not in known_tasks:
            errors.append(f"active Task not found in backlog: {task}")

    handoff = (root / "agent/HANDOFF_TEMPLATE.md").read_text(encoding="utf-8")
    for field in HANDOFF_FIELDS:
        if field not in handoff:
            errors.append(f"handoff template missing field: {field}")

    risk_section = state.split("## 5. 当前阻断与风险", maxsplit=1)
    risks: tuple[str, ...] = ()
    if len(risk_section) == 2:
        body = risk_section[1].split("\n## ", maxsplit=1)[0]
        risks = tuple(line[2:].strip() for line in body.splitlines() if line.startswith("- "))
    if not active_epics or not active_tasks or not risks:
        errors.append("cold-start drill cannot recover active Epic, Task, and risks")

    snapshot = ContextSnapshot(
        state_version=state_version,
        lifecycle=lifecycle,
        active_release=active_release,
        active_epics=active_epics,
        active_tasks=active_tasks,
        risks=risks,
    )
    return errors, snapshot


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    errors, snapshot = check(args.root.resolve())
    if errors:
        print("\n".join(errors))
        return 1
    if snapshot is None:
        print("context snapshot unexpectedly unavailable")
        return 1
    print(
        json.dumps(asdict(snapshot), ensure_ascii=False, indent=2)
        if args.json
        else "context integrity check: ok"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
