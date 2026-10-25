# 安装 dsh-guard-repeat-output（桌面客户端）

- 日期：2026-10-13 21:47 ｜ 对话：`conv-20260928-3b54e160`
- 目标：在 **DSH 桌面客户端**装 `dsh-guard-repeat-output`（防"思考/推理退化循环"）
- 结论：**必须用应用内的插件页安装**——`desktop` profile 由 Electron 应用独占，CLI 会被拒绝（已实测）

---

## 1. 为什么不能用命令行装

实测（`dsh plugin --profile desktop ...`）：

```
error: profile "desktop" is managed exclusively by the Electron application
```

连只读的 `list` 都被拒。本机 CLI 版本是 `0.1.7-rc.2`，而桌面应用是 `0.2.0-rc.2`，本就不该交叉使用。

**对照**：`web` profile 由 CLI 管理（你已装过 `dshmarket@1.66.2` 与 `@dsh-use/wallpaper-engine@0.6.0`），
那边可以用 `dsh plugin --profile web add <包名>`；但桌面版不行。

## 2. 安装步骤（桌面应用内）

1. 打开 DSH 桌面应用 → **侧栏「插件」**（不是"设置 → 内置插件"，那个只是只读清单）
2. 点 **「添加插件」**
3. 在包名框输入下面**任一种**（都接受）：
   - **包名**：`dsh-guard-repeat-output` ← 推荐，最省事
   - **本地压缩包**（已替你下好，网络不畅时用这个）：
     `E:\deepseek\data\conv-20260928-3b54e160\dsh-guard-repeat-output-2.1.7.tgz`
   - **本地目录**：`E:\deepseek\data\conv-20260928-3b54e160\extracted\package`
4. **安装源**保持默认即可：管理器会自动 ping `registry.npmjs.org` 与 `registry.npmmirror.com`，
   取**最先响应**的那个（超时 1500 ms，结果缓存 5 分钟）
5. 点 **「安装」** → 它会先 `inspect` 读出这个包是什么，再跑 pnpm
6. 完成后点 **「立即启用」**（否则只是"已安装但关闭"）
7. **重启 DSH**（宿主代码只在进程启动时加载，不重启不生效）
8. 回到「插件」页确认它出现在 **已安装** 分组，且组合包开关是开的

## 3. 已验证的安装条件（我替你查过了）

| 检查项 | 结果 |
|---|---|
| 版本 | `dsh-guard-repeat-output@2.1.7` |
| dependencies | **空**（零依赖 → 不需要额外下载） |
| scripts | **空**（无构建脚本 → 不会触发 pnpm 的"允许构建脚本"拦截） |
| peerDependencies | `@deepseek-ai/dsh >=0.1.6-alpha.2 <0.3.0-0` → 你的 **0.2.0-rc.2 满足** |
| engines | `node >=20` → 你 24.20.0 满足 |
| 代码内版本门槛 | **无**（只有配置项校验），不会因版本拒绝加载 |
| LICENSE | MIT |
| tarball | 已下载到 `data\conv-20260928-3b54e160\`，并已与 registry 的完整性摘要比对 |

## 4. 它装好后会做什么（默认配置，来自它自带的 `cordis.patch.yml`）

| 配置项 | 默认值 | 含义 |
|---|---|---|
| `truncateChannels` | `['reasoning']` | **只截断推理通道**；`text` 通道只观察不截断 |
| `modelIncludes` | `['deepseek']` | 只对 DeepSeek 系模型生效 |
| `maxDegenerationRetries` | `2` | 主路径：**丢弃塌陷的尝试并重新发起** |
| `windowChars` / `minWindowChars` | 2400 / 1200 | 检测窗口 |
| `minSegments` | 24 | 窗口内最少片段数 |
| `phraseRun` / `phraseTopCount` | 8 / 10 | 短语连击判据 |
| `lowInfoDupShare` / `maxUniqueGramRatio` | 0.80 / 0.30 | 低信息重复占比 / 唯一 n-gram 比例 |
| `holdbackChars` | 4096 | 仅回退路径：回退这么多字符再切割，让刀口落在退化起点 |
| `evalEveryChars` | 200 | 每 200 字符评估一次 |

**作者的关键设计说明**（原注释）：
- **故意不设片段最小长度**——因为 `OK.` / `Let me run.` 这类塌陷完全低于任何长度下限；
  早期版本剔除重复片段后，`OK.` × 44 的循环反而被评为"多样化"（0.60）而漏判；
- 主路径把塌陷尝试结算为 `assistant/attempt`（**不是** `assistant/message`）→ **塌陷文本不进入上下文**；
- 被丢弃的文本会在 sidecar 目录留副本（唯一留证，便于误判时恢复）；
- 重试**故意不降低 reasoning effort**（实测降级后 67% 仍塌陷，且会因适配器不支持而浪费回合）；
- 校准数据：**4 个真实退化样本全部定罪；1708 个真实正常推理片段 + 205 个真实长回答全部放行**。

## 5. 装完怎么验证（别只看"装上了"）

1. 宿主日志出现该插件的启动/生效行（**只认日志**，不要凭界面假设）
2. 插件详情页能看到它注册的配置项
3. 实测一次：故意让它长思考，观察是否在重复刚开始时被切断；被丢弃的内容会出现在 sidecar 副本目录
4. 若想调整阈值：在插件详情页改配置（写回 profile 的 `cordis.patch.yml`），**通常无需重启**

## 6. 如果装不上

| 现象 | 原因与对策 |
|---|---|
| 提示源连不上 | 安装源手动切到「中国大陆镜像源」（npmmirror） |
| 提示包不存在 | 确认输入的是 `dsh-guard-repeat-output`（无 `@scope`、无空格） |
| 提示 pnpm 拦下构建脚本 | 本插件**无脚本**，出现这条说明装的是别的包 |
| 装完没反应 | **重启 DSH**；再到「插件」页确认组合包开关为开 |
| 想卸载/升级 | 界面里卸载；此版本**不支持自动更新**，升级需先卸载再装新版 |

## 7. 文件位置

- 插件包（离线安装用）：`E:\deepseek\data\conv-20260928-3b54e160\dsh-guard-repeat-output-2.1.7.tgz`
- 解包目录：`E:\deepseek\data\conv-20260928-3b54e160\extracted\package\`
- 市场调研背景：`deliverables\conv-20260928-3b54e160\loop-guard-plugins-market-research-v1.md`