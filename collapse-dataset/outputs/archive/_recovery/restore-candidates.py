import json, os, shutil

root = r"E:\deepseek"
conv = "conv-20260928-3b54e160"
cand = json.load(open(os.path.join(root, r"workspace\_recovery\huifu-hits-round2.json"), encoding="utf-8"))["results"]

def identify(path):
    try:
        raw = open(path, "rb").read(300 * 1024)
    except Exception:
        return None, ""
    head = raw[:1200].decode("utf-8", errors="ignore")
    text = raw.decode("utf-8", errors="ignore")
    first = next((l.strip() for l in text.splitlines() if l.strip()), "")
    if "dsh-vision MCP server" in text and "def " in text:
        return "server", first[:70]
    if first.startswith("MCP TEXT-TO-IMAGE OUTAGE") or "MCP TEXT-TO-IMAGE OUTAGE" in head:
        return "log", first[:70]
    if "train-patchcore" in text or "PatchCore" in head and "import" in head:
        return "script-py", first[:70]
    if "fetch-hf-repo" in text or (head.startswith("const ") and "https" in head):
        return "script-js", first[:70]
    if first.startswith("#"):
        return "doc", first[:70]
    return "other", first[:70]

plan = []
for label, items in cand.items():
    for it in sorted(items, key=lambda x: -x["size"])[:4]:
        kind, first = identify(it["path"])
        plan.append((label, kind, it["path"], it["size"], first))

print("=== 候选识别结果 ===")
for label, kind, path, size, first in plan:
    print("  [%-9s] %-46s %7.1f KB  %s" % (kind, os.path.basename(path), size / 1024, first[:60]))

# 按身份复制到正确位置（只复制可判定的脚本/日志）
os.makedirs(os.path.join(root, "scripts", conv), exist_ok=True)
os.makedirs(os.path.join(root, "logs", conv), exist_ok=True)
os.makedirs(os.path.join(root, "workspace", "_recovery", "raw"), exist_ok=True)
restored = []
for label, kind, path, size, first in plan:
    name = None
    dest_dir = None
    if kind == "log" and "OUTAGE" in first.upper() or "MCP TEXT-TO-IMAGE" in first:
        name = "20261005-075116-t2i-outage-fixed.log"; dest_dir = "logs"
    elif kind == "script-py" and "PatchCore" in first or "patchcore" in os.path.basename(path).lower():
        name = "train-patchcore.py"; dest_dir = "scripts"
    elif kind == "script-js":
        name = "fetch-hf-repo.js"; dest_dir = "scripts"
    elif kind == "server":
        name = "vision-server.py.recovered-fragment"; dest_dir = "workspace/_recovery/raw"
    if name and dest_dir:
        dest = os.path.join(root, dest_dir, conv if dest_dir in ("scripts", "logs") else "", name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if not os.path.exists(dest):
            shutil.copy2(path, dest)
            restored.append(dest)
print()
print("=== 已恢复 ===")
for r in restored:
    print("  " + r)
if not restored:
    print("  （无新增：候选未通过身份判定或已存在）")