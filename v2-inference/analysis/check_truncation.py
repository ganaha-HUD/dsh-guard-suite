# -*- coding: utf-8 -*-
"""Count user turns that ended at step 5 with a pending tool call."""
import json, os, sys, collections
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"E:\Deepseek_kolp\data\conv-20261026-f342510a"
tot_turns = tot_trunc = tot_rows = 0
by_cell = collections.Counter()
by_model = collections.Counter()
sess_with = set()
per_sess = []
for model, sub, tag in [("DeepSeek", "api2", "formal"), ("MiMo", "mimo", "mf")]:
    for cell in ["A-shun", "A-ni", "B-shun", "B-ni"]:
        d = os.path.join(BASE, sub, cell)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not (f.startswith(tag + "-s") and f.endswith(".jsonl")):
                continue
            rows = [json.loads(l) for l in open(os.path.join(d, f), encoding="utf-8") if l.strip()]
            tot_rows += len(rows)
            turns = collections.defaultdict(list)
            for r in rows:
                turns[int(r["turn"])].append(r)
            trunc = 0
            for t, rs in turns.items():
                rs.sort(key=lambda x: int(x.get("step", 0)))
                last = rs[-1]
                if int(last.get("step", 0)) >= 5 and int(last.get("tool_calls", 0)) > 0:
                    trunc += 1
                    by_cell[cell] += 1
                    by_model[model] += 1
                    sess_with.add((model, cell, f))
            tot_turns += len(turns)
            tot_trunc += trunc
            if trunc:
                per_sess.append((model, cell, f, trunc, len(turns)))
print("turn rows:", tot_rows, " user turns:", tot_turns)
print("truncated turns (step5 with pending tool call):", tot_trunc)
print("sessions affected:", len(sess_with))
print("by model:", dict(by_model))
print("by cell:", dict(by_cell))
print("top sessions:")
for x in sorted(per_sess, key=lambda y: -y[3])[:8]:
    print("  ", x)