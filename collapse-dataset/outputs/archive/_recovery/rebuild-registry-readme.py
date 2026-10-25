import json, os, datetime

ROOT = r"E:\deepseek"

registry = {
    "note": ("对话登记表。每个对话在六个类别目录下使用同一个 conv-<yyyyMMdd>-<token> 子目录名；"
             "同 ID 已存在则复用，不另建。2026-10-11 重建：E: 盘被清空，历史对话目录随磁盘丢失，"
             "其条目保留为 status=lost 以留痕，自检脚本会跳过它们的目录检查。"),
    "rebuiltAt": "2026-10-11",
    "pattern": "conv-<yyyyMMdd>-<token>",
    "regex": "^conv-[0-9]{8}-([0-9a-f]{8}|[0-9]{6})(-[a-z0-9]{2,32})?$",
    "conversations": [
        {"folder": "conv-20260928-3b54e160", "createdAt": "2026-09-28 12:43:58", "status": "active",
         "note": "长期主线对话：本地 AI 工具集建设与规则制定（磁盘清空后重建工作区）"},
        {"folder": "conv-20260928-c8e2cbb8", "createdAt": "2026-09-28 22:32:20", "status": "lost", "note": "随 E: 盘清空丢失"},
        {"folder": "conv-20260928-5afba4fd", "createdAt": "2026-09-28 22:33:46", "status": "lost", "note": "随 E: 盘清空丢失"},
        {"folder": "conv-20260928-5ca0242e", "createdAt": "2026-09-28 22:33:48", "status": "lost", "note": "随 E: 盘清空丢失"},
        {"folder": "conv-20261003-61324bfb", "createdAt": "2026-10-03 09:58:39", "status": "lost", "note": "随 E: 盘清空丢失"},
        {"folder": "conv-20261004-f5dc7d87", "createdAt": "2026-10-04 15:45:14", "status": "lost", "note": "随 E: 盘清空丢失"},
        {"folder": "conv-20261004-7a531c9a", "createdAt": "2026-10-04 22:16:11", "status": "lost", "note": "随 E: 盘清空丢失"},
        {"folder": "conv-20261004-8041580a", "createdAt": "2026-10-04 22:22:07", "status": "lost", "note": "随 E: 盘清空丢失"}
    ]
}
open(os.path.join(ROOT, r"policy\conversation-registry.json"), "w", encoding="utf-8", newline="\r\n").write(
    json.dumps(registry, ensure_ascii=False, indent=2) + "\n")
print("[OK] policy\\conversation-registry.json  (%d 条：1 active + 7 lost)" % len(registry["conversations"]))

readme = """# E:\\Deepseek 工作区

本工作区是"本地 AI 工具集 + 对话规则"的建设基地。规则由 DSH 自动注入到每个对话（见 `AGENTS.md`）。

## 目录结构

```
AGENTS.md                  工作区规则（自动注入；精简版）
README.md                  本文件（索引）
policy\\                    规则源与部署暂存
  output-storage-policy.md   存放准则全文
  storage-policy.json        存放准则（机器可读）
  ai-tool-policy.md          本地 AI 使用准则全文
  ai-tools.json              本地 AI 使用准则（机器可读）
  conversation-registry.json 对话登记表
  deploy\\global-agents.md    全局规则源（部署到 %USERPROFILE%\\.dsh\\AGENTS.md）
tools\\                     准则自身的工具（跨对话复用）
  New-ConversationWorkspace.ps1  建本次对话的类别子目录（幂等）
  Install-GlobalPolicy.ps1       部署全局规则副本（带备份）
  Test-StoragePolicy.ps1         六段自检（FAIL/WARN 汇总，可 -Json）
reference_file\\            用户投放参考资料（Agent 只读，允许中文名）
deliverables\\ logs\\ scripts\\ workspace\\ data\\ archive\\
                           对话产物，按 conv-<yyyyMMdd>-<token> 分子目录
```

## 常用命令

```powershell
# 建本次对话的目录（写第一个文件前先跑）
powershell.exe -NoProfile -ExecutionPolicy Bypass -File E:\\Deepseek\\tools\\New-ConversationWorkspace.ps1

# 自检
powershell.exe -NoProfile -ExecutionPolicy Bypass -File E:\\Deepseek\\tools\\Test-StoragePolicy.ps1

# 改完规则后部署全局副本
powershell.exe -NoProfile -ExecutionPolicy Bypass -File E:\\Deepseek\\tools\\Install-GlobalPolicy.ps1
```

## 两条准则线

| 规则域 | 权威源（人读） | 机器可读 | 注入层 |
|---|---|---|---|
| 输出存放 | `policy\\output-storage-policy.md` | `policy\\storage-policy.json` | 工作区 `AGENTS.md` 规则 0–6 + 全局规则 1–6 |
| 本地 AI 使用 | `policy\\ai-tool-policy.md` | `policy\\ai-tools.json` | 工作区 `AGENTS.md` 规则 7 + 全局规则 8 |
| 思考语言（强制中文） | 两份 `AGENTS.md` 顶部引用块 | `ai-tools.json` 的 `thinkingLanguage` | 所有对话 |

## 本地 AI 工具（8 个，全部本地推理、无网络、无费用）

`vision_read_document`（PDF/文档）· `vision_ocr`（扫描件文字）· `vision_describe` / `vision_ask`（图形问答）·
`vision_detect`（定位计数，NPU 7 ms）· `anomaly_score`（无监督筛查，NPU）· `image_generate`（FLUX.1-schnell，iGPU）·
`vision_status`（状态与模型健康）

服务端与模型在 `D:\\AI_file`（工作区之外）：`mcp\\vision-server.py`（v1.11.0）、`registry.json`、`logs\\vision-mcp.log`。

## 恢复说明（2026-10-11）

E: 盘曾被清空，本工作区于 2026-10-11 重建：
- `AGENTS.md`、`policy\\deploy\\global-agents.md`：来自 `%USERPROFILE%\\.dsh\\AGENTS.md` 的完好副本（**保真**）
- `storage-policy.json`、`output-storage-policy.md`、`ai-tool-policy.md`、`ai-tools.json`、`tools\\*.ps1`、
  `conversation-registry.json`、本文件：按原版结构与规则语义**重建**（个别描述文字为重新撰写）
- `D:\\AI_file` 未受影响（模型、venv、服务端、登记表完好）
"""
open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8", newline="\r\n").write(readme)
print("[OK] README.md  (%d 字节)" % len(readme.encode("utf-8")))