# Development Rules

Version: 1.0

本文件把 PROJECT_RULES.md 的全局原则落实为工程执行规则。技术选型以 engineering/TECH_STACK.md 为准。

代码目录、包依赖、API、Schema Catalog、Workflow 和 Epic 实施规范见 `design/implementation/README.md`。

---

# 1. 模块边界

每个模块必须定义：

- 单一职责
- 输入契约
- 输出契约
- 依赖接口
- 错误类型

模块之间只能通过已定义的接口或数据契约协作，禁止跨层读取内部状态，禁止形成循环依赖。

架构职责以 SYSTEM_ARCHITECTURE.md 为准。下游不得覆盖上游结果；评审与生产迭代必须生成可追踪的新 Strategy、Timeline 或其他 artifact 版本。任何反馈都不得修改既有 Fact。

---

# 2. 数据与配置

业务事实、推理结果和运行配置必须分离：

- Fact Data：来自视频、音频或文本的可验证观察结果。
- Story Data：基于 Fact Data 产生的剧情推理结果，必须保留证据引用。
- Configuration：策略、阈值、模型选择和运行参数，不得写死在业务逻辑中。
- Timeline Data：全部成片轨道共享同一 timebase，以 Master Timeline / EDL 为唯一成片时间坐标来源。

数据结构和配置结构必须有版本号。破坏兼容性的修改必须提供迁移方案。

---

# 3. 阶段契约

每个 Pipeline 阶段必须明确：

- 输入数据及版本
- 前置条件
- 输出数据及版本
- 成功标准
- 失败状态与重试策略
- 日志和追踪标识

阶段必须能够使用固定输入独立运行，不能依赖未声明的全局状态。

---

# 4. 可追踪性

每次执行必须记录：

- project_id
- run_id
- stage
- 输入与输出版本
- 配置版本
- 模型及模型版本
- 执行时间、耗时和状态
- token、调用成本和错误信息（适用时）

AI 生成的 Story、Strategy、Script 和 Review 结果必须能够追溯到输入事实、提示词版本、模型和配置。

成片使用的视频、BGM、音效、字体和音色必须记录 Rights Metadata。权利状态未知时不得进入发布流程。

---

# 5. 测试与验收

每个模块至少需要：

- 输入输出契约测试
- 正常路径测试
- 关键失败路径测试
- 可复现的固定样例

涉及模型的测试必须区分：

- 确定性工程测试：验证结构、状态、接口和错误处理。
- 质量评测：依据 quality/QUALITY_STANDARD.md 和 quality/QUALITY_REVIEW_PROTOCOL.md 评价内容质量。

模块测试通过不等于内容质量通过，两者必须分别记录。

涉及时间线的模块必须验证修改传播：镜头或语音时长改变后，受影响的音频、字幕和渲染任务必须失效并重新生成。

---

# 6. 依赖与复杂度

新增依赖必须说明用途、维护状态、替代方案和运行成本。

首个生产部署采用模块化单机 Pipeline。单机不代表 MVP 或低标准：数据契约、幂等、恢复、追踪、测试和回滚必须按生产要求实现。未经明确收益验证，不得提前拆分微服务，不得为了 Demo 绕过数据契约、测试或审核节点。

NarratoPro 已验证的能力应先做接口、质量、性能和许可证审计，再决定复用、适配或替换。禁止为了形式上的“新架构”重复实现已经满足标准的能力。

---

# 7. 变更要求

核心架构、数据契约或阶段边界的变更必须说明：

- 变更原因
- 影响范围
- 兼容性
- 迁移方式
- 验证结果

代码实现不得偏离 PROJECT_CHARTER.md、SYSTEM_ARCHITECTURE.md 和 PRODUCT_CAPABILITY.md；如确需偏离，必须先更新相应纲领文件并说明理由。

Hook 效果预测、演员表演评价、穿帮检测等研究性能力，在没有数据集、基准和验收指标前不得作为主线交付阻断项。

---

# 8. Confidence 设计规范

用于排序或自动路由的 AI 输出必须携带 Confidence Record：

- score 或 unavailable
- method 与 calibration_version
- 支持/反对因素
- Evidence Links
- applicable_scope
- risk_class

禁止直接使用 LLM 自报概率作为自动放行依据。不同任务、模型和类型的分数必须分别校准，不得假设相同数值具有相同含义。

阈值必须来自版本化 Automation Policy。没有标注数据和校准报告时，只允许 Shadow Evaluation，不允许影响正式审核路由。

自动路由的测试至少覆盖：

- 阈值边界
- unavailable
- 阻断项优先级
- 高置信度错误
- 分布漂移
- 自动降级和回滚

---

# 9. Automation Policy 规范

Automation Level 可以配置在 project、run 和 module；解析优先级必须明确并记录最终生效值。

等级升级条件必须包含最小样本、严重漏检率、校准误差、类型覆盖和稳定窗口，不能只依据人工介入率或连续成功次数。

高置信度不能覆盖剧情事实错误、权利风险、技术阻断项或 Release Gate。异常和策略缺失时必须 fail closed，回退到更保守等级。

---

# 10. Genre Config 规范

Genre Config 必须包含：

- id、version、schema_version
- applicable_scope 与 validated_scope
- hard_constraints 与 soft_preferences
- rhythm、hook、narration、audio、subtitle 等域配置
- validation_summary 与 known_limitations

硬约束只能用于事实、权利、平台和明确禁止项。创作风格参数默认是可覆盖的软偏好，禁止把类型刻板印象写成不可变业务规则。

配置更新必须提供兼容性、评测结果、审批人和回滚版本。

---

# 11. Feedback Data 规范

所有人工修正必须结构化记录：

- correction_id、project_id、run_id、artifact_id、artifact_version
- module、correction_type、before、after、reason
- model、prompt_version、config_version、automation_level
- reviewer、created_at

发布指标必须关联 variant_id、平台、时间窗口、实验分组和指标来源。

反馈分析只能生成待验证的 Prompt、Config、阈值或模型候选版本。候选上线必须经过离线评测、审批、受控发布和可回滚验证，禁止生产系统自我修改后直接上线。

反馈数据必须遵守数据最小化、访问控制、保留期限和素材权利要求。
