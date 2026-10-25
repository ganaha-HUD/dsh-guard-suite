import json
P = r"E:\deepseek\policy\conversation-registry.json"
reg = json.load(open(P, encoding="utf-8"))
before = len(reg["conversations"])
reg["conversations"] = [c for c in reg["conversations"] if c["folder"] != "conv-20261011-3b54e160"]
json.dump(reg, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("  登记表 %d -> %d 条（移除误建的 ID）" % (before, len(reg["conversations"])))
act = [c for c in reg["conversations"] if c.get("status") == "active"]
print("  active 条目:", ", ".join(c["folder"] for c in act))