# 嘉立创EDA 专业版自动化规则（LCEDA Auto-Design Policy）

- 版本：1.0.0 ｜ 更新：2026-10-21 ｜ 适用：任何需要操作嘉立创EDA 的对话
- 规则源在本文件；机器可读版 `policy\lceda-eda.json`
- **思考语言：一律用中文**；代码、命令、标识符、路径保持原文
- **部署状态：已全局注入**（2026-10-21）。`policy\deploy\global-agents.md` 的规则 9 只放触发条件与四条铁律；
  完整规则按需读取本文件，机器可读版 `policy\lceda-eda.json`
- 实测环境：嘉立创EDA(专业版) **4.1.78** @ `D:\Application\lceda-pro`，Windows x64

**目的**：让 Agent 用**编辑器内部 API**（而不是模拟鼠标）完成原理图/PCB 的自动设计，
并知道哪些接口"返回成功但其实没生效"、哪些参数必须怎么写、数据在什么情况下会被删。

---

## 1. 适用场景

| 需求 | 走这条路 |
|---|---|
| 自动画原理图、批量放器件、批量连线 | ✅ |
| 自动放 PCB 封装、画走线、自动布局 | ✅ |
| 导出网表 / BOM / Gerber / STEP / 截图 | ✅ |
| 图片、PDF、截图 转原理图 | ✅（先过第 9 节的识别流程） |
| 原理图与 PCB 自动同步 | ❌ 见第 8 节，接口失效，需绕行 |

## 2. 环境前置（第一个坑，不解决后面全废）

**`ELECTRON_RUN_AS_NODE=1` 会让 lceda-pro 退化成纯 node**，`doctor` 被当成脚本路径加载，
报 `Cannot find module '...\doctor'`。某些 AI 宿主 / IDE 终端会继承这个变量。

```powershell
Remove-Item Env:\ELECTRON_RUN_AS_NODE -Force
& 'D:\Application\lceda-pro\lceda-pro.exe' doctor
# 期望: {"ok":true,"value":{"connected":true,"versionMatch":true,...}}
```

- `connected:false` = 编辑器没开；**必须让用户先打开任意编辑器窗口**，不要自己乱启动。
- 浏览器版**不支持** CLI、会话与桥接，必须桌面客户端。
- 每次调用 CLI 前都要确认该变量已清除（同一进程内清一次即可）。

## 3. 命令

```text
lceda-pro doctor                          探测端点
lceda-pro open --path <工程> [--headless true]   开工程 → sessionId（4.1.60 不能省略 path）
lceda-pro invoke --session <id> --ext-uuid eda --code "<JS>" [--args <json>] [--timeout ms]
lceda-pro session list | close --session <id> --destroy
lceda-pro doc api --class-name <类> [--method-name <方法>]   查本地 API 文档
lceda-pro --mcp stdio                     MCP 模式
```

返回统一 JSON 信封，**只判断最外层 `ok`**。失败时看 `error.code` / `error.message`。

## 4. invoke 硬约束

1. **永远带 `--ext-uuid eda`**：以内置扩展身份运行，才有读写本地文件等权限。
   实测**不需要**任何"允许外部交互"的 GUI 开关（那是第三方 `.eext` 才要的）。
2. 路径用**正斜杠** `C:/Users/...`，反斜杠会被 shell/JSON 吃掉。
3. `--timeout` 上限在 4.1.60 是 **60000 ms**，超过直接 `INVALID_ARGS`；4.1.78 未复测上限，按 60 s 设计。
4. 器件**每批 20–25 个**，一次塞几百个必超时。
5. 改动后**等 5–10 秒**再查 DRC / 网表 / 渲染；新建工程后 `getCurrentProjectInfo()` 可能要先等 5–8 秒才非空。
6. **不要自己算引脚/焊盘坐标**，一律用 `getAllPinsByPrimitiveId()` 读回。
7. 任务结束 `session close --destroy`，避免窗口堆积。

## 5. 版本差异（必看，会直接决定成败）

| 项 | 4.1.60 | 4.1.78 |
|---|---|---|
| PCB `create`（包装对象 + 数字层） | 崩 | ✅ 可用 |
| `createProject` 第 7 参数 `fileFormat` | 不支持，强制 eprj2 | 支持 `'eprj3'` |
| `invoke --timeout` 上限 | 60000 | 未复测 |
| `resultChannel` | null | true |

**结论：PCB 写入类操作要求 4.1.78 及以上。** 在低版本上不要反复重试，先让用户升级。

## 6. 原理图 API（实测可用）

```js
const LIB = await eda.lib_LibrariesList.getSystemLibraryUuid();   // 系统库 UUID
// ⚠️ 搜索必须显式传 LIB，否则返回空数组（不报错，最坑）
const item = (await eda.lib_Device.search('0603WAF1001T5E', LIB, undefined, undefined, 3, 1))[0];

// create(component, x, y, subPartName?, rotation?, mirror?, addIntoBom?, addIntoPcb?)
const c = await eda.sch_PrimitiveComponent.create(item, 100, 100, undefined, undefined, undefined, true, true);

const pins = await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(c.primitiveId);
// → [{pinNumber:'1', x:80, y:100}, {pinNumber:'2', x:120, y:100}]

// 导线：坐标必须落在引脚上，否则电气上是断开的
// line 支持多段线 [x1,y1,x2,y2,x3,y3]，必须水平/垂直交替且首尾相连
await eda.sch_PrimitiveWire.create([120, 100, 160, 100, 160, 120], 'NET_MID');
await eda.sch_Document.save();
```

- `sch_PrimitiveComponent.getAll()` 在**当前图页**生效，切换文档后要重新取。
- `getAll()` 会带出半成品器件（`name` 为空或 `={Manufacturer Part}`），它们会让网表生成卡死，**先删掉**。

