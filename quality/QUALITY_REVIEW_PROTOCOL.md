# Quality Review Protocol

Version: 2.0

## 1. Review 原则

- 先检查阻断项，再评分。
- 每个问题必须引用时间码、artifact_id 或具体事实证据。
- AI Review Director 给出建议；Release Gate 的最终决定由人作出。
- 不得用“已完成”代替“达到标准”，也不得用主观形容词代替证据。

---

## 2. Review 顺序

1. Technical & Rights Review
2. Story Correctness Review
3. Marketing & Hook Review
4. Rhythm Review
5. Narration Review
6. Visual Editing Review
7. Audio Review
8. Subtitle Review
9. Confidence & Automation Safety Review（使用自动路由时）

发现阻断项后仍需记录其他已确认问题，但 Verdict 必须为 Reject。

---

## 3. 核心检查

### Story

- 人物、事件、时间线和因果是否与 Evidence Links 一致？
- 是否存在无依据补写、跨集身份错误或信息跳跃？

### Marketing & Hook

- Hook 是否来自真实剧情并匹配目标受众？
- 是否快速建立问题、冲突或期待？
- 是否为了刺激破坏剧情真实性？

### Rhythm

- 信息密度和镜头长度是否服务当前情绪？
- 是否存在无意义停顿、机械快切或单纯堆高潮？
- 高潮和留白是否有明确叙事作用？

### Narration

- 是否提供对白之外的背景、动机、连接或期待？
- 用词、语速、停顿和声音情绪是否匹配画面？
- 每句重要解说是否能追溯到剧情证据？

### Visual / Audio / Subtitle

- 素材、构图和转场是否连续？
- 人声、原声、BGM 和音效是否平衡？
- 字幕是否同步、可读且避开关键视觉区域？

### Confidence & Automation Safety

- Confidence 是否有 method、calibration_version、scope 和 Evidence Links？
- 是否出现高置信度错误、严重漏检或分布漂移？
- 最终路由是否符合 Automation Policy 和 risk_class？
- blocker、unavailable 或策略缺失是否正确转人工？
- 是否保存抽样、人工修正和降级记录？

---

## 4. 输出格式

```text
Review ID:
Project / Run / Variant:
Benchmark Version:

Blockers:
- Timecode / Artifact:
  Problem:
  Evidence:
  Required Fix:

Scores (0–5):
- Story Correctness:
- Marketing & Hook:
- Rhythm:
- Narration:
- Visual Editing:
- Audio:
- Subtitle:
- Technical & Rights:

Automation Safety（单独评价，不计入成片加权分）:
- Confidence Explainability: Pass / Fail
- Calibration Status: Shadow / Calibrated / Drifted / Unavailable
- Severe False Negative:
- Effective Automation Level:
- Routing Decision:

Weighted Score (0–100):
Verdict: Pass / Revise / Reject
Risk:
Suggestion:
Reviewer:
```

评分权重与通过条件以 quality/QUALITY_STANDARD.md 为唯一来源。
