# How the adversity factor is coded

`adversity` takes two string values: `shun` (顺, every tool call succeeds) and `ni`
(逆, 80% of calls time out). Every model in the analysis uses the formula
`~ C(adversity)`. Patsy picks the alphabetically first level as the reference, so
`ni` is the baseline and the design matrix carries one term:

```
C(adversity)[T.shun]
```

That column is **1 for `shun`, 0 for `ni`**. In other words the indicator is
`D = (env == "shun")`, not `1 - adversity`.

## What that does to the coefficients

| Outcome | Coefficient | Reading |
|---|---|---|
| `zero_tool` (Binomial, logit) | +0.9233 | the working regime has higher odds of a no-call step (OR = 2.52) |
| `calls` (Poisson, log) | −0.7819 | the working regime issues fewer calls (IRR = 0.46) |

Both agree with the descriptive table: at cell level, `zero_ratio` is 0.768 / 0.829
in the healthy cells against 0.567 / 0.472 in the adverse ones, and `calls` runs the
other way.

## Verify it yourself

```python
import pandas as pd
from patsy import dmatrix
df = pd.read_csv("tables/turnlevel.csv")
X = dmatrix("C(adversity)", df, return_type="dataframe")
print(list(X.columns))            # ['Intercept', 'C(adversity)[T.shun]']
print(X[df.adversity == "ni"].iloc[0].to_dict())    # shun column = 0.0
print(X[df.adversity == "shun"].iloc[0].to_dict())  # shun column = 1.0
```

A regression of any outcome on `C(adversity)` reproduces `mean(shun) - mean(ni)`
exactly, which only holds if the coding is as described.

## A note on the record

The v2.0 paper describes this factor as `(adverse = 1)`. That sentence is wrong; the
data and code never were. With the wrong description, both regime coefficients read
in the opposite direction, which is why the correction matters more than a typo
usually would. The paper was corrected to `(healthy = 1)` and the corrected PDF
carries the same numbers.

Tags: `v2.0-buggy-env-coding` marks the commit whose accompanying paper had the
inverted description; `v2.1` adds this note and changes nothing in the data.