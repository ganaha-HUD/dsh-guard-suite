# -*- coding: utf-8 -*-
"""Interaction-only residual permutation, with every other effect kept.

Null model = full 2x2x2 model minus the persona x regime column. Residuals are
permuted and added back to the fitted values; the Type III sum of squares for
persona x regime is recomputed. Null: persona x regime = 0 with model, persona,
regime, model x persona, model x regime and the three-way term all free.
"""
import sys
import numpy as np, pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = pd.read_csv(r"E:\Deepseek_kolp\data\conv-20261026-f342510a\anova3-records.csv")
F = "y ~ C(model,Sum)*C(persona,Sum)*C(adversity,Sum)"
rng = np.random.default_rng(20261029)


def ss_pa(y):
    df = pd.DataFrame({"y": y, "p": d.persona.values, "a": d.adversity.values})
    g = y.mean(); pm = df.groupby("p").y.mean(); am = df.groupby("a").y.mean()
    pam = df.groupby(["p", "a"]).y.mean()
    return 16.0 * float(sum((v - pm[k[0]] - am[k[1]] + g) ** 2 for k, v in pam.items()))


for metric in ["calls", "zero_ratio"]:
    dd = d.copy(); dd["y"] = dd[metric]
    full = smf.ols(F, data=dd).fit()
    names = list(full.model.exog_names)
    idx = [i for i, n in enumerate(names) if "persona" in n and "adversity" in n and "model" not in n]
    Xr = np.delete(full.model.exog, idx, axis=1)
    red = sm.OLS(dd.y.values, Xr).fit()
    fitted = red.predict(Xr)
    resid = dd.y.values - fitted
    obs = ss_pa(dd.y.values)
    null = np.empty(4000)
    for b in range(4000):
        null[b] = ss_pa(fitted + rng.permutation(resid))
    p = (np.sum(null >= obs) + 1) / 4001.0
    print("%-11s observed=%10.2f  null_med=%10.2f  p=%.4f" % (metric, obs, np.median(null), p))