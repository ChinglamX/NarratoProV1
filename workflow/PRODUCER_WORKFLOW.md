# Producer Workflow

Version: 2.0

## 1. 项目生命周期

```text
Input Assets
    ↓
Project Initialize / Rights Check
    ↓
Episode Catalog / Fact Extraction
    ↓
Story Understanding
    ↓
Review Gate 1: Story Approval
    ↓
Strategy Proposal + Hook Candidates
    ↓
Review Gate 2: Strategy Decision
    ↓
Timeline Draft
  ├─ Visual Direction
  ├─ Rhythm Engineering
  └─ Narration Engineering
    ↓
TTS Alignment / Audio / Subtitle
    ↓
Rendering Candidate
    ↓
Offline Quality Review
    ↓
Review Gate 3: Release Approval
    ↓
Final Output / Optional Performance Feedback
```

多集身份解析属于 Story Understanding；Source Quality Features 在 Fact Extraction 产生，在素材选择时使用，不删除剧情证据。

---

## 2. 阶段状态

每个阶段必须记录：

- Pending
- Running
- Succeeded
- Failed
- Awaiting Review
- Rejected
- Superseded

失败、拒绝或修改必须保留原 artifact，通过新 run_id 或 artifact version 继续，禁止覆盖历史结果。

---

## 3. Review Gates

### Gate 1: Story Approval

输入：Story Database、Evidence Links、未解决冲突。

确认人物、时间线、事件和因果。未经批准的 Story 不能进入正式 Strategy Proposal。

输出：Approved、Revise 或 Reject，以及 reviewer、reason 和 story_version。

### Gate 2: Strategy Decision

输入：Strategy Proposal、Hook Candidates、目标受众、版本与成本预估。

由人选择营销方向、Hook、时长和版本范围。未经批准不得进入高成本 TTS 与渲染阶段。

输出：Approved Strategy Config 与选定 Hook。

### Gate 3: Release Approval

输入：Rendered Candidate、Quality Review、Rights Manifest 和风险项。

该节点在所有模式下不可跳过。只有人可以决定对外发布。

输出：Release、Revise 或 Reject。

---

## 4. Timeline 迭代

Visual、Rhythm 与 Narration 共同修改 Timeline Draft。

TTS 生成后必须用实际语音时长对齐并产生新 timeline_version。任何镜头、解说、音频或字幕时长变化，都必须标记受影响轨道并重新校准后才能渲染。

---

## 5. 自动化等级与审核路由

运行模式统一使用 L0–L4 Automation Level，不再另行定义 Manual、Semi Auto 或 Auto Mode。

- L0：AI 仅辅助，人工主导阶段结果。
- L1：所有正式 Gate 人工决定；项目当前默认。
- L2：已校准的低风险模块按 Confidence 与 Automation Policy 自动流转，低置信度、unavailable、高风险和 blocker 转人工。
- L3：稳定模块采用风险分层抽样；异常和分布漂移立即降级。
- L4：允许受控反馈优化候选版本，但生产配置仍需审批。

Automation Level 可以按 project、run、module 配置，最终生效策略必须写入 Run Record。

Story 与 Strategy Gate 是否允许自动决定，取决于该模块经过批准的 Automation Policy；未配置、校准不足或发生冲突时必须转人工。

Gate 3 在所有等级下始终由人决定，任何置信度或线上指标都不能自动批准发布。

人工介入率只用于度量效率，不作为等级本身的定义。

---

## 6. Final Output

必须包含：

- Rendered Video
- Fact、Story、Strategy 和 Master Timeline 版本
- Narration、Voice、Audio、Subtitle 版本
- Quality Review 与 Rights Manifest
- project_id、run_id、variant_id

如进入线上反馈阶段，还必须保存发布平台、发布时间、实验分组和指标来源。

如使用自动路由，还必须保存 Confidence Record、Automation Policy 版本、最终路由原因及抽样结果。
