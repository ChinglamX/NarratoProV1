"""Long-form multi-episode planning built on NarratoPro's existing production core."""

from packages.longform.canonical_adapter import (
    CanonicalTimelineInputs,
    project_to_canonical_timeline_inputs,
)
from packages.longform.clip_planning import CandidateShot, ChapterClipPlan, plan_chapter_clips
from packages.longform.inventory import MediaInventory, build_media_inventory
from packages.longform.planning import (
    ChapterBlueprint,
    MarketingArcCandidate,
    build_chapter_blueprint,
    propose_marketing_arcs,
    select_default_arc,
)
from packages.longform.review import NarrationDraft, review_longform_narration
from packages.longform.story_index import (
    SeriesEvent,
    SeriesStoryIndex,
    build_series_story_index,
)
from packages.longform.transcript_localization import LocalizedCue, localize_cue, parse_srt
from packages.longform.understanding import (
    EventProposal,
    TranscriptSegment,
    VisualObservation,
    compile_event_proposals,
)

__all__ = [
    "CandidateShot",
    "CanonicalTimelineInputs",
    "ChapterBlueprint",
    "ChapterClipPlan",
    "EventProposal",
    "LocalizedCue",
    "MarketingArcCandidate",
    "MediaInventory",
    "NarrationDraft",
    "SeriesEvent",
    "SeriesStoryIndex",
    "TranscriptSegment",
    "VisualObservation",
    "build_chapter_blueprint",
    "build_media_inventory",
    "build_series_story_index",
    "compile_event_proposals",
    "localize_cue",
    "parse_srt",
    "plan_chapter_clips",
    "project_to_canonical_timeline_inputs",
    "propose_marketing_arcs",
    "review_longform_narration",
    "select_default_arc",
]
