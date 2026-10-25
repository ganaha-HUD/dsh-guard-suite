"""1) Extract the PDF text layer (ground truth). 2) Retry page 2 three times to test flakiness."""
import os
import time

import numpy as np
import openvino as ov
import openvino_genai
import pymupdf
from PIL import Image

PDF = r"E:\Deepseek\reference_file\CH634DS1.PDF"
MODEL = r"D:\AI_file\models\qwen2.5-vl-3b-ov-int4-npu"
CACHE = r"E:\Deepseek\workspace\conv-20260928-3b54e160\ov-cache2"
PAGE2 = r"E:\Deepseek\workspace\conv-20260928-3b54e160\pdf-pages\page02.png"
TXT = r"E:\Deepseek\workspace\conv-20260928-3b54e160\spec-text-layer-p1-6.txt"
OUT = r"E:\Deepseek\workspace\conv-20260928-3b54e160\page2-retry-test.txt"

doc = pymupdf.open(PDF)
print("=== 1) PDF text layer, pages 1-6 (ground truth) ===")
chunks = []
for n in range(1, 7):
    page = doc[n - 1]
    text = page.get_text().strip()
    chunks.append("========== page %d (%d chars) ==========\n%s" % (n, len(text), text))
    print("page %d: %d chars" % (n, len(text)))
with open(TXT, "w", encoding="utf-8") as fh:
    fh.write("\n\n".join(chunks))
print("written: " + TXT)
print()

print("=== 2) page 2 read 3 times (is the empty output flaky?) ===")
img = Image.open(PAGE2).convert("RGB")
budget = 980
tokens = img.size[0] * img.size[1] // 784
if tokens > budget:
    scale = (budget / float(tokens)) ** 0.5 * 0.98
    img = img.resize((int(img.size[0] * scale), int(img.size[1] * scale)))
tokens = img.size[0] * img.size[1] // 784
arr = np.asarray(img, dtype=np.uint8).reshape(1, img.size[1], img.size[0], 3)
tensor = ov.Tensor(arr)
pipe = openvino_genai.VLMPipeline(MODEL, "NPU", CACHE_DIR=CACHE)
results = []
for i in range(1, 4):
    t0 = time.perf_counter()
    res = pipe.generate("Read all the text in this image exactly as written.", image=tensor, max_new_tokens=420)
    gen = time.perf_counter() - t0
    text = (res.texts[0] if getattr(res, "texts", None) else str(res)).strip()
    print("attempt %d: %.1fs chars=%d  %s" % (i, gen, len(text), text[:120].replace("\n", " | ") if text else "(EMPTY)"))
    results.append("attempt %d: %.1fs chars=%d\n%s" % (i, gen, len(text), text or "(EMPTY)"))
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("page 2 at %dx%d (%d tokens)\n\n" % (img.size[0], img.size[1], tokens) + "\n\n".join(results))
print("written: " + OUT)