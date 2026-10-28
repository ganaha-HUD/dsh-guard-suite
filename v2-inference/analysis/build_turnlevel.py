# Build the turn-level table used by the mixed model, and report ICC so the
# effective sample size is known before anyone trusts a p-value.
import json, os, re, sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"E:\Deepseek_kolp\data\conv-20261026-f342510a"
K = 10
FUNC = set("的了着过是在有和与或但而因为所以如果就才还再又也很都只把被让给对我你他它这那些个不没未无已能会可应须将要该当从到于其此即")
def grams(s, n=3):
    return set(s[i:i+n] for i in range(len(s)-n+1)) if len(s) >= n else set()
def jac(a, b): return len(a & b)/len(a | b) if a and b else 0.0
def skel(s): return grams("".join(c for c in s if c in FUNC), 2)

rows = []
for model, (root, tag) in [("DeepSeek", (os.path.join(BASE, "api2"), "formal")),
                           ("MiMo", (os.path.join(BASE, "mimo"), "mf"))]:
    for cell in ["A-shun", "A-ni", "B-shun", "B-ni"]:
        d = os.path.join(root, cell)
        for f in sorted(os.listdir(d)):
            if not (f.startswith(tag + "-s") and f.endswith(".jsonl")): continue
            sess = f"{model}-{cell}-{os.path.splitext(f)[0]}"
            rs = [json.loads(l) for l in open(os.path.join(d, f), encoding="utf-8") if l.strip()]
            turns = {}
            for r in rs:
                turns.setdefault(int(r.get("turn", 0)), []).append(r)
            seq = [(t, "\n".join((x.get("reasoning") or "") for x in v)) for t, v in sorted(turns.items())]
            G3 = [grams(s) for _, s in seq]
            G2 = [skel(s) for _, s in seq]
            for i, (t, s) in enumerate(seq):
                l1 = max((jac(G3[i], G3[j]) for j in range(max(0, i-K), i)), default=0.0)
                l2 = max((jac(G2[i], G2[j]) for j in range(max(0, i-K), i)), default=0.0)
                sub = turns[t]
                rows.append({
                    "session": sess, "model": model,
                    "persona": "A" if cell.startswith("A") else "B",
                    "adversity": "shun" if cell.endswith("shun") else "ni",
                    "turn": t,
                    "L1": l1, "L2": l2,
                    "calls": sum(len((r.get("raw") or {}).get("tools") or []) for r in sub),
                    "zero_tool": int(sum(int(r.get("tool_calls", 0)) for r in sub) == 0),
                    "reason_chars": len(s),
                })
df = pd.DataFrame(rows)
out = os.path.join(BASE, "turnlevel.csv")
df.to_csv(out, index=False, encoding="utf-8")
print(f"rows={len(df)}  sessions={df.session.nunique()}  written {out}")

def icc(d, col):
    # one-way random effects ICC(1)
    g = d.groupby("session")[col]
    k = g.size().mean()
    msb = g.mean().var(ddof=1) * k
    msw = d.groupby("session")[col].apply(lambda x: x.var(ddof=1)).mean()
    return (msb - msw) / (msb + (k - 1) * msw) if (msb + (k - 1) * msw) else float("nan")

print("\n=== ICC(1) per metric (how much of the variance is between sessions) ===")
for c in ["L1", "L2", "calls", "zero_tool"]:
    v = icc(df, c)
    de = 1 + (60 - 1) * v if v == v else float("nan")
    print(f"{c:10} ICC={v:6.3f}  design effect={de:5.1f}  effective n={len(df)/de:7.1f}")