import json, os, shutil

cand = json.load(open(r"E:\deepseek\workspace\_recovery\user-file-candidates.json", encoding="utf-8"))
REF = r"E:\deepseek\reference_file"
os.makedirs(REF, exist_ok=True)

print("=== 1) PNG：按原始字节数 6723.2 KB 精确匹配 ===")
TARGET_PNG = 6723.2 * 1024
best = None
for it in cand["pngs"]:
    diff = abs(it["size"] - TARGET_PNG)
    if best is None or diff < best[0]:
        best = (diff, it)
if best and best[0] < 4096:
    it = best[1]
    dest = os.path.join(REF, "720421F869216DB8CE295D95710712E5.png")
    shutil.copy2(it["path"], dest)
    print("  [OK] 字节差 %d -> 恢复 %s (%d 字节)" % (best[0], it["path"], it["size"]))
    try:
        from PIL import Image
        im = Image.open(dest)
        print("  验证: %s  %s  %s" % (im.format, im.size, im.mode))
    except Exception as exc:
        print("  [WARN] 图像校验失败: %s" % exc)
else:
    print("  未找到字节数匹配的 PNG（最接近差 %s）" % (best[0] if best else "n/a"))

print()
print("=== 2) PDF：在 160 个候选中按 ~610 KB + 内容验证找 CH634DS1 ===")
try:
    import pymupdf
except Exception:
    import fitz as pymupdf

hits = []
for it in cand["pdfs"]:
    if not (400 * 1024 < it["size"] < 800 * 1024):
        continue
    try:
        d = pymupdf.open(it["path"])
        pages = d.page_count
        text = ""
        for i in range(min(3, pages)):
            text += d[i].get_text()
        d.close()
        if "CH634" in text:
            hits.append((it["path"], it["size"], pages, len(text)))
    except Exception:
        continue

print("  按大小筛出并验证通过的候选: %d 个" % len(hits))
for p, s, pages, tl in hits[:6]:
    print("    %-52s %7.1f KB  %d 页  前3页文字 %d 字符" % (os.path.basename(p), s / 1024, pages, tl))

if hits:
    p, s, pages, _ = sorted(hits, key=lambda x: -x[2])[0]
    dest = os.path.join(REF, "CH634DS1.PDF")
    shutil.copy2(p, dest)
    print("  [OK] 恢复 %s -> %s (%d 页, %d 字节)" % (p, dest, pages, s))
else:
    print("  [未找到] 大小区间内没有含 CH634 的 PDF；下面扩大范围再试")
    for it in cand["pdfs"]:
        if not (200 * 1024 < it["size"] < 3 * 1024 * 1024):
            continue
        try:
            d = pymupdf.open(it["path"])
            text = "".join(d[i].get_text() for i in range(min(2, d.page_count)))
            pages = d.page_count
            d.close()
            if "CH634" in text:
                dest = os.path.join(REF, "CH634DS1.PDF")
                shutil.copy2(it["path"], dest)
                print("    [OK] %s (%d 页, %.1f KB)" % (it["path"], pages, it["size"] / 1024))
                break
        except Exception:
            continue

print()
print("=== reference_file 现状 ===")
for f in sorted(os.listdir(REF)):
    print("  %-46s %9.1f KB" % (f, os.path.getsize(os.path.join(REF, f)) / 1024))