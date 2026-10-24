# 对 dsh-guard-repeat-output 2.1.7 的审计与补丁

- 审计对象：`vendor/repeat/index.js`（上游 2.1.7，1,393 行，原样 vendored）
- 审计方法：**读完全部源码 + 驱动真实 `llm/stream` / `agent/pre-step` 接缝**，不看文档自述
- 结论：**4 个真实缺陷已修**，3 个已知盲区**不修**（附理由与调参建议）
- 原始文件保留为 `index.js.orig`，补丁处均带 `PATCH #n` 注释，共 +2,238 字节

---

## 一、已修：P1 `maxTruncationsPerTurn` 是死配置（最严重）

**现象**

`state.truncations` 在全文件中只出现两处：

```js
truncations: 0,                                                    // L852 初始化
if (messages.some(m => m.source?.kind === 'user')) state.truncations = 0  // L1251 清零
```

**从来没有递增，也没有任何地方读它做判断。** 而 `maxTruncationsPerTurn` 只出现在
默认值、配置校验列表、和文档注释里。

**影响**

- 文档承诺「一个 turn 最多注入 `maxTruncationsPerTurn` 次续写」——**从未生效**。
- 一个多 step 的 turn，每个 step 都可能注入一次 wrap-up，**无上界**。
- 用户改这个配置**没有任何反应**，而且不会报错。

**修复**（PATCH #1）

stream 侧 wrap-up 分支改为按 turn 级预算执行，并用 `state.truncations` 计数，
使 `wrapUpText` 里那句「collapsed N times in this turn」第一次成为字面事实
（原来用的是 `state.retries + 1`，而 retries 每个 step 都重置，所谓 "in this turn" 其实是 "in this step"）。

**测试**：case 1（预算 1，两轮 wrap-up 只注入 1 次）、case 2（0 次）、case 3（2 次）。

---

## 二、已修：P2 pre-step 的 backstop 绕过预算

**现象**

`agent/pre-step` 里有一段「backstop」：如果 stream 侧没把 continuation 送进消息，
它无条件补一条：

```js
if (decision.messages.some(isOurs)) return decision
return { ...decision, messages: [createContinuationMessage(...), ...decision.messages] }
```

它**不看预算**。

**影响**

即使 P1 修好了 stream 侧，只要这条路径被走到（预算耗尽、或 `continueOnTruncate:false`），
continuation 依然会被补上——**预算形同虚设**。两个补丁必须一起打，否则只是装饰。

**修复**（PATCH #4）：同一预算、同一计数器；已注入过则退让（原有逻辑），预算耗尽也退让。

---

## 三、已修：P3 模型不匹配时静默失效

**现象**

```js
if (agent === undefined || !inScope(options?.model)) return next()
```

模型 id 不在 `modelIncludes` 里（或为空）时，guard 直接放行，**不写任何日志**。

**影响**

部署后看到「guard 没触发」，无法区分三种情况：真的没问题 / 没匹配到模型 / 插件根本没加载。
这正是「可观测性漏洞」——比功能 bug 更难发现，因为它长得像正常工作。

**修复**（PATCH #3）：每个 session 记一条 `out-of-scope` 日志（只记一次，避免刷屏）。

**测试**：case 4（日志出现一次、流原样透传）。

---

## 四、已修：P4 `maxTruncationsPerTurn: 0` 被拒绝

**现象**：该键在「必须是正整数」的校验列表里，填 0 直接抛错。

**影响**：想关闭 continuation 只能靠另一个开关 `continueOnTruncate`，语义不完整；
而报错信息是 `must be a positive integer`，用户会以为 0 是非法值而不是「禁用」。

**修复**（PATCH #2）：允许 `>= 0`，0 表示从不注入。

**测试**：case 2（0 生效）、case 5（负数仍在加载时抛错）。

---

## 五、已知盲区（**不修**，附理由）

### B1 正文（text 通道）默认不拦截

`truncateChannels: ['reasoning']`，text 只观察。上游有数据支撑：1,546 会话里 59 次定罪全在
reasoning，text 为 0；且 text 是用户唯一读的内容，截错代价高。

**但不是没有风险**：如果模型在正文里循环（例如表格重复行、列表重复项），不会被拦。

**建议**：确认自己的场景需要的话，显式改配置：

```yaml
repeat:
  truncateChannels: ['reasoning', 'text']
```

### B2 长句重复可能够不到 `minSegments`

窗口 2,400 字符、`minSegments` 24，意味着平均每段要 ≤100 字符才凑得满 24 段。
如果重复单元是 200 字符的长句，窗口里最多 12 段，**永远不满足段数门槛**，短语腿也就无从触发。

**为什么不修**：把 `minSegments` 降到 8 会让短文本误报显著上升（上游的 0 误报是靠这个门槛守住的）。
**建议**：这类坍缩交给 `collapse` 引擎的语义信号，或临时把 `windowChars` 提到 4,800 再观察。

### B3 语义重复（字面不同）不检测

「第 1 步完成。第 2 步完成。……」字面每段都不同，短语腿与低信息腿都不成立。
这是设计边界：repeat 管**字面**，collapse 管**动作/证据**。

---

## 六、验证

```powershell
node test/patch-regression.mjs     # 4 个补丁的 5 个 case
node test/suite-check.mjs <session.jsonl>   # 组合后无回归
```

补丁后实测：

```
case 1 PASS  budget=1 -> 1 continuation across 2 wrap-ups
case 2 PASS  budget=0 -> 0 continuations (config accepted)
case 3 PASS  budget=2 -> 2 continuations across 3 wrap-ups
case 4 PASS  out-of-scope logged once, stream untouched
case 5 PASS  negative budget rejected at load
replay: 1384 steps -> 5 interventions   SUITE PASS
```

---

## 七、升级上游时怎么办

`vendor/repeat` 是 vendored 副本，**不会自动跟随 npm 更新**。
升级步骤：

1. 用新版 `index.js` 替换 `vendor/repeat/index.js`
2. 搜索 `PATCH #` —— 如果新版里没有对应逻辑，重新应用四个补丁
3. 跑 `patch-regression.mjs` + `suite-check.mjs`
4. 更新 `VENDORED` 版本号（`index.js` 顶部）

如果上游已经把 P1–P4 修了，删除对应补丁并在这份文档里记一笔。