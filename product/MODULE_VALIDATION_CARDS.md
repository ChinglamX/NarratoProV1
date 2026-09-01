# Module Validation Cards

Version: 1.0

本文件保存产品级验证卡。每张卡必须指向可查看产物；详细自动测试仍留在对应测试与 qualification 文件。

## VC-001 — E06 Visual Observation

- Capability Class：Quality Enhancer；OCR 是 Core 的可选辅助。
- User Question：真实短剧画面中，OCR、Detection、VLM 的输出是否能减少人工理解素材的时间？
- Input：13 剧 / 36 集语料的按剧隔离采样帧。
- Tool：PaddleOCR PP-OCRv6、RT-DETR-L、Volcengine Ark VLM。
- Inspectable Output：`evaluation/benchmarks/e06_visual_v1.json`、`evaluation/reports/E06_VISUAL_BENCHMARK_V1.md`。
- Machine Checks：720 帧调用完成；Provider 错误数为 0；容量 probe 已记录。
- Human Review Question：输出是否准确指出字幕、主要人物/物体和镜头关键信息？是否明显减少人工浏览？
- Human Decision：unreviewed。现有“机器预测提升为 GT”不能替代独立人工判断。
- Known Failure / Fallback：Detection 类别大量 unknown；VLM 采样稀疏；可回退到人工选镜头和 OCR 辅助。
- Current Maturity：M2 Tool Verified。
- Next Smallest Proof：产品负责人查看 12 张固定帧的三类输出，逐项选择 useful/revise/reject。
- First Usable Cut Blocker：no。可使用已批准 Timeline 素材或人工选镜头完成首个候选。

## VC-002 — E07 Story Understanding

- Capability Class：Core 的最小事实摘要；完整跨集身份属于 Quality Enhancer。
- User Question：系统给出的角色、事件和冲突摘要是否足以支持营销方向选择？
- Input：真实 FactSet；当前已验证输入主要为 OCR facts。
- Tool：StoryReasoningWorkflow。
- Inspectable Output：`outputs/vc002_episode_08/comparison_card.md`、`comparison_card.json`、`evidence_manifest.json`、完整原片证据段、三个纠正后独立 Claim 原声片段和九张关键帧；真实 Artifact lineage。
- Machine Checks：Episode 8 `RawProviderResponse→SpeechObservation→FactSet→StoryGraph` exact refs 全部落库可读，payload checksum 重算一致；纠正后三个证据片段均由输出侧 accurate seek 生成并含 video/audio，时间窗、关键帧、文件和 checksum 已验证；430 passed / 5 skipped。
- Human Review Question：摘要有没有关键事实错误？是否漏掉决定 Hook 的主要冲突？
- Human Decision：`approved`（2026-08-19，项目负责人）。系统列出的 Episode 8 三条事实信息均确认正确；首版证据片段 seek 错位经纠正后，Claim 2 已再次人工确认正确。Gate 1 Review `46165292-cb25-4f2e-a756-06196607ac50` 已正式批准 exact StoryGraph，范围仅为 transcript-grounded factual summary。
- Known Failure / Fallback：允许人工填写最小 Story Brief，并保留来源时间码。
- Current Maturity：Delivery=M4 Slice Integrated；Episode 8 factual-summary Effect=M3 Human Useful。语义蕴含保持 confidence unavailable、L1 review required，不外推为通用 Story Understanding。
- Next Smallest Proof：使用该 Approved Story 执行 VC-003 的三候选 Gate 2 人工选择。
- First Usable Cut Blocker：yes，但允许人工 Story Brief 兜底，不阻塞于完整 E06/E07 production qualification。

## VC-003 — E08 Marketing Strategy

