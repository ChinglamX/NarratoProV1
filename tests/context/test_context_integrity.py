from pathlib import Path
from shutil import copytree

from scripts.check_context_integrity import check


def test_repository_context_is_reconstructable() -> None:
    errors, snapshot = check(Path.cwd())
    assert errors == []
    assert snapshot is not None
    assert snapshot.active_epics
    assert snapshot.active_tasks
    assert snapshot.risks


def context_copy(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    for path in (
        "README.md",
        "AGENTS.md",
        "PROJECT_INDEX.md",
        "PROJECT_STATE.md",
        "agent",
        "design/implementation",
    ):
        source = Path.cwd() / path
        destination = root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            copytree(source, destination)
        else:
            destination.write_bytes(source.read_bytes())
    return root


def test_missing_required_file_fails_closed(tmp_path: Path) -> None:
    root = context_copy(tmp_path)
    (root / "PROJECT_INDEX.md").unlink()
    errors, _ = check(root)
    assert any("PROJECT_INDEX.md" in error for error in errors)


def test_unknown_active_task_fails_closed(tmp_path: Path) -> None:
    root = context_copy(tmp_path)
    state = root / "PROJECT_STATE.md"
    state.write_text(
        state.read_text().replace(
            "A03 Local Infrastructure runtime acceptance", "A99 Imaginary Task"
        )
    )
    errors, _ = check(root)
    assert "active Task not found in backlog: A99" in errors


def test_broken_index_link_fails_closed(tmp_path: Path) -> None:
    root = context_copy(tmp_path)
    index = root / "PROJECT_INDEX.md"
    index.write_text(index.read_text() + "\n- `missing/canonical.md`\n")
    errors, _ = check(root)
    assert "PROJECT_INDEX broken link: missing/canonical.md" in errors
