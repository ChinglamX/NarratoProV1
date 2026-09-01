# Episode 8 — 真实 ASR 证据窗口 + VLM 精修（research）

- **threat**：ASR 41.07–49.29s (overlap 0.816) → VLM 精修 42.5–46.5s (overlap 0.5)；人工 42.0–50.0s
- **sale**：ASR 16.09–26.235s (overlap 0.78) → VLM 精修 16.09–26.235s (overlap 0.78)；人工 15.0–28.0s
- **payment**：ASR 28.59–30.53s (overlap 0.388) → VLM 精修 28.59–30.53s (overlap 0.388)；人工 28.0–33.0s

- FunASR paraformer-large (research) with diarization; not production admitted.
- ASR windows are evidence for auto clip selection; VLM re-ranks within them.
- No approved artifact changed; human timeline checkpoint still applies.