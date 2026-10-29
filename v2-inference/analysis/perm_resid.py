# -*- coding: utf-8 -*-
"""Interaction-only permutation: shuffle residuals under the main-effects model.

Null: the persona x regime term is zero, while model, persona and regime main
effects are free. Residuals from y ~ model + persona + regime are permuted
(globally, which preserves the 8-per-cell design), added back to the fitted
main-effects values, and the interaction sum of squares is recomputed with the
same balanced coefficients. The observed statistic is compared to that null.
"""
import sys
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
D = r"E:\Deepseek_kolp\data\conv-20261026-f342510a"
d = pd.read_csv(D + r"\anova3-records.csv")
rng = np.random.default_rng(20261029)


def ss_inter(y, d):
    """Type III SS for persona x regime, balanced 2x2x2, 8 per cell."""
    df = pd.DataFrame({"y": y, "p": d.persona.values, "a": d.adversity.values})
    g = y.mean()
    pm = df.groupby("p").y.mean()
    am = df.groupby("a").y.mean()
    pam = df.groupby(["p", "a"]).y.mean()
    s = sum((v - pm[k[0]] - am[k[1]] + g) ** 2 for k, v in pam.items())
    return 16.0 * float(s)


for metric in ["calls", "zero_ratio"]:
    dd = d.copy(); dd["y"] = dd[metric]
    main = smf.ols("y ~ C(model) + C(persona) + C(adversity)", data=dd).fit()
    fitted = main.fittedvalues.values
    resid = main.resid.values
    obs = ss_inter(dd.y.values, dd)
    null = np.empty(4000)
    for b in range(4000):
        null[b] = ss_inter(fitted + rng.permutation(resid), dd)
    p = (np.sum(null >= obs) + 1) / 4001.0
    print("%-11s observed SS=%10.2f  null median=%10.2f  p_resid=%.4f"
          % (metric, obs, np.median(null), p))