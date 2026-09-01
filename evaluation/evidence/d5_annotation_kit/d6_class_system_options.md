# D6 — DET 类别体系决策（三方案对比）

Date: 2026-08-19（State v116）
背景实证：D5 第一集试标显示 RT-DETR 对短剧画面**框得准（score≈0.9）但标签全为 `unknown`**——COCO 80 类不含短剧类别（人物/卡/钱/手机/武器/野猪/鹿等），DET label 级 precision/recall = 0/0。**类别体系未定时 DET 不能作为准入依据**。

## 三方案对比

| 维度 | A. COCO 映射（保守） | B. 自定义类别 + 微调/规则 | C. 扩展 VLM 标注 |
|---|---|---|---|
| 做法 | 保留 COCO 里对短剧有用的类（person/vehicle/animal…），其余丢弃 | 定义短剧类别（person/card/money/phone/weapon/wild-animal…），用标注数据微调或规则映射 | 用 Ark VLM 给检测框打语义标签 + 人工抽查解除自指链 |
| 覆盖能力 | 低（关键物如卡/钱/手机缺失） | 高（按需定义） | 中高（VLM 可识别大部分语义，但有幻觉风险） |
| 成本 | 零（改标签映射） | 高（需标注数据=扩展 D5 + 训练/配置） | 中（VLM 调用费 + 人工抽查） |
| 依赖 | D5 现有标注即可验证 | D5 扩展标注（更多帧 + 类别覆盖） | D5 标注（VLM 标签正确性抽查）+ VLM 准入（D4） |
| 风险 | 覆盖率不足，mAP 仍低 | 训练/配置周期长 | 自指证据链（VLM 自评），需人工抽查 |
| 建议适用 | 当前立即启用（person 检测至少可用，支撑 E07 identity 的人物出现计数） | 中期目标（D5 标注积累后） | 与 B 并行（VLM 标签作为候选，人工确认） |

## 推荐组合（可分批）
1. **立即（零成本）**：执行 A 的子集——把 RT-DETR 输出中 `person` 类映射为可用标签，其余标记 `other`；重跑 D5 试标集，验证 person 检测 recall 是否从 0 提升到可用水平（若框本身准，person recall 应显著>0）。这同时支撑 E07 identity 的「人物出现」证据。
2. **随 D5 扩展**：标注时额外注明关键物类别（卡/钱/手机/武器/动物），积累后做 B 的自定义类别映射或轻量微调。
3. **并行**：C 的 VLM 标签作为候选池，人工抽查后进入类别表（需 D4 VLM 准入推进）。

## 决策请求（一句话即可）
- 批准立即执行 **A 子集（person 映射 + 重跑试标集验证）**？或指定其他组合。
- 批准后我执行：更新检测 adapter 标签映射 → 重跑 8 帧试标集的 DET 指标 → 出 person-recall 结果。

## 更新（2026-08-19，adapter 修复后）
- **根因修正**：DET 全 unknown 的主因是 **adapter 解析 bug**（PaddleX DetResult 标签在 `boxes[].label`，adapter 误读 `page.get("labels")`）——已修复 `packages/providers/visual/paddle_detection.py`。
- **修复后试标集结果**：DET label 级 **precision 0.8 / recall 1.0**（person 检出正常；1 个误报为 f02「toilet」——陶缸被 COCO 类误判）。
- **D6 真实剩余范围**：person 等 COCO 类可用；**卡/钱/手机/武器/动物等短剧关键类别仍需自定义**（三方案不变，但优先级降低——person 已可用，支撑 E07 identity 的人物出现计数）。
