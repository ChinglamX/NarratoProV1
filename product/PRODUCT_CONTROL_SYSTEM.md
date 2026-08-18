# Product Control System

Version: 1.0

## 1. 目的

本文件解决一个产品管理问题：工程任务、工具接入、真实效果和生产资格不能再使用同一个“完成”状态。

项目继续保留现有生产级架构，但日常推进优先回答：

1. 这个模块现在能给个人创作者产出什么？
2. 输入和输出能否被直接查看？
3. 工具效果是否用真实素材验证？
4. 人是否认为结果有用？
5. 它是否阻塞首个完整候选成片？

根入口为 `PRODUCT_CONTROL_BOARD.md`。`PROJECT_STATE.md` 仍是工程恢复真相源；两者职责不同：

- Product Control Board：产品价值、可见效果、范围和决策。
- Project State：Git、Epic、实现、测试、风险和恢复点。

## 2. 三类能力

### A. Core Generation

个人完成一条营销候选所必需。只有这些能力可以默认阻塞 First Usable Cut：

- 导入和选择合法素材
- 最小剧情事实/人工修正
- 营销方向与 Hook 选择
- 可编辑 Timeline
- 配音或明确选择无配音
- 原声/解说基础混音
- 字幕
- 最终渲染与人工发布确认

### B. Quality Enhancer

能提高质量，但首个候选可以人工替代或降级：

- 高级人物身份、跨集关系和因果推理
- 语义检测、tracking、embedding、VLM 全量分析
- 自动智能裁切、表演质量、复杂 BGM/SFX
- 多候选自动评分和精细局部重生成

### C. Scale and Automation

只有证明个人工作流有效后再投入：

- L2/L3 自动路由和 Confidence calibration
- 大规模并发、完整成本优化和高级故障演练
- 在线 A/B、反馈学习、漂移监控
- 多租户、复杂权限和大规模运营 Dashboard

分类不改变安全底线。剧情事实、素材权利、文件可播放和人工 Release 始终不可绕过。

## 3. 模块成熟度

每个模块分别记录以下五级，不再用单一百分比：

| Level | 名称 | 需要的证据 |
|---|---|---|
| M0 | Specified | 输入、输出和验收描述存在 |
| M1 | Code Verified | 代码和确定性测试通过 |
| M2 | Tool Verified | 真实工具/模型对真实输入成功运行，保存可查看输出 |
| M3 | Human Useful | 产品负责人查看输出并记录 useful / revise / reject 和原因 |
| M4 | Slice Integrated | 在当前纵向切片中由上游真实产物驱动，并产生可用下游产物 |
| M5 | Repeatable Personal Use | 非开发者按固定入口重复完成，失败可理解并可恢复 |

规则：

- M1 不能写成“工具有效”。
- M2 不能写成“内容质量通过”。
- M3 必须有可打开的样例和人工结论。
- M4 必须消费真实上游，不接受手工伪造 placeholder 冒充闭环。
- M5 才能称为“个人可用完成”。

## 4. 双重判定

每个模块同时记录：

- Delivery：实现和接线到了哪里。
- Effect：真实输出对创作是否有帮助。

允许出现 `Delivery=M4, Effect=Reject`。这不是失败隐藏，而是明确说明工具已接通但效果不值得继续。

Effect 只允许：

- `unreviewed`
- `useful`
- `useful_with_revision`
- `reject`

人工结论至少记录 reviewer、日期、输入、可查看输出和一句理由。

## 5. First Usable Cut

当前产品里程碑不是“所有 Stage 完成”，而是：

> 产品负责人通过一个清晰入口，选取一段合法短剧素材，得到一条带画面、可选解说、可听混音、可读字幕的完整候选；可以查看每个中间产物、修改关键文本/镜头并重新生成；最后由人决定是否导出。

First Usable Cut 不要求：

- L2/L3 自动化
- 完整多剧校准体系
- 自动跨集人物身份达到生产阈值
- 在线 A/B 和反馈学习
- 所有 Provider 都升级 production
- 大规模并发和多租户

它仍要求：

- 不编造已知关键剧情
- 素材和音色用途明确
- Timeline、音频和字幕同步
- 输出文件可播放
- 人工 Release 决定

## 6. 模块验证卡

每次只验证一个可见问题。验证卡必须包含：

```text
Module / Owner:
Capability Class: Core / Enhancer / Scale
User Question:
Input:
Tool / Version:
Command or UI Entry:
Inspectable Output:
Expected Behavior:
Machine Checks:
Human Review Question:
Human Decision: unreviewed / useful / useful_with_revision / reject
Known Failure / Fallback:
Current Maturity:
Next Smallest Proof:
First Usable Cut Blocker: yes / no
```

工具调用成功但没有可查看输出，验证无效；输出存在但没人判断是否有用，只能到 M2。

## 7. 推进规则

1. 同时只允许一个产品主目标：First Usable Cut。
2. Core blocker 优先于 Enhancer，Enhancer 优先于 Scale。
3. 新增基础设施前必须写明它关闭哪个 Core blocker。
4. 一个模块最多连续投入一个短周期；周期结束必须展示样例或停止。
5. 人工认为 `reject` 时，先决定替换、降级或人工兜底，不继续用更多架构包装无效工具。
6. 每周只汇报四项：新出现的可见产物、人工结论、关闭的 blocker、下一个可演示目标。
7. 测试数、Schema 数、提交数和文档行数不作为产品进度。

## 8. 产品决策权

产品负责人决定：

- First Usable Cut 的创作目标和可接受人工步骤
- 工具效果是否值得继续
- Enhancer 是否进入当前版本
- 何时从个人可用推进到规模化

工程系统负责提供证据、约束和失败保护，不能用架构复杂度替代产品判断。
