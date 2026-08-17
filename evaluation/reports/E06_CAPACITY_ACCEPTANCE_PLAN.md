# E06 容量验收与故障注入计划

Date: 2026-08-17
Status: Design draft — target values pending project-owner approval
对应 blocker（`evaluation/qualification/e06_g05.json`）：
`long-series-concurrency`、`worker-interruption-recovery`、`resource-cost-baseline`

## 1. 验收目标（2026-08-16 owner 授权按 Mac mini M1 16GB + 50GB 常态硬盘推荐）

机型基线：Mac mini M1（8 核 CPU）/ 16 GB RAM / 50 GB 常态磁盘；Paddle 两模型常驻（实测峰值 RSS 2.7 GB）；目标值依据 2026-08-16 benchmark（顺序、模型常驻后）+ capacity probe（2 worker 并发）实测数据，非主观预设。

| 指标 | 推荐目标 | 实测依据 |
|---|---|---|
| 单帧延迟（单 worker 顺序，模型常驻后） | OCR P95 ≤ 10s、DET P95 ≤ 1.5s | benchmark：OCR P50 6.8s/P95 9.1s/max 9.1s；DET P50 0.78s/P95 0.88s/max 0.94s |
| 单帧延迟（2 项目并发） | OCR P95 ≤ 15s、DET P95 ≤ 8s | probe：OCR P50 8.0s/P95 14.6s；DET P50 1.6s/P95 7.5s（并发争用 CPU） |
| 峰值内存 | 单 worker ≤ 4 GB；2 项目并发 ≤ 12 GB（含全部 worker；16 GB 减 OS+容器 ~4 GB） | probe 峰值 RSS 2.7 GB（两模型常驻） |
| 长视频吞吐 | 1 集 90s 竖屏（720x1280）全观察（OCR+det 全帧 ~20 帧 + VLM 子集 4 帧）≤ 5 min（单 worker）；≤ 10 min（2 项目并发） | 顺序理论 ~2.9 min/集；并发受 CPU 争用 |
| 并发 | 2 项目并行无资源冲突、无 OOM | probe 2 workers 0 errors；PaddleX 需顺序预热后并发 |
| 成本 | VLM API ≤ ¥0.5/集（按 4 帧/集计）；本地 0 增量 | 未实测成本，保留原建议 |
| 故障恢复 | Worker kill 后 workflow 从 durable history 恢复 ≤ 60s | 复用 E09 replay 验证模式 |

注：原草案建议（OCR P95 ≤ 3s）在 M1 CPU 上不可达（实测 P95 9.1s），已按机型与实测修正。磁盘 50 GB：36 集语料 + benchmark 抽帧 + Object Store 产物需在验收前核对占用（预估 < 20 GB）。

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

## 5.1 工程基线（2026-08-16 probe，非验收）

`scripts/probe_e06_capacity.py`（frozen_test 12 集/48 帧/96 次调用，OCR+detection 并发 2 workers，结果 `E06_CAPACITY_RESULTS.md`）：

| 指标 | 实测（工程基线） | 建议验收目标（待批） |
|---|---|---|
| OCR P50 / P95 | 8.0s / 14.6s | ≤ 3s / 5s（模型常驻后） |
| DET P50 / P95 | 1.64s / 7.5s | ≤ 1.5s / 3s |
| 峰值 RSS | 2.7 GB（两模型常驻） | ≤ 6 GB |
| 吞吐 | 0.27 calls/s（单机 CPU 并发） | —（验收需按目标值重测） |

关键发现：**PaddleX 并发首次初始化不兼容**（"PDX has already been initialized"）——probe 采用**顺序预热后再并发**规避；这正是 E06 集成设计中"同进程共享 provider 实例 + 预热"的依据。OCR P95 明显高于 P50（复杂帧/资源争用），DET 相对稳定。本基线不作为验收结论。

## 6. 待项目负责人确认

1. ~~上表验收目标值~~（2026-08-16 已由 owner 授权按 Mac mini M1 16GB 推荐，§1 采纳）
2. VLM API 成本上限（保留建议 ¥0.5/集）
3. 容量验收使用的素材范围（frozen_test 12 集 or 全 36 集——推荐 frozen_test 12 集作为验收输入，全 36 集作为压力扩展）
