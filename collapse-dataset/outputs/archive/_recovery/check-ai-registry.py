import json, os
R = r"D:\AI_file\registry.json"
reg = json.load(open(R, encoding="utf-8"))
print("  registry: 模型 %d / 数据集 %d / 工具 %d" % (len(reg.get("models", [])), len(reg.get("datasets", [])), len(reg.get("tools", []))))
for m in reg.get("models", []):
    p = m.get("path", "")
    ok = os.path.exists(p) if p else False
    print("    [%s] %-34s %s" % ("有" if ok else "缺", m.get("name"), (p[:60] if p else "")))
for t in reg.get("tools", []):
    print("    工具: %s v%s" % (t.get("name"), t.get("version")))