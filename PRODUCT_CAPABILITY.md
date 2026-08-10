# Product Capability

Version: 2.0

能力的具体建设方式、工具、输入输出和限制见 `design/architecture/README.md`。

## 1. Control & Governance

- Project、run、variant 和 artifact 管理
- 可恢复的阶段状态与版本追踪
- Story、Strategy、Release 三个人工审核门
- 模型、配置、资源和成本记录
- 素材权利与发布风险检查
- 项目、运行和模块级 Automation Level
- 基于校准置信度与风险等级的人工审核路由
- 自动降级、受控升级和策略回滚

---

## 2. Story Intelligence

### Media & Fact

- Episode、Scene、Shot、Frame 与统一时间码
- ASR、Speaker、Person、Entity、OCR、Action
- 可观察的画面、声音、表情和素材质量特征
- 每条事实的来源、置信度和模型版本

### Story

- Event、Character State、Relationship
- Conflict、Turning Point、Climax、Story Arc
- 跨集人物身份、全剧时间线和 Story Graph
- Story 结论与 Evidence Links

Fact 与 Story 推理输出必须提供可解释 Confidence Record；无法可靠估计时必须标记 unavailable，而不是伪造精确分数。

素材质量只影响成片选材，不删除剧情理解所需事实。

---

## 3. Marketing Strategy

- 核心卖点和高价值事件发现
- 受众、营销方向、时长和叙事结构
- 情感、逆袭、悬疑等多策略候选
- 多个 Hook 候选及依据
- 不同策略、Hook、时长和平台的 Variant Plan
- 版本化 Genre Config

Strategy 与 Hook 输出必须说明证据、候选差异、置信度方法和适用范围。无校准数据时，评分只用于排序，不用于自动批准。

无真实效果数据时只提供 Hook 先验评分，不宣称效果预测。

---

## 4. Timeline Production

### Master Timeline

统一管理画面、原声、解说、BGM、SFX、字幕、转场和特效轨道。

### Creative Planning

- Visual Direction：素材、构图、色彩和视觉连续性
- Rhythm Engineering：情绪曲线、信息密度、镜头时长和呼吸点
- Narration Engineering：背景、动机、冲突、期待、情感和停顿

### Media Production

- TTS、实际时长对齐和音画校准
- 原声、解说、BGM、SFX、Ducking、混音和响度
- 字幕对齐、重点词、安全区、多层样式和动画
- 竖屏为主的多格式、多版本渲染

---

## 5. Evaluation & Learning

### Offline

- 剧情正确性和证据审核
- Hook、节奏、解说、视觉、音频和字幕评分
- 技术规格、权利和发布风险检查
- demo 基准对比与时间码问题定位
- 置信度校准、严重漏检率与自动化覆盖率评估
- Automation Level 升级、降级和回滚建议

### Online

在具备合法发布数据后支持：

- variant 与曝光、留存、观看时长、完播和互动关联
- A/B Experiment 记录
- Strategy、Hook 和 Genre Config 的效果校准

### Human Correction Loop

- 结构化记录 Story、Strategy、Timeline 和 Release 修正
- 关联原值、新值、修正原因、artifact、模型、Prompt 和 Config 版本
- 生成待评测的 Prompt、阈值和 Genre Config 候选版本
- 对比上线前后错误率、校准质量和成片评分

候选优化不得自动进入生产环境，必须经过离线验证、审批和可回滚发布。

线上表现只产生新策略版本，不能改写剧情事实。

---

## 6. 能力成熟度

- Deterministic：媒体解析、数据契约、时间线、状态、渲染和追踪。
- AI Assisted：剧情、策略、Hook、节奏、解说和质量建议，必须可人工修订。
- Research：表演质量、穿帮检测、无历史数据的效果预测和全自动类型识别。

Research 能力不能作为最小生产闭环的前置条件。
