import os

CANDIDATES = [
    r"C:\huifu\recup_dir.1\f0020224.txt",
    r"C:\huifu\recup_dir.1\f21546752.txt",
    r"C:\huifu\recup_dir.1\f21532160.txt",
    r"C:\huifu\recup_dir.1\f21532181.txt",
    r"C:\huifu\recup_dir.1\f21532429.txt",
    r"C:\huifu\recup_dir.2\f24408832.py",
]

for p in CANDIDATES:
    if not os.path.isfile(p):
        print("缺失: " + p)
        continue
    raw = open(p, "rb").read()
    size = len(raw)
    text = raw.decode("utf-8", errors="ignore")
    lines = [l for l in text.splitlines() if l.strip()]
    print("=" * 90)
    print("%s   %d 字节 / %d 非空行" % (os.path.basename(p), size, len(lines)))
    # 身份特征
    feats = []
    for kw, name in [('"policyVersion"', "JSON-policy"), ('"imageGenerationBudget"', "ai-tools.json 内容"),
                     ('"rootAllowList"', "storage-policy.json 内容"), ("# 工作区输出文件存放准则", "output-storage-policy.md 标题"),
                     ("# AI 工具调用规则", "ai-tool-policy.md 标题"), ("function Add-Finding", "Test-StoragePolicy.ps1 代码"),
                     ("# 全局对话输出文件存放准则", "global-agents.md 标题"),
                     ("param([string]$Root", "PowerShell 脚本"), ("import ", "Python 脚本"),
                     ("=== ", "命令输出/日志"), ("[OK]", "脚本输出"), ("| 工具 |", "markdown 表格")]:
        if kw in text:
            feats.append(name)
    print("  特征: " + (", ".join(feats) if feats else "（无匹配特征）"))
    print("  ---- 前 12 行 ----")
    for l in lines[:12]:
        print("    " + l[:150])
    print()