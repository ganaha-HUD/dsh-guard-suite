import json

orig = json.load(open(r"E:\deepseek\workspace\_recovery\ai-tools.json.recovered-v1.8.0", encoding="utf-8"))
mine = json.load(open(r"E:\deepseek\policy\ai-tools.json", encoding="utf-8"))

def paths(o, pre=""):
    out = {}
    if isinstance(o, dict):
        for k, v in o.items():
            p = pre + "/" + k
            out[p] = type(v).__name__
            if isinstance(v, (dict, list)):
                out.update(paths(v, p))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            p = pre + "[%d]" % i
            out[p] = type(v).__name__
            if isinstance(v, (dict, list)):
                out.update(paths(v, p))
    return out

po, pm = paths(orig), paths(mine)
only_orig = sorted(set(po) - set(pm))
only_mine = sorted(set(pm) - set(po))

print("=== 原件独有（我重建时遗漏或改名的字段）共 %d 个 ===" % len(only_orig))
for p in only_orig:
    print("  " + p)
print()
print("=== 重建版独有（v1.9.0 新增或我改名的字段）共 %d 个 ===" % len(only_mine))
for p in only_mine:
    print("  " + p)
print()

def val(o, p):
    cur = o
    for tok in p.strip("/").split("/"):
        if "[" in tok:
            name, idx = tok[:-1].split("[")
            cur = cur[name][int(idx)]
        else:
            cur = cur[tok]
    return cur

# 值不同的标量字段（只看共同存在的）
diff = []
for p in sorted(set(po) & set(pm)):
    try:
        a, b = val(orig, p), val(mine, p)
    except Exception:
        continue
    if isinstance(a, (dict, list)) or isinstance(b, (dict, list)):
        continue
    if a != b:
        diff.append((p, a, b))
print("=== 共同字段中值不同的（原件 -> 重建版）共 %d 个 ===" % len(diff))
for p, a, b in diff[:40]:
    sa, sb = str(a), str(b)
    if len(sa) > 68: sa = sa[:65] + "..."
    if len(sb) > 68: sb = sb[:65] + "..."
    print("  %-52s | %s -> %s" % (p, sa, sb))