# Zenodo 上传指南（中文）

> 目标：拿到一个带时间戳的 DOI，把这份数据集钉在 2026-10-25。

## 一、上传前必须改的一处

`.zenodo.json` 里的作者是 `ganaha-HUD`。**Zenodo 是学术存档，建议填真实姓名**：

```json
"creators": [
  { "name": "你的真名", "affiliation": "你的学校/学院" }
]
```

如果你坚持用网名，也能发，只是以后别人引用时作者栏会是网名。

## 二、操作步骤（网页版，约 10 分钟）

### 1. 注册

打开 https://zenodo.org/signup/ ，用 GitHub 或 ORCID 登录最省事。需要邮箱验证。

### 2. 新建上传

右上角 **New upload**。

### 3. 上传文件

把这两个文件拖进去：

| 文件 | 为什么 |
|---|---|
| `session-3b54e160-collapse-dataset-v1.zip` | 完整数据（含原始日志、标注、代码、文档） |
| `docs/README.md` | 单独放一份说明，别人不用解压就能看 |

**不要**把 185 个文件一个个拖——Zenodo 对多文件支持没问题，但下载体验差得多。

### 4. 填元数据

如果 Zenodo 没自动读取 `.zenodo.json`（大概率不会），照下面手动填：

| 字段 | 值 |
|---|---|
| **Resource type** | Dataset |
| **Title** | Session 3b54e160: A Single-Trajectory Dataset of Shrink-Collapse in an LLM Tool-Use Agent |
| **Authors** | 你的真名（+ 单位） |
| **Description** | 从 `.zenodo.json` 的 `description` 字段整段复制（是 HTML，粘贴后会自动渲染） |
| **Keywords** | LLM agents; degeneration; repetition collapse; tool use; annotated dataset; agent reliability; persona injection |
| **Language** | English |
| **License** | Creative Commons Attribution 4.0 (CC BY 4.0) |
| **Related identifiers** | `https://github.com/ganaha-HUD/dsh-guard-suite`，关系选 *is supplemented by* |

### 5. 检查

点 **Preview** 看一眼。重点看：

- 文件能不能下载
- Description 的 HTML 有没有渲染错（如果显示成一堆 `<p>`，说明它按纯文本处理了，改成纯文本段落）

### 6. 发布

点 **Publish**。

⚠️ **发布后文件不能改，只能发新版本（新版本会有新 DOI，旧 DOI 仍然有效并指向最新版）。**

所以点之前再确认一遍：文件齐、作者对、许可对。

### 7. 拿到 DOI

发布后页面会显示形如：

```
DOI: 10.5281/zenodo.XXXXXXX
```

**把这个 DOI 填回论文的第八节和数据可用性声明。**

## 三、发布后要做的三件事

1. **更新论文**：`paper/report-v1.md` 第 8 节加一行 DOI。
2. **更新 CITATION.md**：把 BibTeX 里的 `url` 换成 Zenodo 链接，加 `doi` 字段。
3. **GitHub 仓库 README** 顶部加徽章（可选）：
   ```
   [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
   ```

## 四、常见问题

**Q：Zenodo 有文件大小限制吗？**
单文件 50 GB，总量不限制。这个包 28 MB，完全没问题。

**Q：中国访问慢怎么办？**
Zenodo 在国内一般能访问，就是慢。上传 28 MB 可能需要几分钟。如果反复失败，可以挂梯子。

**Q：能不能不发布，先存草稿？**
可以。Draft 状态有 30 天保留期（可续期）。但只有发布才有 DOI。

**Q：以后想改怎么办？**
发新版本（New version）。Zenodo 会保留所有版本，DOI 关系是"最新版"和"指定版本"。论文里引用"最新版" DOI 即可。

**Q：和 arXiv 什么关系？**
不冲突。数据集放 Zenodo（有 DOI），论文放 arXiv（有 arXiv ID），两边互相引用。Zenodo 也支持传预印本，但 arXiv 的学术认可度更高。

## 五、如果你想要 API 方式

有 token 的话可以脚本上传，省去手填。流程是：

```
POST /api/deposit/depositions            # 创建
POST /api/deposit/depositions/{id}/files # 上传（multipart）
PUT  /api/deposit/depositions/{id}       # 填元数据
POST /api/deposit/depositions/{id}/actions/publish  # 发布
```

需要 `ZENODO_TOKEN`（在 Settings → Applications 里生成，勾 `deposit:write` 和 `deposit:actions`）。要的话告诉我，我写好脚本你填 token 就行。