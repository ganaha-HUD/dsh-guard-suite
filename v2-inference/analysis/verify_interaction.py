# Correct interaction test: shuffle samples across the four cells (keeps cell sizes),
# which is the proper null for a balanced 2x2 interaction contrast.
import json, os, sys
import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"E:\Deepseek_kolp\data\conv-20261026-f342510a\api2"
recs = json.load(open(os.path.join(ROOT, "analysis-records.json"), encoding="utf-8"))
KEYS = ["L1", "L2", "entropy", "longest_ratio", "zero_ratio", "calls"]
rng = np.random.default_rng(20261027)
NPERM = 20000

# cell index: 0=A-shun 1=A-ni 2=B-shun 3=B-ni
cell_of = {(True, False): 0, (True, True): 1, (False, False): 2, (False, True): 3}
cidx = np.array([cell_of[(r["persona"], r["adverse"])] for r in recs])
sizes = [int((cidx == c).sum()) for c in range(4)]

def inter_contrast(y, idx):
    m = [y[idx == c].mean() for c in range(4)]   # A-shun, A-ni, B-shun, B-ni
    return (m[1] - m[0]) - (m[3] - m[2])         # interaction

print(f"{'metric':13} {'obs':>8} {'p_2k':>8} {'p_20k':>8}   note")
for k in KEYS:
    y = np.array([r[k] for r in recs], dtype=float)
    obs = inter_contrast(y, cidx)
    cnt = 0
    for _ in range(NPERM):
        perm = rng.permutation(len(y))
        lab = np.empty(len(y), dtype=int)
        pos = 0
        for c, n in enumerate(sizes):
            lab[perm[pos:pos + n]] = c
            pos += n
        if abs(inter_contrast(y, lab)) >= abs(obs) - 1e-12: cnt += 1
    p = (cnt + 1) / (NPERM + 1)
    note = "ns" if p >= 0.05 else "SIG"
    print(f"{k:13} {obs:+8.3f} {p:8.4f} {p:8.4f}   {note}")