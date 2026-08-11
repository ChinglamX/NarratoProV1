"""Deterministic Timeline-to-RenderPlan compiler port."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from packages.contracts import ArtifactRef, MasterTimeline, TimelineItemType


@dataclass(frozen=True, slots=True)
class RenderPlan:
    timeline_ref: ArtifactRef
    profile_ref: ArtifactRef
    toolchain_version: str
    operations: tuple[dict[str, Any], ...]
    checksum: str


def compile_render_plan(
    timeline: MasterTimeline,
    *,
    timeline_ref: ArtifactRef,
    profile_ref: ArtifactRef,
    toolchain_version: str,
) -> RenderPlan:
    operations: list[dict[str, Any]] = []
    for track in sorted(timeline.tracks, key=lambda item: item.order):
        for item in track.items:
            operations.append(
                {
                    "item_id": str(item.item_id),
                    "track": track.kind.value,
                    "type": item.item_type.value,
                    "start": item.timeline_range.start.model_dump(mode="json"),
                    "duration": item.timeline_range.duration.model_dump(mode="json"),
                    "source_ref": (
                        item.source_ref.model_dump(mode="json")
                        if item.item_type is TimelineItemType.CLIP and item.source_ref
                        else None
                    ),
                    "source_range": (
                        item.source_range.model_dump(mode="json") if item.source_range else None
                    ),
                    "parameters": item.parameters,
                }
            )
    identity = {
        "timeline_ref": timeline_ref.model_dump(mode="json"),
        "profile_ref": profile_ref.model_dump(mode="json"),
        "toolchain_version": toolchain_version,
        "operations": operations,
    }
    encoded = json.dumps(
        identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode()
    return RenderPlan(
        timeline_ref,
        profile_ref,
        toolchain_version,
        tuple(operations),
        "sha256:" + sha256(encoded).hexdigest(),
    )
