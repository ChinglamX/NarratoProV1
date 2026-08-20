"""Approve the exact Episode 8 VC-003 Gate 2 strategy selection.

The Gate 2 Review `7734969e-1caa-4a3c-9831-a43c66798cd3` already exists in
``awaiting_review`` state with its StrategyReviewPackage persisted. This script
only decides the existing review (L1 human project owner, Option 1 "威胁倒叙"),
publishes the ``approved_creative_brief`` / ``approved_variant_plan`` pointers in
the same transaction, verifies them, and writes the approval manifest.

Do NOT rerun ``scripts/prepare_vc003_gate2.py`` or ``scripts/approve_vc002_gate1.py``.
"""

# ruff: noqa: RUF001 - Chinese punctuation is intentional in review copy.

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from packages.contracts import (
    ArtifactRef,
    StrategyGateSelection,
)
from packages.foundation.settings import get_settings
from packages.persistence import ArtifactRepository
from packages.persistence.database import create_database_engine
from packages.persistence.review_repository import ReviewRepository

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = UUID("dd397853-79bc-4e6f-a540-bb1c296d6936")
REVIEW_ID = UUID("7734969e-1caa-4a3c-9831-a43c66798cd3")
TRACE_ID = "8e004000000000000000000000000004"

COMPARISON_REF = ArtifactRef.model_validate(
    {
        "artifact_id": "164a0d02-c265-4c3d-bbed-5af2ef52fc9e",
        "version": 1,
        "artifact_type": "StrategyComparisonPackage",
        "checksum": "sha256:480e62304271057e0184c0eb972d6a3a95abe99fc7a13fae222757285dc0671a",
    }
)
STORY_REF = ArtifactRef.model_validate(
    {
        "artifact_id": "c378ba51-da33-4049-baf0-538ca637e9a5",
        "version": 1,
        "artifact_type": "StoryGraph",
        "checksum": "sha256:8b34ae0d15d81126a1907366e27efcb4ce113e5bea0e1d2fae0ec146d0c7aad2",
    }
)
# Option 1 "威胁倒叙" (project owner decision, 2026-08-19).
STRATEGY_ID = UUID("82f2cdc4-bdf6-4e91-915c-c3e04fd95a3b")
HOOK_ID = UUID("9cddcf54-e497-4db0-b516-b59eb6e25786")
BRIEF_REF = ArtifactRef.model_validate(
    {
        "artifact_id": "bc2c693e-8768-40fc-84d5-fcc00946f80a",
        "version": 1,
        "artifact_type": "CreativeBrief",
        "checksum": "sha256:a20c2f1639d5ceb3ce2772dbc3b98d97e14830400b9b0e48d3de73ee8f38e0e8",
    }
)
VARIANT_REF = ArtifactRef.model_validate(
    {
        "artifact_id": "58a7c392-64f3-4d81-b1df-fbcfedb10c1b",
        "version": 1,
        "artifact_type": "VariantPlan",
        "checksum": "sha256:c337552207507ddd7f49a0c413b25c5ef45e3699868c48a0acdf8e5991d968bd",
    }
)


