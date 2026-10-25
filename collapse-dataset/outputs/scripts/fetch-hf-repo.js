sion_detect, anomaly_score, image_generate

image_generate(prompt="a small brass gear …", steps=6, seed=7)
  → [LCM text-to-image GPU, 512x512, 6 steps, guidance=1.5, 6.6s]  image: D:\AI_file\outputs\image-a-small-brass-gear-….png
image_generate(prompt="defect texture on brushed aluminium …", 384x384, steps=4, seed=11)
  → [LCM text-to-image GPU, 384x384, 4 steps, guidance=1.5, 5.7s]  image: D:\AI_file\outputs\image-defect-texture-….png
```

## 6. 换更强模型（一条环境变量）

```
DSH_T2I_MODEL = D:\AI_file\models\<新模型目录>
```
下载对应 OpenVINO 仓库后改这一处即可（MCP 服务端会重新加载）：
- **SDXL base int8**（3.27 GB，openrail++）：`OpenVINO/stable-diffusion-xl-base-1.0-int8-ov`，原生 1024²
- **FLUX.1-schnell int4**（8.61 GB，**Apache-2.0**）：许可最干净、质量最好，4 步采样，但在核显上预计每张 1–3 分钟

## 7. 能力边界（诚实记录）

- LCM/SD1.5 的**原生分辨率是 512²**；再往上画质不会真提升（要 1024² 请换 SDXL）。
- **画面内文字基本不可用**（SD 系列的已知弱点）；需要文字请后期叠加。
- 6 步 + guidance 1.5 是速度/质量折中；想要更好看可把 `steps` 提到 8、`guidance` 提到 2.0（时间线性增加）。
- **合成内容必须标注**：生成图不得当作真实照片或真实测量证据（已写进策略的信任分级）。

## 8. 工具集全景（8 个，全部本地、无网络、无费用）

| 工具 | 引擎 | 设备 | 实测 |
|---|---|---|---|
| `vision_read_document` | 文字层 → PP-OCR → VLM | CPU/NPU | 瞬时 / 1.3–4.1 s/页 |
| `vision_ocr` | PP-OCRv6（OpenVINO） | CPU | 0.6–4.1 s |
| `vision_describe` | Qwen2.5-VL-3B INT4 | NPU | 11–18 s |
| `vision_ask` | Qwen2.5-VL-3B INT4 | NPU | 11–18 s |
| `vision_status` | — | — | 瞬时 |
| `vision_detect` | YOLOX-Tiny（IR） | NPU | **7 ms**（热态） |
| `anomaly_score` | PatchCore（IR） | NPU | 41–97 ms |
| `image_generate` | LCM Dreamshaper v7 | iGPU | **5.7–6.6 s** |

## 9. 文件与登记

| 项 | 路径 |
|---|---|
| 生图模型 | `D:\AI_file\models\lcm-dreamshaper-v7-fp16-ov\`（1.99 GB，26 文件） |
| 服务端 | `D:\AI_file\mcp\vision-server.py`（**v1.7.0，8 工具**） |
| 生成图输出 | `D:\AI_file\outputs\image-<prompt-slug>-<yyyyMMdd-HHmmss-mmm>.png` |
| 下载脚本 | `E:\Deepseek\scripts\conv-20260928-3b54e160\fetch-hf-repo.js`（可复用：仓库级、跳过冗余权重、断点续跑） |
| 登记 | `D:\AI_file\registry.json`（4 环境 / **5 模型** / 1 数据集 / 1 工具） |
| 策略 | `policy\ai-tool-policy.md` v1.4.0、`policy\ai-tools.json` v1.4.0（**预留清单已清空**） |

## 10. 参数速查

```
image_generate(prompt, negative_prompt="", width=512, height=512,
               steps=6, guidance=1.5, seed=-1, device="GPU")
  steps    : 4（最快）～8（更好看）
  guidance : 1.0～2.0（LCM 低引导即可）
  seed     : -1 随机；固定值可复现同一张图
```