- Capability Class：Core。
- User Question：候选 Hook 和营销方向是否比人工从零构思更快、更好比较？
- Input：一个真实、人工确认的 Story Brief。
- Tool：Selling Point、Hook、Strategy Candidate、Gate 2。
- Inspectable Output：`outputs/vc003_episode_08/gate2_candidates.json`；持久化 Strategy comparison package `164a0d02-c265-4c3d-bbed-5af2ef52fc9e@1`。
- Machine Checks：契约、候选边界、Gate 2 已测试。
- Human Review Question：至少有一个方向值得制作吗？Hook 是否真实且有吸引力？
- Human Decision：`approved`（2026-08-19，项目负责人）——Gate 2 Review `7734969e-1caa-4a3c-9831-a43c66798cd3` 正式批准 **选项 1「威胁倒叙」**（Decision `972be1c1-d867-48bf-b0b2-77f368547ed5`），选择 Strategy `82f2cdc4-bdf6-4e91-915c-c3e04fd95a3b` / Hook `9cddcf54-e497-4db0-b516-b59eb6e25786`，发布 `approved_creative_brief`（CreativeBrief `bc2c693e-8768-40fc-84d5-fcc00946f80a@1`）与 `approved_variant_plan`（VariantPlan `58a7c392-64f3-4d81-b1df-fbcfedb10c1b@1`）双 pointer。范围仅批准 Episode 8 营销方向，不证明人物身份或通用自动策略理解。
- Known Failure / Fallback：人工直接指定方向、Hook 和目标时长。
- Current Maturity：Delivery=M2 Tool Verified；Effect=M3 Human Useful（Episode 8 单方向人工选择，不外推通用策略生成）。
- Next Smallest Proof：**已完成（2026-08-19）**——以 approved CreativeBrief/VariantPlan 为输入边界执行 Episode 8 Clip、Narration、Timeline 生产，经人工 checkpoint 批准后走通 E10/E11 canonical 全链（IndexTTS 配音 + 混音 + CJK 字幕），候选 `outputs/vc003_episode_08/audio/canonical_e11.mp4` 获项目负责人 `useful`（State v99）。这是首次在真实 approved Story→Brief→Timeline→E10/E11 全链上人工验收。
- First Usable Cut Blocker：yes，但支持人工策略兜底。

## VC-004 — E09 Creative Timeline

- Capability Class：Core。
- User Question：系统能否生成一条值得继续精修的镜头、节奏和解说草案？
- Input：Approved Story/Brief 与真实媒体。
- Tool：CreativeTimelineWorkflow、Timeline Review Workspace。
- Inspectable Output：run `d8eb4cd5` 的 30.27 秒 Preview、Timeline、字幕播放页和 craft draft。
- Machine Checks：完整 Preview、时间基、restart/replay、多 Variant、人工 checkpoint 已验证。
- Human Review Question：Hook、信息顺序、镜头选择和节奏是否值得保留？
- Human Decision：useful_with_revision；工程 Preview 已批准，但正式带时间码 craft 评分未完成。
- Known Failure / Fallback：人工编辑 Timeline、镜头和解说文本。
- Current Maturity：M3 Human Useful；编辑链接近 M4。
- Next Smallest Proof：完成一次 30 秒全片带时间码 review，并实际修改一处镜头和一处解说后重渲染。
- First Usable Cut Blocker：yes；当前已经具备可用基础。

## VC-005 — E10 Voice / Audio / Subtitle

- Capability Class：Core。
- User Question：能否把 Timeline 变成可听、同步、可读的候选，而不是只有文本规划？
- Input：VC-004 Timeline、NarrationLineSet、参考声音、字幕样式。
- Tool：IndexTTS-2 adapter、take selection、conform、MixPlan、ASS renderer。
- Inspectable Output：`outputs/first_usable_cut_v2/` 中七个 WAV、ASS、manifest、`canonical_acceptance.json` 和 canonical MP4。
- Machine Checks：真实 WAV header 时长、take identity、聚合 VoiceAsset、Alignment/Conform/MixedAudio persistence、committed blob URI 和 exact-ref lineage 已验证；全项目 411 passed / 5 skipped，coverage 80.22%。
- Human Review Question：声音自然吗？人名正确吗？解说与画面同步吗？原声是否被保留且不盖住解说？字幕是否可读？
- Human Decision：`useful`（v2）。v1 已确认声音、原声/解说比例和字幕通过，但四句解说密度不足；v2 扩展为七句后，产品负责人复审通过。
- Known Failure / Fallback：人工提供 WAV；基础音量混合；静态 ASS；必要时首版无 BGM/SFX。
- Current Maturity：M4 Slice Integrated；单一样片的人审效果与 canonical Artifact 链均通过，尚未达到 M5 可重复个人使用。
- Next Smallest Proof：从统一入口换第二份真实素材复跑，并记录人工修改次数与耗时。
- First Usable Cut Blocker：no。

