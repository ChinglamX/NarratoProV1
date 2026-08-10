# AI Drama Marketing Agent

## Project Charter

Version: 2.0

## 1. 项目定位

本项目构建一个个人可运行、可扩展的 AI 短剧营销视频生产系统。

NarratoPro 已经验证基础视频生产链路。本项目不重复建设低标准 MVP，直接面向更高质量、生产级可靠性和持续演进能力。

输入：具有合法处理权限的单集或多集短剧视频资产。

输出：事实可追溯、策略可审核、时间线可编辑、质量可评价的营销候选视频；只有人工通过 Release Gate 后才成为可发布版本。

它不是“视频直接生成剪辑结果”的黑盒工具，而是由 AI System Engineer、AI Drama Producer、AI Review Director 与人协作的生产系统。

---

## 2. 核心生产链

```text
Media & Evidence
→ Fact / Story Intelligence
→ Strategy & Hook Decision
→ Master Timeline Production
→ Offline Quality Review
→ Human Release Approval
→ Optional Performance Feedback
```

视觉、节奏、解说、音频和字幕共同编译到同一个 Master Timeline，不是彼此割裂的独立流水线。

---

## 3. 核心原则

### 理解优先于生成

禁止绕过 Fact 与 Story，直接从原始视频生成正式剪辑方案。

### 事实与推理分离

Fact 记录可观察结果、来源、时间码和置信度；Story、Emotion、Strategy 等推理必须引用 Evidence Links。

### AI 增强，人作决定

AI 负责分析、方案、执行和审核建议。人负责剧情批准、策略选择和最终发布决定。

### 配置与类型驱动

类型模板、模型、阈值和平台规格通过版本化配置管理，禁止写死在业务代码中。

### 反馈不能改写事实

线上表现可以产生新的策略和时间线版本，但不能反向修改 Fact。

---

## 4. 核心资产

- Media Catalog 与 Rights Metadata
- Fact Database 与 Evidence Links
- Story Database 与跨集 Story Graph
- Strategy、Hook 和 Genre Config
- Master Timeline / EDL
- Narration、Audio、Subtitle 与 Render Artifacts
- Quality Review、Experiment 与 Performance Records

长期核心不是某个模型或渲染脚本，而是可积累、可验证的 Short Drama Story Intelligence 与 Marketing Production Intelligence。

---

## 5. 成功标准

项目成功必须同时满足：

- 能用固定输入稳定生成候选成片
- 关键剧情和解说可追溯到证据
- 人可以在三个 Review Gate 修订或拒绝
- 每次运行可追踪模型、配置、成本和产物版本
- 离线质量使用统一评分标准
- 获得真实发布数据后，可以区分创作质量与营销效果
- 每个阶段按最终生产标准设计，不以临时实现换取阶段性演示
