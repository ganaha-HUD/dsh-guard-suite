import json, os

ROOT = r"C:\huifu"
OUT = r"E:\deepseek\workspace\_recovery\huifu-hits-round2.json"

# 更精准的"原件指纹"
FINGERPRINTS = [
    ("# 工作区输出文件存放准则（E:\\Deepseek，强制）", "AGENTS.md 工作区全文"),
    ("# 全局对话输出文件存放准则（对所有工作区生效）", "global-agents.md 全文"),
    ("# AI 工具调用规则（AI Tool Calling Policy）", "ai-tool-policy.md 全文"),
    ("# 工作区输出文件存放准则（完整说明）", "output-storage-policy.md 全文"),
    ("function Add-Finding", "Test-StoragePolicy.ps1 全文"),
    ("function Read-Utf8Json", "我的 PowerShell 脚本"),
    ("New-ConversationWorkspace.ps1 - 幂等", "New-ConversationWorkspace.ps1 全文"),
    ("Install-GlobalPolicy.ps1 - 把", "Install-GlobalPolicy.ps1 全文"),
    ("dsh-vision MCP server", "vision-server.py 服务端"),
    ("local-ai-toolset-guide", "工具集指南 DOCX 或构建脚本"),
    ("MCP TEXT-TO-IMAGE OUTAGE", "生图故障复盘日志"),
    ("Z-Image 与本地生图模型", "Z-Image 对比报告"),
    ("PDF 读取能力", "PDF 能力报告"),
    ("规则审计报告", "规则审计报告"),
    ("storage-policy-audit", "存放准则审计"),
    ("train-patchcore", "PatchCore 训练脚本"),
    ("make-synthetic-defect-dataset", "合成缺陷数据集脚本"),
    ("fetch-hf-repo.js", "HF 仓库下载脚本"),
    ("switch-t2i-to-flux", "FLUX 切换脚本"),
    ("CH634DS1", "用户参考资料引用"),
]
TEXT_EXT = {".txt", ".md", ".json", ".ps1", ".py", ".yml", ".yaml", ".html", ".xml", ".csv", ".log", ".js", ".ts"}
results = {label: [] for _fp, label in FINGERPRINTS}
scanned = 0
for dirpath, _dirs, files in os.walk(ROOT):
    for name in files:
        if os.path.splitext(name)[1].lower() not in TEXT_EXT:
            continue
        p = os.path.join(dirpath, name)
        try:
            if os.path.getsize(p) > 8 * 1024 * 1024:
                continue
            raw = open(p, "rb").read(400 * 1024)
            scanned += 1
            text = raw.decode("utf-8", errors="ignore")
            for fp, label in FINGERPRINTS:
                if fp in text:
                    results[label].append({"path": p, "size": len(raw)})
        except Exception:
            continue

json.dump({"scanned": scanned, "results": results}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("扫描文本文件: %d" % scanned)
for label, got in results.items():
    if got:
        print("  %-34s %d 个" % (label, len(got)))
        for g in sorted(got, key=lambda x: -x["size"])[:3]:
            print("      %-56s %8.1f KB" % (g["path"], g["size"] / 1024))
print("完整结果: " + OUT)