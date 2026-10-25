# 本地无审查生图安装记录 v1

> 日期：2026-10-21 01:04
> 目标：在这台机器（Intel Arc B370 核显，无独显）上获得**无内容审查**的本地文生图能力
> 结论：**已跑通**，首图验证通过

## 一、为什么不是最初给的那条路

用户最初收到的方案是 `dsh-qwen-paint` 插件 + ComfyUI + torch-XPU + IPEX。核实后放弃，原因有三：

1. **插件自检直接拒绝这硬件**：作者脚本 `node scripts/setup.mjs --check` 输出
   `Intel(R) Arc(TM) B370 GPU` → `判定：Intel 核显 → 基本跑不动，建议换台机器`；
   其 `INSTALL.md` 第 99 行支持表同样写着 `| Intel 核显 | 基本跑不动，建议换台机器 |`
2. **实际下载量是方案所述的三倍**：方案称"Q4_K_M 4.60 GB"，实测 Q4_K_M 为 4.29 GB，
   但**还必须**同时具备文本编码器（w4a8 5.88 GB 或 int8 8.71 GB）与 VAE 0.63 GB，合计约 10.8 GB
3. **方案漏了两个必需前提**：必须另装 ComfyUI-GGUF 节点；本机 torch 是 `2.14.1+cpu`，
   `torch.xpu.is_available()` 为 False，且未装 IPEX

OpenVINO 路线同样不可行：`openvino_genai 2026.4.1` 虽已含 `QwenImageTransformer2DModel` 与
`Qwen3TextEncoder` 类，但**没有 `qwen_image` 高层工厂**，`optimum-intel` 也尚未支持。

## 二、最终采用的方案

**stable-diffusion.cpp + Vulkan**。它在 2026-09-20 宣布 Day-0 支持 Qwen-Image 2.1，
原生读取 GGUF、直接驱动 iGPU 的 Vulkan 后端，**不需要 ComfyUI、不需要 torch-XPU、不需要 IPEX**。

| 组件 | 来源 | 大小 | 许可 |
|---|---|---|---|
| `sd-master-95b3090-bin-win-vulkan-x64.zip` | leejet/stable-diffusion.cpp releases（2026-10-18） | 28 MB | MIT |
| 扩散模型 `qwen-image-2.1-UC-Q4_K_M.gguf` | `abenzerps/Qwen-Image-2.1-Uncensored-Quantized` | 4.29 GB | other（见第六节） |
| 文本编码器 `qwen3vl_8b_heretic-Q4_K_M.gguf` | `pottokao/Qwen-Image-2.1-Text-Encoder-Heretic-GGUF` | 4.68 GB | 同上 |
| VAE `qwen_image_2.1_vae_bf16.safetensors` | `abenzerps/...` | 0.63 GB | 同上 |

**"Heretic" 是关键**：不只是扩散权重去了审查，**连 Qwen3-VL-8B 文本编码器也是无审查版**，
整条链路都不带内容过滤。合计下载 **9.6 GB**。

## 三、存放位置

```
D:\AI_file\tools\stable-diffusion-cpp\         sd-cli.exe + ggml-vulkan.dll + CPU 后端 DLL
D:\AI_file\models\qwen-image-2.1-uncensored\
    diffusion\qwen-image-2.1-UC-Q4_K_M.gguf
    text_encoder\qwen3vl_8b_heretic-Q4_K_M.gguf
    vae\qwen_image_2.1_vae_bf16.safetensors
D:\AI_file\tools\download-qwen-image-models.mjs  可断点续传的下载器（备用）
```

## 四、实测性能（本机，Intel Arc B370 核显）

| 配置 | 采样 | 文本编码 | VAE 解码 | 总耗时 |
|---|---|---|---|---|
| 512×512 / **4 步** | 21.0 s | 7.2 s | 16.7 s | **47 s**（画质不合格，见第五节） |
| 512×512 / **20 步** | 62.2 s | ~7 s | 16.1 s | **84 s**（画质良好） |

- 内存占用：**9.3 GB 全在 RAM**（`total params memory size = 9337.96MB, VRAM 0.00MB`），
  因为启用了 `--offload-to-cpu`；对 16.5 GB 共享显存的核显是正确选择
- 模型加载：约 4 s（Vulkan 读取 3.4–3.8 GB/s）
- 后端自调优：`flash attention → off`、`conv2d/conv3d → im2col`（自动探测后选的更快路径）
- 推算 1024×1024 / 20 步约为 **5–6 分钟/张**

