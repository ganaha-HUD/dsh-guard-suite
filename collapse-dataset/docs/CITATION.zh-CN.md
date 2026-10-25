# 引用说明（中文）

> English version: [`CITATION.md`](./CITATION.md)

## BibTeX

```bibtex
@dataset{dsh_collapse_2026,
  title  = {Session 3b54e160: A Single-Trajectory Dataset of Shrink-Collapse in an LLM Agent},
  author = {ganaha-HUD},
  year   = {2026},
  month  = {10},
  note   = {137 turns, 1,384 annotated assistant steps, 10 collapse events.
            Model: deepseek-flash. Includes full append-only log and all
            artifacts produced during the session.},
  url    = {https://github.com/ganaha-HUD/dsh-guard-suite}
}
```

## 每个结论该引哪里

| 你要说的 | 引哪里 |
|---|---|
| "这种收缩型坍缩现象存在" | 本数据集 + `docs/METHOD.md` |
| "膨胀型和收缩型要区分" | 本数据集 `docs/README.md` 的"为什么值得做成数据集" |
| "现有防护看不见"（0.80 vs 0.44） | 本数据集 + `outputs/data/` 里的 `dsh-guard-repeat-output` 源码 |
| "干预方案（TRACE 四闸）" | `https://github.com/ganaha-HUD/dsh-guard-suite` 的 `PATCHES.md` |

## 必须写清的适用范围

这是一个**单轨迹**数据集。它支持**存在性**论断（"这种失效会发生，形态如下"），
**不支持**普遍性论断（"发生率是多少""别的模型也一样"）。

任何比率、频率、跨模型结论，都要补会话。

## 联系

有问题去 https://github.com/ganaha-HUD/dsh-guard-suite 开 issue。