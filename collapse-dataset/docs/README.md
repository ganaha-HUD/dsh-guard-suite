# Session 3b54e160 — Shrink-Collapse Dataset v1

A fully annotated, single-trajectory dataset of an LLM agent that progressively
stopped acting while its assertiveness stayed constant. Released for research on
degeneration, self-verification failure and agentic reliability.

- **Session**: `session-3b54e160-6d42-43a7-b4af-bffba94d76d9` (DSH desktop, workdir `E:\Deepseek`)
- **Span**: 2026-09-28 → 2026-10-24, 137 turns, 10,816 events, 1,384 assistant steps
- **Model**: `deepseek-flash` (deepseek-official)
- **Annotation**: every assistant step, no sampling
- **Labels**: `normal` 1,100 · `suspect` 274 · `collapse` 10

## Why this dataset exists

Existing degeneration literature and tooling focus on **expansion** — one phrase
emitted tens of thousands of times. This session is the opposite:

| metric | first 36 turns | last 12 turns |
|---|---|---|
| tool calls / turn | 10.31 | 1.25 |
| chars / turn | 9,879 | 1,527 |
| evidence markers / kchar | 4.34 | 2.40 |
| **assertions / kchar** | **1.12** | **1.20** |

Text fell 85%, actions fell 88%, assertions did not move. A repetition detector
cannot see this, because nothing repeats enough.

## Contents

```
collapse-dataset/
├── session/
│   ├── session.v4.jsonl.zstd    12.7 MB  original append-only log (5,990 zstd frames)
│   └── session.v4.jsonl         47.3 MB  decompressed, 10,816 events
├── annotations/
│   ├── steps.jsonl              1,384 rows, one per assistant step
│   ├── steps.csv                flat, UTF-8 no BOM  (pandas / R)
│   ├── steps-excel.csv          flat, UTF-8 with BOM (Excel double-click)
│   ├── turns.json               134 rows
│   ├── turns.csv                UTF-8 no BOM
│   └── turns-excel.csv          UTF-8 with BOM
├── outputs/                     everything the session itself produced
│   ├── deliverables/            9 documents (guides, install records)
│   ├── logs/                    31 run logs
│   ├── scripts/                 12 scripts
│   ├── data/                    downloaded plugin artifacts
│   └── archive/                 superseded versions, recovery artifacts
├── analysis/                    pre/post-T86 comparison (report, stats, figure)
├── context/                     experimental context (CONFOUNDERS)
│   ├── policy/                  8 rule files in force during the session
│   ├── tools/                   5 helper scripts the rules required
│   ├── agents-md/               system prompt snapshots before/after persona
│   └── persona-injection-turn86.md   verbatim persona text injected at T86
├── code/
│   ├── annotate-session.mjs     produces steps.jsonl / steps.csv
│   ├── summarize-turns.mjs      produces turns.json / turns.csv
│   ├── collapse-check.mjs       live detector (step-window ratios)
│   └── analyze-fingerprints.mjs phase-level feature comparison
└── docs/
    ├── README.md                this file (English)
    ├── README.zh-CN.md          中文版说明
    ├── METHOD.md                annotation protocol, thresholds, limits
    ├── METHOD.zh-CN.md          中文版标注方法
    ├── REPRODUCE.md             exact commands to regenerate annotations
    ├── REPRODUCE.zh-CN.md       中文版复现步骤
    ├── CITATION.md              how to cite
    ├── DATA-FORMAT.zh-CN.md     中文：CSV 编码差异与打开方式
    ├── CONFOUNDERS.md           ⚠ experimental context and confounders
    └── CONFOUNDERS.zh-CN.md     ⚠ 中文版混杂因素说明
    └── CITATION.zh-CN.md        中文版引用说明
```

## Quick start

```bash
# 1. decompress (if you want to re-run annotation)
node -e "const z=require('zlib'),fs=require('fs');fs.writeFileSync('session.v4.jsonl',z.zstdDecompressSync(fs.readFileSync('session/session.v4.jsonl.zstd')))"
# NOTE: the file is 5,990 concatenated zstd frames; a single-shot call only
# decompresses the first one. Use the splitter in code/ or the copy provided.

# 2. re-annotate
node code/annotate-session.mjs
node code/summarize-turns.mjs

# 3. analyze
#    steps.csv / turns.csv are flat CSVs: open in pandas / R / Excel
```

## Key findings encoded in the labels

1. **Collapse turns**: 27, 112, 113, 125, 127, 128, 130, 132, 134, 136.
   Isolated early (T27), then concentrated in the last 25 turns.
2. **First template-heavy turn**: T73. The `**好** ✓` ("OK ✓") skeleton appears
   in reasoning from T91 onward (285 steps have ≥1 hit; the worst has 78 hits).
3. **The cleanest sample**: T134 step 1 — the user asked "check whether the
   anti-collapse plugin is still active"; reasoning contains `grep` five times,
   **zero tool calls, zero prose**, turn ends in 3 seconds.
4. **Detector blind spot**: `dsh-guard-repeat-output` v2.1.7 fired **0 times**
   during the entire collapse. Its conviction threshold is
   `lowInfoDupShare >= 0.80`; measured maximum in this session is **0.44**.

## License and privacy

- Annotations, documentation, analysis and context files: **CC BY 4.0** (see [`LICENSE`](../LICENSE)).
- Analysis code (`code/`): **MIT**.
- Machine-readable deposit metadata: [`.zenodo.json`](../.zenodo.json).
- Session content: contains only the operator's own prompts and model output;
  no third-party personal data. Local file paths have been left in place because
  they are required to verify claims (they are generic paths, not credentials).
- No API keys, tokens or credentials are present. Verified by regex scan.