# Director / Tool Capability Consolidation Checklist

Version: 1.0  
Owner: Project  
Status: Active  
Scope: E09/J03–J04 + E10/K03 director-assisted repeatability

## 1. Purpose

Prevent a director-assisted demo improvement from being reported as an automated tool capability. Every item must distinguish director decisions, tool outputs, human corrections, and release authority.

## 2. Governance and Recovery

- [x] Candidate v3 classified as `director_assisted_reference`, not automatic production proof.
- [x] VC-009 delivery/effect separated and M4 overstatement removed.
- [x] Product Board, Project State, and validation card point to the same next capability target.
- [x] Effective source/config/test changes are committed in recoverable baseline `f46854e` on `codex/director-anchor-baseline`.
- [x] Large media outputs have a committed lightweight artifact index with checksums.

## 3. Role and Decision Provenance

- [x] Every candidate production run records one `task_type` and one `active_role`.
- [x] Auxiliary roles are explicit and cannot replace the active-role decision.
- [x] Director decisions, tool outputs, manual overrides, and human corrections are separate fields.
- [x] Release Gate 3 remains human-only and is represented separately from content approval.
- [x] Role/provenance records survive handoff and clean-checkout reconstruction.

## 4. Visual–Narration Anchoring

- [x] Narration claims reference visible/audible evidence events.
- [x] Each cue has earliest/preferred/latest timing constraints rather than an unexplained absolute start.
- [x] Narration-before-evidence is rejected or explicitly overridden with reason.
- [x] Locked dialogue/original-sound regions are protected.
- [ ] Hook/payoff anchors and minimum visual comprehension durations are protected.
- [x] Unsupported ending claims are rejected or routed to director review.

## 5. TTS Reflow and Cache Correctness

- [x] Initial schedule is recomputed after measured TTS duration.
- [x] Reflow reports excessive gaps, prevents overlap, and blocks slot overflow; explicit density scoring remains deferred.
- [x] Structural conflicts return to narration/director instead of silently time-stretching.
- [x] TTS cache key includes text, reference voice, provider endpoint, and inference configuration.
- [x] Changed text cannot reuse a stale WAV under the same ordinal filename.

## 6. Verification

- [x] Deterministic unit tests cover anchor validation, reflow, role provenance, and cache keys.
- [x] Candidate v3 remains a regression fixture without hard-coding drama-specific semantics in production code.
- [x] Held-out episodes 7–8 are processed without director-authored absolute cue times.
- [x] Early spoiler violations = 0; unsupported claims = 0; locked-dialogue overlaps = 0 at machine validation.
- [x] Obvious audiovisual mismatch <= 1; manual timing overrides = 0/7; product decision=`useful`.
- [x] Product owner only reviewed the final held-out candidate at the necessary human checkpoint and returned `useful`.
- [x] Held-out episodes 7–8 use exact per-segment canonical SourceMedia refs across both source files.
- [x] Temporal Render/QC passed twice from the same config; the recovered rerun produced the identical final MP4 checksum.

## 7. Stop Conditions

Stop and request human confirmation only for:

- a material marketing-direction or story-fact decision not supported by approved evidence;
- rights/publication ambiguity;
- acceptance of the held-out final candidate;
- any proposal to change the frozen five-domain architecture or human-only Release Gate 3.
