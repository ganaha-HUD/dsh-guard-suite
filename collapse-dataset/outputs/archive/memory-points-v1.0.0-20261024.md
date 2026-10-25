# 经验记忆点（Memory Points）

- 版本：1.0.0 ｜ 生成：2026-10-22 ｜ 来源：`conv-20260928-3b54e160`（约 90 轮对话）
- 用途：跨对话复用的**实战结论**。只记踩过、验过、能省时间的东西；
  一次性过程与完整命令输出见 `logs\conv-20260928-3b54e160\`。

---

## 1. 一踩就坏的坑（全部真实踩过）

| 坑 | 症状 | 正确做法 |
|---|---|---|
| **中文引号进 `pwsh -Command`** | `“ ” 「 」` 被当成字符串边界，整块解析失败 | 含中文引号或全角标点的脚本**写成文件**（.ps1 带 BOM，或直接写 .py/.mjs）再执行。本次因此失败 4 次 |
| PowerShell 脚本无 BOM | 中文按 GB2312 解析 → 语法错乱、报错行号与内容不符、变量莫名 null | 脚本一律 **UTF-8 带 BOM**；数据文件（md/json）**不带** |
| `job_kill` 只杀 pwsh 包装进程 | node 子进程存活，与新下载器抢带宽（350 掉到 183 KB/s） | 用 `Get-CimInstance Win32_Process -Filter "Name='node.exe'"` 按命令行匹配后 `Stop-Process` |
| `(Get-Item).Length` 滞后 | 正被 node 追加写的文件读不到真实大小（日志说 17 MB，PowerShell 说 0） | 用 node 的 `fs.statSync`，或看程序自己写的日志 |
| `$Home` 是只读自动变量 | `Cannot overwrite variable Home` | 换名，如 `$DshHome` |
| `-like` 里的反引号 | 被当转义符，模式匹配永远失败 | 改用 `.Contains()` 或正则 |
| `read_image` 不认 `.avif` | 报 unsupported image format | 用 PIL 转 PNG 再读（Pillow 能读 AVIF） |
| 中文经 PowerShell 传给 Node/Python | 参数被破坏成 `?`，写进文件就是乱码 | 内容先写文件、让脚本自己读；或者整个脚本用 Python/Node 写（它们默认 UTF-8） |
| exFAT 卷不支持硬链接 | `write`/`edit` 报 `EISDIR` | 用 PowerShell `[System.IO.File]::WriteAllText` 直写，或把脚本放 D 盘（NTFS） |
| 沙箱 schannel 取不到 TLS 凭证 | `Invoke-WebRequest`/`curl` 全 SSL 失败 | 用 Node 下载（自带 OpenSSL，支持 302 与 Range 续传） |
| `Start-Job` 里 `$LASTEXITCODE` 恒空 | 误判成功/失败 | 在 job 内显式返回退出码，或改用脚本文件直跑 |

## 2. DSH 平台机制

- **desktop profile 由 Electron 独占**：`dsh plugin --profile desktop <任意子命令>` 一律被拒（连 `list` 也不行）。
  桌面版装/删/更新插件**只能**走「设置 → 插件」；市场页按钮对 desktop 必然 `exit=127`。
- **“已启用”的标志是 `dsh.profile.bundles` 里有它**，不是 `package.json` 的 `dependencies`。
- **加载顺序**：bundles（含各包自带 patch）→ profile 的 `cordis.patch.yml` → `--patch`。
  插件在 bundles 里、profile patch 里没有它，是**正常**的，不是没启用。
- **新增插件必须写 `- insert:`**；直接写 id-targeted 条目会被当“覆盖已存在项”而跳过。
- **有插件兼容性门禁**：peer 不满足会 `incompatible-version` 直接拒绝安装。
- **`^1.66.7` 这类范围会让“更新”失败**（pnpm 认为已满足）→ 升级要**卸载重装**或锁精确版本。
- **给 MCP 服务端加工具**：在 `vision-server.py` 加 `@server.tool` 函数 → 服务端重载后立刻可用（本次无需重启 DSH）。
- **MCP 层不转发异常文本**：`raise` 只会让调用方看到 “Error executing tool”；必须 `return` 文本说明原因。
- **长任务要配超时**：`toolCallTimeoutMs` 在 profile 的 `cordis.patch.yml`；1024² 生图 5–6 分钟要 600000 ms。

## 3. 本地模型栈（本机实测）

| 能力 | 方案 | 设备 | 实测 |
|---|---|---|---|
| 文生图（可商用） | FLUX.1-schnell int4 + OpenVINO | iGPU | **1024²/4 步 13–18 s**；Apache-2.0 |
| 文生图（无审查） | Qwen-Image 2.1 UC + stable-diffusion.cpp | iGPU Vulkan | **512²/20 步 85 s**；1024² 约 **5–6 分钟** |
| 视觉理解 | Qwen2.5-VL-3B int4 | NPU | 11–18 s |
| OCR | PP-OCRv6 | CPU（上游写死） | 0.6–4.1 s/页 |
| 目标检测 | YOLOX-Tiny | NPU | 7 ms 热态 |
| 异常检测 | PatchCore | NPU | 41–97 ms |

**关键参数与限制**

- Qwen-Image **步数 <20 出废图**（4 步实测是模糊噪点）；宽高须为 **32 的倍数**且 ≤1024；`--cfg-scale 6.0`。
- Qwen-Image **必须带 `--offload-to-cpu`**（9.3 GB 权重压不进共享显存，全放 RAM）。
- stable-diffusion.cpp **没有 server 模式** → 每次调用重载 9.3 GB（热缓存 ~4 s，冷缓存 ~1 min）。
- **Qwen-Image 权重是 Qwen Research License（禁商用）**；FLUX 是 Apache-2.0，两者**不可混在同一批对外产物**。
- `openvino_genai 2026.4.1` 已有 `QwenImageTransformer2DModel` + `Qwen3TextEncoder`，但**没有 `qwen_image` 工厂**；optimum-intel 也未支持 → 等上游。
- **Arc B370 iGPU 的 Vulkan 能力**：`uma:1 / fp16:1 / int dot:1 / KHR_coopmat`，**bf16 不支持**（量化模型不受影响）。
- **VLM 会幻觉标识符**：实测把型号 CH634 说成 “CH63034” → 型号/数字一律以 OCR 或文字层为准。

## 4. 下载与网络（实测）

- **`huggingface.co` 直连被墙**（`ECONNRESET`）；`hf-mirror.com` 约 **200–350 KB/s**。
- **挂梯子（TUN/全局）后直连 huggingface.co ≈ 1.4–1.9 MB/s**，单连接吃满，**不需要多线程**。
- **hf-mirror 对 8 个并发大 Range 请求会挂起**：返回 206 但零字节 → 多线程下载器在该镜像上无效。
- **GitHub release 直连也不通**；`gh-proxy.com` 与 `ghfast.top` 可用（`ghproxy.net` 卡死）。
- **ModelScope 快但不全**：只有官方版模型，无 uncensored 搬运。
- 断点续传脚本：`D:\AI_file\tools\download-qwen-image-models.mjs`。

## 5. 工作方法（比技术细节更值钱）

1. **先验证，再动手**：装插件前先跑作者自带的 `--check`；装模型前先用假参数测引擎能否识别格式。
   “路线 A（ComfyUI + torch-XPU）”就是被插件自检否决的，**省了 10 GB 和几小时**。
2. **大文件慢时先测直连原站**，别急着造多线程下载器（本次 20 分钟花在多连接上，瓶颈其实是链路）。
3. **单一权威源**：规则只在 `E:\deepseek\policy\`，其他工作区只引用不复制。
4. **索引式注入**：全局层每轮注入，长规则只在全局放“触发 + 铁律 + 指向”，细节按需读。
5. **改规则固定流程**：权威源 → 机器可读 JSON → 全局层 → 部署 → 自检 → **备份** → 写日志。
6. **改完必须验证**：源与部署副本**字节级比对**；备份后逐文件 SHA-256 比对，FAIL 必须处理。
7. **占位符要填**：`（待补充）` 留在规则里就是隐患。
8. **别把例外藏起来**：白名单每加一项就记一条理由（`rootAllowListNotes`）。

## 6. 本机速查

- 机器：Redmi 16 Pro 2026 ｜ **Core Ultra 5 338H** ｜ **Arc B370 iGPU（无独显）** ｜ **Intel NPU** ｜ 32 GB
- 屏幕：3200×2000 @200% 165 Hz
- 盘：**E: 可移动 exFAT**（无硬链接，工作区在此）；D: 程序与 AI 栈（`D:\AI_file`）；C: `~\.dsh`
- 已就绪：node 24.x、python 3.12/3.14、git
- 桌面版 DSH：`D:\Application\dsh`；**CLI 的 `dsh`（0.1.7）与桌面版（0.2.x）不通用**
- **LCEDA-Pro**：`D:\Application\lceda-pro` **4.1.78**，CLI 在 PATH；
  **调用前必须清 `ELECTRON_RUN_AS_NODE`**（本机 shell 默认就设着它）
- 本地 AI 栈根：`D:\AI_file`，登记在 `D:\AI_file\registry.json`

## 7. 明确不记的东西

- 一次性命令输出、逐条调试过程 → 全在 `logs\conv-20260928-3b54e160\`
- 已被后续版本取代的中间结论
- 与复用无关的单次任务细节
