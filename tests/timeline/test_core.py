from fractions import Fraction
from uuid import uuid4

import pytest

from packages.contracts import TimelinePatch, TimeRange
from packages.timeline import (
    TimelineChange,
    TimelinePatchConflict,
    apply_patch,
    can_rebase,
    semantic_diff,
    validate_timeline,
)
from tests.timeline.fixtures import artifact_ref, item, patch, rational, timeline


def test_validator_detects_overlap_order_source_bounds_and_target_duration() -> None:
    first = item(start=25, duration=25)
    second = item(start=0, duration=50)
    value = timeline(first, second)
    report = validate_timeline(
        value,
        source_availability={
            str(first.source_ref.artifact_id): first.source_range,
            str(second.source_ref.artifact_id): TimeRange.model_validate(
                {"start": rational(0), "duration": rational(25)}
            ),
        },
        target_duration=Fraction(3),
    )
    codes = {issue.code for issue in report.issues}
    assert {"track_not_sorted", "item_overlap", "source_range_out_of_bounds"} <= codes
    assert "target_duration_mismatch" in codes
    assert not report.render_ready


def test_patch_move_trim_parameter_remove_and_diff() -> None:
    original = item(start=0, duration=25)
    value = timeline(original)
    moved = apply_patch(
        value,
        patch(
            original,
            "move",
            {"timeline_range": {"start": rational(25), "duration": rational(25)}},
        ),
    )
    moved_item = moved.tracks[0].items[0]
    assert moved_item.item_version == 2
    assert semantic_diff(value, moved) == (TimelineChange(original.item_id, "modified", 1, 2),)
    parameterized = apply_patch(
        moved,
        patch(moved_item, "set_parameter", {"key": "opacity", "value": 0.5}),
    )
    assert parameterized.tracks[0].items[0].parameters["opacity"] == 0.5
    removed = apply_patch(parameterized, patch(parameterized.tracks[0].items[0], "remove", {}))
    assert removed.tracks[0].items == ()


def test_insert_split_stale_conflict_and_rebase() -> None:
    original = item(start=0, duration=50)
    value = timeline(original)
    inserted = item(start=50, duration=25)
    insert_patch = TimelinePatch.model_validate(
        {
            "patch_id": uuid4(),
            "base_timeline": artifact_ref("MasterTimeline"),
            "operations": [
                {
                    "operation_id": uuid4(),
                    "op": "insert",
                    "payload": {
                        "track_id": str(value.tracks[0].track_id),
                        "item": inserted.model_dump(mode="json"),
                    },
                }
            ],
            "author": {"kind": "human", "id": "editor"},
            "reason": "insert",
        }
    )
    after_insert = apply_patch(value, insert_patch)
    assert len(after_insert.tracks[0].items) == 2
    stale = patch(original, "remove", {}).model_copy(
        update={
            "operations": (
                patch(original, "remove", {})
                .operations[0]
                .model_copy(update={"expected_item_version": 99}),
            )
        }
    )
    with pytest.raises(TimelinePatchConflict, match="stale"):
        apply_patch(value, stale)
    changes = (TimelineChange(inserted.item_id, "modified", 1, 2),)
    assert can_rebase(patch(original, "remove", {}), changes)
    assert not can_rebase(patch(inserted, "remove", {}), changes)


def test_trim_replace_split_and_invalid_payloads() -> None:
    original = item(start=0, duration=50)
    value = timeline(original)
    trimmed = apply_patch(
        value,
        patch(
            original,
            "trim",
            {
                "timeline_range": {"start": rational(0), "duration": rational(25)},
                "source_range": {"start": rational(0), "duration": rational(25)},
            },
        ),
    )
    trimmed_item = trimmed.tracks[0].items[0]
    replacement = trimmed_item.model_copy(update={"parameters": {"crop": "center"}})
    replaced = apply_patch(
        trimmed,
        patch(trimmed_item, "replace", {"item": replacement.model_dump(mode="json")}),
    )
    assert replaced.tracks[0].items[0].item_version == 3
    current = replaced.tracks[0].items[0]
    left = current.model_copy(
        update={
            "timeline_range": current.timeline_range.model_copy(
                update={
                    "duration": current.timeline_range.duration.model_copy(update={"value": 10})
                }
            )
        }
    )
    right = item(start=10, duration=15)
    split = apply_patch(
        replaced,
        patch(
            current,
            "split",
            {"left": left.model_dump(mode="json"), "right": right.model_dump(mode="json")},
        ),
    )
    assert len(split.tracks[0].items) == 2
    with pytest.raises(TimelinePatchConflict, match="parameter key"):
        apply_patch(value, patch(original, "set_parameter", {"key": ""}))
    with pytest.raises(TimelinePatchConflict, match="invalid timeline_range"):
        apply_patch(value, patch(original, "move", {}))


def test_insert_missing_track_and_replace_identity_fail_closed() -> None:
    original = item()
    value = timeline(original)
    bad_insert = TimelinePatch.model_validate(
        {
            "patch_id": uuid4(),
            "base_timeline": artifact_ref("MasterTimeline"),
            "operations": [
                {
                    "operation_id": uuid4(),
                    "op": "insert",
                    "payload": {
                        "track_id": str(uuid4()),
                        "item": item(start=25).model_dump(mode="json"),
                    },
                }
            ],
            "author": {"kind": "human", "id": "editor"},
            "reason": "bad insert",
        }
    )
    with pytest.raises(TimelinePatchConflict, match="track does not exist"):
        apply_patch(value, bad_insert)
    other = item()
    with pytest.raises(TimelinePatchConflict, match="preserve item_id"):
        apply_patch(
            value,
            patch(original, "replace", {"item": other.model_dump(mode="json")}),
        )
