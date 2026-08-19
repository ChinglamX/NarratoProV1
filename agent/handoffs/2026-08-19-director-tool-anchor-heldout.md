# Handoff — Director/Tool Anchor Consolidation and Held-out Candidate

Handoff ID: 2026-08-19-director-tool-anchor-heldout  
Date / Author: 2026-08-19 / Codex  
Task Type / Active Role: TYPE A / AI System Engineer（AI Drama Producer、AI Review Director 辅助）

Objective: 将 Candidate v3 中 Codex 导演判断与工具能力分离，并落实角色溯源、声画锚定、TTS 后重排、缓存正确性和 held-out 验证。  
Active Epic / Backlog ID: E09/J03–J04 + E10/K03  
Starting State Version: 80

Inputs Read:
- `PRODUCT_CONTROL_BOARD.md`
- `product/PRODUCT_CONTROL_SYSTEM.md`
- `product/MODULE_VALIDATION_CARDS.md`
- `design/stage4/05_NARRATION_ENGINEERING.md`
- `design/stage5/02_ALIGNMENT_AND_TIMELINE_CONFORM.md`
- `agent/AGENT_ROLE.md`

Decisions Made:
- Candidate v3 定位为 `director_assisted_reference`，不计自动 M4/M5。
- 不建立平行架构；声画锚定归入 E09/J03–J04，TTS 后重排归入 E10/K03。
- Codex Producer 可提供镜头、事件和解说，但 held-out 验证禁止逐句填写绝对 cue 时间。

Files Changed:
- `product/DIRECTOR_TOOL_CAPABILITY_CHECKLIST.md`: 自检闭环。
- `packages/production/director_provenance.py`: 运行角色/决策来源。
- `packages/timeline/narration_anchor.py`: evidence-gated anchor/reflow。
- `scripts/build_m5_second_cut.py`: anchor mode、post-TTS scheduling、content-addressed cache、manifest provenance。
- `product/series_main_cut_v3.json`: 自动 anchor 回归配置。
- `product/heldout_episode_7_8_anchor_validation.json`: held-out 配置。
- `product/REFERENCE_CANDIDATE_INDEX.md`: 大媒体轻量恢复索引。
- `PRODUCT_CONTROL_BOARD.md`、`PROJECT_STATE.md`、`product/MODULE_VALIDATION_CARDS.md`: 状态统一。

Validation Performed:
- `make check`: 424 passed / 5 skipped, 80.42% coverage；Ruff/mypy/Bandit/context/architecture/contracts passed。
- Candidate v3 automatic-anchor regression rendered with existing verified cache.
- Held-out candidate: 40.00s, 720x1280 H.264/AAC, mean -20.3 dB, max -2.9 dB, checksum `sha256:77b5d770d6f2123f5fbb7e35f4ed6850dee7923ce4f84fa54d572c39340cf2c2`。
- Held-out timing: 0/7 absolute manual cue starts, 0 manual overrides, 0 blocking anchor findings。

Completed:
- Governance labels, role provenance, anchor validation, post-TTS reflow, stale-cache prevention, v3 regression, held-out machine validation。

Not Completed:
- Product-owner held-out full-cut effect decision。
- Automatic visual-event, narration-text, or clip-selection generation。
- Held-out canonical E10/E11 Artifact lineage。
- Human Release Gate 3。

Workspace State:
- Branch `master`; outputs remain local and are indexed by checksum rather than committed as large media。
- Existing broader dirty worktree originated from prior E10/E11/product-control work; full `make check` passes。

Risks / Blockers / Open Decisions:
- Three non-blocking excessive-gap findings intentionally preserve picture/original sound; final listening decides whether they are useful.
- Rights restricted/internal-only; no public release.

Continuation Completed:
- Product decision recorded as `useful`.
- Episodes 7 and 8 canonically ingested as separate SourceMedia lineages.
- Multi-source canonical timeline binds every segment to its exact SourceMedia ref and retains anchor provenance.
- Temporal Render/Technical QC passed on two runs; both produced canonical MP4 checksum `sha256:e84c5d18bc4c180b95a93fbf46bca7ca39d120b6ec184e1837fa22b07eb68e5d`.
- `personal_cut.py` now exposes the same multi-source slice as one resumable six-stage status entry.

Next Exact Step:
- Completed: product owner continued after the six-stage status, so VC-008 is M5 within the approved director-input scope.
- Start VC-002 transcript-grounded Story Brief validation; do not claim automatic Story quality before side-by-side human review.

Project State Update: 85
