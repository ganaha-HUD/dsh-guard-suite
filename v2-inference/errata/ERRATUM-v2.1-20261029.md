# 勘误 v2.1：六处缺陷与修正

> 2026-10-29　｜　对应 Zenodo v2.1
> 本文件取代 v2.0 中的以下描述；原始数据与原始脚本不覆盖，只做声明

| # | v2.0 的错误 | 正确表述 | 证据 |
|---|---|---|---|
| 1 | 会话级 ANOVA 用 `anova_lm(typ=3)` + treatment coding，报 F=12.92/9.51/2.65 | 该调用不返回 Type III 平方和；正确值 F=50.58/97.06/56.50 | `ERRATUM-type3-20261029.md` |
| 2 | 人格系数「正向 = 设定升高 L1」 | 系数是 B（无人格）相对 A；正号意味着设定**降低** L1 | `03-scripts/anova3_fixed.py` 的 term 名 |
| 3 | 轮级 `zero_tool` 与步级 `zero_ratio` 互称印证 | 分母不同（60 轮 vs 69–245 步，均值 112.8），r=.899，不可互证 | `check_truncation.py` 输出 |
| 4 | 「每个阶段同一目标发两次」 | 实现是阶段文本 + 「请继续。」 | `run_api_experiment.py:222-227` |
| 5 | 未披露每轮 5 步上限 | 上限存在；285 轮（7.4%）被截断，全部在逆境，21 会话 | `check_truncation.py` |
| 6 | 「阴性交互即为结论」 | 剔除截断轮后三阶项 p=.008（calls）/ .014（zero_tool），不稳健 | `truncation_sensitivity.py` |

## 复现

包内脚本的数据路径变量 `BASE` 指向 `E:\Deepseek_kolp\data\conv-20261026-f342510a`（作者机器）。
在本包内运行时，把它改为 `01-data` 的上一级即可；`anova3_fixed.py` 读取 `01-data/tables/anova3-records.csv`。

```text
python 03-scripts/anova3_fixed.py
python 03-scripts/check_truncation.py
python 03-scripts/truncation_sensitivity.py
```
