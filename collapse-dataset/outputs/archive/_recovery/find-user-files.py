"""在恢复数据里找用户的两个文件：CH634DS1.PDF（33 页规格书）与 720421...png（6.9 MB 照片）"""
import os
import struct

ROOT = r"C:\huifu"
pdfs, pngs = [], []
n = 0
for dirpath, _dirs, files in os.walk(ROOT):
    for name in files:
        p = os.path.join(dirpath, name)
        try:
            size = os.path.getsize(p)
        except Exception:
            continue
        n += 1
        try:
            with open(p, "rb") as fh:
                head = fh.read(8)
            if head[:5] == b"%PDF-":
                pdfs.append((p, size))
            elif head[:8] == b"\x89PNG\r\n\x1a\n" and 5_000_000 < size < 9_000_000:
                pngs.append((p, size))
        except Exception:
            continue

print("遍历文件数: %d" % n)
print()
print("=== 可能的 PDF（按 %PDF- 文件头，共 %d 个） ===" % len(pdfs))
for p, s in sorted(pdfs, key=lambda x: -x[1])[:12]:
    print("  %-58s %9.1f KB" % (p, s / 1024))
print()
print("=== 5–9 MB 的 PNG（共 %d 个，候选照片） ===" % len(pngs))
for p, s in sorted(pngs, key=lambda x: -x[1])[:12]:
    print("  %-58s %9.1f KB" % (p, s / 1024))

import json
json.dump({"pdfs": pdfs, "pngs": pngs}, open(r"E:\deepseek\workspace\_recovery\user-file-candidates.json", "w"), indent=2)
print()
print("候选清单已存: E:\\deepseek\\workspace\\_recovery\\user-file-candidates.json")