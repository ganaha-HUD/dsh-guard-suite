import json, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"E:\Deepseek_kolp\data\conv-20261026-f342510a\api2"
DET = r"E:\Deepseek_kolp\workspace\conv-20261026-f342510a\det-full"
recs = json.load(open(os.path.join(ROOT, "analysis-records.json"), encoding="utf-8"))

FIELDS = [("L1", ("structure","L1_literal","inter_turn","mean")),
          ("L2", ("structure","L2_skeleton","mean")),
          ("calls", ("structure","L3_behavior","calls")),
          ("entropy", ("structure","L3_behavior","tool_entropy")),
          ("longest", ("structure","L3_behavior","longest_same_tool")),
          ("zero_ratio", ("structure","L3_behavior","zero_tool_ratio"))]

def dig(o, path):
    for k in path:
        if not isinstance(o, dict) or k not in o: return None
        o = o[k]
    return o

worst = {k: (0, None) for k, _ in FIELDS}
rows_out = []
for r in recs:
    cell, s = r["cell"], r["s"]
    f = os.path.join(DET, cell, f"formal-{s}.summary.json")
    if not os.path.exists(f):
        print("MISSING", cell, s); continue
    d = json.load(open(f, encoding="utf-8"))
    line = {"cell": cell, "s": s}
    for name, path in FIELDS:
        v = dig(d, path)
        line[name] = v
        mine = r.get("longest" if name == "longest" else name)
        if v is not None and mine is not None:
            diff = abs(float(mine) - float(v))
            if diff > worst[name][0]: worst[name] = (diff, f"{cell}/{s} mine={mine} det={v}")
    rows_out.append(line)

print(f"{'cell':8}{'s':5}{'L1_det':>8}{'L2_det':>8}{'calls':>7}{'entropy':>9}{'longest':>8}{'zero':>7}")
for x in rows_out:
    print(f"{x['cell']:8}{x['s']:5}{x['L1']:8.3f}{x['L2']:8.3f}{x['calls']:7d}{x['entropy']:9.3f}{x['longest']:8d}{x['zero_ratio']:7.3f}")

print("\n=== max abs diff (mine vs detector) ===")
for k, (dv, where) in worst.items():
    print(f"{k:10} max_diff={dv:.4f}  {where or ''}")