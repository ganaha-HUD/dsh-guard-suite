# 归档索引（conv-20260928-3b54e160）

- 归档日期：2026-10-20 23:12
- 本目录存放本对话的**分析中间产物**与**灾后恢复证据链**

## analysis-artifacts-20261020/（本次归档，11 个文件）

| 文件 | 内容 | 用途 |
|---|---|---|
| `asar-flat.json` | DSH `app.asar` 的完整文件清单（12967 条） | 用于定位 `dsh-agent-loop` / plugin-manager 等实现 |
| `dsh-agent-loop-index.js` | `@deepseek-ai/dsh-agent-loop` 的 `lib/index.js` | 分析"对话为何会自己停止"的源码证据 |
| `dsh-agent-loop-readme.zh.md` | 同包中文文档 | 其中"没有内置轮次预算"是停止机制的关键结论 |
| `dsh-client-ui-plugin-manager__readme.zh.md` | 插件管理器文档 | 得出"桌面版须在应用内装插件"与安装流程 |
| `dsh-client-ui-settings-plugins__readme.md` | 内置插件设置页文档 | 区分"Built-in plugins（只读）"与"Plugins 页（可装）" |
| `dsh-client-ui-settings-plugin-inventory__readme.zh.md` | 插件清单页文档 | 同上 |
| `dsh-repeat-tool-reminder-readme.md` | 官方 repeat-tool-reminder 文档 | 证明官方 guard 只盯工具调用、抓不到纯思考循环 |
| `plugin-market-research.txt` | 插件市场调研原始输出（289 个官方包） | 市场机制取证 |
| `plugin-market-search.txt` | 防重复插件搜索原始输出 | `dsh-guard-repeat-output` 等候选的来源证据 |
| `loop-guard-plugins.txt` | 7 个护栏插件的详情对比 | 选型依据 |
| `docx-check.json` | 工具集指南 DOCX 的结构检查结果 | 交付物质量证据 |

## _recovery/（此前归档，28 个文件）

E: 盘被清空后的恢复过程证据：`huifu` 内容扫描、会话记录解压尝试、候选识别、用户文件恢复脚本、
找回的原件副本（`ai-tools.json.recovered-v1.8.0`、`vision-server.py.recovered-fragment`）等。

## 文档检查结果（2026-10-20）

| 检查项 | 结果 |
|---|---|
| 命名合规（ASCII / 小写 / 无空格） | ✅ 归档后 **全部合规**（归档时把 5 个含 `README` 大写的文件转为小写） |
| 编码（md/json 无 BOM；ps1 带 BOM） | ✅ **15/15 全部正确** |
| deliverables 报告的路径引用 | ✅ 4 份报告共 12 个引用，**零失效** |
| DOCX 完整性 | ✅ 83 段落 / 14 表格 / zip 校验通过 / 17 个分卷 |
| 空壳或异常小文件 | ✅ 无 |
| workspace 清空情况 | ✅ 0 文件（中间产物已全部归档） |

## 当前各目录规模

| 目录 | 文件数 | 大小 |
|---|---|---|
| `deliverables\` | 5 | 73.3 KB |
| `logs\` | 20 | 69.6 KB |
| `scripts\` | 9 | 44.5 KB |
| `workspace\` | 0 | — |
| `archive\` | 39 | 1885.8 KB |

## 已知时效性缺口（如实记录）

`deliverables\local-ai-toolset-guide-v1.docx` 是 **2026-10-11 的 v1.4**。其后的规则变更**未反映进 DOCX**：

1. `storage-policy.json` **v1.4.0 → v1.5.0**（`eim_config.toml` 进入根目录白名单，2026-10-14）
2. **PowerShell 脚本必须带 BOM** 这条环境事实（2026-10-13 发现）
3. **只读模式 ConstrainedLanguage** 的对策（2026-10-13）
4. **stable-diffusion.cpp + Vulkan** 的本地无审查生图方案（2026-10-20，下载中）

以上均已在 `policy\`、`AGENTS.md`、`logs\` 中留档；DOCX 只是没有同步。**是否要把 DOCX 升到 v1.5 由用户决定**。

## 待补（进行中）

`qwen-image-2.1-uncensored` 三件套正在后台下载（约 11–12 小时）。落地并跑通首张图后，
应补一份《本地无审查生图安装记录》到 `deliverables\`，并再走一轮归档。
## qwen-image-verification/（2026-10-21 追加）

| 文件 | 内容 |
|---|---|
| `qwen-uncensored-512-s4.png` | Qwen-Image 2.1 无审查版，512×512、**4 步**的产物。模糊噪点、无结构，用于证明**步数下限真实存在** |
| `qwen-uncensored-512-s20.png` | 同模型 **20 步**的产物："猫举木牌，牌上写 hello"，文字清晰、构图正常，**首图验证通过** |

安装与使用详见 `deliverables\conv-20260928-3b54e160\local-uncensored-imagegen-install-v1.md`。
