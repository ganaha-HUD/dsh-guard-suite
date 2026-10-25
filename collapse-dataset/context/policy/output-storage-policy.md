# 工作区输出文件存放准则（完整说明）

- 版本：1.3.0 ｜ 更新：2026-10-05 ｜ 机器可读配置：`policy\storage-policy.json`
- 重建说明：原文件随 E: 盘清空丢失，本文件按 2026-10-05 审计后的 v1.3.0 结构与规则语义重建（2026-10-11）。
- 适用：工作区 `E:\Deepseek` 及其下所有对话。精简版见工作区 `AGENTS.md`（DSH 自动注入）。

---

## 1. 目的

让每一个对话产出的文件都**有固定的去处、可预测的名字、可追溯的历史**，
并且让"共享资产"（规则、工具、用户参考资料）与"对话产物"**互不污染**。

## 2. 目录类别（六个，目录名一律英文小写）

| 目录 | 中文名 | 放什么 | 文件命名 |
|---|---|---|---|
| `deliverables\` | 交付 | 交给用户的最终交付物 | `<topic>-<version>.<ext>` |
| `logs\` | 日志 | 命令输出、运行日志、会话元信息 | `<yyyyMMdd-HHmmss>-<tool>.log` |
| `scripts\` | 执行脚本 | 为本次对话编写的脚本 | `<verb>-<noun>.ps1/.py/.sh/.bat` |
| `workspace\` | 中间产物 | 临时文件、构建中间产物 | 自由，仍须合命名规范 |
| `data\` | 输入数据 | 输入数据集、样例、夹具 | 自由，仍须合命名规范 |
| `archive\` | 归档 | 被取代的版本、结项留存 | 自由，仍须合命名规范 |

**共享目录**（不属于任何对话）：

| 目录 | 放什么 |
|---|---|
| `policy\` | 本准则：说明文档、机器可读配置、部署暂存（`policy\deploy\`） |
| `tools\` | 准则自身的工具脚本（跨对话复用） |

## 3. 对话子目录命名

- 形如 `conv-<yyyyMMdd>-<token>`，例如 `conv-20260928-3b54e160`
- `token` = `$env:DSH_SESSION_ID` 中 UUID 的**前 8 位十六进制小写**；无会话 ID 时用本地时间 `HHmmss`
- 正则：`^conv-[0-9]{8}-([0-9a-f]{8}|[0-9]{6})(-[a-z0-9]{2,32})?$`
- **同一对话在六个类别下必须使用同一个 `<conv-id>`**；已登记则复用，不得另建第二个
- 登记表：`policy\conversation-registry.json`

建目录请运行（幂等，可重复运行）：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File E:\Deepseek\tools\New-ConversationWorkspace.ps1
```

## 4. 工作区根目录白名单

