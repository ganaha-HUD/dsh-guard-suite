# Permutation tests for the 2x2 design (no distributional assumptions; n=8 per cell).
import json, os, sys
import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"E:\Deepseek_kolp\data\conv-20261026-f342510a\api2"
recs = json.load(open(os.path.join(ROOT, "analysis-records.json"), encoding="utf-8"))
KEYS = ["L1", "L2", "entropy", "longest_ratio", "zero_ratio", "calls"]
rng = np.random.default_rng(20261027)
NPERM = 20000

def contrasts(rec):
    """return persona vector, adverse vector, y for each key (aligned order)"""
    P = np.array([1 if r["persona"] else 0 for r in rec])
    A = np.array([1 if r["adverse"] else 0 for r in rec])
    return P, A

P, A = contrasts(recs)

def stat_persona(y, p): return y[p == 1].mean() - y[p == 0].mean()
def stat_adverse(y, a): return y[a == 1].mean() - y[a == 0].mean()
def stat_inter(y, p, a):
    def cell(pp, aa): return y[(p == pp) & (a == aa)].mean()
    return (cell(1, 1) - cell(1, 0)) - (cell(0, 1) - cell(0, 0))

def perm(y, stat, labels, *rest, nperm=NPERM):
    obs = stat(y, labels, *rest)
    cnt = 0
    for _ in range(nperm):
        idx = rng.permutation(len(y))
        if abs(stat(y, labels[idx], *rest)) >= abs(obs) - 1e-12:
            cnt += 1
    return obs, (cnt + 1) / (nperm + 1)

print(f"{'metric':14} {'persona':>22} {'adverse':>22} {'interaction':>22}")
print(f"{'':14} {'delta':>9} {'p':>11} {'delta':>9} {'p':>11} {'delta':>9} {'p':>11}")
results = {}
for k in KEYS:
    y = np.array([r[k] for r in recs], dtype=float)
    d1, p1 = perm(y, stat_persona, P)
    d2, p2 = perm(y, stat_adverse, A)
    d3, p3 = perm(y, stat_inter, P, A)
    results[k] = {"persona": (d1, p1), "adverse": (d2, p2), "interaction": (d3, p3)}
    print(f"{k:14} {d1:+9.3f} {p1:11.4f} {d2:+9.3f} {p2:11.4f} {d3:+9.3f} {p3:11.4f}")

json.dump(results, open(os.path.join(ROOT, "perm-results.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\nwritten perm-results.json")

# sensitivity: drop the one English-locked session (B-shun/s02) and low-coverage ones
print("\n=== sensitivity: drop B-shun/s02 (English lock failure) ===")
kept = [r for r in recs if not (r["cell"] == "B-shun" and r["s"] == "s02")]
P2, A2 = contrasts(kept)
for k in KEYS:
    y = np.array([r[k] for r in kept], dtype=float)
    d1, p1 = perm(y, stat_persona, P2, nperm=5000)
    d2, p2 = perm(y, stat_adverse, A2, nperm=5000)
    d3, p3 = perm(y, stat_inter, P2, A2, nperm=5000)
    print(f"{k:14} persona {d1:+.3f} p={p1:.4f} | adverse {d2:+.3f} p={p2:.4f} | inter {d3:+.3f} p={p3:.4f}")