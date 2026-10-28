# 2x2x2 between-subject ANOVA (model x persona x adversity), session = one observation.
import json, os, re, sys
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.anova import anova_lm
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"E:\Deepseek_kolp\data\conv-20261026-f342510a"
K = 10
CN = re.compile(r"[\u4e00-\u9fff]")

def grams(s, n=3):
    return set(s[i:i+n] for i in range(len(s) - n + 1)) if len(s) >= n else set()
def jac(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0
def skel(s):
    return grams("".join(ch for ch in s if ch in set("的了着过是在有和与或但而因为所以如果就才还再又也很都只把被让给对我你他它这那些个不没未无已能会可应须将要该当从到于其此即")), 2)
def series(vals):
    out = []
    for i in range(1, len(vals)):
        out.append(max(jac(vals[i], vals[j]) for j in range(max(0, i - K), i)))
    return float(np.mean(out)) if out else 0.0
def ent(counts):
    tot = sum(counts.values())
    if not tot: return 0.0
    return -sum((v / tot) * np.log2(v / tot) for v in counts.values())
def longest(seq):
    best = cur = 0; prev = None
    for x in seq:
        cur = cur + 1 if x == prev else 1
        prev = x; best = max(best, cur)
    return best

def load_session(path):
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    turns, tools = {}, []
    for r in rows:
        turns.setdefault(int(r.get("turn", 0)), []).append(r.get("reasoning") or "")
        tools += (r.get("raw") or {}).get("tools") or []
    seqs = [(t, "\n".join(v)) for t, v in sorted(turns.items()) if "\n".join(v).strip()]
    g3 = [grams(s) for _, s in seqs]
    g2 = [skel(s) for _, s in seqs]
    cnt = {}
    for t in tools: cnt[t] = cnt.get(t, 0) + 1
    zero = sum(1 for r in rows if int(r.get("tool_calls", 0)) == 0)
    cjk = sum(1 for _, s in seqs if CN.search(s))
    return {
        "calls": len(tools),
        "entropy": ent(cnt),
        "longest_ratio": longest(tools) / len(tools) if tools else 0.0,
        "L1": series(g3), "L2": series(g2),
        "zero_ratio": zero / len(rows) if rows else 0.0,
        "cjk_ratio": cjk / len(seqs) if seqs else 0.0,
    }

rows = []
for model, (root, tag) in [("DeepSeek", (os.path.join(BASE, "api2"), "formal")),
                           ("MiMo", (os.path.join(BASE, "mimo"), "mf"))]:
    for cell in ["A-shun", "A-ni", "B-shun", "B-ni"]:
        d = os.path.join(root, cell)
        for f in sorted(os.listdir(d)):
            if not (f.startswith(tag + "-s") and f.endswith(".jsonl")): continue
            rec = load_session(os.path.join(d, f))
            rec.update(model=model, persona="A" if cell.startswith("A") else "B",
                       adversity="shun" if cell.endswith("shun") else "ni", session=f)
            rows.append(rec)

df = pd.DataFrame(rows)
print(f"sessions={len(df)}  cells={df.groupby(['model','persona','adversity']).ngroups}")
print(df.groupby(["model", "persona", "adversity"]).size().to_string())

METRICS = ["calls", "entropy", "longest_ratio", "zero_ratio", "L1", "L2"]
formula = "y ~ C(model) * C(persona) * C(adversity)"
print("\n=== 2x2x2 ANOVA (Type III), partial eta^2 ===")
print(f"{'metric':13}{'effect':22}{'F':>8}{'p':>9}{'p.eta2':>9}")
for m in METRICS:
    d2 = df.copy()
    d2["y"] = d2[m]
    model = smf.ols(formula, data=d2).fit()
    aov = anova_lm(model, typ=3)
    ss_err = aov.loc["Residual", "sum_sq"]
    for idx in aov.index:
        if idx == "Residual" or idx.startswith("Intercept"): continue
        F, p, ss = aov.loc[idx, "F"], aov.loc[idx, "PR(>F)"], aov.loc[idx, "sum_sq"]
        pe = ss / (ss + ss_err)
        name = idx.replace("C(model)", "model").replace("C(persona)", "persona").replace("C(adversity)", "adversity")
        flag = "  *" if p < 0.05 else ""
        print(f"{m:13}{name:22}{F:8.2f}{p:9.3f}{pe:9.3f}{flag}")

print("\n=== Levene (homogeneity across the 8 cells) ===")
for m in METRICS:
    groups = [g[m].values for _, g in df.groupby(["model", "persona", "adversity"])]
    W, p = stats.levene(*groups)
    print(f"{m:13} W={W:6.2f}  p={p:.3f}  {'OK' if p > .05 else 'HETEROGENEOUS'}")
df.to_csv(os.path.join(BASE, "anova3-records.csv"), index=False, encoding="utf-8")
print("\nwritten anova3-records.csv")