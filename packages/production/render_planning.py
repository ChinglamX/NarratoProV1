"""Deterministic E11 render plan construction from E10 products.

Compiles an approved MasterTimeline + MixPlan + ASS into a RenderPlanContract:
trim each video clip to its source range, concat, burn the ASS subtitle track,
mix the audio stems and mux into the final container. Every operation carries
exact refs and a deterministic cache key; the plan checksum is derived from the
canonical operation set so identical inputs produce identical plans.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from packages.contracts import ArtifactRef, MasterTimeline, RenderOperation, RenderPlanContract
from packages.contracts.media_production import MixPlan
from packages.contracts.render_release import RenderMode
from packages.contracts.timeline import TimelineItem, TimelineTrackKind

TOOLCHAIN = "ffmpeg-8.1.2"


def _det_uuid(key: str) -> UUID:
    raw = bytearray(hashlib.sha256(key.encode()).digest()[:16])
    raw[6] = (raw[6] & 0x0F) | 0x40
    raw[8] = (raw[8] & 0x3F) | 0x80
    return UUID(bytes=bytes(raw))


def _track_items(timeline: MasterTimeline, kind: TimelineTrackKind) -> Sequence[TimelineItem]:
    for track in timeline.tracks:
        if track.kind is kind:
            return track.items
    return ()


def _clip_operations(timeline: MasterTimeline) -> tuple[RenderOperation, ...]:
    operations: list[RenderOperation] = []
    for index, item in enumerate(_track_items(timeline, TimelineTrackKind.VIDEO)):
        if item.source_ref is None or item.source_range is None:
            continue
        parameters: dict[str, Any] = {
            "filter": (
                f"scale={item.parameters.get('target_width', 720)}:"
                f"{item.parameters.get('target_height', 1280)}:"
                "force_original_aspect_ratio=decrease,"
                "pad=720:1280:(ow-iw)/2:(oh-ih)/2"
            ),
            "source_start_us": int(item.source_range.start.seconds * 1_000_000),
            "source_duration_us": int(item.source_range.duration.seconds * 1_000_000),
        }
        cache_key = f"trim:{index}:{item.source_ref.artifact_id}:{item.item_version}"
        operations.append(
            RenderOperation(
                operation_id=_det_uuid(cache_key),
                operation_type="trim-clip",
                input_refs=(item.source_ref,),
                parameters=parameters,
                cache_key=cache_key,
            )
        )
    return tuple(operations)


def _subtitle_operation(ass_ref: ArtifactRef, timeline: MasterTimeline) -> RenderOperation:
    cache_key = f"ass:{ass_ref.artifact_id}:{ass_ref.version}"
    return RenderOperation(
        operation_id=_det_uuid(cache_key),
        operation_type="burn-ass",
        input_refs=(ass_ref,),
        parameters={"filter": "subtitles=ass"},  # resolved at execution with real path
        cache_key=cache_key,
    )


def _audio_operation(mix_plan: MixPlan) -> RenderOperation:
    cache_key = f"mix:{mix_plan.target_loudness_lufs}:{mix_plan.true_peak_ceiling_dbtp}"
    return RenderOperation(
        operation_id=_det_uuid(cache_key),
        operation_type="mix-audio",
        input_refs=tuple(stem.source_ref for stem in mix_plan.stems),
        parameters={
            "target_loudness_lufs": mix_plan.target_loudness_lufs,
            "true_peak_ceiling_dbtp": mix_plan.true_peak_ceiling_dbtp,
        },
        cache_key=cache_key,
    )


def _mux_operation(timeline: MasterTimeline, mode: RenderMode) -> RenderOperation:
    cache_key = f"mux:{mode.value}:{timeline.duration.seconds}"
    return RenderOperation(
        operation_id=_det_uuid(cache_key),
        operation_type="mux-final",
        input_refs=(),
        parameters={"container": "mp4", "mode": mode.value},
        cache_key=cache_key,
    )


def _plan_checksum(operations: tuple[RenderOperation, ...]) -> str:
    payload = []
    for op in operations:
        dumped = op.model_dump(mode="json")
        dumped.pop("operation_id", None)
        payload.append(dumped)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


def plan_render_contract(
    *,
    timeline: MasterTimeline,
    timeline_ref: ArtifactRef,
    mix_plan_ref: ArtifactRef,
    mix_plan: MixPlan,
    ass_ref: ArtifactRef,
    platform_profile_ref: ArtifactRef,
    mode: RenderMode = RenderMode.PROXY,
) -> RenderPlanContract:
    operations = (
        *_clip_operations(timeline),
        _subtitle_operation(ass_ref, timeline),
        _audio_operation(mix_plan),
        _mux_operation(timeline, mode),
    )
    return RenderPlanContract(
        conformed_timeline_ref=timeline_ref,
        mixed_audio_ref=mix_plan_ref,
        ass_artifact_ref=ass_ref,
        platform_profile_ref=platform_profile_ref,
        toolchain_version=TOOLCHAIN,
        mode=mode,
        operations=operations,
        expected_duration=timeline.duration,
        output_spec={"container": "mp4", "mode": mode.value},
        checksum=_plan_checksum(operations),
    )
