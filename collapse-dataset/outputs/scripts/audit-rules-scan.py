import json
import os
import re

HOME = os.path.expanduser("~")
FILES = [
    (r"E:\Deepseek\AGENTS.md", "工作区规则（注入到本工作区所有对话）"),
    (r"E:\Deepseek\policy\output-storage-policy.md", "存放准则全文"),
    (r"E:\Deepseek\policy\storage-policy.json", "存放准则（机器可读）"),
    (r"E:\Deepseek\policy\ai-tool-policy.md", "AI 工具规则全文"),
    (r"E:\Deepseek\policy\ai-tools.json", "AI 工具规则（机器可读）"),
    (r"E:\Deepseek\policy\deploy\global-agents.md", "全局规则源"),
    (os.path.join(HOME, ".dsh", "AGENTS.md"), "全局规则（已部署副本）"),
    (r"E:\Deepseek\policy\conversation-registry.json", "对话登记"),
    (r"E:\Deepseek\README.md", "工作区索引"),
    (r"D:\AI_file\registry.json", "AI 资产登记"),
]

print("=== 1) 规则载体清单 ===")
print("  %-46s %8s  %-19s %s" % ("文件", "大小", "修改时间", "版本（从内容提取）"))
for path, label in FILES:
    if not os.path.isfile(path):
        print("  %-46s 缺失!" % os.path.basename(path))
        continue
    txt = open(path, encoding="utf-8", errors="replace").read()
    size = os.path.getsize(path)
    mtime = __import__("datetime").datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
    ver = ""
    for pat in (r'"policyVersion":\s*"([\d.]+)"', r'- 版本：([\d.]+)', r'"version"\s*:\s*"([\d.]+)"', r'v(\d+\.\d+)\b'):
        m = re.search(pat, txt)
        if m:
            ver = m.group(1)
            break
    print("  %-46s %7dB  %-19s %s   %s" % (os.path.basename(path), size, mtime, ver, label))

print()
print("=== 2) 陈旧信息扫描（应为 0 的关键词） ===")
STALE = {
    "LCM": "LCM 模型（应只在删除记录里出现）",
    "6.6 s": "旧 LCM 耗时",
    "512²": "旧分辨率",
    "1.07 B": "旧参数量",
    "14.0 GB": "旧总体积",
    "latent_consistency": "旧工厂名",
    "MIT": "旧许可（现为 Apache-2.0，注意别误报 MIT 的其他含义）",
}
for path, label in FILES:
    if not os.path.isfile(path):
        continue
    txt = open(path, encoding="utf-8", errors="replace").read()
    hits = []
    for kw, why in STALE.items():
        for m in re.finditer(re.escape(kw), txt):
            line = txt[:m.start()].count("\n") + 1
            seg = txt[max(0, m.start() - 40):m.start() + 60].replace("\n", " ")
            hits.append("      行%-5d [%s] …%s…" % (line, kw, seg.strip()))
    if hits:
        print("  %s:" % os.path.basename(path))
        for h in hits[:6]:
            print(h)
        if len(hits) > 6:
            print("      …共 %d 处" % len(hits))

print()
print("=== 3) JSON 有效性 + 关键字段 ===")
for path, keys in ((r"E:\Deepseek\policy\storage-policy.json", ("policyVersion", "rootAllowList")),
                   (r"E:\Deepseek\policy\ai-tools.json", ("policyVersion", "tools", "routing", "imageGenerationBudget", "maintenance")),
                   (r"D:\AI_file\registry.json", ("models", "datasets", "tools"))):
    try:
        o = json.load(open(path, encoding="utf-8"))
        present = [k for k in keys if k in o]
        missing = [k for k in keys if k not in o]
        counts = {k: (len(o[k]) if isinstance(o[k], (list, dict)) else o[k]) for k in present}
        print("  %-30s 解析 OK  字段%s  缺: %s" % (os.path.basename(path), counts, missing or "无"))
    except Exception as exc:
        print("  %-30s 解析失败: %s" % (os.path.basename(path), exc))