from collections.abc import Sequence
from pathlib import Path

from scripts import accept_local_infra


def test_acceptance_drill_covers_start_restart_and_persistence(monkeypatch: object) -> None:
    commands: list[tuple[str, ...]] = []

    def record(command: Sequence[str]) -> None:
        commands.append(tuple(command))

    monkeypatch.setattr(accept_local_infra, "execute", record)  # type: ignore[attr-defined]
    accept_local_infra.accept(Path("/repo"), Path("/repo/local.env"))
    rendered = [" ".join(command) for command in commands]
    assert any("up -d --wait" in command for command in rendered)
    assert any("restart postgres temporal" in command for command in rendered)
    assert sum("a03-persistence" in command for command in rendered) == 4
    assert rendered[-1].endswith("ps")
