# Re-verify the permutation tests with scipy's own implementation.
import json, os, sys
import numpy as np
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"E:\Deepseek_kolp\data\conv-20261026-f342510a\api2"
recs = json.load(open(os.path.join(ROOT, "analysis-records.json"), encoding="utf-8"))
mine = json.load(open(os.path.join(ROOT, "perm-results.json"), encoding="utf-8"))
KEYS = ["L1", "L2", "entropy", "longest_ratio", "zero_ratio", "calls"]
P = np.array([1 if r["persona"] else 0 for r in recs])
A = np.array([1 if r["adverse"] else 0 for r in recs])
rng = np.random.default_rng(7)

def s_persona(y, p): return y[p == 1].mean() - y[p == 0].mean()
def s_adverse(y, a): return y[a == 1].mean() - y[a == 0].mean()
def s_inter(y, p, a):
    def c(pp, aa): return y[(p == pp) & (a == aa)].mean()
    return (c(1, 1) - c(1, 0)) - (c(0, 1) - c(0, 0))

print(f"{'metric':13} {'test':10} {'mine p':>9} {'scipy p':>9}  agree")
for k in KEYS:
    y = np.array([r[k] for r in recs], dtype=float)
    tv = {"persona": (s_persona, P), "adverse": (s_adverse, A)}
    for name, (fn, lab) in tv.items():
        r = stats.permutation_test((y[lab == 1], y[lab == 0]),
                                   lambda a, b: a.mean() - b.mean(),
                                   permutation_type="independent", n_resamples=20000,
                                   random_state=rng)
        p_scipy = float(r.pvalue)
        p_mine = mine[k][name][1]
        ok = abs(p_scipy - p_mine) < 0.01
        print(f"{k:13} {name:10} {p_mine:9.4f} {p_scipy:9.4f}  {'OK' if ok else 'DIFF'}")
    # interaction: 2x2, compare the contrast via label permutation (scipy has no direct 2x2)
    obs = s_inter(y, P, A)
    cnt = 0
    for _ in range(20000):
        idx = rng.permutation(len(y))
        if abs(s_inter(y, P[idx], A[idx])) >= abs(obs) - 1e-12: cnt += 1
    p_inter = (cnt + 1) / 20001
    p_mine = mine[k]["interaction"][1]
    ok = abs(p_inter - p_mine) < 0.01
    print(f"{k:13} {'interact':10} {p_mine:9.4f} {p_inter:9.4f}  {'OK' if ok else 'DIFF'}")