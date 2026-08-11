import json

from packages.timeline import compile_render_plan, export_otio, import_otio
from tests.timeline.fixtures import item, timeline, typed_ref


def test_otio_round_trip_is_lossless_with_private_metadata() -> None:
    value = timeline(item(start=0, duration=25), item(start=25, duration=25, item_type="text"))
    payload, exported_loss = export_otio(value)
    restored, imported_loss = import_otio(payload)
    assert exported_loss.lossless and imported_loss.lossless
    assert restored == value


def test_otio_missing_private_metadata_fails_closed_with_loss_report() -> None:
    value = timeline()
    payload, _ = export_otio(value)
    parsed = json.loads(payload)
    parsed["metadata"].pop("com.narratopro.v1")
    restored, loss = import_otio(json.dumps(parsed))
    assert restored is None
    assert not loss.lossless and loss.entries[0].severity == "error"


def test_otio_missing_item_metadata_is_reported_without_silent_loss() -> None:
    value = timeline()
    payload, _ = export_otio(value)
    parsed = json.loads(payload)
    parsed["tracks"]["children"][0]["children"][0]["metadata"].pop("com.narratopro.v1")
    restored, loss = import_otio(json.dumps(parsed))
    assert restored == value
    assert not loss.lossless and loss.entries[0].field == "com.narratopro.v1"


def test_render_plan_compilation_is_deterministic() -> None:
    value = timeline()
    arguments = {
        "timeline_ref": typed_ref("MasterTimeline"),
        "profile_ref": typed_ref("ConfigArtifact"),
        "toolchain_version": "ffmpeg-8.1.2",
    }
    first = compile_render_plan(value, **arguments)
    second = compile_render_plan(value, **arguments)
    assert first == second
    assert first.checksum.startswith("sha256:")
