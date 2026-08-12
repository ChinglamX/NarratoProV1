from uuid import uuid4

from packages.contracts import ArtifactRef
from packages.contracts.strategy_config import StrategyProfile
from packages.strategy.config import resolve_strategy_config


def ref(kind="ConfigArtifact") -> ArtifactRef:
    return ArtifactRef.model_validate({"artifact_id": uuid4(), "version": 1, "artifact_type": kind})


def profile(kind="genre", status="experimental", hard=None, validated=()):
    return StrategyProfile.model_validate(
        {
            "profile_id": uuid4(),
            "profile_version": "1.0.0",
            "schema_version": "1.0.0",
            "kind": kind,
            "name": f"{kind}-v1",
            "applicable_scope": ["short-drama"],
            "validated_scope": validated,
            "source": "test",
            "owner": "strategy",
            "status": status,
            "hard_constraints": hard or {},
            "soft_preferences": {"pacing": "fast"},
        }
    )


def test_hard_platform_rule_overrides_genre_preference_deterministically() -> None:
    genre = profile()
    platform = profile(
        kind="platform",
        hard={"max_duration_seconds": 60},
        validated=("douyin",),
        status="approved",
    ).model_copy(update={"soft_preferences": {"pacing": "medium"}})
    resolved = resolve_strategy_config(
        approved_story_ref=ref("StoryGraph"),
        project_brief_ref=ref("ConfigArtifact"),
        profiles=((ref(), genre), (ref(), platform)),
    )
    assert not resolved.blocked
    assert next(item for item in resolved.values if item.key == "max_duration_seconds").hard
    assert resolved.canonical_json() == resolved.canonical_json()


def test_equal_priority_hard_conflict_blocks_generation() -> None:
    left = profile(kind="platform", hard={"aspect_ratio": "9:16"})
    right = profile(kind="platform", hard={"aspect_ratio": "16:9"})
    resolved = resolve_strategy_config(
        approved_story_ref=ref("StoryGraph"),
        project_brief_ref=ref(),
        profiles=((ref(), left), (ref(), right)),
    )
    assert resolved.blocked and resolved.conflicts[0].key == "aspect_ratio"