def main() -> int:
    engine = create_database_engine(get_settings().database_url)
    artifacts, reviews = ArtifactRepository(), ReviewRepository()

    with engine.connect() as connection:
        snapshot = reviews.snapshot(connection, review_id=REVIEW_ID)
        if snapshot is None:
            raise RuntimeError("Gate 2 review does not exist")
        if snapshot.state != "awaiting_review":
            raise RuntimeError(f"Gate 2 review is not awaiting_review: {snapshot.state}")
        if snapshot.target_ref.get("version") != 1:
            raise RuntimeError("Gate 2 review target version is not 1")
        if str(snapshot.target_ref.get("artifact_id")) != str(COMPARISON_REF.artifact_id):
            raise RuntimeError("Gate 2 review target comparison mismatch")
        package = snapshot.policy_snapshot.get("strategy_review_package", {})
        if package.get("incomplete"):
            raise RuntimeError("strategy review package is incomplete")
        allowed_strategy_ids = {str(item) for item in package.get("allowed_strategy_ids", [])}
        allowed_hook_ids = {str(item) for item in package.get("allowed_hook_ids", [])}
        blocker_ids = {str(item) for item in package.get("blocker_candidate_ids", [])}
        if str(STRATEGY_ID) not in allowed_strategy_ids:
            raise RuntimeError("selected strategy is not in the review package")
        if str(HOOK_ID) not in allowed_hook_ids:
            raise RuntimeError("selected hook is not in the review package")
        if str(STRATEGY_ID) in blocker_ids:
            raise RuntimeError("selected strategy is blocked")
        if BRIEF_REF.model_dump(mode="json") not in package.get("candidate_brief_refs", []):
            raise RuntimeError("selected CreativeBrief is outside the review package")
        if VARIANT_REF.model_dump(mode="json") not in package.get(
            "candidate_variant_plan_refs", []
        ):
            raise RuntimeError("selected VariantPlan is outside the review package")
        # Verify the selected Brief/Variant artifacts persist with exact checksums.
        brief_row = artifacts.get_version(connection, BRIEF_REF)
        variant_row = artifacts.get_version(connection, VARIANT_REF)
        if brief_row["checksum"] != str(BRIEF_REF.checksum):
            raise RuntimeError("selected CreativeBrief checksum drift")
        if variant_row["checksum"] != str(VARIANT_REF.checksum):
            raise RuntimeError("selected VariantPlan checksum drift")

    selection = StrategyGateSelection(
        selected_strategy_id=STRATEGY_ID,
        selected_hook_id=HOOK_ID,
        creative_brief_ref=BRIEF_REF,
        variant_plan_ref=VARIANT_REF,
    )
    with engine.begin() as connection:
        decision = reviews.decide(
            connection,
            review_id=REVIEW_ID,
            expected_target_version=1,
            decision="approve",
            reviewer_snapshot={
                "actor_id": "project-owner",
                "roles": ["reviewer"],
                "service_account": False,
            },
            reasons=[
                {
                    "code": "project-owner-approved-gate-2",
                    "detail": (
                        "Project owner selected Option 1 威胁倒叙 after reviewing the "
                        "three VC-003 Episode 8 candidates."
                    ),
                }
            ],
            strategy_selection=selection.model_dump(mode="json"),
            trace_id=TRACE_ID,
        )
        brief_pointer = reviews.approved_strategy_ref(
            connection, project_id=PROJECT_ID, registry_type="approved_creative_brief"
        )
        variant_pointer = reviews.approved_strategy_ref(
            connection, project_id=PROJECT_ID, registry_type="approved_variant_plan"
        )
        if (
            brief_pointer is None
            or str(brief_pointer["artifact_id"]) != str(BRIEF_REF.artifact_id)
            or brief_pointer["version"] != BRIEF_REF.version
            or brief_pointer["artifact_type"] != BRIEF_REF.artifact_type
        ):
            raise RuntimeError("approved CreativeBrief publication pointer mismatch")
        if (
            variant_pointer is None
            or str(variant_pointer["artifact_id"]) != str(VARIANT_REF.artifact_id)
            or variant_pointer["version"] != VARIANT_REF.version
            or variant_pointer["artifact_type"] != VARIANT_REF.artifact_type
        ):
            raise RuntimeError("approved VariantPlan publication pointer mismatch")
        after = reviews.snapshot(connection, review_id=REVIEW_ID)
        if after is None or after.state != "decided":
            raise RuntimeError("Gate 2 review did not reach decided state")

    result = {
        "review_id": str(REVIEW_ID),
        "decision_id": str(decision.decision_id),
        "decision": "approve",
        "selected_option": 1,
        "selected_label": "威胁倒叙",
        "selected_strategy_id": str(STRATEGY_ID),
        "selected_hook_id": str(HOOK_ID),
        "approved_creative_brief_ref": BRIEF_REF.model_dump(mode="json", exclude_none=True),
        "approved_variant_plan_ref": VARIANT_REF.model_dump(mode="json", exclude_none=True),
        "approved_creative_brief_pointer": {
            "artifact_id": str(brief_pointer["artifact_id"]),
            "version": brief_pointer["version"],
            "artifact_type": brief_pointer["artifact_type"],
        },
        "approved_variant_plan_pointer": {
            "artifact_id": str(variant_pointer["artifact_id"]),
            "version": variant_pointer["version"],
            "artifact_type": variant_pointer["artifact_type"],
        },
        "comparison_ref": COMPARISON_REF.model_dump(mode="json", exclude_none=True),
        "approved_story_ref": STORY_REF.model_dump(mode="json", exclude_none=True),
        "scope": "Episode 8 strategy direction only; downstream requires approved brief.",
        "shared_risks": [
            "人物身份未证明，Brief/解说不得给角色命名。",
            "无真实发布效果数据，Hook 吸引力保持 unavailable，不以分数自动选择。",
        ],
    }
    output = ROOT / "outputs/vc003_episode_08/gate2_approval.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