## VC-006 — E11 Render / QC / Release

- Capability Class：Core。
- User Question：能否稳定导出带正确画面、声音和字幕的完整 MP4，并明确告诉人哪里失败？
- Input：Conformed Timeline、MixedAudio、ASS、Platform Profile。
- Tool：RenderPlan、FFmpeg command、RenderWorkflow、Technical QC。
- Inspectable Output：`outputs/first_usable_cut_v2/canonical_e11.mp4` 与 `canonical_acceptance.json`；正式 execution/QC Artifact refs 已记录。
- Machine Checks：Temporal RenderWorkflow 成功；30.25s、720×1280 H.264、AAC 48kHz stereo、mean -20.3 dB、max -2.8 dB；TechnicalQC passed、无 blocked code；抽帧确认 libass 字幕烧录。
- Human Review Question：文件是否完整可播？配音、原声、字幕是否都存在且同步？
- Human Decision：`useful`。首次 canonical 字幕因缺 CJK 字体乱码；修复版经机器、七段抽帧和项目负责人整片复核，结论“目前可接受”。
- Known Failure / Fallback：宿主 FFmpeg 无 libass；Docker 镜像无 CJK 字体曾产生乱码。当前 wrapper 显式挂载 `STHeiti Medium.ttc`，字体缺失时 exit 78；长句按 12 字换行。
- Current Maturity：M4 Slice Integrated；尚未达到 M5，也未执行 Release Gate 3。
- Next Smallest Proof：从统一入口换第二份素材复跑，并验证字体、失败提示和人工发布确认。
- First Usable Cut Blocker：no。

## VC-007 — Quality Automation / Scale

- Capability Class：Scale and Automation。
- User Question：在个人工作流被证明有效后，哪些人工步骤值得自动化？
- Input：真实人工 review 和 correction 数据。
- Human Decision：deferred。
- Current Maturity：M0 Specified。
- Next Smallest Proof：First Usable Cut 完成后统计一次人工制作耗时和修改次数。
- First Usable Cut Blocker：no。

## VC-008 — M5 Second-source Repeatability

- Capability Class：Core end-to-end repeatability。
- User Question：换成同剧另一集后，系统是否仍能产出值得继续使用的候选，而不是只对首个样片有效？
- Input：episode 2，82.965s；Rights restricted/internal-only。
- Inspectable Output：`outputs/m5_second_source/candidate_v1/candidate_v1.mp4`、`canonical_e11.mp4`、`canonical_acceptance.json`、七个 WAV、ASS。
- Machine Checks：canonical Temporal Render/QC passed；30.00s、720×1280 H.264、AAC 48kHz stereo、mean -21.2 dB、max -3.2 dB；七段字幕抽帧无乱码/越界；全项目 412 passed / 5 skipped。
- Human Review Question：剧情是否准确？狼群 Hook 是否成立？回溯结构是否清楚？解说、原声和字幕是否可接受？
- Human Decision：`useful`；Candidate v1 结论“可以接受”，canonical E10/E11 成片随后明确“通过”；项目负责人随后以“继续”确认六阶段状态足以继续推进，无需增加中间确认。
- Known Failure / Fallback：FunASR 只给出单一大时间段；本轮 Story 使用 ASR 文本 + 固定帧人工核对。CPU IndexTTS 七句约需 7 分钟。
- Current Maturity：M5 Repeatable Personal Use（当前已批准的导演输入范围）；单份配置支持多源 ingest、候选生成、canonical accept、断点续跑和中文阶段状态。M5 不外推到自动 Story/Strategy/Clip/Narration generation。
- Next Smallest Proof：进入 VC-002，用一个未参与当前导演配置的真实片段生成 transcript-grounded Story Brief，与人工 Brief 并排审核。
- Release Boundary：no public release；Gate 3 未执行。

