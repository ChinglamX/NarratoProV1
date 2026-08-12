# G02 Evaluation Corpus Bootstrap

该目录保存 Provider Benchmark Harness 的确定性工程 fixture，不是生产质量 Gold Dataset（not production quality data）。

- `asr_contract_fixture.json`：验证 series-isolated split、slice、严重错误和 unavailable 汇总。
- 所有 source refs 均为合成占位 ArtifactRef，不对应真实媒体或发布资产。
- Frozen Test 只能用于最终评测，禁止用于 tuning。
- G03/G04 必须添加具有合法权利、人工标注和 agreement 的真实项目语料，才能报告质量 baseline。
