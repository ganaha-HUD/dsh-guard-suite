# Qwen3-TTS 在 Intel NPU 上的可行性实验报告

**结论：这条路走不通，但不是因为"没设上界"。** 上界设对了，是 NPU 编译器自身崩溃。

日期：2026-10-23。机器：Core Ultra 5 338H / Arc B370 iGPU / OpenVINO 2026.4.1。

---

## 1. 起因与假设

用户指出：NPU 报 `Missing upper bound for one or more nodes` 是因为导出时某些维度留成了**无界动态形状**
（如 `SequenceLength = INT64_MAX`）。从 Lunar Lake 起 NPU 支持**有界**动态形状，条件是每个动态维度
都必须显式指定上界，例如 `ov::Dimension(1, 512)`。

**这个判断在原理上完全正确。** 下面的实验就是验证它。

---

## 2. 第一次确认：原 IR 确实全是无界

用 `openvino.Core().read_model()` 逐个扫描发布包里的 IR：

```
text_embedding       input_ids      [1, 0..UNBOUNDED]
codec_embedding      input_ids      [1, 0..UNBOUNDED]
speech_decoder_*     audio_codes    [1, 0..UNBOUNDED, 16]
speech_encoder       input_values   [1, 0..UNBOUNDED]
speaker_encoder      mels           [1, 0..UNBOUNDED, 128]
talker               inputs_embeds  [0..UNBOUNDED, 1, 2048]
                     position_ids   [3, 0..UNBOUNDED, 1]
                     attention_mask [0..UNBOUNDED, 1, 1, 0..UNBOUNDED]
                     beam_idx       [0..UNBOUNDED]
```

**全部 24 个维度都是 `0..UNBOUNDED`**，一个上界都没有。假设成立。

---

## 3. 尝试一：事后修改现有 IR（失败）

想在已发布 IR 上直接 `reshape` + `save_model`，结果两处卡死：

1. `save_model` 报 `Can't open bin file`（read 后句柄未释放）
2. `talker` 的 reshape 报 `TRShape::merge_into(output_shape, in_copy)` failed
   —— OpenVINO 的 shape 推断内部冲突，`position_ids[3,seq,1]` / `attention_mask[b,1,1,seq]` /
   `inputs_embeds[b,1,2048]` 三者一起定界时算不出自洽的静态形状

**结论：事后改 IR 不可行，必须在导出阶段控制。**

---

## 4. 尝试二：改导出器源码，从源头给出上界（成功）

导出器的 `exporter.py` 里 8 处 `PartialShape` 用 `-1`，改成 `ov.Dimension(lo, hi)`：

| 原始 | 改后 |
|---|---|
| `[-1, 1, hidden]` | `[Dimension(1,4), 1, hidden]` |
| `[3, -1, 1]` | `[3, Dimension(1,384), 1]` |
| `[-1, 1, 1, -1]` | `[Dimension(1,4), 1, 1, Dimension(1,384)]` |
| `[1, kv_heads, -1, head_dim]` | `[1, kv_heads, Dimension(0,384), head_dim]` |

上界取自 manifest 自己的声明：`max_cache_len = 384`、`cache_buckets` 最大 384、chunk 24。

补丁脚本：`D:\AI_file\tools\patch-exporter-bounds.py`（43 处）+ `patch-exporter-bounds2.py`（5 处）。
备份：`exporter.py.unbounded.bak`。

**导出结果验证**：

```
talker_stateful_batch_sdpa_paged_gqa_seed.xml
  in  inputs_embeds    [1..4, 1, 2048]        ← 成功上界
  in  position_ids     [3, 1..384, 1]
  in  attention_mask   [1..4, 1, 1, 1..384]
  in  beam_idx         [1..4]
  => unbounded dims: 0
```
31 个图里只剩 3 个无界，全在备用图 `speech_decoder_t256.xml`。

---

## 5. 尝试三：CPU 验证（成功）

同一份有界 IR，`--device CPU` **完整启动并编译成功**：

```
compiled no-cache config={'CACHE_MODE': 'OPTIMIZE_SPEED'} core graphs on CPU in 1.5s
compiled streaming decoder context 0 chunk 8 pool=1 on CPU in 1.1s
compiled streaming decoder context 25 chunk 24 pool=1 on CPU in 1.1s
```

**证明 IR 本身没问题，上界补丁是对的。**

---

## 6. 尝试四：NPU（失败，且找到了真正的原因）

### 6.1 服务静默崩溃

`--device NPU --model-root <new IR>` 启动后：
```
INFO: Started server process
INFO: Waiting for application startup.
OpenVINO available devices: ['CPU', 'GPU', 'NPU']
→ 进程直接消失，无 traceback
```

### 6.2 绕开服务直接编译

用 `core.compile_model(model, "NPU")` 逐个试。**连最简单的 `text_embedding`（形状 `[1, 1..384]`）都让进程硬崩**：

