# 数据格式与打开方式（中文）

## 一句话

**Excel 用户打开 `*-excel.csv`；写代码（pandas/R）用不带后缀的那个。**

## 为什么有两个版本

| 文件 | 编码 | 给谁 |
|---|---|---|
| `steps.csv` / `turns.csv` | UTF-8 **无 BOM** | pandas、R、VS Code、程序读 |
| `steps-excel.csv` / `turns-excel.csv` | UTF-8 **带 BOM** | Excel 双击打开 |

**原因**：Excel 双击 CSV 时不会问编码，直接按系统默认（中文 Windows 是 GBK）解析。
UTF-8 的中文在 GBK 下就是乱码。加 BOM（文件开头三个字节 `EF BB BF`）后，
Excel 才会认出这是 UTF-8。

而 pandas 读带 BOM 的文件时，第一列名会变成 `\ufeffseq`——所以两个版本都要有。

## Excel 怎么开

1. 双击 `steps-excel.csv`
2. 中文应该正常显示

如果还是乱码，用**导入**而不是双击：

```
数据 → 获取数据 → 从文本/CSV → 选文件 → 文件原始格式选 65001: Unicode (UTF-8)
```

## pandas 怎么读

```python
import pandas as pd

steps = pd.read_csv("annotations/steps.csv")          # 无 BOM，直接读
turns = pd.read_csv("annotations/turns.csv")

print(steps["label"].value_counts())
# collapse    10
# suspect    274
# normal    1100

# 只看坍缩的
print(steps[steps.label == "collapse"][["turn","step","note"]])
```

如果读 `-excel.csv` 版本，要写：

```python
pd.read_csv("annotations/steps-excel.csv", encoding="utf-8-sig")
```

## JSON 版本

`steps.jsonl`（每行一个 JSON）和 `turns.json`（一个数组）**都是 UTF-8 无 BOM**，
VS Code、Python、Node、R 都直接读，没有 Excel 的那个问题。

```python
import json
rows = [json.loads(l) for l in open("annotations/steps.jsonl", encoding="utf-8")]
```

## 字段速查

`steps.csv` 共 21 列，最重要的几列：

| 列 | 含义 |
|---|---|
| `seq` | 日志里的序号，用来回溯原文 |
| `turn` / `step` | 第几轮、第几步 |
| `tool_calls` | 这一步调了几次工具（**最关键**） |
| `chars` | 这一步总字数 |
| `action_words` | 思考里的动作词数量 |
| `evidence_marks` | 可核对证据的数量 |
| `template_hits` | `**好** ✓` 模板出现次数 |
| `label` | `normal` / `suspect` / `collapse` |
| `note` | 判定理由（英文，程序生成的标签说明） |

`turns.csv` 共 17 列，多了 `first_user`（这一轮用户说的第一句话）和
`tools_per_step`（平均每步调几次工具）。

## 常见问题

**Q：为什么 `note` 是英文？**
A：那是程序生成的判定标签，英文方便跨语言处理。中文解释在 `docs/METHOD.zh-CN.md`。

**Q：`top_phrase` 里有 `**好** ✓` 这种带星号的，正常吗？**
A：正常。模型思考里就是 markdown 粗体，我保留原貌没清洗。

**Q：数字对不上怎么办？**
A：先确认读的是无 BOM 版本；再确认源文件是 UTF-8。