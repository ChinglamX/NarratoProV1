# 真实短剧素材登记目录（E06 Visual Benchmark）

本目录存放**有合法处理权限**的真实短剧源素材，用于建设 E06 按剧隔离的
OCR / Detection / VLM benchmark pack。**源素材不进 Git**（见 `.gitignore`），
只有元数据与派生基准进入 `evaluation/corpus/`。

## 目录规范

```
data/corpus/
  README.md                 # 本文件
  <series_id>/              # 每部剧一个目录（series_id 用小写连字符，如 "shan-shen-yin"）
    manifest.json           # 该剧元数据 + RightsAndUsage（模板见下）
    episodes/
      <episode_id>.mp4      # 源视频（原始文件，只读；可多集 e01.mp4/e02.mp4…）
```

系列 ID 规范：`[a-z0-9-]+`（契约 DatasetItem.item_id/series_id 约束）。

## 每剧 manifest.json 模板

```json
{
  "series_id": "<小写连字符>",
  "title": "<剧名>",
  "genre": "<古装|现代|都市|悬疑|其他>",
  "orientation": "portrait|landscape",
  "episodes": [
    {
      "episode_id": "e01",
      "file": "episodes/e01.mp4",
      "duration_seconds": null,
      "resolution": null
    }
  ],
  "rights": {
    "rights_status": "approved",
    "allowed_purposes": ["evaluation"],
    "evidence_ref": "<自有版权 | 授权文件路径 | 公开来源 URL>",
    "expires_at": null
  },
  "admitted": false
}
```

字段说明：
- `rights_status`：`approved`（自有/已授权）/ `restricted`（部分限制）/ `unknown`（未知——**拒绝进 benchmark**）
- `evidence_ref`：权利证据（授权书路径、来源 URL、或"self-authored"）
- `admitted`：我校验格式与权利后置 `true`，素材才会进入 split manifest
- `duration_seconds` / `resolution`：我 ffprobe 后回填，你不用填

## 提供方式

把视频文件放进 `<series_id>/episodes/` 并写好 `manifest.json`（或只放文件、告诉我
权利来源，我来写 manifest），然后通知我运行校验与分拆。

## 隔离规则（契约强制）

每部剧（series_id）只能进入 train / validation / frozen_test **其中一个** split，
防止跨集泄漏（`DatasetSplitManifest.prevent_series_leakage`）。因此至少需要 3 部剧。
