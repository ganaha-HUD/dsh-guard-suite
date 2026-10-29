# -*- coding: utf-8 -*-
"""Does dropping the step-5-truncated turns change the conclusions?"""
import json, os, sys
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.anova import anova_lm
from statsmodels.genmod.generalized_estimating_equations import GEE
from statsmodels.genmod.families import Poisson, Gaussian, Binomial
from statsmodels.genmod.cov_struct import Autoregressive
from scipy import stats
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"E:\Deepseek_kolp\data\conv-20261026-f342510a"

rows_all, rows_keep, turns_keep = [], [], []
for model, sub, tag in [("DeepSeek", "api2", "formal"), ("MiMo", "mimo", "mf")]:
    for cell in ["A-shun", "A-ni", "B-shun", "B-ni"]:
        d = os.path.join(BASE, sub, cell)
        for f in sorted(os.listdir(d)):
            if not (f.startswith(tag + "-s") and f.endswith(".jsonl")):
                continue
            sid = "%s-%s-%s" % (model, cell, f.replace(".jsonl", ""))
            rows = [json.loads(l) for l in open(os.path.join(d, f), encoding="utf-8") if l.strip()]
            turns = {}
            for r in rows:
                turns.setdefault(int(r["turn"]), []).append(r)
            trunc = set()
            for t, rs in turns.items():
                rs.sort(key=lambda x: int(x.get("step", 0)))
                if int(rs[-1].get("step", 0)) >= 5 and int(rs[-1].get("tool_calls", 0)) > 0:
                    trunc.add(t)
            for t, rs in turns.items():
                calls = sum(len((x.get("raw") or {}).get("tools") or []) for x in rs)
                zero = int(calls == 0)
                rows_all.append(dict(sid=sid, model=model, persona="A" if cell.startswith("A") else "B",
                                     adversity="shun" if cell.endswith("shun") else "ni", turn=t,
                                     calls=calls, zero=zero))
                if t not in trunc:
                    rows_keep.append(dict(sid=sid, model=model, persona="A" if cell.startswith("A") else "B",
                                          adversity="shun" if cell.endswith("shun") else "ni", turn=t,
                                          calls=calls, zero=zero))
for df, name in [(pd.DataFrame(rows_all), "all turns"), (pd.DataFrame(rows_keep), "drop truncated")]:
    print("\n=== %s  (turns=%d, sessions=%d) ===" % (name, len(df), df.sid.nunique()))
    # turn-level GEE
    for metric, fam in [("calls", Poisson()), ("zero", Binomial())]:
        g = GEE.from_formula("%s ~ C(model)*C(persona)*C(adversity)" % metric, groups="sid",
                             data=df, family=fam, cov_struct=Autoregressive()).fit()
        for term in ["C(adversity)[T.shun]", "C(model)[T.MiMo]",
                     "C(persona)[T.B]", "C(persona)[T.B]:C(adversity)[T.shun]",
                     "C(model)[T.MiMo]:C(persona)[T.B]:C(adversity)[T.shun]"]:
            print("  %-7s %-58s coef=%+8.4f p=%.4g" % (metric, term, g.params[term], g.pvalues[term]))
    # session level
    ses = df.groupby("sid").agg(calls=("calls", "sum"), zero_ratio=("zero", "mean"),
                                model=("model", "first"), persona=("persona", "first"),
                                adversity=("adversity", "first")).reset_index()
    a = anova_lm(smf.ols("calls ~ C(model)*C(persona)*C(adversity)", data=ses).fit(), typ=2)
    sse = a.loc["Residual", "sum_sq"]
    F = a.loc["C(adversity)", "sum_sq"] / (sse / 56)
    print("  session calls  regime F=%.2f p=%.4g  (shun %.1f vs ni %.1f)"
          % (F, stats.f.sf(F, 1, 56), ses[ses.adversity == "shun"].calls.mean(),
             ses[ses.adversity == "ni"].calls.mean()))
    a = anova_lm(smf.ols("zero_ratio ~ C(model)*C(persona)*C(adversity)", data=ses).fit(), typ=2)
    sse = a.loc["Residual", "sum_sq"]
    F = a.loc["C(adversity)", "sum_sq"] / (sse / 56)
    print("  session zero   regime F=%.2f p=%.4g" % (F, stats.f.sf(F, 1, 56)))