# 2x2 analysis of the 32-session formal experiment.
import json, math, os, sys
import numpy as np
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"E:\Deepseek_kolp\data\conv-20261026-f342510a\api2"
CELLS = ["A-shun", "A-ni", "B-shun", "B-ni"]
K = 10

def grams(s, n=3):
    return set(s[i:i+n] for i in range(len(s)-n+1)) if len(s) >= n else set()

def jac(a, b):
    if not a or not b: return 0.0
    return len(a & b) / len(a | b)

FUNC = set("的了着过是在有和与或但而因为所以如果就才还再又也很都只把被让给对我你他它这那些个不没未无已能会可应须将要该当从到于其此即")

def load(cell, snn):
    p = os.path.join(ROOT, cell, f"formal-{snn}.jsonl")
    rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    # aggregate reasoning per user turn (a turn may span several steps)
    turns = {}
    tools = []
    for r in rows:
        t = int(r.get("turn", 0))
        turns.setdefault(t, []).append(r.get("reasoning") or "")
        for name in (r.get("raw", {}) or {}).get("tools", []) or []:
            tools.append(name)
    seq = [(t, "\n".join(v)) for t, v in sorted(turns.items())]
    return rows, seq, tools

def inter_series(seqs, key):
    G = [key(s) for _, s in seqs]
    vals = []
    for i in range(1, len(G)):
        m = 0.0
        for j in range(max(0, i-K), i):
            m = max(m, jac(G[i], G[j]))
        vals.append(m)
    return vals

def skel(s):
    return grams("".join(ch for ch in s if ch in FUNC), 2)

def entropy(counts):
    tot = sum(counts.values())
    if tot == 0: return 0.0
    h = 0.0
    for v in counts.values():
        p = v / tot
        h -= p * math.log2(p)
    return h

def longest_run(seq):
    best = cur = 0; prev = None
    for x in seq:
        if x == prev: cur += 1
        else: cur = 1; prev = x
        best = max(best, cur)
    return best

def safe_div(a, b): return a / b if b else 0.0

records = []
for cell in CELLS:
    for n in range(1, 9):
        snn = f"s{n:02d}"
        try:
            rows, seqs, tools = load(cell, snn)
        except FileNotFoundError:
            print("missing", cell, snn); continue
        # drop turns whose reasoning is empty for L1/L2 (report coverage separately)
        nonempty = [(t, s) for t, s in seqs if s.strip()]
        cov = len(nonempty) / max(1, len(seqs))
        L1 = np.mean(inter_series(nonempty, lambda s: grams(s, 3))) if len(nonempty) > 1 else 0.0
        L2 = np.mean(inter_series(nonempty, skel)) if len(nonempty) > 1 else 0.0
        cnt = {}
        for t in tools: cnt[t] = cnt.get(t, 0) + 1
        zero = sum(1 for r in rows if int(r.get("tool_calls", 0)) == 0)
        records.append({
            "cell": cell, "s": snn,
            "persona": cell.startswith("A"), "adverse": cell.endswith("ni"),
            "rows": len(rows), "turns": len(seqs), "calls": len(tools),
            "entropy": entropy(cnt), "longest": longest_run(tools),
            "longest_ratio": safe_div(longest_run(tools), len(tools)),
            "zero_ratio": zero / max(1, len(rows)),
            "L1": L1, "L2": L2, "coverage": cov,
        })

print(f"records={len(records)}")
metrics = ["L1", "L2", "entropy", "longest_ratio", "zero_ratio", "calls", "coverage"]
print("\n=== per-cell mean +/- sd (n=8) ===")
hdr = "cell      n  " + "  ".join(f"{m:>14}" for m in metrics)
print(hdr)
groups = {}
for cell in CELLS:
    rs = [r for r in records if r["cell"] == cell]
    groups[cell] = rs
    vals = "  ".join(f"{np.mean([r[m] for r in rs]):7.3f}±{np.std([r[m] for r in rs], ddof=1):5.3f}" for m in metrics)
    print(f"{cell:9} {len(rs):2}  {vals}")

def two_way(metric):
    # cells ordered: A-shun, A-ni, B-shun, B-ni  -> persona x adversity
    y = {(p, a): [r[metric] for r in records if r["persona"] == p and r["adverse"] == a]
         for p in (1, 0) for a in (1, 0)}
    n = min(len(v) for v in y.values())
    if n < 2: return None
    Y = {k: np.array(v[:n], dtype=float) for k, v in y.items()}
    allv = np.concatenate(list(Y.values()))
    gm = allv.mean()
    ss_tot = ((allv - gm) ** 2).sum()
    # cell means and MARGINAL means (the earlier version used cell means by mistake)
    cm = {k: v.mean() for k, v in Y.items()}
    m_A1 = (cm[(1, 1)] + cm[(1, 0)]) / 2
    m_A0 = (cm[(0, 1)] + cm[(0, 0)]) / 2
    m_B1 = (cm[(1, 1)] + cm[(0, 1)]) / 2
    m_B0 = (cm[(1, 0)] + cm[(0, 0)]) / 2
    ss_A = 2 * n * ((m_A1 - gm) ** 2 + (m_A0 - gm) ** 2)
    ss_B = 2 * n * ((m_B1 - gm) ** 2 + (m_B0 - gm) ** 2)
    ss_AB = n * sum((cm[(p, a)] - (m_A1 if p else m_A0) - (m_B1 if a else m_B0) + gm) ** 2
                    for p in (1, 0) for a in (1, 0))
    ss_E = max(0.0, ss_tot - ss_A - ss_B - ss_AB)
    dfE = 4 * (n - 1)
    msE = ss_E / dfE if dfE else float("nan")
    out = {}
    for name, ss, df in (("persona", ss_A, 1), ("adverse", ss_B, 1), ("interaction", ss_AB, 1)):
        F = (ss / df) / msE if msE and msE > 0 else float("nan")
        p = stats.f.sf(F, df, dfE) if np.isfinite(F) else float("nan")
        out[name] = (F, p, ss / ss_tot if ss_tot else float("nan"))
    return out

print("\n=== two-way ANOVA (persona x adversity), eta^2 ===")
print(f"{'metric':14} {'effect':12} {'F':>8} {'p':>8} {'eta2':>7}")
for m in metrics:
    r = two_way(m)
    if not r: continue
    for eff, (F, p, e2) in r.items():
        print(f"{m:14} {eff:12} {F:8.2f} {p:8.3f} {e2:7.3f}")

json.dump(records, open(os.path.join(ROOT, "analysis-records.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\nwritten analysis-records.json")