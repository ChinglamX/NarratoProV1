import json
from pathlib import Path

import packages.longform.inventory as inventory_module
from packages.longform.inventory import build_media_inventory


def test_inventory_groups_episodes_and_popular_cuts(tmp_path: Path, monkeypatch: object) -> None:
    series = tmp_path / "普通剧集" / "测试剧"
    popular = tmp_path / "热门剧集" / "测试剧"
    series.mkdir(parents=True)
    popular.mkdir(parents=True)
    (series / "第1集.mp4").write_bytes(b"episode-one")
    (series / "2.mp4").write_bytes(b"episode-two")
    (popular / "热门剪辑.mp4").write_bytes(b"popular")
    monkeypatch.setattr(inventory_module.shutil, "which", lambda _: None)  # type: ignore[attr-defined]

    result = build_media_inventory(tmp_path)

    assert result.rights_status == "user_declared_internal_use"
    assert len(result.files) == 3
    assert {item.episode_number for item in result.files} == {1, 2, None}
    assert sum(item.is_popular_cut for item in result.files) == 1
    assert json.loads(result.to_json())["rights_status"] == "user_declared_internal_use"


def test_inventory_rejects_empty_directory(tmp_path: Path) -> None:
    try:
        build_media_inventory(tmp_path)
    except ValueError as error:
        assert "no supported video" in str(error)
    else:
        raise AssertionError("empty media root must fail closed")
