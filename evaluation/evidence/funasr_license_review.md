# FunASR/SenseVoice 模型卡许可审查（D9）

Date: 2026-08-19（State v112）
结论：**全部 4 个模型模型卡均为 Apache License 2.0**（本机模型卡 README.md 为权威来源，与 ModelScope 下载一致）；主 ASR 权重 checksum 已实测。

| 模型 | 模型卡许可 | checksum（model.pt / 主文件） |
|---|---|---|
| speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch（ASR 主模型，989MB） | Apache-2.0 | `sha256:3d491689244ec5dfbf9170ef3827c358aa10f1f20e42a7c59e15e688647946d1` |
| speech_fsmn_vad_zh-cn-16k-common-pytorch（VAD） | Apache-2.0 | （配套，未单独录） |
| punc_ct-transformer_zh-cn-common-vocab272727-pytorch（标点） | Apache-2.0 | （配套） |
| speech_campplus_sv_zh-cn_16k-common（说话人） | Apache-2.0 | （配套） |

依据：模型目录 `NarratoPro/storage/models/funasr/iic/*/README.md` 中 `license: Apache License 2.0`；FunASR 框架 [Apache-2.0](https://github.com/modelscope/FunASR)。
已执行：注册表 `funasr` 条目更新——`weight_license=Apache-2.0`、`model_checksum` 录入、`identity.model` 修正为实际服务的 paraformer-large；`production_readiness_gaps(funasr)` 由 3 项降为 **1 项（commercial_use_allowed 待批准）**。
待项目负责人：**商用批准决定**（批准后注册表 commercial_use_allowed=True；正式生产准入仍需 Speech 基准 CER 阈值——D5 标注）。
边界：research 运行不受影响（非 production 声明不触发 fail-closed gate）；Apache-2.0 商用允许，但最终商用决定由 owner 做出。

## 更新（2026-08-19，owner 裁决）
- **D9 商用批准：`commercial_use_allowed=True`（owner 2026-08-19）**——许可层面批准（Apache-2.0 模型卡），注册表已更新；`production_readiness_gaps(funasr)` 现为 **0 项**。
- 边界：**不等于 production admission**——FunASR 仍为 research；正式 production 仍需 D5 标注后计算 CER 阈值 + Speech 基准质量验收。当前 canonical 链继续 research 调用 + 人工 QC。