根目录**只允许**出现：`AGENTS.md`、`README.md`、`policy\`、`tools\`、`reference_file\`
以及六个类别目录（`deliverables\` `logs\` `scripts\` `workspace\` `data\` `archive\`）。

另外允许**工具自生成的根目录配置文件**，目前是 `eim_config.toml`（ESP-IDF 安装器 EIM 的配置，
该工具要求在项目根读写它；2026-10-14 按用户决定加入白名单）。
将来若再有同类文件，应同样在 `policy\storage-policy.json` 的 `rootAllowList` 里登记并注明理由。

禁止把产物写在根目录、桌面、`%TEMP%` 或源目录里。共享工具放 `tools\`，不放 `scripts\`。

## 5. `reference_file\`（用户投放参考资料的共享目录）

- **开放性**：跨对话共享，非对话专属；允许子目录，读取时递归
- **归属**：仅属于用户；**Agent 只读**
- **禁止**：删除、移动、改名、覆盖其中任何文件
- **命名豁免**：用户投放的文件允许中文名（不受 ASCII 规则约束）；
  Agent 在其中新建的文件仍须遵守命名规范
- **清理**：删除或归档**仅在用户明确要求时**进行

## 6. 命名规范（兼容性优先）

- 只用 ASCII：`A-Z a-z 0-9 . _ -`；**禁止**中文、空格、emoji、全角字符
- 统一小写，词间用 `-`
- 避开 Windows 保留名：`CON` `PRN` `AUX` `NUL` `COM1-9` `LPT1-9`
- 文件名不超过 100 字符；中文主题写进**文件内容**或 `README`，不写进文件名
- 时间戳统一 `yyyyMMdd-HHmmss`；不要用"最终版/最新版"这类含糊后缀

## 7. 运行环境缺失时（`D:\program_runtime_environment`）

1. **先检测**：`Get-Command <tool>`、`where.exe <tool>`、查 `registry.json`；已在 PATH 的不得重复安装
2. **归类安装**：`<root>\<category>[\<version>]\`，`category` 为语言/工具大类，小写英文：
   `nodejs` `python` `java` `dotnet` `go` `rust` `cli` `browsers` `databases` `caches`
3. 安装包暂存 `_downloads\`，包管理器缓存放 `_caches\<tool>\`
4. 安装前核对**官方 SHA-256** 与 **Authenticode 签名**（须为 `Valid`），任一不符即停止
5. **登记**：更新 `D:\program_runtime_environment\registry.json`
   （可用 `tools\Add-RuntimeEnvironment.ps1`；该脚本禁用了位置参数绑定，数组须用命名参数）
6. 工作区之外写入需提权；不得为绕开限制而改装到工作区内或系统目录

## 8. AI 专用文件根目录（`D:\AI_file`）

本地 AI 的运行时、模型、数据集、虚拟环境一律归此（用户指定）：

```
runtime\<family>\<version>\   tools\<name>\<version>\   envs\<purpose>\
models\   datasets\   outputs\   logs\   workspace\   mcp\   _downloads\   _caches\
```

- `mcp\` 放 MCP 服务端（如 `vision-server.py`）
- 根目录允许两个文件：`README.md`、`registry.json`
- 登记表：`D:\AI_file\registry.json`；**不要**把 AI 环境装进 `program_runtime_environment`

## 9. 输出规则（摘要）

1. 根目录不放产物，只放白名单条目
2. 每个产出文件都在 `<类别>\<conv-id>\` 下
3. 超过约 50 行的命令输出写入 `logs\<conv-id>\`，聊天只给路径与摘要
4. 交付物被新版本取代时，旧版移入 `archive\<conv-id>\`，不就地覆盖
5. 共享工具放 `tools\`

## 10. 环境限制与对策（本机实测）

| 现象 | 原因 | 对策 |
|---|---|---|
| `write`/`edit` 报 `EISDIR` | 工作区在 exFAT 卷，不支持硬链接 | 用 PowerShell 直写：`[System.IO.File]::WriteAllText($p,$t,(New-Object System.Text.UTF8Encoding($false)))` |
| `Invoke-WebRequest`/`curl.exe` SSL 失败 | 沙箱内 .NET/schannel 取不到 TLS 凭证 | 用 node 下载（自带 OpenSSL，支持跳转与续传） |
| `pip`/`venv` 报 `WinError 5` | 沙箱临时区 chmod 被拒 | 先 `$env:TEMP=$env:TMP='E:\Deepseek\workspace\<conv-id>\tmp'` |
| `tools\*.ps1` 存成 **UTF-8 无 BOM** 会导致中文乱码 | PowerShell 5.1 把无 BOM 的 UTF-8 脚本按 ANSI/GB2312 解析 → 中文注释乱码 → **语法解析错乱**（报错行号与磁盘内容不符、变量莫名为 null） | **PowerShell 脚本必须存为 UTF-8 带 BOM**：`[System.IO.File]::WriteAllText($p,$t,(New-Object System.Text.UTF8Encoding($true)))`；数据文件（md/json）仍用**无 BOM** |
| DSH 处于**只读**（read-only）模式时，PowerShell 进入 **ConstrainedLanguage** | `[Math]::Round`、`.Substring()`/`.PadRight()`、`New-Object`（非核心类型）、`[System.IO.File]::ReadAllText/WriteAllText` 全部抛 `PSNotSupportedException` / `MethodInvocationNotSupported` | 改用 **Node.js** 读写文件（无 BOM）：`fs.writeFileSync(p, t, 'utf8')`；只读检查用 cmdlet（`Test-Path`/`Get-Content`/`Select-String`/`ConvertFrom-Json`/`Copy-Item` 仍可用）。**注意**：经 PowerShell 给 Python/Node 传参时中文与双引号会被破坏，要写中文内容请用 `edit` 工具，或让脚本从文件里读取模板 |
| 工作区外写入被拒 | 文件沙箱按工作区限制 | 申请 `danger-full-access` 提权（设计如此，不是故障） |

写文件统一 UTF-8 无 BOM，读文件统一显式 UTF-8。

## 11. 修改与部署流程

1. 改 `policy\storage-policy.json` 与 `policy\output-storage-policy.md`（两者必须同步）
2. 若影响所有工作区，同步 `policy\deploy\global-agents.md`
3. 重新部署全局副本：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File E:\Deepseek\tools\Install-GlobalPolicy.ps1
```

4. 跑自检并留日志：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File E:\Deepseek\tools\Test-StoragePolicy.ps1
```

## 12. 规则备份（灾备，强制）

**背景**：2026-10 曾发生 E: 盘被清空，而 `policy\` 与 `tools\` 是全部规则的**唯一载体**——丢失后虽然重建成功，但代价很大。

1. **备份对象**：`AGENTS.md`、`README.md`、`policy\`、`tools\`；
   **不含**对话产物（`deliverables\`/`logs\`/`scripts\`/`workspace\`/`data\`/`archive\`）——备份的是规则，不是输出
2. **备份位置**：`%USERPROFILE%\Documents\Deepseek-rules-backup\<yyyyMMdd-HHmmss>\`
   ——必须与工作区**物理分离**（E 盘是可移动盘，同盘副本会随之一起损毁）
3. **触发时机**：`policy\` 或 `tools\` **变更后立即执行**；纯对话产物变化**不需要**备份
4. **执行方式**：

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File E:\Deepseek\tools\Backup-Rules.ps1
   ```

5. **必须校验**：脚本逐文件比对 **SHA-256**；出现 `[FAIL]` 必须处理后才能收尾
6. **保留策略**：默认保留最近 **5** 份，更旧的自动清理（`-Keep` 可调）
7. **还原**：见每次备份内的 `BACKUP-README.md`（含可直接运行的还原脚本与三条注意事项）
8. **不做的事**：不备份对话产物；不把备份放进工作区内；不在只读模式下试图备份
   （写 `%USERPROFILE%` 需要放宽权限，只读模式下 PowerShell 还处于 ConstrainedLanguage）

> 与规则 6 的关系：规则 6 管"改完规则怎么让全局副本同步"，本节管"改完规则怎么让本体不丢"。
