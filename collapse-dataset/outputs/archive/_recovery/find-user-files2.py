"""在恢复数据里定位用户的两个文件：CH634DS1.PDF（33 页）与 720421...png（照片）"""
import os, json

ROOT = r"C:\huifu"
OUT = r"E:\deepseek\workspace\_recovery\user-file-candidates.json"
pdfs, pngs, n = [], [], 0

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
        except Exception:
            continue
        if head[:5] == b"%PDF-":
            pdfs.append({"path": p, "size": size})
        elif head[:8] == b"\x89PNG\r\n\x1a\n" and 4_000_000 < size < 10_000_000:
            pngs.append({"path": p, "size": size})

json.dump({"scanned": n, "pdfs": pdfs, "pngs": pngs}, open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("遍历文件数: {}".format(n))
print()
print("=== 可能是 PDF 的文件（共 {} 个）===".format(len(pdfs)))
for it in sorted(pdfs, key=lambda x: -x["size"])[:15]:
    print("  {:58s} {:9.1f} KB".format(it["path"], it["size"] / 1024))
print()
print("=== 4-10 MB 的 PNG（共 {} 个，候选照片）===".format(len(pngs)))
for it in sorted(pngs, key=lambda x: -x["size"])[:15]:
    print("  {:58s} {:9.1f} KB".format(it["path"], it["size"] / 1024))
print()
print("候选清单: " + OUT)