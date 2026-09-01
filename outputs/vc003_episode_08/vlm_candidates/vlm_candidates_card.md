# Episode 8 — VLM 自动选镜 v2（research）

- **另一方得知那小子一天得到三十万，因其有钱不还…**：人工窗口 42.0–50.0s；raw 选窗 [(40.5, 46.5)] (overlap [0.474])；evidence 精修 [42.5, 46.5] (overlap 0.5)；相关帧 5/25
- **对白表明有人以三十万购买两样货物，并完成交易…**：人工窗口 15.0–28.0s；raw 选窗 [] (overlap [])；evidence 精修 [15.0, 28.0] (overlap 1.0)；相关帧 3/25
- **交易方交出一张内有三十万、密码为六个八的卡。…**：人工窗口 28.0–33.0s；raw 选窗 [(26.5, 30.5)] (overlap [0.385])；evidence 精修 [28.5, 30.5] (overlap 0.4)；相关帧 4/25

- VLM verdicts are non-deterministic; relevance parse fails closed
- on ambiguity.
- Windows are research drafts, not approved edits; the human timeline
- checkpoint still applies.
- No production admission implied; provider stays research.