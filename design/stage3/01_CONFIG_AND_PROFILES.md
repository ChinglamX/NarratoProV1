# Config and Profiles

Version: 1.0

## 1. 目标

用版本化配置表达类型经验、平台规格、受众假设和目标时长，避免把创作规律写死在代码或 Prompt 中。

输入：Approved Story metadata、Project Brief、Config Registry、validation evidence。

输出：GenreResolution、EffectiveConfigSnapshot、ConstraintSet、PreferenceSet、ConfigConflictReport。

---

## 2. 配置类型

| 配置 | 负责 | 不负责 |
|---|---|---|
| Genre Config | 类型惯例、节奏/Hook/解说软偏好 | 判断剧情事实 |
| Platform Profile | 比例、时长、安全区、内容和技术限制 | 预测平台流量 |
| Audience Profile | 受众假设、理解门槛、兴趣与禁忌 | 把人群刻板化为确定结论 |
| Duration Profile | 信息预算、结构槽位、允许偏差 | 直接决定剪辑点 |
| Brand/Safety Policy | 品牌语气、禁用表达、合规风险 | 覆盖素材权利审核 |

所有 Profile 具有 `id/version/schema_version/applicable_scope/validated_scope/source/owner/status`。

---

## 3. Hard Constraint 与 Soft Preference

Hard Constraint 仅包括：

- Approved Story 事实与连续性；
- 权利、品牌安全和法规要求；
- 平台明确技术/内容限制；
- 项目 Brief 明确不可违反的要求。

Soft Preference 包括类型节奏、常见 Hook 形式、语气、信息密度和表达风格。软偏好可以被作品特性或人工决策覆盖，覆盖原因进入 Decision。

禁止把“逆袭必须快切”“年代剧必须煽情”等经验设为硬约束。

---

## 4. Genre Resolution

Genre Resolver 输出多个候选及证据，不直接替项目贴唯一标签。流程：

1. 读取 Story 的冲突、关系、Arc 与语境信号。
2. 规则和模型分别生成候选。
3. 标记主类型、次类型、混合类型与 unknown。
4. 计算与 Config `applicable_scope` 的匹配，不计算虚假精确类型概率。
5. 人工可覆盖，覆盖不修改 Story。

Genre Config 未验证或不匹配时可作为 experimental soft preference，不能驱动自动批准。

---

## 5. 配置合并与优先级

优先级：Rights/Safety → Platform hard rules → Project Brief hard rules → approved human override → Genre/Audience/Duration soft preferences → provider defaults。

合并结果必须产生 EffectiveConfigSnapshot，记录每个字段的来源、覆盖链、单位和最终值。冲突无法自动解决时生成 ConfigConflictReport 并阻止正式候选生成。

配置解析必须确定性；相同输入版本产生相同快照。

---

## 6. Schema 与 Registry

- YAML/JSON 只作为编辑格式，运行时通过 JSON Schema/Pydantic 校验。
- 数值字段声明单位、范围和 nullable 语义。
- Config 发布状态：draft、experimental、candidate、approved、deprecated、revoked。
- 发布需要 benchmark summary、known limitations、approver 和 rollback ref。
- 删除字段采用 expand/migrate/contract；旧 Creative Brief 必须能读取原 snapshot。

---

## 7. 并发与缓存

Genre candidate 可并行生成；配置解析与优先级合并是无状态确定性操作。Registry commit 使用版本 CAS，运行中的 Project 始终读取固定 snapshot，不随最新配置漂移。

缓存键包含 ApprovedStoryRef、Brief version 和所有 Profile refs。配置变化只失效 Strategy 及下游，不重跑 Intelligence。

---

## 8. 测试与验收

- Schema 边界、单位、未知字段、破坏兼容变更和迁移测试。
- 类型混合、unknown、人工覆盖和冲突优先级测试。
- 相同输入重复解析得到字节级稳定的 canonical snapshot。
- Genre soft preference 不能覆盖 Story/rights/platform hard constraint。
- Config 回滚后可重放同一候选生成环境。
- experimental 配置不能进入自动路由依据。
