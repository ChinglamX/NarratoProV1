"""E10 provider-neutral voice, alignment, audio-mix and subtitle contracts."""

from __future__ import annotations

from enum import StrEnum
from itertools import pairwise
from typing import Annotated, Self

from pydantic import Field, model_validator

from packages.contracts.base import StrictContract
from packages.contracts.envelopes import JsonObject
from packages.contracts.foundation import UUID, ArtifactRef, RationalTime, StableName, TimeRange
from packages.contracts.rights import RightsMetadata


class TakeDisposition(StrEnum):
    CANDIDATE = "candidate"
    SELECTED = "selected"
    REJECTED = "rejected"
    UNAVAILABLE = "unavailable"


class VoiceTake(StrictContract):
    take_id: UUID
    narration_line_id: UUID
    raw_response_ref: ArtifactRef
    audio_blob_ref: StableName | None = None
    duration: RationalTime | None = None
    provider_id: StableName
    provider_version: StableName
    voice_id: StableName
    pronunciation_findings: tuple[StableName, ...] = ()
    qc_findings: tuple[StableName, ...] = ()
    disposition: TakeDisposition
    estimated_cost_micros: Annotated[int, Field(ge=0)]

    @model_validator(mode="after")
    def require_selected_audio(self) -> Self:
        if self.disposition is TakeDisposition.SELECTED and (
            self.audio_blob_ref is None or self.duration is None or self.duration.value <= 0
        ):
            raise ValueError("selected voice take requires committed audio and positive duration")
        if self.disposition is TakeDisposition.UNAVAILABLE and self.audio_blob_ref is not None:
            raise ValueError("unavailable voice take cannot carry audio")
        return self


class VoiceTakeSet(StrictContract):
    narration_line_set_ref: ArtifactRef
    voice_profile_ref: ArtifactRef
    takes: tuple[VoiceTake, ...]
    max_takes_per_line: Annotated[int, Field(ge=1, le=10)]
    incomplete: bool = False

    @model_validator(mode="after")
    def enforce_bounded_unique_takes(self) -> Self:
        ids = [take.take_id for take in self.takes]
        if len(ids) != len(set(ids)):
            raise ValueError("voice take ids must be unique")
        counts: dict[UUID, int] = {}
        for take in self.takes:
            counts[take.narration_line_id] = counts.get(take.narration_line_id, 0) + 1
        if any(count > self.max_takes_per_line for count in counts.values()):
            raise ValueError("voice take budget exceeded")
        return self


class VoiceAsset(StrictContract):
    voice_take_set_ref: ArtifactRef
    selected_take_ids: tuple[UUID, ...]
    audio_blob_ref: StableName
    duration: RationalTime
    checksum: StableName
    rights: RightsMetadata

    @model_validator(mode="after")
    def require_selected_voice(self) -> Self:
        if not self.selected_take_ids or self.duration.value <= 0:
            raise ValueError("voice asset requires selected takes and positive duration")
        return self


class AlignmentToken(StrictContract):
    token: Annotated[str, Field(min_length=1, max_length=256)]
    line_id: UUID
    timeline_range: TimeRange
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] | None = None


class AlignmentArtifact(StrictContract):
    voice_asset_ref: ArtifactRef
    narration_line_set_ref: ArtifactRef
    tokens: tuple[AlignmentToken, ...]
    alignment_method: StableName
    unresolved_line_ids: tuple[UUID, ...] = ()


class AudioRole(StrEnum):
    ORIGINAL = "original"
    NARRATION = "narration"
    BGM = "bgm"
    SFX = "sfx"


class AudioAssetSelection(StrictContract):
    asset_ref: ArtifactRef
    role: AudioRole
    source_range: TimeRange | None = None
    rights: RightsMetadata
    rationale: Annotated[str, Field(min_length=1, max_length=2_048)]


class MixStem(StrictContract):
    role: AudioRole
    source_ref: ArtifactRef
    timeline_range: TimeRange
    gain_db: Annotated[float, Field(ge=-60.0, le=24.0)] = 0.0
    duck_under_narration_db: Annotated[float, Field(ge=-60.0, le=0.0)] | None = None


class MixPlan(StrictContract):
    conformed_timeline_ref: ArtifactRef
    stems: tuple[MixStem, ...]
    target_loudness_lufs: Annotated[float, Field(ge=-40.0, le=-5.0)]
    true_peak_ceiling_dbtp: Annotated[float, Field(ge=-12.0, le=0.0)]
    measurement_profile_ref: ArtifactRef
    unresolved_findings: tuple[StableName, ...] = ()

    @model_validator(mode="after")
    def require_narration_and_ducking(self) -> Self:
        roles = {stem.role for stem in self.stems}
        if AudioRole.NARRATION not in roles:
            raise ValueError("mix plan requires narration stem")
        if AudioRole.BGM in roles and not any(
            stem.role is AudioRole.BGM and stem.duck_under_narration_db is not None
            for stem in self.stems
        ):
            raise ValueError("BGM requires explicit narration ducking")
        return self


class MixedAudio(StrictContract):
    mix_plan_ref: ArtifactRef
    audio_blob_ref: StableName
    duration: RationalTime
    integrated_loudness_lufs: float
    true_peak_dbtp: float
    qc_findings: tuple[StableName, ...] = ()


class SubtitleCue(StrictContract):
    cue_id: UUID
    line_id: UUID | None = None
    timeline_range: TimeRange
    text: Annotated[str, Field(min_length=1, max_length=1_024)]
    highlighted_ranges: tuple[
        tuple[Annotated[int, Field(ge=0)], Annotated[int, Field(ge=0)]], ...
    ] = ()
    style_ref: StableName
    safe_area: JsonObject

    @model_validator(mode="after")
    def validate_highlights(self) -> Self:
        if self.timeline_range.is_empty:
            raise ValueError("subtitle cue duration must be positive")
        if any(start >= end or end > len(self.text) for start, end in self.highlighted_ranges):
            raise ValueError("subtitle highlight must be inside cue text")
        return self


class SubtitleCueSet(StrictContract):
    alignment_ref: ArtifactRef
    cues: tuple[SubtitleCue, ...]
    style_profile_ref: ArtifactRef
    collision_findings: tuple[StableName, ...] = ()

    @model_validator(mode="after")
    def require_unique_nonoverlapping_cues(self) -> Self:
        if len({cue.cue_id for cue in self.cues}) != len(self.cues):
            raise ValueError("subtitle cue ids must be unique")
        ordered = sorted(self.cues, key=lambda cue: cue.timeline_range.start.seconds)
        if any(
            left.timeline_range.end_seconds > right.timeline_range.start.seconds
            for left, right in pairwise(ordered)
        ):
            raise ValueError("subtitle cues cannot overlap on the primary layer")
        return self


class ASSArtifact(StrictContract):
    subtitle_cue_set_ref: ArtifactRef
    blob_ref: StableName
    checksum: StableName
    libass_profile_ref: ArtifactRef
    render_findings: tuple[StableName, ...] = ()


class ConformReport(StrictContract):
    source_timeline_ref: ArtifactRef
    conformed_timeline_ref: ArtifactRef
    voice_asset_ref: ArtifactRef
    alignment_ref: ArtifactRef
    changed_item_ids: tuple[UUID, ...]
    invalidated_artifact_refs: tuple[ArtifactRef, ...]
    duration_delta: RationalTime
    unresolved_conflicts: tuple[StableName, ...] = ()
