import os, shutil

root = r"E:\deepseek"
conv = "conv-20260928-3b54e160"

# 按首行签名恢复（身份明确者）
MAP = [
    (r"C:\huifu\recup_dir.2\f0137728.py",   "scripts", "render-pdf-pages.py"),
    (r"C:\huifu\recup_dir.1\f21506048.py",  "scripts", "verify-pdf-text-layer-vs-ocr.py"),
    (r"C:\huifu\recup_dir.1\f21515520.py",  "scripts", "verify-vision-v14.py"),
    (r"C:\huifu\recup_dir.1\f21512448.py",  "scripts", "verify-vision-v13.py"),
    (r"C:\huifu\recup_dir.1\f21507840.txt", "logs",    "20261004-160000-npu-input-limit-and-spec-reading.log"),
    (r"C:\huifu\recup_dir.1\f21556480.txt", "logs",    "20261004-210000-toolset-guide-docx-and-longevity.log"),
    (r"C:\huifu\recup_dir.1\f21543176.txt", "logs",    "20261004-213000-anomaly-score-verification.log"),
    (r"C:\huifu\recup_dir.2\f24409088.py",  "scripts", "sync-rules-everywhere.py"),
]
restored = []
for src, kind, name in MAP:
    if not os.path.isfile(src):
        continue
    dest = os.path.join(root, kind, conv, name)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if not os.path.exists(dest):
        shutil.copy2(src, dest)
        restored.append((kind, name, os.path.getsize(dest)))
print("=== 追加恢复的原件 ===")
for kind, name, size in restored:
    print("  %-8s %-52s %6.1f KB" % (kind, name, size / 1024))
print()
print("总计追加 %d 个文件" % len(restored))