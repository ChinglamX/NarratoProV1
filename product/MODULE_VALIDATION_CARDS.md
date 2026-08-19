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
- Inspectable Output：真实运行 Artifact lineage；`scripts/accept_e07_story_real_data.py`。
- Machine Checks：四阶段 Workflow 和 Artifact 持久化成功。
- Human Review Question：摘要有没有关键事实错误？是否漏掉决定 Hook 的主要冲突？
- Human Decision：unreviewed；当前 OCR-only 运行产生零事件，不能评价剧情理解效果。
- Known Failure / Fallback：允许人工填写最小 Story Brief，并保留来源时间码。
- Current Maturity：M2 Tool Verified（工作流），内容效果仍为 M0/M1。
- Next Smallest Proof：选一个 3–5 分钟片段，提供人工 Story Brief 与系统 Story 输出并排审核。
- First Usable Cut Blocker：yes，但允许人工 Story Brief 兜底，不阻塞于完整 E06/E07 production qualification。

## VC-003 — E08 Marketing Strategy

- Capability Class：Core。
- User Question：候选 Hook 和营销方向是否比人工从零构思更快、更好比较？
- Input：一个真实、人工确认的 Story Brief。
- Tool：Selling Point、Hook、Strategy Candidate、Gate 2。
- Inspectable Output：Strategy comparison package 和 Review Web。
- Machine Checks：契约、候选边界、Gate 2 已测试。
- Human Review Question：至少有一个方向值得制作吗？Hook 是否真实且有吸引力？
- Human Decision：unreviewed。
- Known Failure / Fallback：人工直接指定方向、Hook 和目标时长。
- Current Maturity：M1 Code Verified。
- Next Smallest Proof：用 VC-002 的同一片段生成 3 个候选，由产品负责人选择或全部拒绝。
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
- Human Decision：`useful`；Candidate v1 结论“可以接受”，canonical E10/E11 成片随后明确“通过”。
- Known Failure / Fallback：FunASR 只给出单一大时间段；本轮 Story 使用 ASR 文本 + 固定帧人工核对。CPU IndexTTS 七句约需 7 分钟。
- Current Maturity：M4 Human Useful + canonical integrated on second source；单份配置、六阶段中文状态和断点续跑入口已工程验证，但尚待非开发者可理解性确认，因此不计 M5。
- Next Smallest Proof：项目负责人查看 `product/PERSONAL_CUT_GUIDE.md` 与 `personal_cut_status.json`，确认能理解当前进度和失败恢复位置。
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
- Inspectable Output：`outputs/heldout_episode_7_8/candidate_v1/candidate_v1.mp4`、`manifest.json`、七个 WAV、ASS、contact sheet；轻量索引见 `product/REFERENCE_CANDIDATE_INDEX.md`。
- Machine Checks：40.00s、720×1280 H.264/AAC、mean -20.3 dB、max -2.9 dB；七条 cue 均在真实 TTS 后由工具排程；绝对时间人工覆盖 0/7；blocking anchor finding 0；角色、导演决策、工具输出与 Release 状态已分栏记录；`make check` 424 passed / 5 skipped，80.42% coverage。
- Human Review Question：剧情是否清楚、声画是否匹配、三十万原声保护是否自然、结尾威胁是否成立？
- Human Decision：`useful`（2026-08-19，项目负责人完整成片判断）。剧情、声画、三十万原声保护和结尾威胁整体达到继续使用标准；未要求逐句调时。
- Known Failure / Fallback：当前视觉事件与解说文本仍由 Codex Producer 生成；自动视觉事件提取不在本验证声明内。三处 gap warning 为保留画面/原声的非 blocker，需整片听感确认。
- Current Maturity：Anchor scheduling Delivery=M2 Tool Verified；Effect=`useful`，达到 M3 Human Useful。不是自动 Story/Strategy/Clip generation proof。
- Next Smallest Proof：将同一 held-out 配置和自动 Anchor Plan 接入 canonical E10/E11 Artifact 链，验证 exact refs、Temporal Render/QC 和可恢复复跑；无需重复内容方向确认。
- Release Boundary：restricted/internal-only；Gate 3 未执行。
