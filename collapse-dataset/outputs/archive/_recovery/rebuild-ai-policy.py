import json

MD = r'''# AI 工具调用规则（AI Tool Calling Policy）

- 版本：1.9.0 ｜ 更新：2026-10-05 ｜ 适用：**所有工作区、所有对话**
- 规则源在本文件；机器可读版 `policy\ai-tools.json`
- **思考语言：一律用中文**（推理、计划、草稿、内部独白）；代码、命令、标识符、路径保持原文
- 重建说明：原文件随 E: 盘清空丢失，本文件按 2026-10-05 审计后的 v1.9.0 结构与规则语义重建（2026-10-11）

**目的**：让 Agent 在"看图 / 读文档 / 出图 / 检测 / 筛查"时**选对工具、知道边界、不误信结果**，
并在使用本地算力时**兼顾这台笔记本的寿命**。

---

## 1. 工具清单（8 个，全部本地推理、无网络、无费用）

| 工具 | 后端 | 设备 | 实测耗时 | 说明 |
|---|---|---|---|---|
| `vision_read_document(path, pages, dpi, prefer)` | PDF 文字层 → PP-OCR → VLM | CPU/NPU | 文字层瞬时；OCR 1.3–4.1 s/页；VLM 11–18 s | **文档首选入口**，自动分流；`pages` 支持 `'1'`/`'1,3'`/`'2-5'` |
| `vision_ocr(image_path)` | rapidocr PP-OCRv6（OpenVINO） | **CPU**（上游写死） | 0.6–4.1 s | 原生分辨率、**无 token 上限**；小字、表格、引脚图都能读 |
| `vision_describe(image_path)` | Qwen2.5-VL-3B INT4 | **NPU** | 11–18 s | 图形/图表/框图/场景/照片 |
| `vision_ask(image_path, question)` | 同上 | NPU | 11–18 s | 视觉问答：计数、方位、图表读数、缺陷提问 |
| `vision_status()` | — | — | 瞬时 | 引擎、设备、token 预算，以及各模型的 `[present]/[MISSING]` |
| `vision_detect(image_path, conf, iou, classes, device)` | YOLOX-Tiny（OpenVINO IR） | **NPU** | **7 ms**（热态） | 物体定位/计数：返回框、类别、分数，并写标注图 |
| `anomaly_score(image_path, device)` | PatchCore（Anomalib → OpenVINO） | **NPU** | 41–97 ms | 无监督良品/不良品筛查：分数 + 判定 + 热力图；**只训练正常样本** |
| `image_generate(prompt, ...)` | **FLUX.1-schnell int4**（OpenVINO GenAI） | **iGPU** | **13–18 s**（1024²，4 步） | 文生图；时间步蒸馏，**4 步、不用 CFG**；许可 Apache-2.0 |

模型侧工具名形如 `mcp__vision__vision_ocr`。服务端 `D:\AI_file\mcp\vision-server.py`（v1.11.0）。
模型：`qwen2.5-vl-3b-ov-int4-npu`、`pp-ocrv6-small`、`yolox-tiny`、`patchcore-synth-v1`、`flux1-schnell-int4-ov`。

## 2. 路由规则（按顺序判断，命中即用）

```
1) 是 PDF 且是电子原生（有文字层）  → vision_read_document        ← 精确、瞬时，禁止绕道 OCR
2) 扫描件/照片里的文字/截图/标签     → vision_ocr                  ← 原生分辨率，小字也准
3) 图形、图表、框图、曲线、场景、照片 → vision_describe / vision_ask
4) 要"在哪里/有几个/占多大"的框      → vision_detect
5) 只有"良品基准"没有缺陷样本        → anomaly_score
6) 需要具体数值（型号/序列号/尺寸/电压/剂量）
                                    → 必须来自 文字层 或 vision_ocr；**禁止采信 VLM**
7) 图片很大且要看细节               → 先裁出目标区域再调用（VLM 会把图缩到 ≤980 token）
8) 表格                           → vision_ocr（VLM 只适合给结构提示，不适合抄表）
9) 需要一张不存在的图               → image_generate（默认只出 1 张）
```

**一句话记忆**：**文字走 OCR/文字层，图形走 VLM；数字只信 OCR。**

## 3. 硬限制与已知缺陷（必须知道，否则会白等）

| 限制 | 数值/表现 | 对策 |
|---|---|---|
| **NPU 视觉输入上限** | **≤1024 token ≈ 80 万像素**；超过直接报错 | 服务端自动裁白边并降到 ≤980；要细节**先裁区域** |
| `MAX_PROMPT_LEN` | **NPU 专属**，GPU/CPU 拒绝；抬高后**输出为空** | 不要试图抬高 |
| **空输出（偶发）** | 模型有时把 EOS 当第一个 token | 服务端用 `min_new_tokens` 阶梯（1→32→96）自动重试 |
| 大图必被降采样 | 4096×2730 的照片会降到约 26% | 主体/姿态/配色可靠；**面部、纹理、小字会丢** → 裁切或改 OCR |
| PP-OCR 走 CPU | 上游 `compile_model(..., device_name="CPU")` 写死 | 1–4 s/页可接受，NPU 留给 VLM；**不要声称 OCR 用了 NPU** |
| **加密 PDF 不支持** | 需要用户密码的 PDF 无法读取（owner 密码但空用户密码可开的可以） | 工具返回 `READ FAILED [RuntimeError]: password-protected PDF ...`；请先解密或导出无保护副本 |
| VLM 幻觉 | 实测把型号 CH634 说成 "CH63034" | 标识符/数字**一律以 OCR/文字层为准** |
| VLM 输出长度 | 约 400–900 字符/次 | 长文档**逐页**读 |
| 生图首次调用 | 含模型编译 30–50 s | 稳态 13–18 s/张（1024²/4 步） |

## 4. 结果可信度与验证

1. **可信度分级**：文字层 = 精确；PP-OCR = 高（实测与文字层逐字一致）；VLM = **中偏低**（语义可靠、细节不可靠）；
   检测/异常分数 = **模型输出，不是测量值**；生成图片 = **合成内容**。
2. **允许"仅凭 VLM"回答，但必须给出提示**：不因缺少 OCR 而拒答；只要是视觉模型给的结论，就必须附**来源提示**：

   > ⚠️ 来源提示：以下内容由本地视觉模型（Qwen2.5-VL-3B @ NPU，耗时 〔X〕s）生成，
   > **未与文字层/OCR 交叉校验**；其中数字、型号、标签文字等关键信息可能有误。
   > 需要精确值时，请让我用 `vision_ocr` 复核。

3. **数字/型号/标签文字**：可先给出，但必须写成"**疑似…**"并在同一句给出复核途径（`vision_ocr`）。
4. **禁止措辞**：不得把 VLM 输出说成"已确认/精确读取/已校验"；只有文字层或 OCR 支撑时才可如此表述。
5. **无精确值的描述**（场景、布局、姿态、配色、物体类别）：可按 VLM 结论直接陈述，但仍须标注工具与耗时。
6. **异常分数**：以"分数"陈述，不得当作合格证；阈值需按产线误检/漏检代价标定。
7. **生成图片**：属合成数据，**不得当作真实照片或真实测量证据**。

## 5. 调用规范

1. **路径**：全部传**绝对 Windows 路径**；PDF 用 `vision_read_document`（不要先转图再 OCR）。
2. **分页**：`pages` 支持 `'1'`、`'1,3'`、`'2-5'`；`dpi` 默认 150（表格/小字可提到 200–300）。
3. **优先低成本路径**：文字层 > PP-OCR > VLM > 检测/异常 > 生图/训练。
4. **中间产物**：渲染页缓存于 `D:\AI_file\workspace\pdf-pages\`；服务端日志 `D:\AI_file\logs\vision-mcp.log`。
5. **跨工作区写入**：`D:\AI_file` 在工作区之外，写入需提权；只读调用不需要。
6. **排查顺序**：**先看工具返回的文本**（失败会返回 `READ FAILED …` / `GENERATION FAILED …`），再看日志。

## 6. 隐私与成本

- **全部本地推理**：无网络请求，**数据不出本机**。涉密/客户资料可放心交给这些工具。
- **无 API 费用**：成本是**时间与电力**，所以按"最省的够用工具"选。
- 需要外部模型时走云端需另经许可，**不得默认外发**。

## 7. 工具落地情况与备选模型

8 个工具**全部已落地**（原"预留清单"已清空）。

**备选生图模型**（换 `DSH_T2I_MODEL` 即可）：
- **FLUX.1-schnell int4**（8.61 GB，Apache-2.0）— **当前主力**，1024²/4 步，热态约 13 s
- FLUX.1-schnell int8（15.73 GB，未下载）
- SDXL base int8（3.27 GB，openrail++，原生 1024²，约 3.5 B 参数）
- LCM Dreamshaper v7（1.07 B，MIT，512² 热态 0.5 s／1024² 2.9 s，风格服从度弱）——**已于 2026-10-05 按用户决定删除**

**Z-Image（阿里通义，6B，Apache-2.0）**：文本编码器为 **Qwen3-4B**，中文与画面内中英文字渲染是其强项；
但官方 fp16 体积 30.64 GB 本机装不下，且本机 `openvino_genai` **没有 `z_image` 高层工厂**，
只能用第三方 int4 OpenVINO 版（5.39 GB）并需独立 venv（其依赖链要求替换 transformers 等）。

## 8. 变更流程

1. 改本文件 + `policy\ai-tools.json`（两者必须同步）
2. 若影响所有对话，同步 `policy\deploy\global-agents.md`
3. 运行 `E:\Deepseek\tools\Install-GlobalPolicy.ps1` 重新部署全局副本
4. 在 `logs\<conv-id>\` 留一条变更日志

## 9. 快速参考卡

| 我要… | 用 |
|---|---|
| 读一份 PDF | `vision_read_document`（文字层自动优先） |
| 读扫描件/截图/标签 | `vision_ocr` |
| 看一张照片/图表讲清楚 | `vision_describe` |
| 问图里"有几个/在哪/是什么" | `vision_ask`（语义） / `vision_detect`（给框和分数） |
| 抄型号、序列号、数字 | `vision_ocr`（**永远不要用 VLM 抄数字**） |
| 表格 | `vision_ocr` |
| 良品/不良品筛查（无缺陷样本） | `anomaly_score`（分数 + 热力图） |
| 生成一张插画/纹理/合成样本 | `image_generate`（本地，无网络；默认 1 张） |
| 查后端状态 | `vision_status` |

## 10. 硬件寿命（每次调用本地 AI 都要考虑）

本机是**笔记本**（核显 + 16 GB 共享内存，无独立显存），散热与电池寿命是真实约束。

1. **能用 NPU/iGPU 就不占 CPU**：同一任务实测 NPU 7 ms vs CPU 21 ms（YOLOX-Tiny），能效差距更大——发热更少、风扇更少转、电池更耐久。
2. **够用即止，选最省的够用工具**：文字层 → PP-OCR → VLM → 检测/异常 → 生图/训练。
3. **一次加载、多次复用**：服务端按设备**懒加载并缓存**管线，空闲不耗电；
   **不要为了"预热"空跑**，也不要频繁重启服务端（每次都要重新编译模型、重读数 GB 权重）；
   **配置变更后的必要重启除外**——那种情况必须重启并自检，见 §12。
4. **重负载先声明**：预计 **>60 s 持续满载**的任务（训练、批量推理、生图循环）必须**先告知用户**，
   并**优先在插电状态**下进行；**不要同时排多个重负载任务**。
   （现役生图模型 FLUX 单张 13–18 s 属中等负载；**批量生图仍按重负载处理**。）
5. **不做无谓的大写入**：模型只下载一次，包管理器缓存在 `D:\AI_file\_caches`；避免 SSD 无谓磨损。
6. **温度监控（本机实测可用）**：

   ```powershell
   (Get-Counter '\Thermal Zone Information(*)\Temperature').CounterSamples |
     ForEach-Object { '{0}: {1:N1} C' -f $_.InstanceName, ($_.CookedValue - 273.15) }
   ```

   本机基线约 **27.9 °C**（空闲）。`MSAcpi_ThermalZoneTemperature` 在本机**拒绝访问**，不要用。
7. **电池与散热**：长时间重负载请**插电 + 保证通风**（不要放在床上/沙发上堵住进风口）；
   若厂商提供电池"养护/限制充电"模式，长期插电时建议开启。
8. **长任务可中断**：把重负载拆成可分批的小任务，允许随时叫停。

## 11. 生图的时间预算（`image_generate` 专用 · 硬规则）

**背景**：用户反馈过——给一个提示词后，Agent 会连续生成数十甚至上百张图，再逐张审查，回答极慢。
注意：**工具本身一次调用只生成 1 张**（FLUX 1024²/4 步：首次含编译约 30–50 s，之后每张 13–18 s），
批量行为来自 Agent 自己的调度，因此必须从调度上约束。

1. **默认只生成 1 张**。用户没有明确要求"多张 / 几个方案 / 多试几次"时，**只调用一次**。
2. **上限 4 张**。用户明确要多方案时才可增加，并且**先把张数与预计耗时告知用户**。**严禁**生成数十或上百张。
3. **审查预算**：用户没要求评价时，**不要**用 `vision_describe`/`vision_ask` 去"检查"生成的图——
   直接把文件路径交给用户。用户要求评价时，**每次请求最多 1 次视觉调用**。
4. **迭代预算**：prompt 调整**最多 2 轮**；仍不满意就停下来问用户，**不要自行无限重抽**。
5. **单次请求总时长目标 ≤60 s**（FLUX 一冷一热即约 30–50 s）；预计超过就先说明再继续。
6. **参数默认**：**1024×1024、steps 4、guidance 0.0**（FLUX.1-schnell 是时间步蒸馏模型，
   `guidance_scale=0.0` **必须显式传递**——库默认 7.5 是 SD 时代的值，会让画质崩坏）；用户没要求就不改。
7. **可复现**：用户要"同一张"时固定 `seed`；不要为了"更好看"反复换 seed 抽卡。
8. **报告格式**：一句话给出〔张数 / 尺寸 / 步数 / 总耗时 / 文件路径〕，不要罗列每次尝试的细节。

> 一句话记忆：**一次调用一张图，要评价只评一次，最多两轮就收手。**

## 12. 模型变更后的运维规则（2026-10-05 实际故障教训）

**事故**：更换生图模型并删除旧模型目录后，**其他对话的生图工具报错**。
**根因**：MCP 服务端是**常驻进程**，Python 已把旧配置载入内存——它仍指向**已被删除的旧模型目录**；
而旧代码**只在成功时写日志**，失败是静默的，排查只能靠进程启动时间。

1. **改完模型配置，必须重启 MCP 服务端进程**（终止旧进程让宿主重新拉起，或重启客户端/新开对话），
   否则旧配置会一直留在内存里。
2. **重启后必须调用 `vision_status` 确认**：它会列出四个模型的路径与 `[present]/[MISSING]`。
   **看到 `MISSING` 就说明进程还在跑旧配置，不要继续调用工具**。
3. **删除/移动模型文件前，先确认没有常驻进程依赖它**。
4. 服务端 v1.9 起：启动时把四个模型的自检结果写进 `vision-mcp.log`，失败调用也会写日志；
   v1.11 起：失败**作为文本返回**给调用方（见第 6 条）。
5. **验证要用真实的工具调用**，不要只看代码或文件是否存在。
6. **工具失败要「返回错误文本」，不要抛异常**：MCP 框架**不会**把异常消息转发给调用方，
   只会显示一句 `Error executing tool <name>`——所以任何失败都必须**作为正常文本返回**
   （`READ FAILED [...]` / `GENERATION FAILED [...]`，写明原因与解决办法），同时写入日志。
   排查顺序：**先看工具返回的文本，再看 `vision-mcp.log`**。
'''

