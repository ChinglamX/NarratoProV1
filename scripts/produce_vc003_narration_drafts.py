"""Research LLM narration draft generation for Episode 8 (威胁倒叙).

For each approved Story event (in the approved threat -> sale -> payment
order), call the Volcengine Ark chat model for a marketing narration draft,
validate it deterministically against the project rules (no identity names, no
verbatim dialogue repetition, no unsupported psychology), retry once with the
violations fed back, and emit a DRAFT NarrationLineSet artifact plus a review
card comparing the drafts with the human-approved agent lines.

This is a *research* path: drafts are candidates with confidence unavailable;
the final decision stays at the L1 narration boundary (human checkpoint).
No approved artifact or the production chain is changed.
"""

# ruff: noqa: RUF001 - CJK narration prompts and drafts are intentional.

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from uuid import UUID, uuid4

from packages.contracts import ActorRef, ArtifactRef
from packages.contracts.timeline_intent import (
    DialogueRelationship,
    NarrationLine,
    NarrationLineSet,
)
from packages.foundation.settings import get_settings
from packages.intelligence.narration_draft import validate_narration_draft
from packages.persistence.artifact_repository import ArtifactRepository
from packages.persistence.artifact_writer import commit_contract_artifact
from packages.persistence.database import create_database_engine

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = UUID("dd397853-79bc-4e6f-a540-bb1c296d6936")
RUN_ID = UUID("d3690d71-444a-43d9-bbd0-52bd1c91d371")
STORY_REF = ArtifactRef.model_validate(
    {
        "artifact_id": "c378ba51-da33-4049-baf0-538ca637e9a5",
        "version": 1,
        "artifact_type": "StoryGraph",
        "checksum": "sha256:8b34ae0d15d81126a1907366e27efcb4ce113e5bea0e1d2fae0ec146d0c7aad2",
    }
)
BRIEF_REF = ArtifactRef.model_validate(
    {
        "artifact_id": "bc2c693e-8768-40fc-84d5-fcc00946f80a",
        "version": 1,
        "artifact_type": "CreativeBrief",
        "checksum": "sha256:a20c2f1639d5ceb3ce2772dbc3b98d97e14830400b9b0e48d3de73ee8f38e0e8",
    }
)

# Approved Episode 8 events in the 威胁倒叙 order (threat -> sale -> payment).
EVENTS = (
    (
        UUID("87f8ff89-54ec-42b1-8e46-c12cefba6e47"),
        UUID("1267ab6e-3cc8-4a10-8ef5-5764077f0616"),
        "danger-hook",
        "另一方得知那小子一天得到三十万，因其有钱不还并曾动手，决定盯住并威胁杀死他。",
        "那小子一天就弄到了三十万。那小子手里有钱，却藏着掖着，不还还敢对我动手，给我盯住，这次我就不信弄不死他",
    ),
    (
        UUID("1df88e31-efac-44ac-8e73-8bcb5c8269ec"),
        UUID("172bf99b-af5d-4070-b836-ec6d50eedf58"),
        "transaction-context",
        "对白表明有人以三十万购买两样货物，并完成交易。",
        "三十万这两样我都要了",
    ),
    (
        UUID("1c583c8c-7291-4f8f-91e9-b02181958c26"),
        UUID("d008fa4a-3bd6-40c0-83f3-79885d89b34d"),
        "value-proof",
        "交易方交出一张内有三十万、密码为六个八的卡。",
        "这张卡里有三十万，密码，六个八",
    ),
)

TRACE_ID = "8e007000000000000000000000000007"
ACTOR = ActorRef.model_validate({"kind": "model", "id": "vc003-research-llm-narration"})


