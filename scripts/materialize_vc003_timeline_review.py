"""Materialize the human-approved Episode 8 timeline as a canonical DB review.

The E09 CreativeTimelineWorkflow checkpoint was signed approve by the project
owner via the Temporal signal (run d3690d71-444a-43d9-bbd0-52bd1c91d371). This
script records that human approval in the canonical review table (gate
"timeline"), publishes the ``approved_timeline_intent`` publication pointer and
writes an approval manifest — closing the J05 DB-level integration for the
first real approved-data timeline.

The decision is already made by the project owner; this only persists it.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID, uuid4

from packages.contracts import ArtifactRef
from packages.contracts.timeline_intent import TimelineReviewPackage
from packages.foundation.settings import get_settings
from packages.persistence.database import create_database_engine
from packages.persistence.review_repository import ReviewRepository

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = UUID("dd397853-79bc-4e6f-a540-bb1c296d6936")
RUN_ID = UUID("d3690d71-444a-43d9-bbd0-52bd1c91d371")
TRACE_ID = "8e005000000000000000000000000005"


def _ref(artifact_id: str, artifact_type: str, checksum: str) -> ArtifactRef:
    return ArtifactRef.model_validate(
        {
            "artifact_id": artifact_id,
            "version": 1,
            "artifact_type": artifact_type,
            "checksum": checksum,
        }
    )


MASTER_TIMELINE = _ref(
    "c537a05d-4c0c-4b69-9f57-83c7abe9c42a",
    "MasterTimeline",
    "sha256:69115476c7eee1dd0f9e78912282c9346164f1ce7ff9a68e474a8d4bb6693c0d",
)
PREVIEW = _ref(
    "0af9efa2-0ef6-442b-95c8-8b1fcb508b65",
    "ProxyRender",
    "sha256:92cc3d06247766398d9d5534aad2324c6732da3b2a1c802ccb68ec0ebd78d3f5",
)
CREATIVE_BRIEF = _ref(
    "bc2c693e-8768-40fc-84d5-fcc00946f80a",
    "CreativeBrief",
    "sha256:a20c2f1639d5ceb3ce2772dbc3b98d97e14830400b9b0e48d3de73ee8f38e0e8",
)
APPROVED_STORY = _ref(
    "c378ba51-da33-4049-baf0-538ca637e9a5",
    "StoryGraph",
    "sha256:8b34ae0d15d81126a1907366e27efcb4ce113e5bea0e1d2fae0ec146d0c7aad2",
)
PLATFORM_PROFILE = _ref(
    "a1a985f7-8d9f-4630-a898-11cde5b149e3",
    "ResourceProfile",
    "sha256:4c8304d8e0e4363d21fe4d15e09bfab6f575ad2e871cd983b326712eb44fb1f6",
)
VISUAL_REPORT = _ref(
    "f35af866-0b88-49c6-8d8e-be90ae995d1a",
    "VisualPlanningReport",
    "sha256:74e54021c2d071ebda671b1e6b8ab9f180b146da45b9a9fd2bee5b03c66d7be1",
)
NARRATION_REPORT = _ref(
    "c7a98afe-d061-4915-98aa-b8ce6bb40d64",
    "NarrationPlanningReport",
    "sha256:7f22d7e97bd00b86867c0bce183075dba745cd5f6dd6cace03825c397e9ab4cb",
)
ASSEMBLY_REPORT = _ref(
    "6cab851d-d199-4893-9383-95f040a538e3",
    "TimelineAssemblyReport",
    "sha256:331a2828f7f1f31e8866daf0f8d3e534d949d8be17214d01e90be9460840658f",
)


def main() -> int:
    engine = create_database_engine(get_settings().database_url)
    reviews = ReviewRepository()
    package = TimelineReviewPackage(
        master_timeline_ref=MASTER_TIMELINE,
        preview_ref=PREVIEW,
        creative_brief_ref=CREATIVE_BRIEF,
        approved_story_ref=APPROVED_STORY,
        platform_profile_ref=PLATFORM_PROFILE,
        visual_planning_report_ref=VISUAL_REPORT,
        narration_planning_report_ref=NARRATION_REPORT,
        assembly_report_ref=ASSEMBLY_REPORT,
        blocker_codes=(),
        accepted_risk_codes=("reverse-chronology-approved-by-gate-2",),
    )
    review_id = uuid4()
    with engine.begin() as connection:
        reviews.create_request(
            connection,
            review_id=review_id,
            project_id=PROJECT_ID,
            workflow_id=f"vc003-e08-timeline/{RUN_ID}",
            gate="timeline",
            target_ref=MASTER_TIMELINE.model_dump(mode="json"),
            policy_snapshot={
                "automation_level": "L1",
                "timeline_review_package": package.model_dump(mode="json"),
            },
        )
        decision = reviews.decide(
            connection,
            review_id=review_id,
            expected_target_version=1,
            decision="approve",
            reviewer_snapshot={
                "actor_id": "project-owner",
                "roles": ["reviewer"],
                "service_account": False,
            },
            reasons=[
                {
                    "code": "project-owner-approved-timeline-checkpoint",
                    "detail": (
                        "Project owner approved the Episode 8 timeline v2 (26.00s, "
                        "威胁倒叙, threat 42-50s) at the E09 checkpoint."
                    ),
                }
            ],
            trace_id=TRACE_ID,
        )
        pointer = reviews.publication_ref(
            connection,
            project_id=PROJECT_ID,
            registry_type="approved_timeline_intent",
            artifact_type="MasterTimeline",
        )
        if (
            pointer is None
            or str(pointer["artifact_id"]) != str(MASTER_TIMELINE.artifact_id)
            or pointer["version"] != MASTER_TIMELINE.version
        ):
            raise RuntimeError("approved_timeline_intent publication pointer mismatch")
        snapshot = reviews.snapshot(connection, review_id=review_id)
        if snapshot is None or snapshot.state != "decided":
            raise RuntimeError("timeline review did not reach decided state")

    result = {
        "review_id": str(review_id),
        "decision_id": str(decision.decision_id),
        "decision": "approve",
        "run_id": str(RUN_ID),
        "approved_timeline_intent": MASTER_TIMELINE.model_dump(mode="json", exclude_none=True),
        "publication_pointer": {
            "artifact_id": str(pointer["artifact_id"]),
            "version": pointer["version"],
            "artifact_type": pointer["artifact_type"],
        },
        "package": package.model_dump(mode="json"),
    }
    output = ROOT / "outputs/vc003_episode_08/timeline/timeline_approval.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