TOOLS = {
    "policyVersion": "1.9.0",
    "updatedAt": "2026-10-05",
    "rebuiltAt": "2026-10-11",
    "rebuiltNote": "重建版：原文件随 E: 盘清空丢失；按 2026-10-05 审计后的 v1.9.0 结构与规则语义重建。",
    "policyDoc": "policy\\ai-tool-policy.md",
    "scope": "all workspaces and conversations",
    "thinkingLanguage": "zh-CN: reason, plan and draft in Chinese; keep code, commands, identifiers and paths verbatim",
    "transport": "MCP stdio server registered as id: mcp-vision in the DSH profile patch (must be wrapped in an insert)",
    "server": {
        "path": "D:\\AI_file\\mcp\\vision-server.py",
        "version": "1.11.0",
        "venv": "D:\\AI_file\\envs\\openvino",
        "log": "D:\\AI_file\\logs\\vision-mcp.log",
        "registry": "D:\\AI_file\\registry.json"
    },
    "tools": [
        {"name": "vision_read_document", "backend": "PDF text layer -> PP-OCR -> VLM", "device": "CPU/NPU",
         "latencyMs": [0, 4100, 18000], "useFor": "documents (PDF and page images)",
         "params": "path, pages='1'|'1,3'|'2-5', dpi=150, prefer=auto|text|vlm",
         "limits": "text layer used when a page has >=120 chars; password-protected PDFs are refused with a clear message"},
        {"name": "vision_ocr", "backend": "rapidocr 3.9.2 PP-OCRv6-small (OpenVINO)", "device": "CPU",
         "latencyMs": [600, 4100], "useFor": "scans, photos of text, screenshots, labels, tables",
         "limits": "no token limit; native resolution; upstream hardcodes CPU"},
        {"name": "vision_describe", "backend": "Qwen2.5-VL-3B INT4 (OpenVINO GenAI)", "device": "NPU",
         "latencyMs": [11000, 18000], "useFor": "figures, charts, diagrams, scenes, photos",
         "limits": "auto crop + downscale to <=980 visual tokens"},
        {"name": "vision_ask", "backend": "Qwen2.5-VL-3B INT4 (OpenVINO GenAI)", "device": "NPU",
         "latencyMs": [11000, 18000], "useFor": "visual QA, counting, spatial relations, chart reading",
         "limits": "auto crop + downscale to <=980 visual tokens"},
        {"name": "vision_status", "backend": "-", "device": "-", "latencyMs": [0, 0],
         "useFor": "engine, device, budget, and per-model [present]/[MISSING] health check", "limits": "none"},
        {"name": "vision_detect", "backend": "YOLOX-Tiny (OpenVINO IR)", "device": "NPU", "latencyMs": [7, 60],
         "useFor": "locating and counting objects, defect localisation, base model for fine-tuning",
         "params": "image_path, conf=0.25, iou=0.45, classes='', device=NPU, max_det=30, annotate_image=True",
         "limits": "COCO 80 classes; static 416x416 input; tiny model, so scores are modest on large photos"},
        {"name": "anomaly_score", "backend": "PatchCore (OpenVINO IR, Anomalib)", "device": "NPU",
         "latencyMs": [41, 97],
         "useFor": "unsupervised surface inspection against a known-good baseline",
         "params": "image_path, device=NPU, save_heatmap=True",
         "limits": "trained on normal samples only; currently the synthetic demo model; input RGB [0,1] at 256x256; the score is model output, not a measurement"},
        {"name": "image_generate", "backend": "FLUX.1-schnell int4 (OpenVINO GenAI)", "device": "iGPU",
         "latencyMs": [13000, 18000],
         "useFor": "illustrations, textures and synthetic training data from a text prompt",
         "params": "prompt, negative_prompt='', width=1024, height=1024, steps=4, guidance=0.0, seed=-1, device=GPU",
         "limits": "timestep-distilled: 4 steps and guidance_scale=0.0 must be passed explicitly (the library default 7.5 would wreck it); Apache-2.0; first call includes compilation (30-50 s)"}
    ],
    "routing": [
        "born-digital PDF -> vision_read_document (text layer first; never OCR a text-layer PDF)",
        "scanned or photographed text, screenshots, labels -> vision_ocr",
        "figures, charts, diagrams, scenes, photos -> vision_describe or vision_ask",
        "numbers, part numbers, serial numbers, dimensions -> must come from the text layer or vision_ocr; never from the VLM",
        "large image with fine detail -> crop the region first",
        "tables -> vision_ocr",
        "locate or count objects -> vision_detect",
        "screen a part against a known-good baseline (no labelled defects) -> anomaly_score",
        "need a picture that does not exist -> image_generate (one image per call by default)",
        "numbers that come out of a detection (counts, positions) are model output, not OCR: state the confidence and the threshold used",
        "generated images are synthetic: never present them as photographs of a real object",
        "anomaly scores are model output, not measurements: report them as such and never as a pass/fail certificate"
    ],
    "hardLimits": {
        "npuVisualTokens": 1024,
        "npuPixelsApprox": 800000,
        "serverBudgetTokens": 980,
        "maxPromptLen": "NPU-only option; accepting a larger value still yields empty output, so it is unusable",
        "emptyOutput": "model occasionally samples EOS first; server retries with a min_new_tokens ladder (1 -> 32 -> 96)",
        "ocrDevice": "CPU (upstream hardcodes device_name=CPU)",
        "vlmHallucination": "identifiers and numbers must be verified by OCR or the text layer",
        "encryptedPdf": "not supported: a PDF with a user password cannot be read; owner-password-only files that open with an empty password are fine. The tool returns 'READ FAILED [RuntimeError]: password-protected PDF ...'"
    },
    "trust": {
        "textLayer": "exact",
        "ppocr": "high (matches the text layer verbatim in tests)",
        "vlm": "medium-low: reliable on gist, unreliable on detail and categories",
        "yolox": "medium: boxes are stable and device-independent, but class labels can be wrong",
        "patchcore": "medium-high on its own training distribution; it will not transfer to a different product without retraining",
        "imageGeneration": "synthetic by construction: usable as illustration or augmentation data, never as evidence about the real world"
    },
    "vlmOnlyAnswerPolicy": {
        "allowed": True,
        "decidedBy": "user, 2026-10-04",
        "noticeRequired": True,
        "noticeTemplate": "⚠️ 来源提示：以下内容由本地视觉模型（Qwen2.5-VL-3B @ NPU，耗时 {seconds}s）生成，未与文字层/OCR 交叉校验；其中数字、型号、标签文字等关键信息可能有误。需要精确值时，请让我用 vision_ocr 复核。",
        "numbersMustBeHedged": True,
        "hedgeWord": "疑似",
        "verificationTool": "vision_ocr",
        "forbiddenPhrasing": ["已确认", "精确读取", "已校验", "verified", "exact"],
        "noPreciseValueContent": "scene, layout, pose, colour and object-category descriptions may be stated directly, but the tool and elapsed time must still be named"
    },
    "imageGenerationBudget": {
        "defaultImages": 1,
        "maxImages": 4,
        "requiresExplicitRequestForMore": True,
        "announceCountAndTimeFirst": True,
        "maxVisionReviewCallsPerRequest": 1,
        "reviewOnlyWhenAsked": True,
        "maxPromptIterations": 2,
        "targetTotalSeconds": 60,
        "defaults": "1024x1024, steps 4, guidance 0.0 (FLUX.1-schnell, no CFG)",
        "measured": {"coldSeconds": 17.4, "warmSeconds": 13.2, "loadSeconds": 26.0, "resolution": "1024x1024", "steps": 4},
        "reproducibility": "fix seed when the user asks for the same image; do not re-roll seeds for taste",
        "report": "one line: count / size / steps / total time / file path",
        "forbidden": "dozens or hundreds of images per request, per-image review loops, unbounded retries"
    },
    "hardwareLongevity": {
        "rationale": "this is a laptop: thermals, fan wear and battery life are real constraints",
        "rules": [
            "prefer NPU/iGPU over CPU (same work, far less heat)",
            "use the cheapest adequate tool (text layer > OCR > VLM > detect/anomaly > generation/training)",
            "pipelines are cached per device: do not warm up or restart the server needlessly (exception: a configuration change requires a restart, see maintenance)",
            "announce any job above 60 s of sustained load, prefer AC power, never run heavy jobs concurrently",
            "avoid pointless large writes; models are downloaded once and cached",
            "monitor the ACPI thermal zone (idle baseline about 27.9 C on this machine); MSAcpi_ThermalZoneTemperature is access-denied here",
            "keep long jobs interruptible and split them into batches"
        ]
    },
    "maintenance": {
        "rule": "after changing any model path, restart the MCP server process and verify with vision_status",
        "why": "the server is a long-lived process: it keeps the configuration it loaded at startup, so a deleted or replaced model directory makes tools fail silently (happened 2026-10-05)",
        "verify": "call vision_status; every model line must read [present]",
        "diagnose": "read the tail of D:\\AI_file\\logs\\vision-mcp.log (v1.9 logs model checks at startup; v1.11 returns failures as text)",
        "never": "do not delete or move a model directory while a server process may still reference it",
        "returnErrorsAsText": "tools return failure messages as normal text (READ FAILED / GENERATION FAILED) because the MCP layer hides exception text from callers; every failure is also written to vision-mcp.log"
    },
    "privacy": "all inference is local; no network calls; nothing leaves the machine",
    "cost": "no API cost; choose the cheapest adequate tool to save time and power",
    "reservedTools": [],
    "reservedToolsNaming": {
        "confirmedBy": "user, 2026-10-04",
        "convention": "vision_* for perception, image_* for generation, anomaly_* for anomaly scoring",
        "confirmed": ["vision_detect"],
        "planned": [],
        "deployed": ["vision_detect", "anomaly_score", "image_generate"]
    },
    "alternatives": {
        "imageGeneration": [
            {"model": "FLUX.1-schnell int4", "size": "8.61 GB", "license": "Apache-2.0", "note": "current default, 1024x1024 in 4 steps"},
            {"model": "FLUX.1-schnell int8", "size": "15.73 GB", "license": "Apache-2.0", "note": "not downloaded"},
            {"model": "SDXL base int8", "size": "3.27 GB", "license": "openrail++", "note": "native 1024, about 3.5 B params, 20-25 steps"},
            {"model": "LCM Dreamshaper v7", "size": "2.04 GB", "license": "MIT", "note": "deleted on 2026-10-05 by user decision"},
            {"model": "Z-Image-Turbo", "size": "30.64 GB official / 5.39 GB third-party int4 OV", "license": "Apache-2.0",
             "note": "6B, text encoder is Qwen3-4B (strong Chinese); openvino_genai 2026.4.1 has NO z_image factory, so it needs a separate venv and the optimum-intel@zimage fork"}
        ]
    },
    "changeProcess": [
        "edit policy\\ai-tool-policy.md and policy\\ai-tools.json together",
        "mirror to policy\\deploy\\global-agents.md when it affects every conversation",
        "run tools\\Install-GlobalPolicy.ps1",
        "write a change log under logs\\<conv-id>\\"
    ]
}

open(r"E:\deepseek\policy\ai-tool-policy.md", "w", encoding="utf-8", newline="\r\n").write(MD)
open(r"E:\deepseek\policy\ai-tools.json", "w", encoding="utf-8", newline="\r\n").write(
    json.dumps(TOOLS, ensure_ascii=False, indent=2) + "\n")
print("[OK] ai-tool-policy.md 写入完成")
print("[OK] ai-tools.json 写入完成")