# D4 — VLM（API 型 Provider）production 准入等价物设计注记

Date: 2026-08-19（State v119）
背景：volcengine-ark（doubao-seed-2-0-mini-260428）为 API 托管，无权重文件；`production_readiness_gaps` 现报 `model_checksum` / `weight_license` 两项硬缺口（fail-closed 拒绝 production 声明）。owner 暂缓（D4：需仔细设计）。本注记给出设计草案，供决策时直接采用。

## 1. 问题
ProviderPackage 的 `model_checksum`（权重 sha256）与 `weight_license` 假定本地权重。API 型 Provider 的"模型身份"由 **endpoint + model id + API schema 版本 + TOS 版本** 固定，无权重文件可哈希。

## 2. 设计：API 固定证据替代权重 checksum

在 ProviderPackage 增加可选字段（Registry 兼容 minor 升级）：

```python
# 契约层新增（packages/contracts/providers.py）
class ProviderApiIdentity(StrictContract):
    endpoint: str                    # 如 https://ark.cn-beijing.volces.com/api/v3/chat/completions
    model: str                       # 如 doubao-seed-2-0-mini-260428
    api_schema_version: str          # 如 ark-openapi-v1
    tos_version: str                 # 如 volcengine-ark-tos-2026-08（记录审查时点）
    invocation_checksum: Checksum    # 抽样调用的规范化请求/响应 checksum（防漂移证据）

# ProviderPackage 新增可选字段
api_identity: ProviderApiIdentity | None = None
```

`production_readiness_gaps` 修订（API 分支）：
- 若 `data_policy.execution_location == "external_cloud"`：要求 `api_identity` 完整 + `commercial_use_allowed` + 无 pending 标记；**豁免** `model_checksum`/`weight_license` 硬缺口。
- 否则维持现逻辑（本地权重必须 checksum + license）。

## 3. 契约/测试/迁移影响
- Registry SemVer：新增可选字段为 **minor** 升级（现有 package 兼容）。
- `production_readiness_gaps` 增加分支 + 单测（API 完整 → 0 gaps；API 缺字段 → 报缺项；本地 Provider 不受影响）。
- `enforce_admission_evidence`：production 声明时，本地模型仍要求 weight_license+checksum；API 型要求 api_identity 完整。
- 迁移：volcengine-ark 注册表条目补 `api_identity`（endpoint/model/schema/TOS 版本/调用 checksum 实测），admission 仍 research 直至 owner 批准升级。

## 4. 证据准备（决策后可立即执行）
- endpoint/model/schema：已在 settings 与注册表（`volcengine_ark_endpoint` / `volcengine_ark_model`）。
- TOS 版本：需 owner/法务确认审查时点（2026-08-16 法务已通过 `commercial_use_allowed`，TOS 版本号待记录）。
- invocation_checksum：对一次规范化 VLM 调用（如 D5 预标注的 24 帧之一）计算请求/响应 canonical checksum。

## 5. 边界
- 设计仅解 API 身份固定问题；**production 升级仍需要** D5 质量证据（claim 合规率已 24/24=1.0 为正面证据）+ 成本上限（D3）+ owner 批准。
- research 调用不受影响（非 production 声明不触发 gate）。
