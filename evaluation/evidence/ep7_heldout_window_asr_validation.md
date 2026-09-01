# ep7 held-out 事件窗口 × 真实 ASR 交叉验证（research）

Date: 2026-08-19（State v110）
方法：用 ep7 真实 FunASR 定时 ASR（`evaluation/evidence/speech_baseline/9519fd49…srt`，19 段 + 说话人分离）逐窗对照 held-out 候选的 10 个事件窗口中属于 ep7 的 4 个（`outputs/heldout_episode_7_8/candidate_v1/manifest.json`）。

| held-out 事件窗口 | ASR 命中（真实对白） | 内容对齐 |
|---|---|---|
| 20–24s（云纹发现） | 22.94–24.32s「这是云纹。」 | ✅ |
| 28–32s（极品品相） | 27.38–30.86s「这块茯苓的表面却有云纹，是难得一见的极品啊」 | ✅ |
| 52–56s（识货确认） | 53.37–55.97s「没错…我不会看错的。」 | ✅ |
| 64–68s（抢着出价） | 63.84–68.16s「谁都别投抢卖给我一万…多少钱都行。」 | ✅ |

结论：**自动选镜的语音证据方法在第二集泛化**——Codex 定义的事件窗口与真实 ASR 对白窗口内容对齐（4/4），且 ep8 上 ASR 窗口与人工核验窗口 overlap 0.816/0.78/0.388（State v105）。这为「ASR 证据窗口为主驱动 + VLM 精修」的自动选镜提供跨集一致性证据（research；窗口选择仍由人工/Codex 定义，非自动生成）。

边界：全部 research；held-out 事件窗口为 Codex 定义（非 Gate 批准）；confidence unavailable；不改变任何 approved 产物。
