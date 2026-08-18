from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import ANY, MagicMock
from uuid import uuid4

from apps.services import media_production as module
from apps.services.media_production import MediaProductionService
from packages.artifacts import BlobMetadata
from packages.contracts import ActorRef, ArtifactRef
from packages.contracts.media_production import AlignmentArtifact, ConformReport, MixedAudio


def _ref(kind: str) -> ArtifactRef:
    return ArtifactRef.model_validate(
        {"artifact_id": str(uuid4()), "version": 1, "artifact_type": kind}
    )


def _context() -> dict[str, object]:
    return {
        "project_id": uuid4(),
        "run_id": uuid4(),
        "trace_id": "a" * 32,
        "actor": ActorRef.model_validate({"kind": "human", "id": "unit"}),
        "resource_profile_ref": _ref("ResourceProfile"),
    }


def test_persist_alignment_and_conform_delegate_exact_inputs(monkeypatch) -> None:
    repository = MagicMock()
    service = MediaProductionService(artifacts=repository, store=MagicMock())
    committed = _ref("AlignmentArtifact")
    writer = MagicMock(return_value=committed)
    monkeypatch.setattr(module, "commit_contract_artifact", writer)
    voice_ref = _ref("VoiceAsset")
    narration_ref = _ref("NarrationLineSet")
    alignment = AlignmentArtifact(
        voice_asset_ref=voice_ref,
        narration_line_set_ref=narration_ref,
        tokens=(),
        alignment_method="measured-line-boundary",
    )
    result = service.persist_alignment(MagicMock(), alignment=alignment, **_context())
    assert result == committed
    assert writer.call_args.kwargs["inputs"] == (voice_ref, narration_ref)

    timeline_ref = _ref("MasterTimeline")
    report = ConformReport(
        source_timeline_ref=timeline_ref,
        conformed_timeline_ref=timeline_ref,
        voice_asset_ref=voice_ref,
        alignment_ref=committed,
        changed_item_ids=(),
        invalidated_artifact_refs=(),
        duration_delta={"value": 0, "rate_num": 1_000_000},
    )
    conform_ref = _ref("ConformReport")
    writer.return_value = conform_ref
    result = service.persist_conform_report(MagicMock(), report=report, **_context())
    assert result == conform_ref
    assert writer.call_args.kwargs["inputs"] == (
        timeline_ref,
        timeline_ref,
        voice_ref,
        committed,
    )


def test_persist_mixed_audio_commits_blob_and_links_artifact() -> None:
    repository = MagicMock()
    store = MagicMock()
    staged = BlobMetadata("local-object://staging/mix.part", "sha256:" + "1" * 64, 3)
    committed_meta = BlobMetadata("local-object://objects/sha256/abc", staged.checksum, 3)
    store.stage.return_value = staged
    service = MediaProductionService(artifacts=repository, store=store)
    registered = SimpleNamespace(blob_id=uuid4(), metadata=staged, state="staging")
    committed = SimpleNamespace(
        blob_id=registered.blob_id, metadata=committed_meta, state="committed"
    )
    blobs = MagicMock()
    blobs.register_or_get_staged.return_value = registered
    blobs.commit.return_value = committed
    service._blobs = blobs
    mix_ref = _ref("MixPlan")
    mixed = MixedAudio(
        mix_plan_ref=mix_ref,
        audio_blob_ref="placeholder",
        duration={"value": 1_000_000, "rate_num": 1_000_000},
        integrated_loudness_lufs=-20.3,
        true_peak_dbtp=-2.6,
    )
    expected = _ref("MixedAudio")
    repository.commit_version.return_value = expected
    result = service.persist_mixed_audio(MagicMock(), audio=b"wav", mixed_audio=mixed, **_context())
    assert result == expected
    blobs.commit.assert_called_once_with(ANY, store, registered)
    envelope = repository.commit_version.call_args.args[1]
    assert envelope.payload["audio_blob_ref"] == committed_meta.uri
    assert repository.commit_version.call_args.kwargs["blob_id"] == registered.blob_id
