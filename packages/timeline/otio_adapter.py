"""OpenTimelineIO 0.18 adapter with explicit private-metadata loss reporting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import opentimelineio as otio  # type: ignore[import-untyped]
from pydantic import ValidationError

from packages.contracts import MasterTimeline, TimelineItem, TimelineItemType

NAMESPACE = "com.narratopro.v1"


@dataclass(frozen=True, slots=True)
class LossEntry:
    path: str
    field: str
    severity: str
    message: str


@dataclass(frozen=True, slots=True)
class LossReport:
    entries: tuple[LossEntry, ...] = ()

    @property
    def lossless(self) -> bool:
        return not self.entries


def _otio_time(value: int, rate_num: int, rate_den: int) -> otio.opentime.RationalTime:
    return otio.opentime.RationalTime(value, rate_num / rate_den)


def export_otio(timeline: MasterTimeline) -> tuple[str, LossReport]:
    root = otio.schema.Timeline(name=str(timeline.timeline_id))
    root.metadata[NAMESPACE] = {"master_timeline": timeline.model_dump(mode="json")}
    for track in timeline.tracks:
        otio_track = otio.schema.Track(name=str(track.track_id), kind=track.kind.value)
        otio_track.metadata[NAMESPACE] = {
            "track_id": str(track.track_id),
            "kind": track.kind.value,
            "order": track.order,
        }
        for item in track.items:
            duration = _otio_time(
                item.timeline_range.duration.value,
                item.timeline_range.duration.rate_num,
                item.timeline_range.duration.rate_den,
            )
            if item.item_type is TimelineItemType.CLIP:
                source_range = item.source_range
                if source_range is None or item.source_ref is None:
                    raise ValueError("clip lacks source mapping")
                child = otio.schema.Clip(
                    name=str(item.item_id),
                    media_reference=otio.schema.ExternalReference(
                        target_url=f"artifact://{item.source_ref.artifact_id}/{item.source_ref.version}"
                    ),
                    source_range=otio.opentime.TimeRange(
                        _otio_time(
                            source_range.start.value,
                            source_range.start.rate_num,
                            source_range.start.rate_den,
                        ),
                        _otio_time(
                            source_range.duration.value,
                            source_range.duration.rate_num,
                            source_range.duration.rate_den,
                        ),
                    ),
                )
            elif item.item_type is TimelineItemType.TRANSITION:
                child = otio.schema.Transition(
                    name=str(item.item_id),
                    in_offset=duration,
                    out_offset=otio.opentime.RationalTime(0, duration.rate),
                )
            else:
                child = otio.schema.Gap(
                    name=str(item.item_id),
                    source_range=otio.opentime.TimeRange(
                        otio.opentime.RationalTime(0, duration.rate), duration
                    ),
                )
            child.metadata[NAMESPACE] = {"item": item.model_dump(mode="json")}
            otio_track.append(child)
        root.tracks.append(otio_track)
    return otio.adapters.write_to_string(root, adapter_name="otio_json"), LossReport()


def import_otio(payload: str) -> tuple[MasterTimeline | None, LossReport]:
    parsed = otio.adapters.read_from_string(payload, adapter_name="otio_json")
    if not isinstance(parsed, otio.schema.Timeline):
        return None, LossReport((LossEntry("/", NAMESPACE, "error", "root is not Timeline"),))
    namespace = cast(dict[str, Any] | None, parsed.metadata.get(NAMESPACE))
    if not namespace or "master_timeline" not in namespace:
        return None, LossReport(
            (
                LossEntry(
                    "/metadata",
                    NAMESPACE,
                    "error",
                    "NarratoPro master metadata is missing; import cannot overwrite "
                    "canonical timeline",
                ),
            )
        )
    losses: list[LossEntry] = []
    for track_index, track in enumerate(parsed.tracks):
        for item_index, item in enumerate(track):
            private = cast(dict[str, Any] | None, item.metadata.get(NAMESPACE))
            if not private or "item" not in private:
                losses.append(
                    LossEntry(
                        f"/tracks/{track_index}/children/{item_index}",
                        NAMESPACE,
                        "error",
                        "item identity/evidence metadata is missing",
                    )
                )
                continue
            try:
                TimelineItem.model_validate(private["item"])
            except ValidationError:
                losses.append(
                    LossEntry(
                        f"/tracks/{track_index}/children/{item_index}",
                        "item",
                        "error",
                        "item metadata is invalid",
                    )
                )
    try:
        timeline = MasterTimeline.model_validate(namespace["master_timeline"])
    except ValidationError:
        return None, LossReport(
            (*losses, LossEntry("/metadata", "master_timeline", "error", "metadata is invalid"))
        )
    return timeline, LossReport(tuple(losses))
