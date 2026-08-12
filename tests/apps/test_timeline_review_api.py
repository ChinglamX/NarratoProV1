from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

from apps.api import reviews as api
from packages.contracts import ArtifactRef
from packages.contracts.timeline_intent import TimelineReviewPackage


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=kind)


def package() -> TimelineReviewPackage:
    return TimelineReviewPackage(
        master_timeline_ref=ref("MasterTimeline"),
        preview_ref=ref("ProxyRender"),
        creative_brief_ref=ref("CreativeBrief"),
        approved_story_ref=ref("StoryGraph"),
        platform_profile_ref=ref("ConfigArtifact"),
        visual_planning_report_ref=ref("QualityReview"),
        narration_planning_report_ref=ref("QualityReview"),
        assembly_report_ref=ref("QualityReview"),
    )


class FakeReviewRepository:
    def __init__(self) -> None:
        self.created: dict[str, object] | None = None

    def create_request(self, _connection: object, **kwargs: object) -> None:
        self.created = kwargs

    def publication_ref(self, _connection: object, **_kwargs: object) -> dict[str, object]:
        return ref("MasterTimeline").model_dump(mode="json")

    def snapshot(self, _connection: object, **_kwargs: object):
        return self.snapshot_value

    snapshot_value = None


def test_timeline_checkpoint_uses_candidate_intent_not_mutable_ui_state(monkeypatch) -> None:
    repository = FakeReviewRepository()
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(database_engine=object(), review_repository=repository)
        )
    )

    @contextmanager
    def tx(_engine: object):
        yield object()

    monkeypatch.setattr(api, "transaction", tx)
    body = api.TimelineReviewRequestBody(
        review_id=uuid4(), project_id=uuid4(), workflow_id="timeline:1", package=package()
    )
    response = api.create_timeline_review(body, request)
    assert response["gate"] == "timeline"
    assert repository.created is not None
    assert repository.created["target_ref"] == body.package.master_timeline_ref.model_dump(
        mode="json"
    )


def test_timeline_workspace_loads_exact_review_package(monkeypatch) -> None:
    review_package = package()
    review_id = uuid4()
    project_id = uuid4()
    repository = FakeReviewRepository()
    repository.snapshot_value = SimpleNamespace(
        review_id=review_id,
        project_id=project_id,
        gate="timeline",
        state="awaiting_review",
        target_ref=review_package.master_timeline_ref.model_dump(mode="json"),
        policy_snapshot={
            "automation_level": "L1",
            "timeline_review_package": review_package.model_dump(mode="json"),
        },
    )
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                database_engine=SimpleNamespace(connect=lambda: connection()),
                review_repository=repository,
            )
        )
    )

    @contextmanager
    def connection():
        yield object()

    response = api.get_timeline_review(review_id, request)
    assert response.review_id == review_id
    assert response.target_version == review_package.master_timeline_ref.version
    assert response.package == review_package
