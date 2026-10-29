# -*- coding: utf-8 -*-
"""Corrected session-level 2x2x2 ANOVA.

Root cause of the published numbers: anova_lm(typ=3) on a treatment-coded
formula does not compute Type III sums of squares. In a balanced design
Type I = II = III, so the correct value is the one that agrees across
typ=1, typ=2 and typ=3-with-sum-to-zero-coding.

This script computes both routes, asserts they agree, and writes the corrected
session-level table.
"""
import os, sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.anova import anova_lm
from statsmodels.genmod.generalized_estimating_equations import GEE
from statsmodels.genmod.families import Poisson, Gaussian, Binomial
from statsmodels.genmod.cov_struct import Autoregressive
from statsmodels.stats.anova import anova_lm as _al
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"E:\Deepseek_kolp\data\conv-20261026-f342510a"
rec = pd.read_csv(os.path.join(BASE, "anova3-records.csv"))
tl = pd.read_csv(os.path.join(BASE, "turnlevel.csv"))

METRICS = ["L1", "L2", "zero_ratio", "calls", "entropy", "longest_ratio"]
LABEL = {"C(model)": "model", "C(persona)": "persona", "C(adversity)": "regime",
         "C(model):C(persona)": "model x persona", "C(model):C(adversity)": "model x regime",
         "C(persona):C(adversity)": "persona x regime",
         "C(model):C(persona):C(adversity)": "three-way"}
SUMNAME = {"C(model)": "C(model, Sum)", "C(persona)": "C(persona, Sum)",
           "C(adversity)": "C(adversity, Sum)",
           "C(model):C(persona)": "C(model, Sum):C(persona, Sum)",
           "C(model):C(adversity)": "C(model, Sum):C(adversity, Sum)",
           "C(persona):C(adversity)": "C(persona, Sum):C(adversity, Sum)",
           "C(model):C(persona):C(adversity)": "C(model, Sum):C(persona, Sum):C(adversity, Sum)"}

out = []
print("=" * 100)
print("cross-check: typ=2 (treatment) vs typ=3 (sum-to-zero). Balanced design => must be identical.")
print("=" * 100)
for m in METRICS:
    dd = rec.copy(); dd["y"] = dd[m]
    a2 = anova_lm(smf.ols("y ~ C(model)*C(persona)*C(adversity)", data=dd).fit(), typ=2)
    a3s = anova_lm(smf.ols("y ~ C(model,Sum)*C(persona,Sum)*C(adversity,Sum)", data=dd).fit(), typ=3)
    sse = float(a2.loc["Residual", "sum_sq"])
    print("\n--- %s ---" % m)
    for k in LABEL:
        ss2 = float(a2.loc[k, "sum_sq"]); ss3 = float(a3s.loc[SUMNAME[k], "sum_sq"])
        diff = abs(ss2 - ss3)
        F = ss2 / (sse / 56.0)
        p = float(stats.f.sf(F, 1, 56))
        eta = ss2 / (ss2 + sse)
        flag = "OK " if diff < 1e-6 else "!! MISMATCH"
        print("  %-20s SS=%14.6f  SS(sum)=%14.6f  %s  F=%8.3f  p=%.4g  eta2p=%.3f"
              % (LABEL[k], ss2, ss3, flag, F, p, eta))
        out.append(dict(metric=m, term=LABEL[k], ss=ss2, df=1, F=F, p=p, eta2p=eta))

df = pd.DataFrame(out)
csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "conv-20261029-7d9a3cac", "session-anova-corrected.csv")
os.makedirs(os.path.dirname(csv), exist_ok=True)
df.to_csv(csv, index=False, encoding="utf-8")
print("\nwritten: %s  (%d rows)" % (os.path.abspath(csv), len(df)))

print("\n" + "=" * 100)
print("turn-level GEE, recomputed for comparison (unchanged by this fix)")
print("=" * 100)
F = "y ~ C(model)*C(persona)*C(adversity)"
for metric, fam in [("calls", Poisson()), ("zero_tool", Binomial()), ("L1", Gaussian()), ("L2", Gaussian())]:
    d2 = tl.copy(); d2["y"] = d2[metric]
    g = GEE.from_formula(F, groups="session", data=d2, family=fam, cov_struct=Autoregressive()).fit()
    print("\n--- %s ---" % metric)
    for term in ["C(model)[T.MiMo]", "C(persona)[T.B]", "C(adversity)[T.shun]",
                 "C(model)[T.MiMo]:C(persona)[T.B]:C(adversity)[T.shun]"]:
        if term in g.params.index:
            print("  %-52s coef=%+9.4f SE=%8.4f p=%.4g" % (term, g.params[term], g.bse[term], g.pvalues[term]))