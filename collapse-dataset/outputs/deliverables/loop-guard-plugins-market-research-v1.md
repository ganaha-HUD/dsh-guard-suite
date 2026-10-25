# DSH 插件市场调研：防"模型重复 / 思考循环"的插件

- 日期：2026-10-13 21:44 ｜ 对话：`conv-20260928-3b54e160`
- 触发：另一个对话（ESP32 项目）在思考阶段陷入重复循环后自行停止，用户要求到插件市场找防护方案
- 结论：**市场里有，而且有 4 个对口插件**；DSH **自带的 guard 家族抓不到这种情况**（见 §2）

---

## 1. DSH 插件市场的形态（先说清"市场"在哪）

| 层面 | 事实 |
|---|---|
| 插件来源 | **npm registry**（`registry.npmjs.org` / `registry.npmmirror.com`）；插件即 npm 包，命名多为 `dsh-*` 或 `@scope/dsh-*` |
| 官方包 | `@deepseek-ai/dsh-*`（本机 asar 内共 **289 个**） |
| 社区目录 | **dsh-plugin.org**（包 README 里带 "Listed on dsh-plugin.org" 徽章）；另有 `dsh.so` 做风险评估 |
| GUI 入口 | 侧边栏 **Plugins 页面**（配置/安装）；设置里的 "Built-in plugins" 只是**只读清单** |
| CLI 入口 | `dsh plugin --profile <profile> add <包名>`（本机 `dsh` 在 `%APPDATA%\npm\dsh.ps1` ✓ 可用） |
| 桌面版限制 | **`desktop` profile 由应用独占管理，CLI 会被拒绝** → 桌面版必须在应用内 Plugins 页安装 |

## 2. 关键洞察：为什么 DSH 自带的 guard 抓不到

把 `@deepseek-ai/dsh-agent-loop` 的中文文档解出来读，它明确写着：

> **没有内置轮次预算**：工具调用或 steering 会让当前轮次继续；限制失控轮次的策略必须从既有生命周期扩展点（如 `agent/turn-stopping`）执行取消。

而内置的 guard 家族**全部围绕工具调用**：

| 内置 guard | 挂载点 | 能抓什么 |
|---|---|---|
| `guard/timeout-policy` | `tools/execute` | 工具调用超时 |
| `guard/repeat-tool-reminder` | `tools/post-execute` | 重复的同一个**工具调用链** |

**退化循环的特征恰恰是"完全不调工具"**：只有 `reasoning-delta`，零 `text-delta`、零 `tool-call-delta`
→ 两个 guard 都不触发 → `turnEnds` 永远为 null → **回合停不下来，只能手动中止**。
（本机 `maxTokens` 也未配置，所以最终停下靠的是模型服务端的输出上限。）

第三方插件作者把这一条写得很直白：官方 `guard/repeat-tool-reminder` 是 **advisory（只提醒）**，
而且它的 chain key 是 `(工具名, 规范化参数)` —— **对纯文本/思考重复完全无效**。

## 3. 四个对口插件（按机制强弱）

| 插件 | 版本 | 许可 | 机制 | 动作强度 | 兼容本机 |
|---|---|---|---|---|---|
| **`dsh-guard-repeat-output`** | **2.1.7** | MIT | 宿主侧流守卫：① 过滤垃圾码点（控制字符/U+FFFD/零宽）② 滑窗检测重复崩溃 ③ **丢弃该次尝试，不进历史** ④ **可追溯清理已被污染的会话** | **最彻底** | ✓ peerDep `@deepseek-ai/dsh >=0.1.6-alpha.2 <0.3.0-0` |
| **`dsh-dupguard`** | **1.9.1** | MIT | 同一字符串连续重复 **≥10 次**（可配）→ **立即停止本次生成**；**思考文本一并检测**；代码区按 3 倍放宽 | 停止生成（内容照常提交） | ✓ 要求 DSH ≥0.1.2-rc.1、Node ≥20 |
| **`@mrweicodes/dsh-loop-guard`** | **1.0.9** | MIT | 接管 `llm/stream`：识别 "reasoning-only" 与 "restated-material" 两种退化形态 → **从流内部切断** + **注入纠正提示让任务继续** | 切断 + 自动接续 | ✓ peerDeps 明确含 `>=0.2.0-alpha.1 <0.3.0` → **正好匹配本机 0.2.0-rc.2** |
| **`dsh-local-loop-fuse`** | **0.8.3** | MIT | 三层：① assistant 文本/推理流重复（可 abort）①b 低多样性滑窗（抓"带噪声的空转"）② 无进展停滞 ③ 累计强信号 → `agent.cancel()` | 真切断 | ✓ peerDep `dsh-llm >=0.1.5-rc.1` |

