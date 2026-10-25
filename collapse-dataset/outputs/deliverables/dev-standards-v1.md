# 本地 AI 工具开发规范 v1.0

> 适用对象：在本机（Windows 11 / Core Ultra 5 338H / Arc B370 / Intel AI Boost）上，
> 把本地 AI 能力（TTS、语音识别、视觉、生图）封装成可长期维护的软件。
>
> 这份规范来自 2026-10-22 ~ 10-24 三天的实战：三条 TTS 路线、四种下载通道、三个
> vpux 编译器 bug。凡是写着「实测」的结论都真跑过，不是背书。

---

## 一、项目结构

```
项目根/
├── AGENTS.md                  # 给 AI 的规则（可选）
├── README.md                  # 给人看的：怎么装、怎么跑、怎么验收
├── pyproject.toml             # 依赖与元数据（不要用 requirements.txt 散装）
├── src/<package>/             # 源码，包名小写、可用下划线
│   ├── __init__.py            # 只导出公共 API
│   ├── client.py              # 对外部服务的封装（HTTP/进程）
│   ├── models.py              # 数据类，不放业务逻辑
│   ├── config.py              # 配置集中处，全部来自环境变量
│   └── cli.py                 # 命令行入口，只做参数解析和调用
├── tests/                     # pytest；每个 client 至少一个冒烟测试
├── tools/                     # 一次性脚本、转换脚本（不进 package）
└── docs/                      # 架构说明、踩坑记录
```

**原则**：`src/` 里能 import 的代码不写死路径、不读全局状态、不在 import 时连接服务。

---

## 二、命名

| 对象 | 规则 | 例 |
|---|---|---|
| 包 / 模块 | 小写下划线 | `tts_client.py` |
| 类 | 大驼峰 | `TTSClient`, `Speech` |
| 函数 / 变量 | 小写下划线 | `synth_to_file`, `sample_rate` |
| 常量 | 全大写下划线 | `DEFAULT_TIMEOUT` |
| 内部函数 | 单下划线前缀 | `_fit`, `_request` |
| 私有成员 | 单下划线 | `self._want` |
| 环境变量 | `DSH_` 前缀 + 全大写 | `DSH_TTS_URL` |

**禁止**：中文文件名、空格、`最终版`/`最新版` 这类后缀。时间戳统一 `%Y%m%d-%H%M%S`。

---

## 三、错误处理（最容易写错的地方）

### 3.1 异常要分层，不要一个 `Exception` 走天下

```python
class TTSClientError(RuntimeError):      # 所有错误的基类
class TTSUnavailable(TTSClientError):    # 服务根本连不上
class TTSError(TTSClientError):          # 服务连上了但返回错误
```

调用方可以据此决定：`TTSUnavailable` → 提示用户启动服务；`TTSError` → 记录并重试或报错。

### 3.2 永远带上下文

```python
# 差
raise ValueError("invalid input")

# 好
raise ValueError("mode must be voice_design/voice_clone/custom_voice (got %r)" % mode)
```

**要写清楚：期望什么、实际是什么、从哪来。** 三天里我靠错误信息定位了十几个问题，
凡是只写 `"failed"` 的地方都得重跑一遍才能查。

### 3.3 外部进程随时可能死，所有调用必须有超时

```python
urllib.request.urlopen(req, timeout=timeout)     # 每层都要有
```

**实测教训**：没有超时的调用在 WebSocket 卡死时会挂住整个进程 4 小时。

### 3.4 MCP 工具不抛异常，返回可读文本

MCP 层会吞掉异常文本，用户只看到「工具失败」。所以：

```python
@server.tool(...)
def speak(...) -> str:
    try:
        ...
    except Exception as exc:
        log(...)                                  # 详情进日志
        return "SPEAK FAILED [%s]: %s%s" % (type(exc).__name__, exc, hint)   # 摘要给用户
```

**且必须给 hint**：告诉用户「下一步做什么」，不只是「失败了」。

---

## 四、配置管理

### 4.1 一切可变量走环境变量，带默认值

```python
BASE_URL = os.environ.get("DSH_TTS_URL", "http://127.0.0.1:17860")
TIMEOUT  = float(os.environ.get("DSH_TTS_TIMEOUT", "300"))
```

**理由**：本机换端口/换设备时不用改代码；容器化时天然可用。

### 4.2 路径不写死在业务逻辑里

路径常量放模块顶部，用 `os.path.join` 拼，**不要用字符串 `+`**。
注意本机用户名是中文（`徐丰哲`），**OpenVINO 的 C++ 层处理中文路径会失败**，
所以模型/IR 一律放纯 ASCII 路径（如 `D:\AI_file\...`）。