## 五、使用方法

```powershell
cd D:\AI_file\tools\stable-diffusion-cpp

.\sd-cli.exe `
  --diffusion-model D:\AI_file\models\qwen-image-2.1-uncensored\diffusion\qwen-image-2.1-UC-Q4_K_M.gguf `
  --vae D:\AI_file\models\qwen-image-2.1-uncensored\vae\qwen_image_2.1_vae_bf16.safetensors `
  --llm D:\AI_file\models\qwen-image-2.1-uncensored\text_encoder\qwen3vl_8b_heretic-Q4_K_M.gguf `
  -p "your prompt" -W 1024 -H 1024 --steps 20 --cfg-scale 6.0 --sampling-method euler `
  --offload-to-cpu -o out.png
```

**参数要点**：

- **步数至少 20**：4 步会得到模糊噪点（已实测，见下方证据图）
- **宽高必须能被 32 整除**
- **`--cfg-scale 6.0`**（不同于 FLUX schnell 的 0.0）
- **必须带 `--offload-to-cpu`**：否则 9.3 GB 权重压不进共享显存
- 若要图像编辑（`-r` 参考图），还需额外下载 `mmproj-Qwen3VL-8B-Instruct-F16.gguf` 并用 `--llm_vision` 指定

## 六、许可与合规（重要）

- **stable-diffusion.cpp**：MIT
- **模型权重**：HuggingFace 仓库标注 `license: other`，`INSTALL.md` 明确写为
  **Qwen Research License —— 仅限研究 / 评估，禁止商用**
- 这与现有 FLUX.1-schnell int4（**Apache-2.0**，可商用）**有本质区别**
- 因此：**本套仅适合本地个人研究与评估**；若要用于发布或商业用途，请改用 FLUX（Apache-2.0）
- 模型为 Uncensored 变体，不含内容过滤；使用者需自行承担内容合规责任

## 七、已知限制

1. **慢**：512² / 20 步 84 秒；1024² 预计 5–6 分钟/张。FLUX int4 则是 13–18 秒/张
2. **无视觉权重**：日志 `no vision weights detected, vision disabled`，即文生图正常但**图像编辑不可用**
3. **未接入 DSH 工具链**：目前是命令行调用，尚未做成 MCP 工具。若要做，需仿照现有
   `vision-server.py` 增加一个 `image_generate_uncensored` 工具并重启服务端
4. **依赖 VPN**：下载走 huggingface.co 时需梯子（本机直连被 `ECONNRESET`，hf-mirror 仅约 200 KB/s）

## 八、验证证据

两张测试图存于 `E:\deepseek\archive\conv-20260928-3b54e160\qwen-image-verification\`：

- `qwen-uncensored-512-s4.png` —— 4 步，模糊噪点，证明步数下限确实存在
- `qwen-uncensored-512-s20.png` —— 20 步，"猫举木牌，牌上写 hello"，文字清晰、结构正常

## 九、下载过程中的两点经验

1. **`job_kill` 不杀 node 子进程**：杀掉 pwsh 包装进程后 node 仍在跑，会与新的下载器抢带宽。
   需要用 `Get-CimInstance Win32_Process -Filter "Name='node.exe'"` 按命令行匹配后 `Stop-Process`。
2. **PowerShell 读到的文件大小会滞后**：对正被 node 追加写的文件，`(Get-Item).Length` 可能长时间不更新，
   应改用 node 的 `fs.statSync` 或下载器自身的日志来判断进度。
## 十、工具化（2026-10-21 完成）

已注册为 MCP 工具 **`mcp__vision__image_generate_uncensored`**，**其他对话可直接调用**，无需命令行。

- 实现：并入现有 `vision-server.py`（v1.12.0），不新增服务端、不改配置
- 参数：`prompt`、`negative_prompt`、`width`/`height`（默认 512，须为 32 的倍数且 ≤1024）、`steps`（≥20）、`cfg_scale`（6.0）、`seed`、`timeout_seconds`
- 内置硬约束：步数 <20 直接拒绝；尺寸不合规直接拒绝
- 实测（经 MCP 端到端）：512²/20 步 = **84.0 秒**
- MCP 超时已从 300 s 提到 **600 s**（1024² 需 5–6 分钟）
- `vision_status` 已新增一行 `uncensored: … [present]`
- **默认仍走 FLUX**（快约 14 倍）；本工具仅在用户明确要求无审查或换模型时使用
- 司锁串行：同时只跑一个生成任务（GPU 与内存共享，并发只会互相拖慢）
