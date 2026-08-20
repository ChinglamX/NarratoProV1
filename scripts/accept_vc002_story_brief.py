"""Persist and verify the Episode 8 VC-002 evidence chain and review card."""

# ruff: noqa: RUF001 - Chinese punctuation is intentional in the review artifact.

from __future__ import annotations

import argparse
import io
import json
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

from apps.services.story_brief import StoryBriefPersistenceService
from packages.artifacts import LocalObjectStore
from packages.contracts import ActorRef, ArtifactRef, ProviderIdentity, RawProviderResponse
from packages.contracts.providers import ProviderCapability
from packages.foundation.settings import get_settings
from packages.intelligence.story_brief import StoryClaim, parse_srt
from packages.persistence import ArtifactRepository
from packages.persistence.artifact_writer import commit_contract_artifact, payload_checksum
from packages.persistence.database import create_database_engine

ROOT = Path(__file__).resolve().parents[1]
TRACE_ID = "8e002000000000000000000000000001"


def _ref(data: dict[str, object]) -> ArtifactRef:
    return ArtifactRef.model_validate(data)


def _dump_ref(reference: ArtifactRef) -> dict[str, object]:
    return reference.model_dump(mode="json", exclude_none=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "product/episode_08_story_brief_validation.json",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/vc002_episode_08")
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    transcript_path = (config_path.parent / config["transcript"]).resolve()
    ingest_path = (config_path.parent / config["ingest_manifest"]).resolve()
    ingest = json.loads(ingest_path.read_text(encoding="utf-8"))
    transcript_bytes = transcript_path.read_bytes()
    cues = parse_srt(transcript_path)
    claims = tuple(StoryClaim(**item) for item in config["claims"])

    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    store = LocalObjectStore(settings.object_store_root)
    repository = ArtifactRepository()
    project_id, run_id = UUID(ingest["project_id"]), UUID(ingest["run_id"])
    audio_ref = _ref(ingest["artifacts"]["audio"])
    profile_ref = ArtifactRef.model_validate(
        {"artifact_id": uuid4(), "version": 1, "artifact_type": "ConfigArtifact"}
    )
    actor = ActorRef.model_validate({"kind": "system", "id": "vc002-acceptance"})
    provider = ProviderIdentity(
        provider="funasr-local-research",
        implementation="srt-import",
        version="1.0.0",
        model="episode-08-existing-research-output",
        license="research-only-unqualified",
    )

    staged = store.stage(run_id, "vc002-episode-08-srt", io.BytesIO(transcript_bytes))
    committed = store.commit(staged.uri, staged.checksum)
    raw_payload = RawProviderResponse.model_validate(
        {
            "provider": provider,
            "capability": ProviderCapability.ASR,
            "request_checksum": payload_checksum({"audio_ref": _dump_ref(audio_ref)}),
            "payload_uri": committed.uri,
            "payload_checksum": committed.checksum,
            "media_type": "application/x-subrip; charset=utf-8",
            "provider_schema_version": "research-srt-v1",
            "redacted": False,
        }
    )
    with engine.begin() as connection:
        raw_ref = commit_contract_artifact(
            connection,
            repository,
            artifact_id=uuid4(),
            artifact_type="RawProviderResponse",
            payload=raw_payload,
            project_id=project_id,
            run_id=run_id,
            variant_id=None,
            trace_id=TRACE_ID,
            actor=actor,
            producer_module="vc002-research-transcript-import",
            module_version="1.0.0",
            resource_profile_ref=profile_ref,
            rights_class="internal-only",
            inputs=(audio_ref,),
            schema_version="1.3.0",
        )

    result = StoryBriefPersistenceService(engine=engine, artifacts=repository).persist(
        project_id=project_id,
        run_id=run_id,
        source_audio_ref=audio_ref,
        raw_response_ref=raw_ref,
        resource_profile_ref=profile_ref,
        provider=provider,
        cues=cues,
        claims=claims,
        unresolved=tuple(config["unresolved"]),
        trace_id=TRACE_ID,
        rights_class="internal-only",
        actor=actor,
    )
    refs = [raw_ref, result.speech_observation, result.fact_set, result.story_graph]
    with engine.connect() as connection:
        records = [repository.get_version(connection, item) for item in refs]
    for reference, record in zip(refs, records, strict=True):
        if record["checksum"] != payload_checksum(record["payload_json"]):
            raise RuntimeError(f"checksum mismatch: {reference.artifact_type}")
    story = records[-1]["payload_json"]
    card = {
        "module": "VC-002 — E07 Story Understanding",
        "input": {
            "episode": 8,
            "transcript": str(transcript_path),
            "ingest_manifest": str(ingest_path),
        },
        "artifact_chain": [_dump_ref(item) for item in refs],
        "database_verification": {"all_refs_resolved": True, "payload_checksums_verified": True},
        "system_story_brief": {
            "events": [item["description"] for item in story["events"]],
            "unresolved_questions": [item["question"] for item in story["unresolved_questions"]],
            "confidence": "unavailable",
        },
        "manual_reference": config["manual_reference"],
        "human_review_question": [
            "系统摘要是否存在关键事实错误?",
            "是否漏掉决定 Hook 的主要冲突?",
            "是否足以支持后续营销方向选择?",
        ],
        "human_decision": "unreviewed",
        "current_maturity": "M2 Tool Verified; content effect unreviewed",
    }
    args.output.mkdir(parents=True, exist_ok=True)
    card_path = args.output / "comparison_card.json"
    card_path.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path = args.output / "comparison_card.md"
    system_lines = "\n".join(
        f"{index}. {event}" for index, event in enumerate(card["system_story_brief"]["events"], 1)
    )
    unresolved_lines = "\n".join(
        f"- {item}" for item in card["system_story_brief"]["unresolved_questions"]
    )
    markdown_path.write_text(
        "# VC-002 Episode 8 Story Brief 对比卡\n\n"
        "## 系统 Story Brief\n\n"
        f"{system_lines}\n\n"
        "未决问题：\n\n"
        f"{unresolved_lines}\n\n"
        "Confidence：`unavailable`；必须 L1 人工审核。\n\n"
        "## 人工参考草稿\n\n"
        f"{config['manual_reference']['summary']}\n\n"
        "状态：`producer_draft_pending_human_review`，不能视为已批准人工真值。\n\n"
        "## 必要人工判断\n\n"
        "1. 系统摘要是否存在关键事实错误？\n"
        "2. 是否漏掉决定 Hook 的主要冲突？\n"
        "3. 是否足以支持后续营销方向选择？\n\n"
        "Decision：`unreviewed`\n",
        encoding="utf-8",
    )
    manifest = {
        "comparison_card": str(card_path),
        "comparison_card_markdown": str(markdown_path),
        "comparison_card_checksum": "sha256:" + sha256(card_path.read_bytes()).hexdigest(),
        "artifact_chain": card["artifact_chain"],
    }
    (args.output / "acceptance_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
