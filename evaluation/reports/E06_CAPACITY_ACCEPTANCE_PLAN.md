# E06 容量验收与故障注入计划

Date: 2026-08-17
Status: Design draft — target values pending project-owner approval
对应 blocker（`evaluation/qualification/e06_g05.json`）：
`long-series-concurrency`、`worker-interruption-recovery`、`resource-cost-baseline`

## 1. 验收目标（建议值，待批准）

| 指标 | 建议目标 | 说明 |
|---|---|---|
| 长视频吞吐 | 1 集 90s 竖屏（720x1280）全观察（OCR+det 全帧 + VLM 子集）≤ 30 min 处理 | 以 13 剧 36 集语料实测 |
| 单帧延迟 | OCR P95 ≤ 3s、det P95 ≤ 1.5s（模型常驻后） | 本地 CPU（Mac mini） |
| 峰值内存 | 单 worker ≤ 6 GB（Paddle 两模型常驻） | 防 OOM |
| 并发 | 2 项目并行无资源冲突 | 同进程 OCR+det 已验共存 |
| 成本 | VLM API ≤ ¥0.5/集；本地 0 增量 | 按 4 帧/集计 |
| 故障恢复 | Worker kill 后 workflow 从 durable history 恢复 ≤ 60s | 复用 E09 replay 验证模式 |

## 2. 长视频/多项目并发测试

- 复用 `scripts/accept_e09_multi_variant.py` 模式：构造 2 个 VisualObservationWorkflow 并发跑
- 指标采集：Temporal metrics（activity 时长/重试）+ 进程 RSS 采样
- 语料：frozen_test 4 剧 12 集（隔离集）作为吞吐验收输入
- 输出：`evaluation/reports/E06_CAPACITY_RESULTS.md` + qualification 更新

## 3. Worker 故障注入

| 场景 | 方法 | 通过条件 |
|---|---|---|
| Worker 硬 kill | 观察活动进行中 kill worker 进程 → 重启 | workflow 从 history 恢复，无重复 artifact |
| OOM 模拟 | 限制 RSS（ulimit）触发 | 活动失败 → 重试/降级，不污染数据 |
| 预算耗尽 | resource_profile cost 上限触发 | fail-closed 拒绝，unavailable 记录 |
| Provider 不可用 | 断网/停 Ark endpoint | explicit unavailable，不空成功 |

## 4. 资源成本基线

- 每媒体分钟：OCR+det 本地（CPU/内存摊销）+ VLM API 帧数×单价
- 36 集语料实测后产出基线表；作为 production 资源 profile 输入

## 5. 与升级路径衔接

- 容量验收通过 + 已有质量证据（CER 0.0/P 0.87/R 0.85）+ D1 commercial 批准
  → PaddleOCR/RT-DETR 具备 production 升级完整证据链（新 Acceptance Report + 人工签名，ADR-032）
- VLM 仍待：ToS 法务审查 + 成本上限确认

## 6. 待项目负责人确认

1. 上表验收目标值（或给替代值）
2. VLM API 成本上限
3. 容量验收使用的素材范围（frozen_test 12 集 or 全 36 集）
