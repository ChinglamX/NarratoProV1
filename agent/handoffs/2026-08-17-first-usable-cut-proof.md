# First Usable Cut Product Proof Handoff

Handoff ID: first-usable-cut-proof-v1
Date / Author: 2026-08-17 / Codex
Task Type / Active Role: TYPE A / AI System Engineer

Objective: Produce the smallest inspectable personal-generation cut and keep product proof distinct from formal E10/E11 qualification.

Active Epic / Backlog ID: Product Goal — First Usable Cut across E09/E10/E11.
Starting State Version: 58

Inputs Read:

- Canonical project/agent/quality/engineering files required by AGENTS.md.
- Approved E09 30.27s preview and ASS for run d8eb4cd5.
- E10/E11 production implementation and tests.

Decisions Made:

- Render a bounded product proof now so the product owner can judge usefulness.
- Preserve formal E11 fail-closed semantics; do not call the PNG-overlay fallback a libass qualification.
- Do not expand to enhancers or scale work before the human product decision.

Files Changed:

- `packages/production/render_command.py`, `render.py` — consume real MixedAudio/ASS and fix atomic temp output.
- `workflows/production/render_activities.py`, `render_workflow.py` — resolve stored blobs and propagate truthful typed QC state.
- production render tests — regression coverage.
- `scripts/build_first_usable_cut.py` — repeatable, resume-safe product-proof builder.
- product board/cards/state — evidence and remaining boundary.

Validation Performed:

- Targeted render tests: 7 passed; Ruff and strict mypy passed.
- Full `make check`: 405 passed, 5 DB-environment skips, 80.16% coverage; all static, security, context, architecture and registry checks passed.
- Output probe: 30.28s, 720×1280 H.264, AAC 48kHz stereo.
- Audio: mean -21.2 dB, max -2.3 dB, no silence ≥1s at -45dB.
- Frames at 1/5/15/27s inspected; caption overflow found, fixed with safe-width wrapping, then re-inspected.

Completed:

- Four real narration WAVs and checksums.
- Inspectable mixed, captioned MP4 and manifest.
- Three identified E11 code defects fixed and regression-tested.

Human Review Result:

- v1: `useful_with_revision`; voice, mix and captions passed, narration was too sparse.
- v2: `useful`; seven narration beats passed product-owner review.

Not Completed:

- Canonical VoiceAsset, Alignment, Conform and MixedAudio Artifact success path.
- Formal libass-enabled E11 Temporal success/qualification.

Workspace State:

- Changes are uncommitted; existing shared-branch commit was preserved.
- Generated evidence is under `outputs/first_usable_cut/`.

Risks / Blockers / Open Decisions:

- IndexTTS exited during consecutive synthesis and required restart; reliability is unqualified.
- Local FFmpeg lacks libass; product proof uses deterministic PNG overlays.
- Product effect is positively validated for this sample; generalization to other episodes remains unknown.

Next Exact Step:

- Migrate the approved v2 parameters into canonical E10 Artifacts and run one libass-enabled E11 workflow success path.

Project State Update: State v61.