### 4.3 设备选择是配置，不是硬编码

```python
core.compile_model(model, device)      # device 来自参数/环境变量
```

本机实测能力：

| 设备 | 能跑什么 | 不能跑什么 |
|---|---|---|
| **GPU** (Arc B370) | Qwen3-TTS、OmniVoice、FLUX、Kokoro | — |
| **NPU** (AI Boost) | Kokoro（静态图，RTF 0.437）、YOLOX、PatchCore、VLM | **任何含无界动态维度的图** |
| **CPU** | 兜底，OmniVoice RTF 5.6 | 慢 |

---

## 五、对外部服务的封装（client 模式）

**每个外部依赖都写一个 client 类**，不要让业务代码直接调 HTTP：

```python
class TTSClient:
    def __init__(self, base_url=..., timeout=...): ...
    def is_up(self) -> bool: ...              # 健康检查，不抛异常
    def wait_until_ready(self, timeout) -> bool: ...
    def synth(self, text, **kw) -> Speech: ...     # 返回结构化对象
    def synth_to_file(self, text, path, **kw) -> Speech: ...
```

**四个必须有的方法**：`is_up`、`wait_until_ready`、主功能、`to_file` 便捷封装。

**返回值用 dataclass，不用裸 dict**：

```python
@dataclass
class Speech:
    audio: bytes
    sample_rate: int
    channels: int
    duration: float
    mode: str
    elapsed: float
    text: str
```

这样调用方写 `s.duration` 而不是 `s["duration"]`，拼错立刻报错。

---

## 六、服务生命周期

本地 AI 服务都是**常驻外部进程**，必须显式管理：

```python
# 启动（幂等）
subprocess.Popen([exe, "--device", "GPU"], cwd=..., creationflags=CREATE_NO_WINDOW)

# 等待就绪（有超时，不能死等）
client.wait_until_ready(timeout=120)

# 健康检查（调用前先确认）
if not client.is_up():
    return "服务未启动，请先运行 ..."
```

**三条铁律**：
1. **启动要幂等** —— 已运行就直接用，不要起第二个实例（否则两个进程抢同一端口/显存）
2. **就绪要轮询** —— 端口通了不代表模型加载完了，还要看 `/health` 的 `warmup.status`
3. **退出要清理** —— 程序退出时 terminate 子进程，否则残留进程占内存

**实测坑**：debug 时反复 `Start-Process` 没杀旧的，导致两个下载任务抢带宽（350 → 183 KB/s）。

---

## 七、音频处理约定

| 项 | 约定 |
|---|---|
| 采样率 | **24000 Hz**（Qwen3-TTS 与 Kokoro 都是） |
| 声道 | **单声道** |
| 位深 | **16 bit PCM** |
| 容器 | **WAV（RIFF）**，`wave` 模块可读 |
| 校验 | 每次生成后检查：`len(bytes) > 1000` 且前 4 字节 == `b"RIFF"` 且 `duration` 在 0.5~30 s |

**不要相信"返回了 200 就是成功"**：曾遇到 200 + 空音频、200 + JSON 错误体。
**必须校验 RIFF 头**。

---

## 八、测试

### 8.1 三层测试，从便宜到贵

1. **单元测试**：纯函数、参数校验、错误分支（无 IO）
2. **冒烟测试**：真调一次服务，验证能出声（`pytest -m smoke`）
3. **验收测试**：按用户需求逐项验证（短句/长文/超长/异常输入）

### 8.2 每个 client 必须有这四条断言

```python
assert speech.audio[:4] == b"RIFF"
assert len(speech.audio) > 1000
assert 0.5 <= speech.duration <= 30
assert speech.sample_rate == 24000
```

### 8.3 记录实测数据，不写"应该很快"

```
GPU/GPU   load=15.38s  gen=4.22s  audio=3.40s  rtf=1.242
CPU/CPU   load= 2.47s  gen=18.51s audio=3.30s  rtf=5.609
```

**RTF = 生成耗时 / 音频时长**。RTF < 1 表示比实时快。这是唯一可信的性能指标。

---

## 九、日志

```python
def log(message: str) -> None:
    line = "%s  %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message)
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
```

**必须记录**：调用参数摘要、耗时、结果路径、完整异常类型与消息。
**不要记录**：完整文本内容（隐私）、大块二进制。

---

## 十、依赖管理

用 `pyproject.toml`，**固定关键版本**：

