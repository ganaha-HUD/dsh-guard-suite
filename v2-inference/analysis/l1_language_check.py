import json, os, re, sys
import numpy as np
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"E:\Deepseek_kolp\data\conv-20261026-f342510a"
K = 10
CN = re.compile(r"[\u4e00-\u9fff]")
EN_WORD = re.compile(r"[A-Za-z]{3,}")

def grams(s, n=3):
    return set(s[i:i+n] for i in range(len(s) - n + 1)) if len(s) >= n else set()

def jac(a, b):
    if not a or not b: return 0.0
    return len(a & b) / len(a | b)

def l1(turns):
    G = [grams(s) for _, s in turns]
    vals = []
    for i in range(1, len(G)):
        m = 0.0
        for j in range(max(0, i - K), i):
            m = max(m, jac(G[i], G[j]))
        vals.append(m)
    return float(np.mean(vals)) if vals else 0.0

def load(path):
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    turns = {}
    for r in rows:
        turns.setdefault(int(r.get("turn", 0)), []).append(r.get("reasoning") or "")
    return [(t, "\n".join(v)) for t, v in sorted(turns.items())]

print(f"{'model':9}{'cell':8}{'L1_all':>8}{'L1_cn':>8}{'cn_turns':>9}{'all_turns':>10}")
for name, (root, tag) in [("DeepSeek", (os.path.join(BASE, "api2"), "formal")),
                          ("MiMo", (os.path.join(BASE, "mimo"), "mf"))]:
    for cell in ["A-shun", "A-ni", "B-shun", "B-ni"]:
        d = os.path.join(root, cell)
        alls, cns = [], []
        for f in sorted(os.listdir(d)):
            if not (f.startswith(tag + "-s") and f.endswith(".jsonl")): continue
            turns = [(t, s) for t, s in load(os.path.join(d, f)) if s.strip()]
            alls.append(l1(turns))
            strict = [(t, s) for t, s in turns if CN.search(s) and not EN_WORD.search(s)]
            cns.append(l1(strict) if len(strict) > 1 else float("nan"))
        print(f"{name:9}{cell:8}{np.nanmean(alls):8.3f}{np.nanmean(cns):8.3f}"
              f"{np.mean([x for x in cns if x == x]):9.3f}{np.mean(alls):10.3f}")