```
read ok, inputs: 1
  in input_ids  [1,1..384]
→ exit -1073741676   (0xC0000094 = INTEGER_DIVIDE_BY_ZERO)
```

### 6.3 最小模型对照实验（决定性）

用 `opset13` 手搭 `y = x + 1`，只改输入形状：

| 形状 | GPU | NPU |
|---|---|---|
| 完全静态 `[1, 4]` | ✅ OK | ✅ **OK** |
| 有界动态 `[1, 1..4]` | ❌ FAIL | ❌ **崩溃** |
| 有界动态 `[1, 1..384]` | — | ❌ **崩溃** |

NPU 崩溃时的完整信息：

```
[ERROR] [vpux-compiler] Got non broadcastable dimensions pair :
        '-9223372036854775808' and 4'
LLVM ERROR: Failed to infer result type(s):
  "IE.Add"(...) {} : (tensor<1x?xf32, {bounds = #const.OpaqueI64Elements<[1, 4]>...}>,
                      tensor<1x4xf32>) -> ( ??? )
exit -1073740791   (0xC0000409 = STACK_BUFFER_OVERRUN / LLVM 崩溃)
```

**关键点**：编译器**已经读到 `bounds = [1, 4]`**（错误信息里明确写着），
但它内部把上界算成了 `-9223372036854775808`（INT64_MIN），随后 LLVM 类型推断失败并崩溃。

**所以：上界设对了，是 NPU 编译器（vpux-compiler）处理有界动态维度时有 bug。**

---

## 7. 最终结论

| 问题 | 答案 |
|---|---|
| 原 IR 是否无界？ | 是，24 个维度全 `0..UNBOUNDED` |
| 加上界能否让 IR 更规范？ | **能，且已做到**（31 图中 28 个完全有界） |
| 有界 IR 在 CPU 能否跑？ | **能，完整启动** |
| 有界 IR 在 GPU 能否跑？ | 最小模型测试中 GPU 对有界形状也失败；TTS 用原 IR 的 GPU 路径正常 |
| 有界 IR 在 NPU 能否跑？ | **不能。NPU 编译器对任何有界动态维度都会崩（INT64_MIN + LLVM 崩溃）** |
| 是否值得继续投入？ | **不值得**，需要 Intel 修 vpux-compiler，不是应用层能解决的 |

**根本障碍**：NPU 只接受**完全静态**的形状；TTS 的序列长度天然可变（文本长度、音频长度都不固定），
两者不兼容。这就是为什么作者只在 README 里写 `--device GPU`，并且提供了
`--npu-offload`（把部分子图卸载到 NPU）而不是 `--device NPU` 全量运行。

---

## 8. 本次产出的可复用资产

| 路径 | 内容 |
|---|---|
| `D:\AI_file\build\qwen3-tts\qwen3-tts-openvino\` | 导出器源码（含已打补丁的 `exporter.py`） |
| `D:\AI_file\build\qwen3-tts\Qwen3-TTS-main\` | 官方 PyTorch 包（zip 下载，非 git） |
| `D:\AI_file\build\qwen3-tts\models\Qwen3-TTS-12Hz-1.7B-VoiceDesign\` | 1.7B 原始权重，4310.8 MB |
| `D:\AI_file\build\qwen3-tts\openvino\voice_design\` | **有界 IR**，58 文件 / 32.6 GB，含 int8 量化版 |
| `D:\AI_file\envs\tts-export\` | 隔离 venv（transformers 4.57.3 / torch 2.14.1 / nncf 3.4.0） |
| `D:\AI_file\build\qwen3-tts\stubs\sox.py` | sox stub（仅 25Hz 路径用，12Hz 不需要真 sox） |
| `D:\AI_file\tools\patch-exporter-bounds.py` | 有界形状补丁（43 处） |
| `D:\AI_file\tools\check-bounded-ir.py` | 检查 IR 是否还有无界维度 |
| `D:\AI_file\tools\test-npu-dynamic.py` | 静态/有界/无界 × GPU/NPU 对照实验 |

**注意**：构建产物占 **32.6 GB**（D 盘余 259 GB）。如果不再需要，可以删除
`D:\AI_file\build\qwen3-tts\openvino\` 和 `models\`，保留脚本即可重跑。

---

## 9. 对现有可用方案的最终建议

**GPU 是唯一可用设备**，实测数据：

| 模式 | 首次 | 后续 |
|---|---|---|
| voice_design | 13.83 s | 1.75–3.61 s |
| voice_clone | 41.70 s | — |

对"让 AI 说话"这个用途**完全够用**。NPU 的收益（省电、释放 iGPU）不足以抵消
"Intel 修完编译器之前完全不可用"这个事实。

**如果将来要再试**，只有一条路：等 OpenVINO 新版本的 NPU 插件修好有界动态形状支持，
然后用现成的有界 IR 直接 `--device NPU`。**IR 已经准备好了**，不需要重新导出。
