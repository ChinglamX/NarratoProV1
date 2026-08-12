# Stage 1 Acceptance Report — E05 Media Ingest

Version: 1.0
Date: 2026-08-12
Status: Approved

## Scope

E02 Artifact/Persistence、E03 Durable Workflow/Review、E04 Master Timeline、E05 Media Ingest。该报告不覆盖 Speech、Visual、Identity、Fact、Story、Strategy 或 demo 级成片质量。

## Automated Evidence

- `make check`：157 tests passed；coverage 80.05%；Ruff、strict mypy、Bandit、Context/Architecture、Schema freshness 通过。
- Real media：`/Users/chinglam/Desktop/youzijuchang_demo.mp4`，12,747,283 bytes。
- E05 result：6 core Artifacts、9 frame samples、220 shadow shot boundaries、audio stem present。
- Duplicate ingest：source/proxy/audio identity reused；UUIDv4 Contract 保持不变。
- Rights：unknown 正确产生 `rights_status:unknown` Release blocker。
- Migration：`0001_e02 -> 0002_e05_media_identity` 在隔离 PostgreSQL 验收库成功。
- Failure：损坏媒体 fail closed；无支持 stream fail closed；无音频路径由 adapter 显式返回 `None`。
- Workflow：Temporal payload 不携带媒体字节；Activity heartbeat/retry/resource admission；Catalog 在 L1 等待人工 Review。

## Known Limits

- PySceneDetect 边界为 Shadow baseline，不是剧情/场景真相。
- Desktop demo 只用于本地技术验收，未取得发布授权，不能发布或进入 Gold dataset。
- 外部 resumable upload adapter、多机共享 object store、真实 VFR/多音轨 corpus 的扩展 benchmark 留在部署与 E06 provider benchmark。
- Release Gate 仍只能由人批准。

## Human Sign-off

Project Owner: **Project Owner（user authorization in Codex task）**

Decision: **approve**

Approved At: **2026-08-12 Asia/Shanghai**

Notes: 项目负责人明确指令“正式关闭 E05，进入 E06”。该指令作为人工 Stage 1 签收证据；Release Gate 规则不受影响。
