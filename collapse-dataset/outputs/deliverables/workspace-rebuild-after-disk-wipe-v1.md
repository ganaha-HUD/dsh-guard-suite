# 磁盘清空后的工作区与规则重建报告

- 日期：2026-10-11 23:06 ｜ 对话：`conv-20260928-3b54e160`
- 事故：**E: 盘被清空**（我的工作区所在盘），用户已尽力恢复数据到 `C:\huifu`
- 结果：**规则体系已重建并验证通过**（自检 FAIL=0 WARN=0）；**AI 工具链未受影响，8 个工具全部可用**

---

## 1. 影响范围勘察（先查清事实，再动手）

| 位置 | 状态 | 结论 |
|---|---|---|
| **E: 盘** | 已用 **0 GB** | ❌ 工作区 `E:\Deepseek` 全部丢失（规则、脚本、交付物、日志） |
| **`D:\AI_file`** | ✅ 20.4 GB 完好 | **AI 环境无损**：模型、venv、MCP 服务端（v1.11.0）、registry.json 都在 |
| **`~\.dsh`** | ✅ 403.5 MB 完好 | 全局规则 `AGENTS.md`（9173 字节）+ **12 个历史备份** + profile（MCP 注册）+ 会话记录都在 |
| **`C:\huifu`** | 16.85 GB / 56797 文件 | PhotoRec 式恢复：**文件名全部丢失**（`f0000304.txt`），需按内容识别 |

## 2. 恢复策略：保真优先，其次按规则语义重建

| 来源 | 保真度 | 用于 |
|---|---|---|
| `~\.dsh\AGENTS.md`（完好） | **逐字保真** | 全局规则副本 `policy\deploy\global-agents.md` |
| 本对话上下文中的规则全文 | **逐字保真** | 工作区 `AGENTS.md` |
| `C:\huifu` 按内容搜索 | 取决于命中 | （后台搜索中，用于补充） |
| 按原版结构与规则语义重建 | **结构+语义保真**，措辞可能不同 | policy 的 md/json、tools 脚本、登记表、README |

**关于会话记录**：`session.v4.jsonl.zstd`（6.34 MB）是**非标准多帧 zstd**，
`zstdDecompressSync` 与流式解压都只得到元数据头（`Unknown frame descriptor`）→ 该路径放弃。

## 3. 重建清单

| 文件 | 大小 | 来源 |
|---|---|---|
| `AGENTS.md` | 10.1 KB | 上下文逐字重建（DSH 已重新加载生效 ✓） |
| `policy\deploy\global-agents.md` | 9.2 KB | **从 C 盘完好副本复制（保真）** |
| `policy\storage-policy.json` | 6.3 KB | 重建（v1.3.0：6 类别 / 11 根白名单 / aiRoot 11 类别） |
| `policy\output-storage-policy.md` | 6.5 KB | 重建（含 v1.3.0 的 mcp 目录与 rootFiles 补充） |
| `policy\ai-tool-policy.md` | 14.6 KB | 重建（v1.9.0：§1–§12，含 §11 生图预算、§12 运维规则） |
| `policy\ai-tools.json` | — | 重建（v1.9.0：8 工具 / 12 路由 / 7 条寿命规则 / maintenance / vlmOnlyAnswerPolicy） |
| `policy\conversation-registry.json` | — | 重建（8 条：1 active + 7 标记 `lost`） |
| `tools\New-ConversationWorkspace.ps1` | 2.4 KB | 重建并**改进**（见 §4） |
| `tools\Install-GlobalPolicy.ps1` | 1.6 KB | 重建 |
| `tools\Test-StoragePolicy.ps1` | 7.9 KB | 重建（六段自检，支持 `-Json`，对 `lost` 条目跳过目录检查） |
| `README.md` | 3.3 KB | 重建（含本次恢复说明） |
| 六个类别目录 + `policy\` `tools\` `reference_file\` | — | 按规则建立 |

## 4. 重建中发现并修正的一个真实缺陷

**问题**：重建的建目录脚本按**当天日期**生成 conv-id，于是本对话被建成 `conv-20261011-3b54e160`，
而它原本是 `conv-20260928-3b54e160` → **同一对话出现两个 ID**（违反"一个对话一个 ID"规则），
自检因此报出 `WARN: conversation folder missing ...`。

**修正**：脚本改为**优先复用登记表中同一 token 的已有条目**；目录统一回原 ID；清理误建条目。
复跑结果：`reusing registered conversation id: conv-20260928-3b54e160` ✓

> 这条改进对"磁盘故障后重建""跨天继续同一对话"都有效——原版脚本没有这个保护。

## 5. 验证证据

```
Test-StoragePolicy.ps1 → Summary: FAIL=0 WARN=0
  [PASS] policy file parses: policy\storage-policy.json (version 1.3.0)
  [PASS] 六个类别目录全部存在
  [PASS] workspace root contains only allow-listed entries
  [PASS] conversation registry parses; registered conversations: 8
  [PASS] conversation folder present in every category: conv-20260928-3b54e160
  [PASS] 7 条历史对话按 lost 跳过（留痕不误报）
  [PASS] no non-ASCII names found under the category folders