def _llm_draft(prompt: str) -> str:
    settings = get_settings()
    if settings.volcengine_ark_api_key is None or not settings.volcengine_ark_model:
        raise RuntimeError("Ark LLM is unavailable: API key or model not configured")
    body = json.dumps(
        {
            "model": settings.volcengine_ark_model,
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        },
        separators=(",", ":"),
    ).encode()
    request = urllib.request.Request(  # nosec B310
        settings.volcengine_ark_endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {settings.volcengine_ark_api_key.get_secret_value()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:  # nosec B310
            parsed = json.loads(response.read())
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Ark LLM request failed ({error.code})") from error
    return str(parsed["choices"][0]["message"]["content"]).strip()


def _prompt(description: str, dialogue: str, violations: list[str] | None = None) -> str:
    extra = ""
    if violations:
        extra = f" 上次草稿违规：{', '.join(violations)}。必须全部修正。"
    return (
        "你是短剧营销解说撰稿人，为「威胁倒叙」营销片写一句中文解说。"
        f"情节：「{description}」原对白（仅参考，不得照抄）：「{dialogue}」。"
        "要求：1) 不出现任何人物姓名或称呼（如虎哥、那小子等）；"
        "2) 不得复述原对白；3) 不得写人物内心活动；4) 一句话、不超过40字、有冲击力。"
        f"只输出解说正文。{extra}"
    )


def main() -> int:
    settings = get_settings()
    out_dir = ROOT / "outputs/vc003_episode_08/narration_drafts"
    out_dir.mkdir(parents=True, exist_ok=True)

    lines: list[NarrationLine] = []
    card_rows: list[dict[str, object]] = []
    for index, (event_id, evidence_id, function, description, dialogue) in enumerate(EVENTS):
        text = _llm_draft(_prompt(description, dialogue))
        violations = validate_narration_draft(text, dialogue_excerpts=(dialogue,))
        if violations:
            text = _llm_draft(_prompt(description, dialogue, violations))
            violations = validate_narration_draft(text, dialogue_excerpts=(dialogue,))
        line_id = uuid4()
        lines.append(
            NarrationLine.model_validate(
                {
                    "line_id": str(line_id),
                    "beat_id": uuid4(),
                    "text": text,
                    "function": function,
                    "story_refs": [str(event_id)],
                    "evidence_refs": [str(evidence_id)],
                    "target_duration": {"value": 5_000_000, "rate_den": 1, "rate_num": 1_000_000},
                    "dialogue_relationship": DialogueRelationship.NONE.value,
                    "rhetorical": False,
                    "locked": False,
                }
            )
        )
        card_rows.append(
            {
                "line_index": index + 1,
                "function": function,
                "draft": text,
                "violations": violations,
                "ok": not violations,
                "evidence_ref": str(evidence_id),
            }
        )
        print(f"line {index + 1} ({function}) violations={violations} draft={text[:40]}…")

    line_set = NarrationLineSet(
        creative_brief_ref=BRIEF_REF,
        rhythm_plan_ref=STORY_REF,
        lines=tuple(lines),
        estimated_duration={"value": 15_000_000, "rate_den": 1, "rate_num": 1_000_000},
    )
    engine = create_database_engine(settings.database_url)
    with engine.begin() as connection:
        repository = ArtifactRepository()
        line_set_ref = commit_contract_artifact(
            connection,
            repository,
            artifact_id=uuid4(),
            artifact_type="NarrationLineSet",
            payload=line_set,
            project_id=PROJECT_ID,
            run_id=RUN_ID,
            variant_id=None,
            trace_id=TRACE_ID,
            actor=ACTOR,
            producer_module="vc003-research-llm-narration",
            module_version="0.1.0",
            resource_profile_ref=STORY_REF,
            rights_class="internal-preview",
            inputs=(STORY_REF,),
        )
    engine.dispose()

    manifest = {
        "scope": "Episode 8 research LLM narration drafts; confidence unavailable; "
        "L1 human review required",
        "line_set_ref": line_set_ref.model_dump(mode="json", exclude_none=True),
        "lines": card_rows,
        "boundary_notes": [
            "Drafts are candidates only; final narration stays at the L1 human boundary.",
            "Rules enforced: no identity names, no verbatim dialogue repetition, "
            "no unsupported psychology.",
            "No production admission implied; research provider.",
        ],
    }
    (out_dir / "narration_drafts_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = ["# Episode 8 — LLM 解说草稿（research）", ""]
    for row in card_rows:
        badge = "✅" if row["ok"] else f"⚠️ {row['violations']}"
        md.append(f"- **L{row['line_index']}（{row['function']}）**：{row['draft']}  {badge}")
    md.append("")
    md.extend(f"- {note}" for note in manifest["boundary_notes"])
    md.append("")
    md.append("与人工批准解说对照见 State v98（威胁→交易→卡密三句）。")
    (out_dir / "narration_drafts_card.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"== card: {out_dir}/narration_drafts_card.md ==")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
