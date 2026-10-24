# dsh-guard-suite

**一次安装，两种坍缩都管。**

| 方向 | 表现 | 引擎 |
|---|---|---|
| **膨胀**（expansion） | 同一句话重复几万次，137 万字符刷屏 | `vendor/repeat`（dsh-guard-repeat-output **2.1.7**，原样 vendored） |
| **收缩**（shrink） | 文本与动作一起变少，语气和断言密度不变 | `vendor/collapse`（dsh-guard-collapse **0.1.0**） |

---

## 一、为什么是"套件"，不是"合并源码"

三个选项摆出来对比过：

| 方案 | 做法 | 问题 |
|---|---|---|
| **A. 源码合并** | 把 repeat 的 1,393 行搬进一个 index.js | **要 fork 一个生产验证过的插件**。它经过 1,546 个会话校准、12 次真实拦截、0 失败；重写等于拿这些换一个本地分支，且上游更新再也拿不到 |
| **B. npm 套件依赖** | 新包 `dependencies` 引用两个包 | 本地安装不走 npm，依赖不会自动落地；桌面版又只能用界面装，链路太长 |
| **C. ▸ 本方案** | 一个目录，两个引擎原样 vendored 在 `vendor/`，`apply` 里组合 | 唯一代价：升级上游要手动替换 `vendor/repeat` 目录 |

选 C：**装起来是一个包，跑起来是两套引擎，改起来互不影响。**

---

## 二、共存是测出来的，不是猜的

两个插件都挂 `agent/pre-step`，所以必须先回答"会不会打架"。实测（mock host，同一 ctx）：

```
listeners: llm/stream=1  agent/request-error=1  agent/pre-step=2
commands : collapse-repair, collapse-report, guard-cleanup
```

**冲突点确实存在**：同一 step 上，两个守卫各注入一条通知 → 消息数 `2 → 3`，模型收到两条互相矛盾的指令。

修法是加互通规则：`collapse` 在注入前检查是否已有**任何** `plugin:dsh-guard-*` 通知，有就退让。

```
修复前：plugin:dsh-guard-collapse | plugin:dsh-guard-repeat-output | user   (叠加)
修复后：plugin:dsh-guard-repeat-output | user                              (不叠加)
```

修复后又跑了全量回放：**1,384 步 → 5 次干预**（4 次模拟执行 + 1 次空想），T134 仍在列。

---

## 三、分工

| 层 | 引擎 | 触发时机 | 动作 |
|---|---|---|---|
| 流式 | `repeat` | 生成过程中 | 截断 + 丢弃 + 重发 |
| 步级 | `collapse` | 下一步开始前 | 注入一条动作指令 |

两者顺序：`repeat` 先注册，流包装在外层；`collapse` 在内层，看到的是已经被 `repeat` 准入的消息。

---

## 四、命令

| 命令 | 来源 | 作用 |
|---|---|---|
| `/guard-cleanup` | repeat | 清掉历史里的巨型重复块 |
| `/collapse-report` | collapse | 最近 12 步的工具/证据/断言比 + 未验证断言 |
| `/collapse-repair` | collapse | 遮掉历史里的空转步（只碰无 tool-call 的消息） |

---

## 五、安装

```powershell
node install.mjs              # 先看会改什么
node install.mjs --apply      # 真的装
```

然后**重启 DSH**，在日志里确认三行：

```
[guard-repeat-output] active (...)
[guard-collapse] active (...)
[guard-suite] active: guard-repeat-output@2.1.7 + guard-collapse@0.1.0
```

**少一行就是没加载。**

---

## 六、配置

所有选项透传给两个引擎，写法不变：

```yaml
- id: guard-suite
  config:
    repeat:   { ... }   # dsh-guard-repeat-output 的配置
    collapse: { ... }   # dsh-guard-collapse 的配置
```

默认值见 `cordis.patch.yml`，每一项都在原包文档里有说明。

---

## 六点五、对上游的补丁

vendored 的 repeat 2.1.7 **不是原样照抄**：审计发现 4 个缺陷，已修并留档。

| # | 缺陷 | 影响 |
|---|---|---|
| P1 | `maxTruncationsPerTurn` 是死配置（计数器从不递增、从不读取） | 每轮续写预算从未生效，多 step 轮次可无限注入 |
| P2 | `pre-step` 的 backstop 不查预算 | 即使 P1 修了，这条路径仍会把续写塞回去 |
| P3 | 模型不匹配时静默放行 | 无法区分「没触发」和「没运行」 |
| P4 | `maxTruncationsPerTurn: 0` 被拒绝 | 想禁用只能靠另一个开关 |

详见 [`PATCHES.md`](./PATCHES.md)，含 3 个**不修**的已知盲区与调参建议。
升级上游时必须重新应用补丁并跑 `test/patch-regression.mjs`。

## 七、局限

1. **vendored 不自动跟随上游**。repeat 出了 2.2.0，要手动替换 `vendor/repeat` 并回归测试。
2. **两个引擎的阈值是各自校准的**，合在一起不等于联合最优。改一个可能影响另一个的观感。
3. **stop 不是 kill**：`collapse` 的注入只是"要求换动作"，模型仍可能嘴上答应、继续空转。真正的兜底是 `/collapse-report` 让你看见数字。
4. 未在真实 DSH 里加载验证（需要重启）。mock 与回放都过了，但"能装进去并跑"仍是 **U**。

---

## 许可

MIT。`vendor/repeat` 来自 `dsh-guard-repeat-output` 2.1.7（MIT，作者 Mcd0LUO），原样保留其 LICENSE。