## 7. PCB API（实测可用）

```js
const f = (await eda.lib_Footprint.search('0603', LIB, undefined, undefined, 3, 1))[0];
// ⚠️ 必须包一层，直接传 f 会报 [object Object]
const wrap = { libraryType: '4', libraryUuid: f.libraryUuid, uuid: f.uuid };
const c = await eda.pcb_PrimitiveComponent.create(wrap, 1, 1000, 1000);  // 1=顶层 2=底层

const pads = await eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId(c.primitiveId);
// → [{padNumber, x, y, rotation, layer}]

// 走线：create(net, layer, startX, startY, endX, endY, lineWidth?, lock?)
await eda.pcb_PrimitiveLine.create('NET1', 1, 1000, 1000, 1500, 1000, 10);
await eda.pcb_Document.save();
```

- 坐标单位按 mil 理解（0603 约 63 mil 长），别用 1000 mm 这种量级乱试。
- `pcb_Document.autoLayout()` 实测生效（会真的移动器件）。
- `pcb_Document.autoRouting()` 只有**焊盘已带网络关系、存在飞线**时才布；
  手放器件之间没有网表关系时会返回 `{success:false, totalNetsCount:0}`，这是正常的。

## 8. 禁用清单（返回 `true` 但什么都不写）

| 接口 | 实测表现 |
|---|---|
| `pcb_Document.importChanges(schUuid)` | 返回 true，PCB 文件仍是 300 字节空文档；eprj2/eprj3 都一样 |
| `pcb_Net.setNetlist('JLCEDA', txt)` | 返回 true，网络数 0；保存+重开仍为 0 |
| `sch_Netlist.getNetlist()` | 已废弃，直接调**卡死 60 s 超时** |

**铁律：不要用返回值判断成功。** 必须验证：
1. `getAll()` 能读到对象；
2. 磁盘文件确实变大（eprj3 的 `.epcb2` 从 300 B → 49 KB 才算写进去）。
3. 导出网表用 `sch_ManufactureData.getNetlistFile(name, 'JLCEDA')` → 返回 **File 对象**（不是路径），
   `await file.text()` 取内容；它不落盘。

**原理图 ↔ PCB 没有可靠的自动同步通道**，正确形态是：AI 按网表自己算坐标、自己放、自己连。

## 9. 图片 / PDF → 原理图

1. **先分流**：电子版 PDF → `vision_read_document`（走文字层，精确）；
   扫描件/截图 → `vision_ocr`（原生分辨率）；图形/框图 → `vision_describe`。
2. **型号、封装、引脚号一律以 OCR/文字层为准**，VLM 只用来给候选，必须写成"疑似…"并给复核途径。
3. **不要逐像素还原连线**。原理图的线是纯图形、没有电气语义。
   正确产出是**网表 DSL**：

```json
{ "components": [{ "ref": "U1", "mpn": "AMS1117-3.3", "package": "SOT-223", "pins": { "1": "GND" } }],
  "nets": [{ "name": "VCC", "nodes": ["U1.3", "C1.1"] }] }
```

4. 校验后才落图：引脚数 vs 封装、电源/地连通、悬空引脚、去耦是否落在对应电源域。
5. **精度预期**：单模块 80–95%（人工修线 10 分钟）；整页密集原理图只抽 BOM + 关键网络；手绘照片不要承诺自动。

## 10. 数据安全（血泪教训）

1. **升级客户端会清空 `projects` 目录**（实测 4.1.60→4.1.78：整个 `Documents\LCEDA-Pro` 被替换，
   旧目录进回收站）。**升级前必须先备份 `projects`**。
2. 只能写 `APP_PROJECT_DIR`（`%USERPROFILE%\Documents\LCEDA-Pro\projects` 等）。
3. **不要对着用户的真实工程做写操作**；一律新建测试工程（`DSH PoC` 之类），验证完删掉。
4. 需要读用户工程时用 `--headless true` 打开，做完 `session close --destroy`。
5. 误删排查顺序：回收站 → `projects-recovery` → `database`。回收站里的目录可用
   `Shell.Application.Namespace(10)` 的 `CopyHere` 复制出来（**不要"还原"**，会和新目录撞车）。

## 11. 标准工作流

```text
0. 清 ELECTRON_RUN_AS_NODE → doctor → connected:true
1. createProject(..., 'eprj3') → openProject → 等 6 s → getCurrentProjectInfo
2. openDocument(图页 uuid) → 等 2.5 s（否则 create 会卡 60 s）
3. 搜器件（带 LIB）→ 批量 create → 读引脚 → 画线 → save
4. 导出：getNetlistFile / getBomFile / getGerberFile → File.text() 或 saveFileToFileSystem
5. PCB：openDocument(pcb) → 放封装（wrap+数字层）→ 读焊盘 → 画线 → autoLayout → save
6. 逐项验证磁盘产物 → session close --destroy
```

## 12. 每次任务必须做的验证

- [ ] `doctor` 的 `connected` 为 `true`
- [ ] 每个 `invoke` 的 `ok` 为 `true`
- [ ] 关键写操作后 `getAll()` 数量 > 0
- [ ] 目标文件大小/时间戳有变化
- [ ] 用户工程未被修改（只碰测试工程）

## 13. 禁止事项

1. 禁止用返回值 `true` 当作"已生效"的证据。
2. 禁止在用户真实工程上做实验性写入。
3. 禁止自己计算引脚/焊盘坐标。
4. 禁止在浏览器版上尝试 CLI / 会话 / 桥接。
5. 禁止对原理图做"逐像素还原"式的自动转换并宣称可用；必须经网表 DSL 与人工确认。
6. 禁止自动下单（Gerber 必须人工过一遍再发嘉立创）。
