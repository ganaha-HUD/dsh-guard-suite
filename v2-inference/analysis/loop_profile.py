# Loop / repetition profile for both 32-session runs.
import json, os, re, sys
from collections import Counter
import numpy as np
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"E:\Deepseek_kolp\data\conv-20261026-f342510a"
K = 10
CN = re.compile(r"[\u4e00-\u9fff]")
EN3 = re.compile(r"[A-Za-z]{3,}")
FUNC = set("的了着过是在有和与或但而因为所以如果就才还再又也很都只把被让给对我你他它这那些个不没未无已能会可应须将要该当从到于其此即")

def grams(s, n=3):
    return set(s[i:i+n] for i in range(len(s) - n + 1)) if len(s) >= n else set()
def jac(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0
def skel(s):
    return grams("".join(c for c in s if c in FUNC), 2)
def run_length(flags, thr):
    best = cur = 0
    for v in flags:
        cur = cur + 1 if v >= thr else 0
        best = max(best, cur)
    return best
def series(vals):
    out = []
    for i in range(1, len(vals)):
        out.append(max(jac(vals[i], vals[j]) for j in range(max(0, i - K), i)))
    return out
def top_prefix_share(texts, n=12):
    c = Counter(t.strip()[:n] for t in texts if t.strip())
    return (c.most_common(1)[0][1] / max(1, sum(c.values()))) if c else 0.0

def load(path):
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    turns, tools = {}, []
    for r in rows:
        turns.setdefault(int(r.get("turn", 0)), []).append(r.get("reasoning") or "")
        tools += (r.get("raw") or {}).get("tools") or []
    seqs = [(t, "\n".join(v)) for t, v in sorted(turns.items())]
    return rows, seqs, tools

print(f"{'model':9}{'cell':8}{'L1m':>6}{'L1run':>7}{'L2m':>6}{'L2run':>7}{'pfx':>6}{'cjk':>6}{'mixed':>7}{'toolRun':>8}")
for model, (root, tag) in [("DeepSeek", (os.path.join(BASE, "api2"), "formal")),
                           ("MiMo", (os.path.join(BASE, "mimo"), "mf"))]:
    for cell in ["A-shun", "A-ni", "B-shun", "B-ni"]:
        d = os.path.join(root, cell)
        acc = {"L1": [], "L1run": [], "L2": [], "L2run": [], "pfx": [], "cjk": [], "mixed": [], "tRun": []}
        for f in sorted(os.listdir(d)):
            if not (f.startswith(tag + "-s") and f.endswith(".jsonl")): continue
            rows, seqs, tools = load(os.path.join(d, f))
            ne = [(t, s) for t, s in seqs if s.strip()]
            s1 = series([grams(s) for _, s in ne])
            s2 = series([skel(s) for _, s in ne])
            acc["L1"].append(np.mean(s1) if s1 else 0)
            acc["L1run"].append(run_length(s1, 0.6))
            acc["L2"].append(np.mean(s2) if s2 else 0)
            acc["L2run"].append(run_length(s2, 0.6))
            texts = [s for _, s in ne]
            acc["pfx"].append(top_prefix_share(texts))
            acc["cjk"].append(sum(1 for t in texts if CN.search(t)) / max(1, len(texts)))
            acc["mixed"].append(sum(1 for t in texts if CN.search(t) and EN3.search(t)) / max(1, len(texts)))
            best = cur = 0; prev = None
            for t in tools:
                cur = cur + 1 if t == prev else 1
                prev = t; best = max(best, cur)
            acc["tRun"].append(best / len(tools) if tools else 0)
        print(f"{model:9}{cell:8}{np.mean(acc['L1']):6.3f}{np.mean(acc['L1run']):7.1f}"
              f"{np.mean(acc['L2']):6.3f}{np.mean(acc['L2run']):7.1f}{np.mean(acc['pfx']):6.2f}"
              f"{np.mean(acc['cjk']):6.2f}{np.mean(acc['mixed']):7.2f}{np.mean(acc['tRun']):8.3f}")