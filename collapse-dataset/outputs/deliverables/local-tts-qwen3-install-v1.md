# Qwen3-TTS OpenVINO 本地部署记录

**状态：可用。** `voice_design` 与 `voice_clone` 两个模式均能出合法 WAV。
日期：2026-10-23。设备：Intel Arc B370 iGPU（**NPU 不可用，实测见第 6 节**）。

---

## 1. 为什么选 A-2 而不是 A-1

| 路线 | 内容 | 实测结论 |
|---|---|---|
| **A-1** 官方 notebooks | 克隆 `openvinotoolkit/openvino_notebooks`，跑 `notebooks/qwen3-tts` | **放弃**。helper `qwen_3_tts_helper.py` 有 **2947 行**，且**完全不用** `openvino_genai.Text2SpeechPipeline`，而是自己用 torch 重写 `OVQwen3TTSTalkerForConditionalGeneration` + `OVQwen3TTSSpeechTokenizer` + `OVQwen3TTSModel`，硬依赖 torch / transformers / optimum。代价远超预期 |
| **A-2** 预编译包 ★ | `qwen3-tts-ov-server-windows-x64-0.1.4-runtime-minimal.zip`（104.5 MB） | **采用**。PyInstaller 打包，自带定制 `qwen3_tts_ov_genai.dll`，附 HTTP 边车服务 + 网页控制台 |
| A-3 optimum-cli | `optimum-cli export openvino` | 未尝试 |

**安全审查（A-2）**：仓库 0 star / 0 fork，但 Apache-2.0；exe 与 DLL 均未签名（PyInstaller 常态）；
静态扫描 **零** `.bat/.cmd/.ps1/.vbs/.reg/.scr`，只有 PyInstaller 标准布局，无异常自启动项。

---

## 2. 组件与路径

```
D:\AI_file\tools\qwen3-tts-ov\            296.5 MB / 1353 文件
  qwen3-tts-ov-server.exe                 10.3 MB   ← 主程序
  native\build\qwen3_tts_ov_genai.dll     646 KB    ← 定制 OpenVINO TTS 实现
  _internal\                              Python 3.12 + numpy + huggingface_hub + openvino

模型权重（自动下载到用户缓存）
  %LOCALAPPDATA%\qwen3-tts-openvino\models\
    waston10086--qwen3-tts-openvino-voice-design--main\openvino_realtime\
      voice_design\   18 文件 / 2987.3 MB   ← voice_design 模式
      base\           24 文件 / 3251.3 MB   ← voice_clone 模式
      custom_voice\   （未下载，需要时再拉）

参考音色
  D:\AI_file\datasets\dafeiyu-voice\ref-dwg-0031.wav   385324 B
  D:\AI_file\datasets\dafeiyu-voice\metadata.csv       58 行

输出
  D:\AI_file\outputs\tts-first.wav     165164 B  1ch 24000Hz 16bit  3.44s
  D:\AI_file\outputs\tts-clone.wav     280364 B  1ch 24000Hz 16bit  5.84s
```

---

## 3. 启动

```powershell
$exe = 'D:\AI_file\tools\qwen3-tts-ov\qwen3-tts-ov-server.exe'
Start-Process -FilePath $exe -ArgumentList '--device','GPU' `
  -WorkingDirectory (Split-Path $exe) -WindowStyle Hidden
# 端口起来即可用：http://127.0.0.1:17860/
```

**必须用 `--device GPU`**。设备可选 `GPU` / `CPU` / `NPU`，但 NPU 会编译失败（见第 6 节）。

常用参数：`--model-root <dir>` 指定离线 IR 目录；`--no-auto-download-model` 禁止联网下载。

---

## 4. API

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/health` | 状态与 warmup 详情（含 errors） |
| GET | `/v1/models` | 三个模式可用性 + 下载状态 |
| POST | `/v1/models/download` | 按 mode 触发下载，body `{"mode":"voice_design"}` |
| GET | `/v1/audio/voices` | 音色列表（voice_design 下为空） |
| POST | `/v1/tts` | **主接口**，文本转语音 |
| POST | `/v1/tts/stream` | 流式 |
| POST | `/v1/tts/tokenize` | 分词预览 |
| POST | `/v1/audio/speech` | OpenAI 兼容封装 |
| GET | `/` `/web` | 网页控制台 |

