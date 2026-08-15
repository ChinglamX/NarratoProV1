# E06 Visual Benchmark Corpus（派生产物）

源素材登记在 `data/corpus/`（不进 Git）；本目录存放**派生产物**：

- `frames/`：PySceneDetect 分镜后的采样帧（OCR/detection/VLM 输入）
- `reports/`：三 provider 的 baseline 报告（按剧汇总）

## 顶层文件（构建后生成）

- `manifest.json`：`DatasetSplitManifest`（train/validation/frozen_test，按剧隔离）
- `benchmark.json`：`evaluation/benchmarks/e06_visual_v1.json` 的输入数据

构建入口：`scripts/build_e06_benchmark.py`（待建）：
1. 读取 `data/corpus/*/manifest.json`（admitted=true）
2. ffprobe 校验格式/时长 → 回填 manifest
3. PySceneDetect 分镜 → 采样帧到 `frames/<series_id>/<episode_id>/`
4. 按剧隔离生成 split manifest
5. 跑 PaddleOCR / RT-DETR / Ark VLM baseline → `reports/`
