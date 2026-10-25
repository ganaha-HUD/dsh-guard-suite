# 会话 3b54e160 — 收缩型坍缩数据集 v1

> English version: [`README.md`](./README.md)

这是一个**单条轨迹**的完整标注数据集：一个 AI 智能体在 137 轮对话里，
逐渐"只说不做"，但语气始终笃定。发布出来供研究"模型退化""自我验证失效"
"智能体可靠性"的同学使用。

- **会话**：`session-3b54e160-6d42-43a7-b4af-bffba94d76d9`（DSH 桌面版，工作目录 `E:\Deepseek`）
- **时间跨度**：2026-09-28 → 2026-10-24，137 轮，10,816 条事件，**1,384 个 assistant 步**
- **模型**：`deepseek-flash`
- **标注范围**：每一个 assistant 步，**全量，没有抽样**
- **标签分布**：`normal` 1,100 · `suspect` 274 · `collapse` 10

## 为什么值得做成数据集

现在讲"模型重复崩坏"的论文和工具，盯的都是**膨胀型**：同一句话重复几万次，
文本越来越长。但这个会话是反过来的：

| 指标 | 前 36 轮 | 最后 12 轮 |
|---|---|---|
| 工具调用 / 轮 | 10.31 | 1.25 |
| 字符数 / 轮 | 9,879 | 1,527 |
| 证据标记 / 千字 | 4.34 | 2.40 |
| **断言 / 千字** | **1.12** | **1.20** |

文字少了 85%，动作少了 88%，**但"断言"的密度几乎没变**。

这就是关键：它没有变啰嗦，是**变安静、变短、语气没变**。
所以任何"数重复"的检测器都看不见它——因为没有东西在重复。

## 包里有什么

```
collapse-dataset/
├── session/                     原始日志
│   ├── session.v4.jsonl.zstd      12.7 MB（5,990 个 zstd 帧）
│   └── session.v4.jsonl           47.3 MB（解压后，10,816 条事件）
├── annotations/                 标注结果
│   ├── steps.jsonl                1,384 行，每个 assistant 步一行
│   ├── steps.csv                  扁平表，UTF-8 无 BOM（pandas/R 用这个）
│   ├── steps-excel.csv            扁平表，UTF-8 带 BOM（Excel 双击用这个）
│   ├── turns.json                 134 行，按轮汇总
│   ├── turns.csv
│   └── turns-excel.csv
├── outputs/                     这个会话自己产出的所有文件
│   ├── deliverables/              9 份交付文档
│   ├── logs/                      31 份运行日志
│   ├── scripts/                   12 个脚本
│   ├── data/                      下载的插件包
│   └── archive/                   旧版本、恢复产物
├── analysis/                     T86 前后对比（报告、统计、图）
├── context/                     实验环境（必看！）
│   ├── policy/                    当时生效的 8 个规则文件
│   ├── tools/                     规则要求的 5 个脚本
│   ├── agents-md/                 人格注入前后的系统提示词快照
│   └── persona-injection-turn86.md   T86 注入的人格原文
├── code/                        复现代码
│   ├── annotate-session.mjs       生成 steps.jsonl / steps.csv
│   ├── summarize-turns.mjs        生成 turns.json / turns.csv
│   ├── collapse-check.mjs         实时检测器（论文里那个干预方案）
│   └── analyze-fingerprints.mjs   分阶段特征对比
└── docs/                        文档（中英各一份）
```

## 三条最关键的发现

**1. 坍缩不是突然发生的，是滑下去的。**

```
出现 collapse 的轮次：27, 112, 113, 125, 127, 128, 130, 132, 134, 136
第一次出现"模板重"：T73
最后一次 collapse：T136
```

T27 是孤立的一次，真正的累积从 **T73** 开始，**T112 之后密集爆发**。

**2. 最干净的一个样本：T134 第 1 步**

用户问：「检查一下防概率自陷的插件和规则是否还生效。」

模型的思考里写了 **5 次 `grep`**，但：
- 工具调用 **0 次**
- 正文 **0 字符**
- 3 秒结束

它把"打算检查"演了一遍，然后当成"检查完了"。

**3. 现有防护完全没反应**

`dsh-guard-repeat-output` v2.1.7 在整个坍缩期间**触发 0 次**。
它的定罪线是 `lowInfoDupShare >= 0.80`，而本会话实测最高 **0.44**。
永远够不到。

## 快速上手

```bash
# 标注结果直接看表
#   steps.csv / turns.csv —— 用 Excel、pandas、R 都行

# 想重新跑标注
node code/annotate-session.mjs
node code/summarize-turns.mjs

# 想看实时检测器的视角
node code/collapse-check.mjs session/session.v4.jsonl 12
```

**注意**：`session.v4.jsonl.zstd` 是 **5,990 个 zstd 帧拼接**的，
单次 `zstdDecompressSync` 只解第一帧（192 字节）。要么用 `session/` 里的
解压版，要么按帧边界切。这个坑 `docs/REPRODUCE.md` 里写了。

## 脱敏说明

`session/session.v4.jsonl` 是解压后的会话日志，其中**一处 API key 已脱敏**。
原始会话里，某次配置检查把 `DEEPSEEK_API_KEY` 的值打印了出来，该值已替换为
`sk-***REDACTED***`。压缩原件（`session.v4.jsonl.zstd`）**未包含**在数据集中，
因为重新压缩会改变字节，而它本身仍带着这个密钥。

这不影响任何标注、统计或结论：被替换的字符串出现在一段配置输出里，
不在模型推理步骤中。

## 许可与隐私

- 标注、文档、分析、上下文文件：**CC BY 4.0**（全文见根目录 `LICENSE`）
- 分析代码（`code/`）：**MIT**
- 机器可读的存档元数据：`.zenodo.json`
- 会话内容：只有你自己的提问和模型输出，没有第三方个人信息
- 文件路径保留原样（验证结论需要），但**没有任何密钥、token、密码**（已用正则扫过）

## 一句话

> 它不是撒谎。它是把"想做"当成了"做了"，而且自己真的信了。