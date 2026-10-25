# 复现步骤（中文）

> English version: [`REPRODUCE.md`](./REPRODUCE.md)

## 需要什么

- Node.js 20 以上（我用的 24.20）
- **不需要装任何 npm 包**，脚本只用 `node:fs` / `node:path`

## 第一步：拿日志

`session/session.v4.jsonl` 已经解压好了，就是生成所有数字用的那份，直接用。

如果你想自己从 `session.v4.jsonl.zstd` 解压，**先看这个坑**：

> 这个文件是 **5,990 个 zstd 帧拼起来的**（每次写入一帧）。
> `zlib.zstdDecompressSync()` 一次只解**第一帧**——只有 192 字节，就是会话头。
> 必须按帧边界切开逐帧解，或者用流式解压。

## 第二步：重新标注

```bash
cd collapse-dataset
node code/annotate-session.mjs
node code/summarize-turns.mjs
```

`annotate-session.mjs` 顶部的 `SRC` 是硬编码路径，指向你机器上的
`session/session.v4.jsonl`。

## 第三步：对答案

跑出来应该是：

```
steps: 1384
labels: { normal: 1100, collapse: 10, suspect: 274 }
flags:  { think_only: 10, template_heavy: 283, simulated_action: 4 }

turns: 134
collapse_turns: [27,112,113,125,127,128,130,132,134,136]
first_suspect_turn: 73
```

数字对不上，先检查源文件编码（必须是 UTF-8 无 BOM）。

## 第四步：三条自检

在相信任何衍生统计之前，先跑这三条：

```bash
# a) 那个 3 秒的"检查"必须被标成 collapse
grep '"turn":134' annotations/steps.jsonl | grep '"label":"collapse"'

# b) 调了 10 次工具的那一步，不能被误判成模拟执行
grep '"turn":131' annotations/steps.jsonl | grep -c 'simulated_action'   # 应该是 0

# c) 防护插件在坍缩期间触发 0 次
#    外部证据：~\.dsh\logs\dsh-guard-repeat-output.log，最后写入是 2026-10-21
```

## 第五步：看检测器视角

`code/collapse-check.mjs` 是论文里那个干预方案的检测器，吃同一份日志：

```bash
node code/collapse-check.mjs session/session.v4.jsonl 12
```

预期会看到尾窗四项同时爆表：

```
toolsPerTurn      1.25   (< 2.0)
evidenceD         2.40   (< 3.0)
pseudoCertainty   0.40   (> 0.25)
falsifyPerTurn    0.25   (< 0.30)
```

**四项同时不达标——这就是"该停手交接"的客观信号**，不用等人喊停。