**参数名以网页控制台源码为准**（`JSON.stringify({ mode, text, instruct, speaker, refText, language, ... })`），
`refAudio` 是前端控件名，**API 实际用 `ref_audio`（下划线）**——这是踩过的坑。

### voice_design（按指令设计音色）

```bash
curl -X POST http://127.0.0.1:17860/v1/tts \
  -H "Content-Type: application/json" \
  -d '{"mode":"voice_design","text":"你好，我是DSH，蓝色大肥鱼。","instruct":"少女音，软一点，活泼。","language":"chinese"}' \
  --output out.wav
```
实测：165164 B / **13.83 s**（首次），后续约 1.75 s。

### voice_clone（克隆参考音色）

```bash
curl -X POST http://127.0.0.1:17860/v1/tts \
  -H "Content-Type: application/json" \
  -d '{"mode":"voice_clone","text":"你好，我是DSH，蓝色大肥鱼。","ref_audio":"D:/AI_file/datasets/dafeiyu-voice/ref-dwg-0031.wav","ref_text":"这是一段参考音频。","language":"chinese"}' \
  --output clone.wav
```
实测：280364 B / **41.70 s**（首次，含音色编码）。

参数说明：
- `ref_audio`：参考音频**绝对路径**（也可用 `voice_clone_prompt`，服务端报错信息里给出的替代名）
- `ref_text`：参考音频对应的文本，**建议提供**，能提升对齐质量
- `language`：`chinese` / `english` 等

---

## 5. 关键修复：manifest 键名不匹配

**这是整件事最大的坑。** 发布包里的 `manifest.json` 与 exe 期望的键名不一致，直接跑会
`KeyError`，而且**换一个模式也一样**。修法是给 `graphs` 补别名：

| exe 查找的键 | manifest 实际有的键 | 处理 |
|---|---|---|
| `talker` | `paged_kv_seed.talker_stateful_batch_gqa` | 加 `graphs.talker` = 该 XML 文件名 |
| `subcode_greedy` | `subcode_greedy_cached` | 加 `graphs.subcode_greedy` = `graphs.subcode_greedy_cached` |

补丁脚本（幂等，可重复运行）：
```
D:\AI_file\tools\patch-manifest-talker.py    # 加 graphs.talker
D:\AI_file\tools\alias-graph-keys.py         # 补齐 subcode_greedy 等别名
```
两个脚本都会自动备份 `.bak2` / `.bak3`。

**排查过程记录**：`KeyError: 'talker'` → 加 `graphs.talker` → 变成 `KeyError: 'subcode_greedy'`
→ 加该别名 → 成功。exe 是**按固定顺序**逐个取键的，所以每补一个就往下走一步。

---

## 6. GPU 与 NPU 实测对照

**同一份权重、同一份（已修好的）manifest，只改 `--device`：**

| 设备 | 结果 | 耗时 |
|---|---|---|
| **GPU** | ✅ `HTTP 200`，合法 RIFF WAV | 13.83 s（首次） |
| **NPU** | ❌ `HTTP 400`，编译失败 | 0.21 s 即失败 |

NPU 的完整错误：

```
Compilation failed. vclAllocatedExecutableCreate2 result: 0x78000004
- [NPU_VCL] Compiler returned msg: Missing upper bound for one or more nodes.
```

**结论只写实测**：这版 exe + 这份 IR，走 NPU 会报 `Missing upper bound`（某个算子维度是动态的），
GPU 能正常编译运行。**不断言"该模型不支持 NPU"** —— 没有验证过其他版本或调过 NPU 编译参数。

> 注：最初资料声称"NPU 优先、首包延迟 0.369 s、NPU 成熟度最好"，**本地实测未能复现**。

---

## 7. 许可（双重限制，均为非商用）

| 对象 | 许可 | 限制 |
|---|---|---|
| Qwen3-TTS 模型权重 | Qwen Research License | **仅研究/评估，禁止商用** |
| 音色数据集 da-fei-yu-girl-voice-zh | **CC BY-NC 4.0** | **禁止商用**；转载或改编须**署名「尹紫鹭幻想社」（Bilibili）**、附许可链接并说明修改；商用须另行授权 |

