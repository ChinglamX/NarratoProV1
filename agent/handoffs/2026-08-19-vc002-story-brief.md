# Handoff — VC-002 Transcript-grounded Story Brief

Handoff ID: 2026-08-19-vc002-story-brief  
Date / Author: 2026-08-19 / Codex  
Task Type / Active Role: TYPE A / AI System Engineer（AI Drama Producer、AI Review Director 辅助）

Objective: 建立不允许 Host Agent 以无证据剧情摘要冒充自动 Story 能力的最小 evidence gate。  
Active Epic / Backlog ID: E07/H03–H05 product qualification / VC-002  
Starting State Version: 85

Completed:
- SRT cue 解析保留原始 time range。
- StoryClaim 必须引用 exact cue 和存在于 cue 的 excerpt。
- 缺失 excerpt、未知 cue、空 claim fail closed。
- 编译输出使用 canonical StoryGraph；不自动创建人物、因果边或 Story Arc。
- Semantic entailment 未校准，明确 `confidence=unavailable`、high risk、L1 review required。

Not Completed:
- 真实 SpeechObservation 与 FactSet Artifact 落库接线。
- 真实 StoryGraph Artifact 与 comparison card。
- 产品负责人的 Story 准确性/完整性判断。
- 自动 Strategy、Clip 或 Narration generation。

Validation:
- `tests/intelligence/test_story_brief.py`: exact excerpt pass + absent excerpt fail-closed。
- Full `make check` result recorded in Project State v86。

Next Exact Step:
- Import one real research transcript behind a persisted SpeechObservation and FactSet exact-ref chain, compile and persist the StoryGraph, then create the side-by-side VC-002 review card.

Project State Update: 86
