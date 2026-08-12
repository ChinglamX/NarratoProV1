"""Deterministic strategy profile resolution; hard constraints always outrank preferences."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import JsonValue

from packages.contracts import ArtifactRef
from packages.contracts.strategy_config import (
    ConstraintSource,
    EffectiveStrategyConfig,
    ResolvedStrategyValue,
    StrategyConfigConflict,
    StrategyProfile,
)

SOURCE_PRIORITY = {
    ConstraintSource.RIGHTS_SAFETY.value: 0,
    ConstraintSource.PLATFORM.value: 1,
    ConstraintSource.PROJECT_BRIEF.value: 2,
    ConstraintSource.HUMAN_OVERRIDE.value: 3,
}


def resolve_strategy_config(
    *,
    approved_story_ref: ArtifactRef,
    project_brief_ref: ArtifactRef,
    profiles: Sequence[tuple[ArtifactRef, StrategyProfile]],
) -> EffectiveStrategyConfig:
    """Resolve exact profile versions without mutating or interpreting Story."""

    hard: dict[str, list[tuple[ArtifactRef, JsonValue, str]]] = {}
    soft: dict[str, list[tuple[ArtifactRef, JsonValue]]] = {}
    for reference, profile in profiles:
        for key, value in profile.hard_constraints.items():
            source = (
                ConstraintSource.RIGHTS_SAFETY.value
                if profile.kind.value == "brand_safety"
                else ConstraintSource.PLATFORM.value
            )
            hard.setdefault(key, []).append((reference, value, source))
        for key, value in profile.soft_preferences.items():
            soft.setdefault(key, []).append((reference, value))
    values: list[ResolvedStrategyValue] = []
    conflicts: list[StrategyConfigConflict] = []
    for key in sorted(set(hard) | set(soft)):
        hard_values = sorted(
            hard.get(key, ()),
            key=lambda item: (SOURCE_PRIORITY[item[2]], str(item[0].artifact_id)),
        )
        if hard_values:
            winning = hard_values[0]
            incompatible = [item for item in hard_values[1:] if item[1] != winning[1]]
            if incompatible and SOURCE_PRIORITY[incompatible[0][2]] == SOURCE_PRIORITY[winning[2]]:
                conflicts.append(
                    StrategyConfigConflict(
                        key=key,
                        source_refs=tuple(item[0] for item in hard_values),
                        detail="Equal-priority hard constraints disagree",
                    )
                )
                continue
            values.append(
                ResolvedStrategyValue(
                    key=key,
                    value=winning[1],
                    hard=True,
                    source=winning[2],
                    source_ref=winning[0],
                    overridden_source_refs=tuple(
                        item[0] for item in (*incompatible, *soft.get(key, ()))
                    ),
                )
            )
        elif soft.get(key):
            reference, value = sorted(soft[key], key=lambda item: str(item[0].artifact_id))[0]
            values.append(
                ResolvedStrategyValue(
                    key=key,
                    value=value,
                    hard=False,
                    source="soft_preference",
                    source_ref=reference,
                    overridden_source_refs=tuple(item[0] for item in soft[key][1:]),
                )
            )
    return EffectiveStrategyConfig(
        approved_story_ref=approved_story_ref,
        project_brief_ref=project_brief_ref,
        profile_refs=tuple(reference for reference, _ in profiles),
        values=tuple(values),
        conflicts=tuple(conflicts),
    )
