import json, os, shutil

cand = json.load(open(r"E:\deepseek\workspace\_recovery\user-file-candidates.json", encoding="utf-8"))
REF = r"E:\deepseek\reference_file"
try:
    import pymupdf
except Exception:
    import fitz as pymupdf

# 原件已知特征（勘察时记录）：610.0 KB、33 页、第 1 页文字层 1267 字符、含 "CH634"
TARGET_BYTES = 610.0 * 1024
print("=== 严格匹配：大小 ~610.0 KB 且 33 页 且 文字层含 CH634 ===")
matches = []
for it in cand["pdfs"]:
    if abs(it["size"] - TARGET_BYTES) > 2048:
        continue
    try:
        d = pymupdf.open(it["path"])
        pages = d.page_count
        t1 = d[0].get_text()
        d.close()
        if pages == 33 and "CH634" in t1:
            matches.append((it["path"], it["size"], pages, len(t1.strip())))
            print("  [匹配] %-52s %7.1f KB  %d 页  第1页 %d 字符" % (it["path"], it["size"] / 1024, pages, len(t1.strip())))
    except Exception as exc:
        print("  [跳过] %s (%s)" % (it["path"], str(exc)[:50]))

if matches:
    # 优先选第 1 页字符数最接近 1267 的
    best = sorted(matches, key=lambda x: abs(x[3] - 1267))[0]
    dest = os.path.join(REF, "CH634DS1.PDF")
    shutil.copy2(best[0], dest)
    print()
    print("  [OK] 已恢复: %s" % best[0])
    print("       -> %s" % dest)
    print("       %d 页 / %d 字节 / 第1页 %d 字符（原件记录：33 页 / 610.0 KB / 1267 字符）" % (
        best[2], best[1], best[3]))
    # 完整性验证：随机读几页
    d = pymupdf.open(dest)
    print("       验证各页文字层:")
    for pg in (0, 4, 20, 32):
        if pg < d.page_count:
            print("         第 %2d 页: %5d 字符" % (pg + 1, len(d[pg].get_text().strip())))
    d.close()
else:
    print("  未找到严格匹配的候选")

print()
print("=== 另外发现的候选（供用户判断，不擅自放入 reference_file）===")
for it in cand["pdfs"]:
    if abs(it["size"] - TARGET_BYTES) > 4096:
        continue
    try:
        d = pymupdf.open(it["path"])
        pages, t1 = d.page_count, d[0].get_text()[:60].replace("\n", " ")
        d.close()
        print("  %-52s %7.1f KB  %d 页  首行: %s" % (os.path.basename(it["path"]), it["size"] / 1024, pages, t1))
    except Exception:
        pass

print()
print("=== reference_file 最终状态 ===")
for f in sorted(os.listdir(REF)):
    print("  %-46s %9.1f KB" % (f, os.path.getsize(os.path.join(REF, f)) / 1024))