```toml
dependencies = [
  "transformers==4.57.3",   # 精确锁定：5.x 改过 check_model_inputs 签名，直接崩
  "torch>=2.0",
  "openvino>=2026.3",
]
```

**实测教训**：`transformers` 从 4.57.3 升到 5.5.4，`qwen_tts` 直接
`TypeError: check_model_inputs() missing 1 required positional argument`。

**隔离原则**：不同模型要不同依赖版本时，**建独立 venv**，不要在一个环境里硬凑。
本机现有：`D:\AI_file\envs\openvino`（视觉）、`D:\AI_file\envs\tts-export`（TTS 导出）。

---

## 十一、本机环境事实（写代码前必读）

| 事实 | 后果 |
|---|---|
| Shell 是 **Windows PowerShell 5.1**，无 `pwsh` | 脚本语法受限，用 `.ps1` + BOM |
| `pwsh -Command` 里的**中文全角引号会被当字符串分隔符** | 含中文的脚本必须先写文件再执行 |
| `Add-Type` 在本机**会卡数小时** | 关屏用 `powercfg /change monitor-timeout-ac` |
| 用户名是中文 `徐丰哲` | **OpenVINO C++ 层读写中文路径失败**，模型放 D 盘 |
| `write`/`edit` 工具对 **exFAT（E 盘）** 报 `EISDIR` | E 盘文件用 Python 写 |
| `(Get-Item).Length` 对正在写入的文件**滞后** | 用 Python `os.path.getsize` 或 `Get-Item` 前先停写 |
| PowerShell 变量名**大小写不敏感**，`$Home` 是只读 | 自定义变量别用 `$Home` |

---

## 十二、AI 工具封装清单（本机已就绪）

| 能力 | 入口 | 设备 | 实测 |
|---|---|---|---|
| **中文 TTS** | `tts_client.py` / MCP `speak` | GPU | 2.88 s 音频 / 2.49 s，RTF **0.86** |
| 图像生成 | MCP `image_generate` | iGPU | 1024² 4 步 13–18 s |
| 无审查生图 | MCP `image_generate_uncensored` | iGPU Vulkan | 512² 20 步 85 s |
| 图像理解 | MCP `vision_describe` / `vision_ask` | NPU | 11–18 s |
| OCR | MCP `vision_ocr` | CPU | 0.6–4.1 s/页 |
| 目标检测 | MCP `vision_detect` | NPU | 7 ms |
| 缺陷筛查 | MCP `anomaly_score` | NPU | 41–97 ms |

**新增工具时**：在 `vision-server.py` 加 `@server.tool` 函数，返回 `str`，
失败返回文本不抛异常，然后重启 MCP 服务端让新工具生效。

---

## 十三、许可

用别人的模型前先看许可，写进 README，**发布产物时标注**：

| 模型 | 许可 | 限制 |
|---|---|---|
| Qwen3-TTS | Qwen Research License | **仅研究/评估，禁商用** |
| Kokoro-82M | Apache-2.0 | 可商用 |
| FLUX.1-schnell | Apache-2.0 | 可商用 |
| Qwen-Image 2.1 无审查 | Qwen Research License | **禁商用** |
| 大肥鱼音色数据集 | **CC BY-NC 4.0** | 禁商用 + 须署名「尹紫鹭幻想社」 |

**默认假设：这些都给自用，不给客户。** 要对外交付先换 Apache-2.0 / MIT 的模型。

---

## 十四、踩坑速查（写代码前扫一眼）

1. **HF 与 ModelScope 要反着来**：HF 长连接被掐 → 用分段；ModelScope 限流 Range → 用单流
2. **`hf_xet` 快但会死锁**，卡在 628 MB 有过先例
3. **NPU 只吃完全静态**，有界动态也会崩（INT64_MIN）
4. **CFG 的 batch=2 会被 reshape 进 head 维**，NPU 编译报 `32 vs 16`
5. **`openvino_genai` 的语言白名单是硬编码的**，`zh` 直接拒绝
6. **`manifest.json` 与 exe 可能不同步**，需要手工补键别名
7. **不要用 `-1` 当"未指定"**，在 OpenVINO 里它就是 `INT64_MAX`
8. **RTF 才是性能真相**，不要用"感觉快"

---

## 十五、一句话总结

> **显式 > 隐式，验证 > 假设，实测 > 背书。**
>
> 每个外部调用都要超时，每个返回值都要校验，每个失败都要能定位。
> 三天里所有卡住我的问题，都能归到这三条里的一条。