**另有**：`dsh-task-reliability`（0.4.9）—— 全家桶（含"思考重复干预：n-gram 相似度 + 终止回合 + 分级打断"，外加超时重试、任务自动继续、休眠/锁屏恢复、输出截断补完、自主决策、远程触发）；要求 Node ≥22。

**官方可选项**：`@deepseek-ai/dsh-repeat-tool-reminder`（30 个版本）—— **只盯工具调用且只提醒**，对本例**无效**。

## 4. 本机兼容性核对（已实测）

| 项 | 本机版本 | 结论 |
|---|---|---|
| DSH 桌面运行时 | `@deepseek-ai/dsh-desktop-runtime` **0.2.0-rc.2** | — |
| `dsh-llm` / `dsh-agent` / `dsh-agent-loop` | 均 **0.2.0-rc.2** | 落在 loop-guard 要求的 `>=0.2.0-alpha.1 <0.3.0` ✓ |
| `@deepseek-ai/schemastery` | 3.18.4 | 满足 `^3.18.1` ✓ |
| `cordis` | 4.0.4 | 满足 `^4.0.2` ✓ |
| Node.js | 24.20.0 | 满足 `>=20` / `>=22` ✓ |

## 5. 安装方式

**桌面版（本机主用，Electron）** —— CLI 会被拒绝，必须在应用内装：

1. 打开 DSH → 侧边栏 **Plugins** 页面
2. 搜索包名（例如 `dsh-dupguard`）→ 安装
3. **重启 DSH 生效**（宿主代码只在进程启动时加载）
4. 验证：`dsh-dupguard` 装好后设置页会出现「重复守卫」分节；宿主日志出现 `[dupguard] 生效参数：…`（**只认这一行**）

**Web profile（可用 CLI）**：

```bash
dsh plugin --profile web add dsh-dupguard
dsh plugin --profile web remove dsh-dupguard     # 卸载
dsh plugin --profile web update dsh-dupguard     # 升级
```

## 6. 建议

1. **首选 `dsh-guard-repeat-output`（最彻底）**：它不只截断，还**不让垃圾进历史**，并能**清理已被污染的会话**——
   这正对上你那次的情况（重复文本已经烧进上下文）。
2. **或 `dsh-dupguard`（最简单）**：装上即用、阈值可在设置页调（≥10 次）、思考文本一并检测。
3. **若更看重"不中断任务"**：`@mrweicodes/dsh-loop-guard` —— 它在截断后**注入纠正提示让任务继续**，而不是把整轮废掉。
4. **不要同时装多个**：四者大多挂在同一个流挂载点（`llm/stream`），可能互相干扰。**先装一个观察效果**。
5. **先验证再依赖**：装好后故意让它重复一次，确认日志里出现该插件的生效参数行。

## 7. 参考

- npm: `dsh-guard-repeat-output` · `dsh-dupguard` · `@mrweicodes/dsh-loop-guard` · `dsh-local-loop-fuse` · `@deepseek-ai/dsh-repeat-tool-reminder`
- 社区目录：**dsh-plugin.org**（以及 dsh.so 的风险标记）
- 本机证据：`app.asar` 内 `@deepseek-ai/dsh-agent-loop` 的 `README.zh.md`（"没有内置轮次预算"一节）；`~/.dsh` 无 `maxTokens` 配置