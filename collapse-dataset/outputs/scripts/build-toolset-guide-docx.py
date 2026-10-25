"""Build the local-AI toolset guide as a DOCX."""
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

OUT = r"E:\Deepseek\deliverables\conv-20260928-3b54e160\local-ai-toolset-guide-v1.docx"
DATE = "2026-10-04"

doc = Document()
normal = doc.styles["Normal"]
normal.font.name = "Microsoft YaHei"
normal.font.size = Pt(10.5)
normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
for lvl, size in (("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 11.5)):
    st = doc.styles[lvl]
    st.font.name = "Microsoft YaHei"
    st.font.size = Pt(size)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    st.font.color.rgb = RGBColor(0x1F, 0x3B, 0x63)


def code(text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Pt(14)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(text)
    r.font.name = "Consolas"
    r.font.size = Pt(9)
    r.element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
    r.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    return p


# printable width is 6.0 in; keep 0.1 in of slack so Word and LibreOffice agree
PRINTABLE = 5.9
DEFAULT_WIDTHS = {
    2: [1.43, 4.47],
    3: [1.72, 1.77, 2.41],
    4: [1.57, 1.23, 0.93, 2.17],
    5: [1.28, 1.57, 1.28, 0.59, 1.18],
}


def table(headers, rows, widths=None):
    """Fixed-width table so nothing runs past the page margin (printable width is 6.0 in)."""
    n = len(headers)
    if widths is None:
        widths = DEFAULT_WIDTHS.get(n, [6.0 / n] * n)
    t = doc.add_table(rows=1, cols=n)
    t.style = "Table Grid"
    t.autofit = False
    for i, h in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.text = ""
        run = cell.paragraphs[0].add_run(h)
        run.bold = True
        run.font.size = Pt(9)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(v))
            r.font.size = Pt(8.5)
    # a fixed layout plus an explicit grid is what actually keeps Word/LibreOffice inside the margin
    tbl_pr = t._tbl.tblPr
    # python-docx already emits w:tblW and w:tblLayout; appending a second copy is ignored, so edit in place
    layout = tbl_pr.find(qn("w:tblLayout"))
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        tbl_pr.append(layout)
    layout.set(qn("w:type"), "fixed")
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(int(sum(widths) * 1440)))
    tbl_w.set(qn("w:type"), "dxa")
    grid = t._tbl.find(qn("w:tblGrid"))
    if grid is not None:
        for col, w in zip(grid.findall(qn("w:gridCol")), widths):
            col.set(qn("w:w"), str(int(w * 1440)))
    for row in t.rows:
        for i, cell in enumerate(row.cells):
            cell.width = Inches(widths[i])
    doc.add_paragraph()
    return t


doc.add_heading("本地 AI 工具集指南：规则 · 文件 · 卸载", level=0)
p = doc.add_paragraph("版本 1.4 ｜ 生成日期 %s ｜ 适用机器：Redmi 16 Pro 2026（Intel Core Ultra 5 338H）" % DATE)
p2 = doc.add_paragraph("强制规则 · 思考语言：思考、推理、计划与草稿一律使用中文；代码、命令、标识符、路径保持原文。")
p2.runs[0].bold = True
p.runs[0].font.size = Pt(9.5)
p.alignment = WD_ALIGN_PARAGRAPH.LEFT

doc.add_heading("1. 这份文档是什么", level=1)
doc.add_paragraph("本机部署了一套完全本地运行的 AI 工具（识图、读文档、目标检测、异常检测、生成图片），"
                  "通过 MCP 协议接入 DeepSeek Harness，任何对话都能直接调用。全部推理在本机完成，"
                  "不联网、不上传、无 API 费用。本文档给出三样东西：① 工具清单与调用规则；"
                  "② 到底装了哪些文件、放在哪里；③ 如何把它彻底删除干净。")
doc.add_paragraph("配套的机器可读规则在 E:\\Deepseek\\policy\\ai-tools.json，人类可读规则在 "
                  "E:\\Deepseek\\policy\\ai-tool-policy.md；两者是本工具集的“规则源”。")

doc.add_heading("2. 运行环境", level=1)
table(["项目", "内容"], [
    ["机型", "Redmi 16 Pro 2026（笔记本）"],
    ["CPU", "Intel Core Ultra 5 338H，12 逻辑核心"],
    ["GPU", "Intel Arc B370 核显（10 Xe3 / 80 EU），无独立显存，共享内存"],
    ["NPU", "Intel AI Boost（驱动随系统提供，非本工具集安装）"],
    ["内存", "32 GB"],
    ["屏幕", "3200×2000 @200% 165 Hz"],
    ["AI 文件根目录", "D:\\AI_file（约 20.3 GB）"],
    ["D 盘余量", "约 366 GB（安装后）"],
], )
doc.add_paragraph("重要：NPU 只做推理，不能训练；显存为共享内存，所以模型体积与并发数要克制。")

doc.add_heading("3. 工具总表（8 个）", level=1)
table(["工具", "用途", "引擎", "设备", "实测耗时"], [
    ["vision_read_document", "读 PDF / 图片文档", "文字层 → PP-OCR → VLM", "CPU/NPU", "文字层瞬时；OCR 1.3–4.1 s/页"],
    ["vision_ocr", "识别扫描件、截图、标签、表格文字", "PP-OCRv6", "CPU", "0.6–4.1 s"],
    ["vision_describe", "描述图形/图表/场景/照片", "Qwen2.5-VL-3B", "NPU", "11–18 s"],
    ["vision_ask", "就图片提问（计数、方位、读数）", "Qwen2.5-VL-3B", "NPU", "11–18 s"],
    ["vision_status", "查看引擎、设备、预算状态", "—", "—", "瞬时"],
    ["vision_detect", "物体定位 / 计数（给框与分数）", "YOLOX-Tiny（IR）", "NPU", "7 ms（热态）"],
    ["anomaly_score", "无监督良品/不良品筛查（给分数与热力图）", "PatchCore（Anomalib）", "NPU", "41–97 ms"],
    ["image_generate", "文生图（插画、纹理、合成数据）", "FLUX.1-schnell int4", "iGPU", "13–18 s（1024²，4 步）"],
])
doc.add_paragraph("调用方式：在对话中直接说明需求即可，模型侧工具名为 mcp__vision__<工具名>。")

doc.add_heading("4. 调用规则（必须遵守）", level=1)
doc.add_heading("4.1 路由：按输入类型选工具", level=2)
table(["输入", "用哪个工具", "理由"], [
    ["电子原生 PDF（有文字层）", "vision_read_document", "文字层精确且瞬时，不要绕道 OCR"],
    ["扫描件 / 照片里的文字 / 截图 / 标签 / 表格", "vision_ocr", "原生分辨率、无 token 上限、小字准"],
    ["图形 / 图表 / 框图 / 场景 / 照片", "vision_describe 或 vision_ask", "这是视觉语言模型的强项"],
    ["要“在哪里、有几个、占多大”", "vision_detect", "返回框、类别、分数，可加类别过滤"],
    ["只有良品基准、没有缺陷样本", "anomaly_score", "无监督，输出分数与热力图"],
    ["需要一张不存在的图", "image_generate", "本地生成，合成内容须标注"],
])
doc.add_heading("4.2 可信度分级（决定回答怎么措辞）", level=2)
table(["来源", "可信度", "要求"], [
    ["PDF 文字层", "精确", "可直接引用"],
    ["PP-OCR", "高（实测与文字层逐字一致）", "可直接引用"],
    ["视觉语言模型（VLM）", "中偏低：语义可靠、细节与品类不可靠", "必须附来源提示，写明“未与文字层/OCR 交叉校验”；数字与型号写成“疑似”并给出复核途径"],
    ["检测 / 异常分数", "模型输出，不是测量值", "必须以“分数”陈述，不得当作合格证"],
    ["生成图片", "合成内容", "不得当作真实照片或证据"],
])
doc.add_heading("4.3 硬限制", level=2)
table(["限制", "数值", "对策"], [
    ["NPU 单次视觉输入上限", "1024 token ≈ 80 万像素", "服务端自动裁白边并降到 ≤980；要看细节先裁区域"],
    ["MAX_PROMPT_LEN", "NPU 专属，抬高后输出为空", "不要尝试"],
    ["偶发空输出", "模型有时把 EOS 当第一个 token", "服务端用 min_new_tokens 阶梯（1→32→96）自动重试"],
    ["PP-OCR 设备", "上游写死 CPU", "1–4 s/页可接受，不要声称用了 NPU"],
])

doc.add_heading("4.4 生图的时间预算（image_generate 专用）", level=2)
doc.add_paragraph("背景：曾出现“给一个提示词就连续生成数十上百张图、再逐张审查”的情况，导致回答极慢。"
                  "注意工具本身一次调用只出 1 张（FLUX 1024²/4 步：首次含编译约 30–50 s，之后每张 13–18 s），"
                  "批量行为来自调度，因此按下列预算约束：")
table(["项目", "硬性预算"], [
    ["默认张数", "1 张（用户未明确要求多张时只调用一次；模型：FLUX.1-schnell int4，Apache-2.0）"],
    ["上限", "4 张；仅在用户明确要多方案时，且须先告知张数与预计耗时"],
    ["视觉审查", "用户没要求就不审查；要审查时每次请求最多 1 次视觉调用"],
    ["prompt 迭代", "最多 2 轮，之后停下来问用户，不得无限重抽"],
    ["单次请求总时长", "目标 ≤60 s（FLUX 一冷一热约 30–50 s；约 1 张图 + 至多 1 次审查）"],
    ["参数默认", "1024×1024、steps 4、guidance 0.0（FLUX.1-schnell 不用 CFG，0.0 必须显式传递）；用户没要求不改"],
    ["可复现", "要“同一张”时固定 seed，不为挑好看反复换 seed"],
    ["报告格式", "一句话：张数 / 尺寸 / 步数 / 总耗时 / 文件路径"],
])
doc.add_paragraph("一句话记忆：一次调用一张图，要评价只评一次，最多两轮就收手。")
doc.add_heading("4.5 模型变更后的运维规则（必读）", level=2)
doc.add_paragraph("2026-10-05 实际故障：更换生图模型并删除旧模型目录后，其他对话的生图工具报错。"
                  "根因是 MCP 服务端为常驻进程，内存里仍是启动时载入的旧配置（默认模型路径指向已删除的目录），"
                  "而旧代码只在成功时写日志，失败是静默的。")
table(["步骤", "要求"], [
    ["1. 改完模型配置", "必须重启 MCP 服务端：终止旧进程让宿主重新拉起，或重启客户端／新开一个对话"],
    ["2. 重启后自检", "调用 vision_status：四个模型都必须显示 [present]；出现 MISSING 就说明进程仍在跑旧配置，不要再调用工具"],
    ["3. 删除或移动模型文件前", "先确认没有常驻进程依赖它，否则相关工具会静默失效"],
    ["4. 排查入口", "看 vision-mcp.log 末尾：服务端启动时会记录四个 model check，调用失败会记录 image_generate FAILED"],
    ["5. 验证方式", "必须做真实的工具调用，不能只看代码或文件是否存在（本次事故中代码与文件都是对的，坏的是进程里那份旧代码）"],
])
doc.add_paragraph("一句话记忆：改配置 → 重启服务端 → vision_status 确认 [present] → 再调用。")


doc.add_heading("5. 硬件寿命规则（本机为笔记本）", level=1)
doc.add_paragraph("调用本地 AI 时必须同时考虑延长这台电脑的寿命，规则如下：")
for line in [
    "能用 NPU/iGPU 就不占 CPU：同一任务实测 NPU 7 ms vs CPU 21 ms（YOLOX-Tiny），能效差距更大，发热更少、风扇更少转、电池更耐久。",
    "够用即止：文字层 → PP-OCR → VLM → 检测/异常 → 生图/训练，能用毫秒级工具解决就不要动用分钟级的。",
    "一次加载、多次复用：服务端按设备懒加载并缓存管线，空闲不耗电；不要为“预热”空跑，也不要频繁重启服务端（每次都要重新编译模型、重读数 GB 权重）。",
    "重负载先声明：预计超过 60 s 持续满载的任务（训练、批量推理、生图循环）必须先告知使用者，并优先在插电状态下进行；不要同时排多个重负载任务。",
    "不做无谓的大写入：模型只下载一次，包管理器缓存在 D:\\AI_file\\_caches；不要把同一份数据在多处复制，避免 SSD 无谓磨损。",
    "温度监控（本机实测可用）：",
]:
    doc.add_paragraph(line, style="List Bullet")
code("(Get-Counter '\\Thermal Zone Information(*)\\Temperature').CounterSamples |\n"
     "  ForEach-Object { '{0}: {1:N1} C' -f $_.InstanceName, ($_.CookedValue - 273.15) }")
doc.add_paragraph("本机空闲基线约 27.9 ℃。MSAcpi_ThermalZoneTemperature 在本机拒绝访问，不要使用。")
doc.add_paragraph("电池与散热：长时间重负载请插电并保证通风（不要放在床上或沙发上堵住进风口）；"
                  "若厂商提供电池养护/限制充电模式，长期插电时建议开启。", style="List Bullet")
doc.add_paragraph("长任务可中断：把重负载拆成可分批的小任务，允许随时叫停，避免“一跑几小时”。", style="List Bullet")

doc.add_heading("6. 装了哪些文件（清单与路径）", level=1)
doc.add_heading("6.1 目录结构", level=2)
table(["目录", "内容", "体积"], [
    ["D:\\AI_file\\runtime", "Python 3.12.10 运行时", "117 MB"],
    ["D:\\AI_file\\tools", "MinGit 2.56.0", "91 MB"],
    ["D:\\AI_file\\envs\\openvino", "Python 虚拟环境（全部 AI 依赖）", "1.90 GB"],
    ["D:\\AI_file\\models", "4 个模型 + 1 份导出源码（见 6.2）", "11.5 GB"],
    ["D:\\AI_file\\datasets", "自建合成缺陷数据集", "3.8 MB"],
    ["D:\\AI_file\\outputs", "标注图、热力图、生成图", "6.1 MB"],
    ["D:\\AI_file\\mcp", "MCP 视觉服务端", "< 1 MB"],
    ["D:\\AI_file\\logs", "服务端日志 vision-mcp.log", "< 1 MB"],
    ["D:\\AI_file\\workspace", "PDF 渲染页、临时文件", "199 MB"],
    ["D:\\AI_file\\_downloads", "安装包暂存（Python、MinGit）", "64 MB"],
    ["D:\\AI_file\\_caches", "pip / HuggingFace / PyTorch / OpenVINO 缓存", "6.89 GB"],
    ["合计", "", "约 20.3 GB"],
])
doc.add_heading("6.2 模型清单", level=2)
table(["模型", "用途", "体积", "来源与许可"], [
    ["qwen2.5-vl-3b-ov-int4-npu", "识图与视觉问答", "2587 MB", "hf-mirror（Qwen2.5-VL 许可）"],
    ["flux1-schnell-int4-ov", "文生图（主模型，FLUX.1-schnell）", "8821 MB", "hf-mirror，Apache-2.0（LCM Dreamshaper 已于 2026-10-05 删除）"],
    ["patchcore-synth-v1", "异常检测（自训练）", "63 MB", "本机训练，Apache-2.0 工具链"],
    ["yolox-tiny", "目标检测", "49 MB", "OpenVINO Model Zoo 镜像，Apache-2.0"],
    ["yolox-tiny-src", "导出用源码（含补丁）", "< 1 MB", "Megvii YOLOX，Apache-2.0"],
])
doc.add_heading("6.3 Python 依赖（虚拟环境 D:\\AI_file\\envs\\openvino）", level=2)
table(["包", "版本", "包", "版本"], [
    ["Python", "3.12.10", "rapidocr", "3.9.2"],
    ["openvino", "2026.4.1", "anomalib", "2.6.2"],
    ["openvino-genai", "2026.4.1.0", "lightning", "2.6.6"],
    ["openvino-tokenizers", "2026.4.1.0", "torch", "2.14.1"],
    ["numpy", "2.4.6", "torchvision", "0.29.1"],
    ["Pillow", "12.3.0", "timm", "1.0.30"],
    ["opencv-python", "5.0.0.93", "onnx", "1.23.1"],
    ["transformers", "5.5.4", "pandas", "2.3.3（须 <3，anomalib 2.6.2 不兼容 pandas 3）"],
])
doc.add_heading("6.4 本工具集写入系统其他位置的内容（就这两处）", level=2)
table(["位置", "写入内容", "说明"], [
    ["C:\\Users\\<用户>\\.dsh\\profiles\\desktop\\cordis.patch.yml", "一条 insert 补丁（id: mcp-vision）", "注册 MCP 服务端（桌面端）"],
    ["C:\\Users\\<用户>\\.dsh\\profiles\\web\\cordis.patch.yml", "同上", "注册 MCP 服务端（web profile）"],
    ["C:\\Users\\<用户>\\.dsh\\AGENTS.md", "规则 8“本地 AI 工具”", "让所有工作区/对话都遵守工具规则"],
    ["E:\\Deepseek\\AGENTS.md、policy\\*", "规则 7、策略与机器可读配置", "工作区内的规则源与文档"],
])
doc.add_paragraph("除以上四处外，本工具集没有改注册表、没有装服务、没有开机自启、没有替换系统库；"
                  "NPU 驱动是系统自带的，不属于本工具集。")

doc.add_heading("7. 如何完全卸载", level=1)
doc.add_paragraph("卸载分三步：先摘掉注册与规则（让 DSH 不再加载它），再删文件，最后验证。"
                  "整个过程不需要管理员权限，也不会影响系统其他部分。")

doc.add_heading("第 1 步：移除 MCP 注册（必须最先做）", level=2)
doc.add_paragraph("编辑下面两个文件，删除其中以 - insert: 开头、id 为 mcp-vision 的整段（含其下所有缩进行）：")
code("C:\\Users\\<用户>\\.dsh\\profiles\\desktop\\cordis.patch.yml\n"
     "C:\\Users\\<用户>\\.dsh\\profiles\\web\\cordis.patch.yml")
doc.add_paragraph("要删除的段落形如：")
code("- insert:\n"
     "    - id: mcp-vision\n"
     "      name: \"@deepseek-ai/dsh-mcp-client\"\n"
     "      config:\n"
     "        serverName: vision\n"
     "        transport: stdio\n"
     "        command: D:/AI_file/envs/openvino/Scripts/python.exe\n"
     "        args: [ D:/AI_file/mcp/vision-server.py ]")
doc.add_paragraph("验证（应看不到 mcp-vision，且没有 patch 报错）：")
code("dsh --profile web --dump-config | Select-String 'mcp-vision'")

doc.add_heading("第 2 步：移除指令规则", level=2)
doc.add_paragraph("删除工作区 E:\\Deepseek\\AGENTS.md 的“规则 7 · AI 工具调用”，"
                  "以及 C:\\Users\\<用户>\\.dsh\\AGENTS.md 的“规则 8 · 本地 AI 工具”。")
doc.add_paragraph("如果只想停用而不删文件，把策略文件改名即可（例如 ai-tools.json → ai-tools.json.off），"
                  "规则文档仍可留作参考。")

doc.add_heading("第 3 步：删除文件（约 14 GB）", level=2)
doc.add_paragraph("先确认没有残留进程占用（正在跑的会话会锁住模型文件）：")
code("Get-Process | Where-Object { $_.Path -like 'D:\\AI_file\\*' } | Stop-Process -Force")
doc.add_paragraph("确认要删的绝对路径无误后，再删除（此操作不可恢复）：")
code("Test-Path 'D:\\AI_file'          # 先确认路径存在\n"
     "Remove-Item -LiteralPath 'D:\\AI_file' -Recurse -Force")
doc.add_paragraph("如果只想回收空间、保留工具，可以只删缓存与中间产物（约 7 GB，工具仍可用，"
                  "首次调用会重新编译模型、略慢）：")
code("Remove-Item -LiteralPath 'D:\\AI_file\\_caches' -Recurse -Force\n"
     "Remove-Item -LiteralPath 'D:\\AI_file\\workspace' -Recurse -Force\n"
     "Remove-Item -LiteralPath 'D:\\AI_file\\_downloads' -Recurse -Force")

doc.add_heading("第 4 步：验证卸载干净", level=2)
table(["检查", "命令", "期望结果"], [
    ["注册已移除", "dsh --profile web --dump-config | Select-String mcp-vision", "无输出"],
    ["文件已删除", "Test-Path 'D:\\AI_file'", "False"],
    ["无残留进程", "Get-Process python -ErrorAction SilentlyContinue", "无 D:\\AI_file 下的进程"],
    ["工具列表", "新开一个对话，查看可用工具", "不再出现 mcp__vision__* 与 mcp__vision__anomaly_score 等"],
])
doc.add_paragraph("说明：D:\\program_runtime_environment（通用运行时目录）与 %DSH_HOME%\\attachments（图片规范化缓存）"
                  "不属于本工具集，可按需另行清理。")

doc.add_heading("8. 重新安装（可复现）", level=1)
table(["步骤", "关键内容"], [
    ["1. 运行时", "Python 3.12.10 装到 D:\\AI_file\\runtime\\python\\3.12.10；MinGit 到 tools\\git"],
    ["2. 虚拟环境", "python -m venv D:\\AI_file\\envs\\openvino，安装 openvino、openvino-genai、rapidocr、anomalib、onnx 等"],
    ["3. 模型", "Qwen2.5-VL-3B INT4（NPU 识图）、FLUX.1-schnell int4（Apache-2.0，文生图）、YOLOX-Tiny（自动导出 IR）、PatchCore（本地训练）"],
    ["4. 服务端", "D:\\AI_file\\mcp\\vision-server.py（v1.7.0，8 个工具）"],
    ["5. 注册", "在两个 profile 的 cordis.patch.yml 里加 insert 补丁（见 6.4）"],
    ["6. 规则", "部署 policy\\ai-tool-policy.md 与 AGENTS.md 规则，运行 tools\\Install-GlobalPolicy.ps1"],
])
doc.add_paragraph("下载源提示（本机实测）：模型从 hf-mirror.com 取，单文件多连接可达约 1.8 MB/s；"
                  "OpenVINO Model Zoo 的预转换 IR 已下线，检测模型需按官方配方自行导出。")

doc.add_heading("9. 已知限制", level=1)
for line in [
    "NPU 单次视觉输入上限 1024 token（约 80 万像素）：大图会被降采样，细节需先裁区域。",
    "视觉语言模型会“幻觉”：实测把 CH634 说成 CH63034；数字与型号一律以 OCR/文字层为准。",
    "YOLOX-Tiny 在 416 分辨率下框的位置稳定，但类别会错（扭蛋机被识别成 suitcase）。",
    "PatchCore 异常检测只在训练分布内可靠，换产品必须用新的良品样本重训（秒级）。",
    "FLUX.1-schnell 文生图：4 步、不用 CFG（guidance 必须显式传 0.0，否则库默认 7.5 会毁掉画质）；"
                  "首次调用含编译约 30–50 s；画面内文字仍不可靠；生成内容属于合成数据。",
    "PP-OCR 走 CPU（上游写死），当前 1–4 s/页；如需上 NPU 需要给上游打补丁。",
]:
    doc.add_paragraph(line, style="List Bullet")

doc.add_heading("10. 版本记录", level=1)
table(["版本", "日期", "变更"], [
    ["1.0", DATE, "首版：8 个工具全部落地；规则整合（路由、可信度、硬限制、硬件寿命）；文件清单与卸载指南"],
    ["1.1", DATE, "新增：强制中文思考；image_generate 生图时间预算（§4.4，默认 1 张 / 上限 4 张 / 审查≤1 次 / ≤30 s），并写入工具契约"],
    ["1.3", DATE, "删除已弃用的 LCM Dreamshaper 模型（回收 2040 MB）；同步工具集总量（约 20.3 GB）与模型清单"],
    ["1.4", DATE, "新增 §4.5 模型变更后的运维规则（源于 2026-10-05 生图故障复盘）：改配置必须重启服务端并用 vision_status 自检；"
                   "同步策略 §12、机器可读 maintenance 字段与两份注入指令"],
    ["1.2", DATE, "生图模型由 LCM Dreamshaper（1.07 B，MIT）更换为 FLUX.1-schnell int4（Apache-2.0）："
                   "1024²／4 步／不用 CFG，热态 13.2 s、冷态 17.4 s、加载 26–31 s；实测画质与提示词服从度显著提升"],
])

doc.save(OUT)
print("saved:", OUT)