"""Scan the recovery folder for my rule files by CONTENT (PhotoRec lost all filenames)."""
import os

ROOT = r"C:\huifu"
OUT = r"E:\deepseek\workspace\_recovery\huifu-hits.txt"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

SIGNATURES = [
    ("rootAllowList", "storage-policy.json"),
    ("imageGenerationBudget", "ai-tools.json"),
    ("output-storage-policy", "output-storage-policy.md"),
    ("ai-tool-policy", "ai-tool-policy.md"),
    ("Test-StoragePolicy", "Test-StoragePolicy.ps1"),
    ("Install-GlobalPolicy", "Install-GlobalPolicy.ps1"),
    ("New-ConversationWorkspace", "New-ConversationWorkspace.ps1"),
    ("conversation-registry", "conversation-registry.json"),
    ("全局对话输出文件存放准则", "global-agents.md"),
    ("工作区输出文件存放准则", "AGENTS.md 工作区"),
    ("本地 AI 工具（视觉 / 文档）", "规则 8"),
    ("AI 工具调用规则", "ai-tool-policy 标题"),
    ("vision_read_document", "AI 规则/服务端"),
    ("生图的时间预算", "ai-tool-policy 11"),
    ("硬件寿命", "ai-tool-policy 10"),
    ("模型变更后的运维规则", "ai-tool-policy 12"),
    ("思考语言", "中文思考规则"),
    ("local-ai-toolset-guide", "工具集指南"),
    ("CH634DS1", "参考资料"),
]
TEXT_EXT = {".txt", ".md", ".json", ".ps1", ".py", ".yml", ".yaml", ".html", ".xml", ".csv", ".log", ".js", ".ts"}

hits = {sig: [] for sig, _ in SIGNATURES}
scanned = 0
for dirpath, _dirs, files in os.walk(ROOT):
    for name in files:
        ext = os.path.splitext(name)[1].lower()
        if ext not in TEXT_EXT:
            continue
        path = os.path.join(dirpath, name)
        try:
            if os.path.getsize(path) > 4 * 1024 * 1024:
                continue
            with open(path, "rb") as fh:
                raw = fh.read(200 * 1024)
            scanned += 1
            text = raw.decode("utf-8", errors="ignore")
            for sig, _label in SIGNATURES:
                if sig in text:
                    hits[sig].append((path, len(raw)))
        except Exception:
            continue

lines = ["扫描目录: %s" % ROOT, "扫描文本文件数: %d" % scanned, ""]
for sig, label in SIGNATURES:
    got = hits[sig]
    lines.append("=" * 78)
    lines.append("%s   ->   %s   (命中 %d)" % (sig, label, len(got)))
    for p, size in got[:20]:
        lines.append("    %-56s %8.1f KB" % (p, size / 1024))
    if len(got) > 20:
        lines.append("    …另有 %d 个" % (len(got) - 20))
text = "\n".join(lines)
open(OUT, "w", encoding="utf-8").write(text)
print(text[:5000])
print("完整结果: " + OUT)