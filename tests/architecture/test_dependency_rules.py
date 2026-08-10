from pathlib import Path

from scripts.check_architecture import violations


def test_repository_obeys_dependency_dag() -> None:
    assert violations(Path.cwd()) == []


def test_bad_fixture_proves_rule_is_enforced(tmp_path: Path) -> None:
    source = tmp_path / "packages" / "foundation" / "bad.py"
    source.parent.mkdir(parents=True)
    source.write_text("from packages.strategy import anything\n", encoding="utf-8")
    errors = violations(tmp_path)
    assert errors and "foundation -> strategy forbidden" in errors[0]