```

**AI 工具链实测**（`vision_status`）：

```
image gen : D:\AI_file\models\flux1-schnell-int4-ov [present]
detector  : D:\AI_file\models\yolox-tiny\openvino\yolox-tiny.xml [present]
anomaly   : D:\AI_file\models\patchcore-synth-v1\weights\openvino\model-static.xml [present]
```
服务端 v1.11.0 运行中，启动自检四项 OK → **8 个工具（读文档/OCR/看图/问答/检测/异常/生图/状态）全部可用**。

## 6. 仍需处理

1. ~~`reference_file\` 的用户文件~~ → **已恢复并逐项验证通过，见 §11**。
2. **其余历史交付物**（原 `deliverables\` 下十余份报告）：可按需从本对话上下文重新导出。
3. **全局规则无需重新部署**（C 盘那份本来就是最新版），但 `policy\deploy\global-agents.md`
   已按"源文件"定位恢复——今后改规则请走 `tools\Install-GlobalPolicy.ps1`。

## 7. 建议

- **备份**：这次事故的根因是工作区在**单一可移动盘**上且无备份。建议把 `E:\Deepseek\policy\` 与
  `tools\`（合计不到 100 KB）纳入版本控制或定期复制到 `D:\AI_file\workspace\` 之外的第三个位置。
- **可移动盘风险**：工作区在可移动介质上还有另一个已知后果——拔盘时 DSH 的 `pwsh`/`glob`/`grep` 会整体失效。

---

## 8. 从恢复数据（`C:\huifu`）中找回的原件 —— 保真恢复

用户恢复出的 16.85 GB 数据是 PhotoRec 式的（文件名全丢，文本文件都堆在 `.txt` 里），
我按**文件内容特征**扫描了 21327 个文本文件，找回了以下原件：

| 原件 | 大小 | 恢复去向 | 说明 |
|---|---|---|---|
| **`build-toolset-guide-docx.py`** | 22.5 KB | `scripts\` | **DOCX 构建脚本全文（v1.4）**，据此**重新生成了交付物**（见 §9） |
| **`ai-tools.json`（v1.8.0）** | 10.4 KB | 作为 `policy\ai-tools.json` 的**基底** | 逐字段校正，恢复了原件独有的 `reservedToolsNaming.planned`（2 项）、`tools[0].prefer` 字段与**原始 routing 顺序** |
| `audit-rules-scan.py` | 3.5 KB | `scripts\` | 规则审计脚本 |
| `fetch-hf-repo.js` | 3.0 KB | `scripts\` | HF 仓库下载器（8 路分块） |
| `render-pdf-pages.py` | 2.7 KB | `scripts\` | PDF 渲染脚本 |
| `verify-pdf-text-layer-vs-ocr.py` | 2.2 KB | `scripts\` | 文字层 vs OCR 对照验证 |
| `verify-vision-v14.py` / `verify-vision-v13.py` | 2.0 / 1.8 KB | `scripts\` | 服务端端到端验证 |
| `sync-rules-everywhere.py` | 3.3 KB | `scripts\` | 规则全库同步脚本 |
| 存放准则建立日志 | 6.8 KB | `logs\` | 2026-09-28 建立过程记录 |
| 生图故障复盘运行日志 | 2.7 KB | `logs\` | 2026-10-05 事故事后日志 |
| NPU 输入上限调查报告 | 3.0 KB | `logs\` | 规格书读取验证 |
| 工具集 DOCX + 寿命规则日志 | 3.1 KB | `logs\` | 历史运行记录 |
| 异常检测验证输出 | 2.7 KB | `logs\` | PatchCore 实跑结果 |

**未能找回全文、因而按规则语义重建的**：工作区 `AGENTS.md`、`output-storage-policy.md`、
`ai-tool-policy.md`、`tools\*.ps1`、`storage-policy.json`、`conversation-registry.json`、`README.md`。
（这些只找回片段；重建版**结构、字段、规则语义一致**，个别描述文字为重新撰写，并已在文件内标注 `rebuiltNote`。）

## 9. 交付物恢复：工具集指南 DOCX

`deliverables\conv-20260928-3b54e160\local-ai-toolset-guide-v1.docx`（46 KB）
—— **由找回的原件脚本重新生成**（不是重写文档）：

- 结构检查：`verdict: pass`
- 83 段落 / **14 个表格** / 9067 字符
- 关键章节全部在位：FLUX.1-schnell 生图、**§4.5 模型变更后的运维规则**、§11 生图时间预算、
  硬件寿命规则、版本记录 **v1.4**

## 10. 恢复完成度总览

| 类别 | 状态 |
|---|---|
| 规则体系（AGENTS ×2 + policy ×4 + tools ×3） | ✅ **完整**，且两条规则线已被 DSH 重新加载生效 |
| 机器可读配置 | ✅ `storage-policy.json` v1.3.0、`ai-tools.json` v1.9.0（后者已用原件校正） |
| 交付物 | ✅ 主要交付物（工具集指南 DOCX）已由原件脚本重新生成 |
| 脚本 / 日志 | ✅ 部分原件找回（8 个脚本 + 5 份日志），其余可按需重写 |
| 自检 | ✅ `FAIL=0 WARN=0` |
| AI 工具链（D 盘） | ✅ **完全无损**，8 个工具可用 |
| `reference_file\` 用户文件 | ⏳ 搜索中（PDF 33 页规格书 + 照片） |

---

## 11. 用户文件恢复（`reference_file\`）—— 逐项验证通过

在 `C:\huifu` 的 56797 个文件中，按**文件头 + 已知特征**定位并恢复了用户投放在本目录的两个文件：

| 文件 | 原件已知特征 | 恢复结果 | 判定依据 |
|---|---|---|---|
| `CH634DS1.PDF` | 33 页、610.0 KB、第 1 页文字层 1267 字符、第 5 页 454 字符 | **33 页、610.0 KB、1267 / 454 字符** | 逐页字符数**完全吻合** ✓ |
| `720421F869216DB8CE295D95710712E5.png` | 6723.2 KB | **6723.2 KB、PNG 4096×2730 RGB** | 字节数与尺寸**完全吻合** ✓ |

（另有同内容的第二份 PDF 副本 `f51776512.pdf` 与一份 45 页的其他 CH634 手册，均未放入 `reference_file\`，
以免混入未经确认的文件。）

## 12. 一句话总结

**规则体系已完整重建并生效，AI 工具链毫发无损，用户资料找回，交付物由原件脚本重新生成。**
这次事故的教训是：工作区在**单一可移动盘**上且**没有备份**——`policy\` + `tools\` 合计不到 100 KB，
值得纳入版本控制或定期复制一份到别处。