**结论：整套 TTS 只能自用，不能商用。** 公开发布音频时需保留上述署名。

---

## 8. 已知限制

1. **NPU 不可用**（见第 6 节），只能用 GPU 或 CPU。
2. **`custom_voice` 模式未下载**，需要时执行 `python pull-ir-subdir.py openvino_realtime/custom_voice`。
3. **manifest 需手工打补丁**——重装或重新下载权重后**必须重跑两个补丁脚本**，否则又报 KeyError。
4. **首次调用较慢**（voice_design 13.83 s，voice_clone 41.70 s），之后明显加快（约 1.75 s）。
5. **`/health` 长期显示 `warmup.status = ready_with_errors`**，即使功能正常，不要被它误导。
6. 网页控制台的字段名（`refAudio`）与 API 字段名（`ref_audio`）**不一致**，以 API 报错提示为准。
7. 服务是**前台 exe**，无 Windows 服务注册，重启后需手动启动。

---

## 9. 下载工具链（可复用）

| 脚本 | 用途 |
|---|---|
| `D:\AI_file\tools\pull-ir-subdir.py <subdir>` | 分段下载任意 IR 子目录（8 MB/段，4 并发，断点续传） |
| `D:\AI_file\tools\pull-voice-design-segmented.py` | 同上，专用于 voice_design |
| `D:\AI_file\tools\pull-whole-file.cjs` | 单文件流式下载（某些 Range 被 CDN 截断时用） |
| `D:\AI_file\tools\repair-seg022-chunks.py` | 用 1 MB 小块修复单个损坏分段 |
| `D:\AI_file\tools\test-tts.cjs` / `test-tts-clone.cjs` | TTS 测试 |

### 踩过的下载坑

1. **HF 已迁到 Xet 存储**：`resolve` 会 302 跳 `us.aws.cdn.hf.co/xet-bridge-us/...`，该 CDN 对个别
   Range 请求会**固定在 1022087 字节截断**（重试、换镜像、改 1 MB 分块都一样）。修法：改成**整文件流式下载**。
2. **tree API 报的 size 可能小于真实 content-length**：`speech_decoder_stream_c25_t24.bin`
   tree 说 227944192，实际 **228056860**（差 112668 字节）。**分段时以 content-length 为准**。
3. **长连接会被掐**：单连接跑 1.35 GB，两次都**卡满 4 小时**才超时，只下了零头。
   改 8 MB 分段 + 4 并发后，同一线路速度从 ~4 KB/s 提到 2.5 MB/s。
4. **速度差异全在线路**：同一套脚本，08:11–12:23 只有 ~24 KB/s，12:35 后变成 2.5 MB/s，
   13:31 又掉到 17 KB/s，13:32 恢复 2.5 MB/s。**卡住时先测速，再判断是代码问题还是线路问题。**

---

## 10. 复现步骤（从零开始）

```powershell
# 1. 解压预编译包到 D:\AI_file\tools\qwen3-tts-ov\

# 2. 下载两个模式的 IR（各约 3 GB）
python D:\AI_file\tools\pull-ir-subdir.py openvino_realtime/voice_design
python D:\AI_file\tools\pull-ir-subdir.py openvino_realtime/base

# 3. 打 manifest 补丁（关键！）
python D:\AI_file\tools\patch-manifest-talker.py
python D:\AI_file\tools\alias-graph-keys.py

# 4. 启动（必须 GPU）
$exe = 'D:\AI_file\tools\qwen3-tts-ov\qwen3-tts-ov-server.exe'
Start-Process -FilePath $exe -ArgumentList '--device','GPU' -WorkingDirectory (Split-Path $exe) -WindowStyle Hidden

# 5. 测试
node D:\AI_file\tools\test-tts.cjs
node D:\AI_file\tools\test-tts-clone.cjs
```

---

## 11. 尚未完成

- **未封装成 MCP 工具**（`speak` / `tts_generate`）。这需要改 `D:\AI_file\mcp\vision-server.py`
  并重启服务端，等用户决定。
- `custom_voice` 模式未下载。
