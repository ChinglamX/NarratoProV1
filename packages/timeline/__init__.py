"""Master Timeline domain."""

from packages.timeline.compiler import RenderPlan, compile_render_plan
from packages.timeline.multitrack import TimelineAssemblyError, assemble_multitrack_timeline
from packages.timeline.narration import NarrationSourcePort, NarrationSourceUnavailable
from packages.timeline.otio_adapter import LossEntry, LossReport, export_otio, import_otio
from packages.timeline.patches import (
    TimelineChange,
    TimelinePatchConflict,
    apply_patch,
    can_rebase,
    semantic_diff,
)
from packages.timeline.revisions import (
    RevisionEntry,
    RevisionHistory,
    RevisionHistoryError,
    build_history_from_versions,
)
from packages.timeline.rhythm_narration import (
    allocate_rhythm,
    replace_lines_in_scope,
    review_narration,
)
from packages.timeline.validator import (
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
    validate_timeline,
)
from packages.timeline.visual_planning import (
    ClipIndexPort,
    VisualPlanningPolicy,
    analyze_continuity,
    choose_source_subtitle_policy,
    local_recompute_scope,
    plan_clip_sequence,
    retrieve_candidates,
    solve_crop_path,
)

__all__ = [
    "ClipIndexPort",
    "LossEntry",
    "LossReport",
    "NarrationSourcePort",
    "NarrationSourceUnavailable",
    "RenderPlan",
    "RevisionEntry",
    "RevisionHistory",
    "RevisionHistoryError",
    "TimelineAssemblyError",
    "TimelineChange",
    "TimelinePatchConflict",
    "ValidationIssue",
    "ValidationReport",
    "ValidationSeverity",
    "VisualPlanningPolicy",
    "allocate_rhythm",
    "analyze_continuity",
    "apply_patch",
    "assemble_multitrack_timeline",
    "build_history_from_versions",
    "can_rebase",
    "choose_source_subtitle_policy",
    "compile_render_plan",
    "export_otio",
    "import_otio",
    "local_recompute_scope",
    "plan_clip_sequence",
    "replace_lines_in_scope",
    "retrieve_candidates",
    "review_narration",
    "semantic_diff",
    "solve_crop_path",
    "validate_timeline",
]
