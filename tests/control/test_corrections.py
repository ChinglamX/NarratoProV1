import pytest

from packages.control.corrections import PatchConflict, SemanticOperation, preview_patch


def test_patch_preview_is_non_mutating_and_reports_impact() -> None:
    source = {"story": {"title": "old"}}
    impact = preview_patch(
        source,
        (SemanticOperation("replace", ("story", "title"), "new"),),
        downstream_refs=("strategy:1",),
    )
    assert source["story"]["title"] == "old"
    assert impact.result["story"]["title"] == "new"
    assert impact.changed_paths == ("/story/title",)
    assert impact.downstream_refs == ("strategy:1",)


def test_patch_rejects_ambiguous_paths() -> None:
    with pytest.raises(PatchConflict):
        preview_patch({}, (SemanticOperation("replace", ("missing",), 1),))
    with pytest.raises(PatchConflict):
        preview_patch({}, (SemanticOperation("replace", (), 1),))


def test_patch_add_remove_and_nested_path_failures() -> None:
    impact = preview_patch(
        {"nested": {"old": 1}},
        (
            SemanticOperation("remove", ("nested", "old")),
            SemanticOperation("add", ("nested", "new"), 2),
        ),
    )
    assert impact.result == {"nested": {"new": 2}}
    with pytest.raises(PatchConflict):
        preview_patch({"nested": 1}, (SemanticOperation("add", ("nested", "x"), 2),))
    with pytest.raises(PatchConflict):
        preview_patch({"x": 1}, (SemanticOperation("add", ("x",), 2),))
