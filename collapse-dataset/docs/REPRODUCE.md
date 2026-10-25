# Reproducing the annotations

## Requirements

- Node.js >= 20 (tested on 24.20)
- No npm dependencies — the scripts use only `node:fs` / `node:path`

## 1. Get the log

`session/session.v4.jsonl` is already decompressed and is the exact input used to
produce every number in this dataset. Use it directly.

If you must decompress from `session/session.v4.jsonl.zstd` yourself, note:

> The file is **5,990 concatenated zstd frames** (one per flush). A single
> `zlib.zstdDecompressSync()` call returns only the **first frame** — 192 bytes,
> which is the session header and nothing else. You must split on frame
> boundaries or stream-decompress.

## 2. Re-annotate

```bash
cd collapse-dataset
node code/annotate-session.mjs
node code/summarize-turns.mjs
```

`annotate-session.mjs` reads the log path hard-coded at the top; point it at
`session/session.v4.jsonl` on your machine.

## 3. Expected output

```
steps: 1384
labels: { normal: 1100, collapse: 10, suspect: 274 }
flags:  { think_only: 10, template_heavy: 283, simulated_action: 4 }

turns: 134
collapse_turns: [27,112,113,125,127,128,130,132,134,136]
first_suspect_turn: 73
```

If you get different counts, check the locale/encoding of your source file
(it must be UTF-8 without BOM).

## 4. Sanity checks

Three assertions worth running before trusting any derived statistic:

```bash
# a) the 3-second "check" step must be labelled collapse
grep '"turn":134' annotations/steps.jsonl | grep '"label":"collapse"'

# b) the step with 10 tool calls must NOT be flagged as simulated action
grep '"turn":131' annotations/steps.jsonl | grep -c 'simulated_action'   # expect 0

# c) the guard plugin fired zero times during the collapse window
#    (external evidence: ~/.dsh/logs/dsh-guard-repeat-output.log, last write 2026-10-21)
```

## 5. Reproducing the detector perspective

`code/collapse-check.mjs` is the live detector the paper's intervention is based
on. It consumes the same log and prints rolling-window ratios:

```bash
node code/collapse-check.mjs session/session.v4.jsonl 12
```

Expected tail behaviour: `toolsPerTurn` 1.25, `evidenceD` 2.40,
`pseudoCertainty` 0.40, `falsifyPerTurn` 0.25 — all four below their thresholds
simultaneously, which is the "stop and hand over" condition.