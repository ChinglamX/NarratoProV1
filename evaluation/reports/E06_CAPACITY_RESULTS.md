# E06 容量并发 probe(engineering evidence)

Date: 2026-08-16
Status: Engineering evidence — acceptance targets pending project-owner approval

方法:frozen_test 12 集抽帧,OCR + detection 并发
- episodes: 12,frames: 48,
  calls: 96
- elapsed: 352.43s,throughput: 
  0.27 calls/s
- peak RSS: 2711.9 MB (ru_maxrss peak)

| capability | calls | P50 (ms) | P95 (ms) | total items | errors |
|---|---|---|---|---|---|
| ocr | 48 | 8005 | 14631 | 96 | 0 |
| detection | 48 | 1643 | 7541 | 60 | 0 |

说明:单机本地 CPU,Paddle 模型常驻;结果受宿主调度影响,仅作工程基线,
不构成容量验收结论.验收需 owner 批准目标值后按 `E06_CAPACITY_ACCEPTANCE_PLAN.md` 执行.
