"""Master Timeline domain."""

from packages.timeline.compiler import RenderPlan, compile_render_plan
from packages.timeline.otio_adapter import LossEntry, LossReport, export_otio, import_otio
from packages.timeline.patches import (
    TimelineChange,
    TimelinePatchConflict,
    apply_patch,
    can_rebase,
    semantic_diff,
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
    "RenderPlan",
    "TimelineChange",
    "TimelinePatchConflict",
    "ValidationIssue",
    "ValidationReport",
    "ValidationSeverity",
    "VisualPlanningPolicy",
    "analyze_continuity",
    "apply_patch",
    "can_rebase",
    "choose_source_subtitle_policy",
    "compile_render_plan",
    "export_otio",
    "import_otio",
    "local_recompute_scope",
    "plan_clip_sequence",
    "retrieve_candidates",
    "semantic_diff",
    "solve_crop_path",
    "validate_timeline",
]
