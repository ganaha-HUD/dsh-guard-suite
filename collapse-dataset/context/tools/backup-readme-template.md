# Deepseek 规则备份

本目录是 `E:\Deepseek` 工作区**规则本体**的独立副本，放在系统盘（Documents），
与可移动的 E 盘**物理分离**——2026-10 曾发生 E 盘被清空、规则全部丢失的事故。

- 备份范围：`AGENTS.md`、`README.md`、`policy\`、`tools\`
- **不含**对话产物（`deliverables\`/`logs\`/`scripts\`/`workspace\`）——备份的是规则，不是输出
- 由 `E:\Deepseek\tools\Backup-Rules.ps1` 生成，每次一个 `yyyyMMdd-HHmmss` 子目录，保留最近 5 份
- 生成时脚本已逐文件比对 SHA-256；`[verify] ... failures 0` 表示副本与源**完全一致**

## 内容

| 路径 | 说明 |
|---|---|
| `AGENTS.md` | 工作区规则（DSH 自动注入本工作区所有对话） |
| `README.md` | 工作区索引与常用命令 |
| `policy\output-storage-policy.md` | 存放准则全文 |
| `policy\storage-policy.json` | 存放准则（机器可读） |
| `policy\ai-tool-policy.md` | 本地 AI 使用准则全文 |
| `policy\ai-tools.json` | 本地 AI 使用准则（机器可读） |
| `policy\conversation-registry.json` | 对话登记表 |
| `policy\deploy\global-agents.md` | 全局规则**源文件**（部署到 `%USERPROFILE%\.dsh\AGENTS.md`） |
| `tools\New-ConversationWorkspace.ps1` | 建对话类别子目录（幂等） |
| `tools\Install-GlobalPolicy.ps1` | 部署全局规则副本（带备份） |
| `tools\Test-StoragePolicy.ps1` | 六段自检 |
| `tools\Backup-Rules.ps1` | 本备份工具自身 |

## 还原到工作区

```powershell
$src = 'C:\Users\<用户>\Documents\Deepseek-rules-backup\<时间戳>'
$dst = 'E:\Deepseek'

# 1) 工作区骨架
foreach ($d in 'deliverables','logs','scripts','workspace','data','archive','policy','policy\deploy','tools','reference_file') {
    New-Item -ItemType Directory -Force -Path (Join-Path $dst $d) | Out-Null
}
# 2) 规则本体
Copy-Item "$src\AGENTS.md" "$dst\AGENTS.md" -Force
Copy-Item "$src\README.md" "$dst\README.md" -Force
Copy-Item "$src\policy\*" "$dst\policy\" -Recurse -Force
Copy-Item "$src\tools\*"  "$dst\tools\"  -Recurse -Force

# 3) 部署全局副本（让其他对话/工作区也生效）
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$dst\tools\Install-GlobalPolicy.ps1"

# 4) 自检（期望 FAIL=0 WARN=0）
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$dst\tools\Test-StoragePolicy.ps1"
```

## 注意

1. `policy\` 必须与自检脚本**一起**还原，否则自检会报缺文件。
2. 全局副本在 C 盘，通常**能挺过 E 盘故障**；还原前先比对它与 `policy\deploy\global-agents.md` 的时间戳，取较新的一侧。
3. **以工作区为准**，本目录只是灾备副本。
4. 只读模式下**无法**运行备份脚本（C 盘写入需要放宽权限）。