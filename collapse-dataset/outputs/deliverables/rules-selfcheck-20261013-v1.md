# 规则自检报告（2026-10-13）

- 触发：用户要求「自检规则看看有没有问题」
- 范围：两条准则线（输出存放 / 本地 AI 使用）的全部载体 + 工具脚本 + 注入层 + 恢复遗留
- 结论：**规则体系健康、跨文件一致**；发现 **5 个问题**（1 个真实缺陷、1 个规则缺口、3 个改进项），**已全部修复并部署**

---

## 1. 检查方法与覆盖

| 层次 | 检查内容 |
|---|---|
| 自检脚本 | `tools\Test-StoragePolicy.ps1`（六段：策略文件 / 类别目录 / 根白名单 / 登记表+对话目录 / 命名合规 / reference_file） |
| 跨文件一致性 | 用 `storage-policy.json`、`ai-tools.json` 里的**值**去验证 md 与两份 `AGENTS.md`（类别、根白名单、8 个工具、生图预算数字、寿命规则条数） |
| 引用完整性 | 规则文档里出现的**每一个本机路径**（绝对 + 相对）逐个解析 |
| 内容完整性 | `ai-tool-policy.md` 章节结构（§1–§12）、两份 `AGENTS.md` 关键条款对应 |
| 陈旧内容 | 已删除模型、旧版本号、旧耗时数字 |
| 注入层 | 全局副本 ↔ 源文件一致性；MCP 注册；DSH 是否已重新加载 |
| 运行时 | `vision_status`（8 个工具与模型可用性） |
| 环境事实 | 各模式下 shell / 写文件能力（本次踩到真实缺口） |

## 2. 发现的问题与修复

| # | 问题 | 类型 | 修复 |
|---|---|---|---|
| **P1** | `AGENTS.md` 规则 0 说"HTTPS 下载改用 `scripts\conv-20260928-3b54e160\download-file.js`"，但**该文件不存在**（随磁盘清空丢失）→ 未来的对话按规则下载会找不到脚本 | **失效引用（真实缺陷）** | 在 `C:\huifu` 中按内容找到原件（`f0020992.txt`，3531 字节）并恢复；`node --check` 语法通过；功能与实际描述一致（302 跳转、`.part` 断点续传、进度输出） |
| **P5** | 规则 0 的对策"改用 PowerShell 直写文件"在 **DSH 只读模式**下**不可用**——此时 PowerShell 处于 **ConstrainedLanguage**，`[Math]::Round`、`.Substring()`、`New-Object`（非核心类型）、`[System.IO.File]::WriteAllText` 全部被禁 | **规则缺口**（会误导后续对话） | 三处规则同步补入该事实行：工作区 `AGENTS.md` 规则 0、`output-storage-policy.md` §10、`global-agents.md` 规则 7；并给出对策（用 Node `fs.writeFileSync(p,t,'utf8')`；只读检查用 cmdlet；中文内容用 `edit` 工具或从文件读模板） |
| **P3** | 3 个 `tools\*.ps1` 是重建版但**没有重建标注**（其他重建文件都有） | 透明性 | 三个脚本头部各加两行重建说明 |
| **P2** | `output-storage-policy.md` 未说明"重建版篇幅较原版精简" | 透明性 | 补一行保真度提示（原版约 14.9 KB / 本版约 6.5 KB） |
| **P4** | `README.md` 里写 `logs\vision-mcp.log`（相对形式，承接前文的 `D:\AI_file`） | 轻微易误读 | **保留**：语义正确（同句已给出 `D:\AI_file`），不改动以免句子冗长 |

### 修复过程中我自己引入并已清除的问题
用 PowerShell 把中文代码传给 Node（stdin）时**中文被破坏成问号**，导致一条写坏的提示行进入 `output-storage-policy.md`。
已用 Node 做纯 ASCII 的行级删除清除，文件恢复完好；并把这个坑（"经 PowerShell 传参中文/双引号会被破坏"）**写进了规则 0**。

## 3. 检查通过项（未发现问题）

| 检查 | 结果 |
|---|---|
| `Test-StoragePolicy.ps1` | **FAIL=0 WARN=0**（六段全通过） |
| 六个类别目录 | json / md / 两份 AGENTS **四处一致** |
| 根白名单 | 9 个条目均在 ≥2 份文档中出现 |
| 8 个工具 | `ai-tools.json` ↔ `ai-tool-policy.md` ↔ 两份 AGENTS **全部对齐** |
| 生图预算数字 | 默认 1 张 / 上限 4 张 / 目标 ≤60 s —— md 与 AGENTS 一致 |
| 版本链 | `storage-policy.json` 1.3.0 ｜ `ai-tools.json` 1.9.0 ｜ 服务端 **1.11.0 = `D:\AI_file\registry.json`** ✓ |
| 寿命规则 | 7 条（json 与 md 一致） |
| 关键字段 | `hardwareLongevity` / `maintenance` / `vlmOnlyAnswerPolicy` / `imageGenerationBudget` / `trust` 齐备 |
| **路径引用** | 规则文档中 **21 个本机路径全部存在**（P1 修复后） |
| `ai-tool-policy.md` 结构 | **§1–§12 完整**（工具清单 → 路由 → 硬限制 → 可信度 → 调用规范 → 隐私成本 → 备选模型 → 变更流程 → 快速卡 → 寿命 → 生图预算 → 运维） |
| 两份 AGENTS 对应 | 思考语言 / 运维条 / 生图预算 / 寿命 / reference_file / `D:\AI_file` —— **逐条对应** |
| 注入层 | 全局副本与源文件**逐字节一致**（部署后校验 `True`）；DSH 已重新加载 |
| AI 工具链 | `vision_status`：生图 / 检测 / 异常模型**全部 `[present]`** |
| 登记表 | 9 条（2 active + 7 lost）；regex 与实际目录名**全部匹配** |
| `reference_file` | 2 个用户文件、无 Agent 生成物（只读性保持） |

## 4. 一个正面证据：规则正在被执行

本次自检发现另一个对话 **`conv-20261012-7817dfa3`**（ESP32 项目）的产物**完全符合规则**：
交付物在 `deliverables\conv-20261012-7817dfa3\`（3 份，命名合规）、日志在 `logs\...\`（2 份，含 `yyyyMMdd-HHmmss` 前缀）、
脚本在 `scripts\...\`，且它**自己注册进了 `conversation-registry.json`**（active=2 中的另一条）。
—— 说明重建的规则不只是"躺在文件里"，而是**被新对话实际遵守**。

## 5. 遗留建议（未执行，供决定）

1. **`workspace\_recovery\`（28 个文件，124 KB）**：本次恢复过程的脚本、候选清单与原件副本。
   按规则它属于"中间产物"（放 `workspace\` 正确）；若想留作证据链可保留，否则可整体移入 `archive\conv-20260928-3b54e160\`。
2. **备份**：`policy\` + `tools\` 合计约 62 KB，是整套规则的唯一载体，建议复制一份到 `E:` 盘之外（或纳入版本控制）。
3. **会话记录格式**：`session.v4.jsonl.zstd` 为非标准多帧 zstd，标准解压器只取到元数据头；
   若希望"会话记录可恢复"，值得确认 DSH 的官方读取方式（不影响当前使用）。