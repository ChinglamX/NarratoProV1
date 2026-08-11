"""Stateless Master Timeline validation beyond transport-contract invariants."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from itertools import pairwise
from uuid import UUID

from packages.contracts import MasterTimeline, TimelineItemType, TimelineTrackKind, TimeRange


class ValidationSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    severity: ValidationSeverity
    message: str
    item_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ValidationReport:
    issues: tuple[ValidationIssue, ...]

    @property
    def render_ready(self) -> bool:
        return not any(issue.severity is ValidationSeverity.ERROR for issue in self.issues)


def validate_timeline(
    timeline: MasterTimeline,
    *,
    source_availability: Mapping[str, TimeRange] | None = None,
    target_duration: Fraction | None = None,
) -> ValidationReport:
    issues: list[ValidationIssue] = []
    availability = source_availability or {}
    non_overlap_kinds = {
        TimelineTrackKind.VIDEO,
        TimelineTrackKind.ORIGINAL_AUDIO,
        TimelineTrackKind.NARRATION,
        TimelineTrackKind.BGM,
        TimelineTrackKind.SFX,
    }
    for track in timeline.tracks:
        ordered = sorted(track.items, key=lambda item: item.timeline_range.start.seconds)
        if tuple(ordered) != track.items:
            issues.append(
                ValidationIssue(
                    "track_not_sorted",
                    ValidationSeverity.ERROR,
                    f"track {track.track_id} is unsorted",
                )
            )
        if track.kind in non_overlap_kinds:
            for previous, current in pairwise(ordered):
                if previous.timeline_range.end_seconds > current.timeline_range.start.seconds:
                    issues.append(
                        ValidationIssue(
                            "item_overlap",
                            ValidationSeverity.ERROR,
                            "non-overlay track items overlap",
                            current.item_id,
                        )
                    )
        for item in track.items:
            if item.item_type in {TimelineItemType.TEXT, TimelineItemType.EFFECT} and not (
                item.content_ref or item.parameters
            ):
                issues.append(
                    ValidationIssue(
                        "empty_creative_item",
                        ValidationSeverity.WARNING,
                        "text/effect item has no content or parameters",
                        item.item_id,
                    )
                )
            if item.source_ref is not None and item.source_range is not None:
                available = availability.get(str(item.source_ref.artifact_id))
                if available is None:
                    issues.append(
                        ValidationIssue(
                            "source_availability_unknown",
                            ValidationSeverity.WARNING,
                            "source availability was not supplied",
                            item.item_id,
                        )
                    )
                elif (
                    item.source_range.start.seconds < available.start.seconds
                    or item.source_range.end_seconds > available.end_seconds
                ):
                    issues.append(
                        ValidationIssue(
                            "source_range_out_of_bounds",
                            ValidationSeverity.ERROR,
                            "source range exceeds available media",
                            item.item_id,
                        )
                    )
    if target_duration is not None and timeline.duration.seconds != target_duration:
        issues.append(
            ValidationIssue(
                "target_duration_mismatch",
                ValidationSeverity.ERROR,
                "timeline duration does not equal profile target",
            )
        )
    return ValidationReport(tuple(issues))
