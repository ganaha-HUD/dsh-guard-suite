import json

SRC = r"E:\deepseek\workspace\_recovery\ai-tools.json.recovered-v1.8.0"
DST = r"E:\deepseek\policy\ai-tools.json"

orig = json.load(open(SRC, encoding="utf-8"))
print("=== 原件顶层键 ===")
print("  " + ", ".join(orig.keys()))
print()
print("=== 原件里与备选模型相关的键 ===")
for k in orig:
    if "alt" in k.lower() or "model" in k.lower():
        print("  " + k + " -> " + json.dumps(orig[k], ensure_ascii=False)[:200])
print()
print("=== 原件 reservedToolsNaming.planned ===")
print("  " + json.dumps(orig.get("reservedToolsNaming", {}).get("planned"), ensure_ascii=False))
print()
print("=== 原件 tools[0] 的字段 ===")
print("  " + json.dumps(orig["tools"][0], ensure_ascii=False, indent=2)[:400])

# ---- 以原件为基底，叠加 v1.9.0 的六处变更 ----
orig["policyVersion"] = "1.9.0"
orig["updatedAt"] = "2026-10-05"
orig["server"]["version"] = "1.11.0"
orig["tools"][0]["limits"] = orig["tools"][0]["limits"] + "; password-protected PDFs are refused with a clear message"
orig["tools"][4]["useFor"] = "engine, device, budget, and per-model [present]/[MISSING] health check"
orig["hardLimits"]["encryptedPdf"] = ("not supported: a PDF with a user password cannot be read; owner-password-only "
                                      "files that open with an empty password are fine. The tool returns "
                                      "'READ FAILED [RuntimeError]: password-protected PDF ...'")
orig.setdefault("maintenance", {})["returnErrorsAsText"] = (
    "tools return failure messages as normal text (READ FAILED / GENERATION FAILED) because the MCP layer hides "
    "exception text from callers; every failure is also written to vision-mcp.log")

# 重建标注 + 保留重建时补充的 alternatives（原件无此字段，属 v1.9.0 之后新增的调研结论）
orig["rebuiltAt"] = "2026-10-11"
orig["rebuiltNote"] = ("重建版：原文件随 E: 盘清空丢失。本文件以恢复出的原件（v1.8.0，2026-10-04）为基底，"
                       "叠加 2026-10-05 的 v1.9.0 变更（加密 PDF 硬限制、失败返回文本约定、服务端 1.11.0、"
                       "health check 说明），并补入 alternatives（备选生图模型调研结论）。")
orig["alternatives"] = {
    "imageGeneration": [
        {"model": "FLUX.1-schnell int4", "size": "8.61 GB", "license": "Apache-2.0",
         "note": "current default, 1024x1024 in 4 steps, 13-18 s warm"},
        {"model": "FLUX.1-schnell int8", "size": "15.73 GB", "license": "Apache-2.0", "note": "not downloaded"},
        {"model": "SDXL base int8", "size": "3.27 GB", "license": "openrail++",
         "note": "native 1024, about 3.5 B params, 20-25 steps"},
        {"model": "LCM Dreamshaper v7", "size": "2.04 GB", "license": "MIT",
         "note": "deleted on 2026-10-05 by user decision (style adherence was weak)"},
        {"model": "Z-Image-Turbo", "size": "30.64 GB official / 5.39 GB third-party int4 OV", "license": "Apache-2.0",
         "note": ("6B; text encoder is Qwen3-4B (strong Chinese, 40960 context); 8 NFEs. Blocked here: "
                  "openvino_genai 2026.4.1 has no z_image factory and no official OV conversion exists, so it "
                  "needs a separate venv plus the optimum-intel@zimage fork")}
    ]
}

open(DST, "w", encoding="utf-8", newline="\r\n").write(json.dumps(orig, ensure_ascii=False, indent=2) + "\n")
print()
print("=== 已写回 policy\\ai-tools.json（原件基底 + v1.9.0 叠加） ===")
chk = json.load(open(DST, encoding="utf-8"))
print("  版本=%s  顶层键数=%d  工具=%d  路由=%d  planned=%d" % (
    chk["policyVersion"], len(chk), len(chk["tools"]), len(chk["routing"]),
    len(chk["reservedToolsNaming"].get("planned") or [])))
print("  routing 顺序（采用原件）：")
for i, r in enumerate(chk["routing"]):
    print("    [%2d] %s" % (i, r[:88]))