## VC-009 — Full-series Understanding to Cross-episode Cut

- Capability Class：Core series-to-cut production。
- User Question：系统是否能先理解整剧、统一选题，再跨集生成完整营销闭环，而不是逐集机械生产？
- Input：《山神印觉醒后满山风月皆归我》原片 1–8 集；主片使用 1–6 集。
- Inspectable Output：`outputs/series_main_cut/candidate_v3/candidate_v3.mp4`、`manifest.json`、12 WAV、ASS 和 contact sheet；v1/v2 保留为可回退版本。
- Machine Checks：54.00s、720×1280 H.264、AAC 48kHz stereo、mean -20.0 dB、max -2.5 dB；12 个视觉事件与 12 条独立时间线 TTS 按顺序对应；尾音距片尾 0.46s；CJK 抽帧正常。
- Human Review Question：解说是否与画面同步？是否仍提前透露下一镜头？结尾兑现式收束是否自然？
- Human Decision：pending。v2 的连贯性获认可；其画面错位、提前剧透和尾钩反馈已落实为 v3。
- Known Failure / Fallback：Docker 重启后需显式启动；外部 Desktop 文件访问曾系统级阻塞，已通过重启恢复；命中片段 staging 支持断点复用。
- Current Maturity：Delivery=M2 Tool Verified；Effect=`useful_with_revision`（v2 连贯性通过、v3 声画基本匹配）；模式=`director_assisted_reference`。尚未消费自动生成的声画锚点，不计 M4/M5。
- Next Smallest Proof：实现声画锚定与 TTS 后重排后，用 held-out 短剧生成候选；Codex 不得逐句填写绝对 cue 时间，产品负责人只审核最终成片。
- Release Boundary：restricted/internal-only；Gate 3 未执行。

## VC-010 — Visual–Narration Anchor Held-out Validation

- Capability Class：Core narration/timeline repeatability。
- User Question：Codex 只提供镜头、视觉事件和解说主张，不逐句填写绝对时间时，工具能否依据真实 TTS 时长生成不提前剧透的声画排程？
- Input：同剧未参与 Candidate v3 的第 7–8 集；十个四秒镜头、十个视觉事件、七条解说主张；Rights restricted/internal-only。
- Inspectable Output：`outputs/heldout_episode_7_8/candidate_v1/candidate_v1.mp4`、`canonical_e11.mp4`、`canonical_acceptance.json`、两个 ingest manifest、候选 manifest、七个 WAV、ASS、contact sheet；轻量索引见 `product/REFERENCE_CANDIDATE_INDEX.md`。
- Machine Checks：候选与 canonical 均为 40.00s、720×1280 H.264/AAC；canonical mean -20.3 dB、max -2.0 dB；七条 cue 均在真实 TTS 后由工具排程；绝对时间人工覆盖 0/7；blocking anchor finding 0；两次独立 canonical run 均 TechnicalQC passed、blocked_codes=[]，最终 MP4 checksum 完全相同；`make check` 427 passed / 5 skipped，80.42% coverage。
- Human Review Question：剧情是否清楚、声画是否匹配、三十万原声保护是否自然、结尾威胁是否成立？
- Human Decision：`useful`（2026-08-19，项目负责人完整成片判断）。剧情、声画、三十万原声保护和结尾威胁整体达到继续使用标准；未要求逐句调时。
- Known Failure / Fallback：当前视觉事件与解说文本仍由 Codex Producer 生成；自动视觉事件提取不在本验证声明内。三处 gap warning 为保留画面/原声的非 blocker，需整片听感确认。
- Current Maturity：Anchor scheduling Effect=M3 Human Useful；该 held-out 切片 Delivery=M4 Slice Integrated（多源 exact refs、Temporal Render/QC、可恢复复跑）。不是自动 Story/Strategy/Clip/Narration generation proof。
- Next Smallest Proof：单一多源入口与阶段状态已完成；转入 VC-002 Story Brief 自动生成验证。
- Release Boundary：restricted/internal-only；Gate 3 未执行。
