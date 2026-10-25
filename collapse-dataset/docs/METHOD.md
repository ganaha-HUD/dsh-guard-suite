# Annotation Protocol

## Unit

One row per **assistant step** (`assistant/message` event). A step is the atomic
model output between two tool calls. 1,384 steps over 137 turns.

Every row carries `seq` — the event sequence number in the append-only log — so
any label can be traced to the exact byte range it came from.

## Signals

All signals are structural or lexical. **No model self-assessment is used anywhere**:
an LLM judging its own degeneration is the failure mode being measured.

| field | definition |
|---|---|
| `tool_calls` | number of `tool-call` blocks in the assistant message |
| `reasoning_chars` | total characters across `reasoning` blocks |
| `text_chars` | total characters across `text` blocks |
| `action_words` | count of action verbs in **reasoning only**: 检查/查看/搜索/grep/读一下/验证一下/执行一下/调用一下/排查/定位/确认一下/试试 |
| `assert_words` | count of completion assertions in reasoning+text: 已完成/成功/可用/已就绪/跑通/没问题/证明/根本原因/完全 … |
| `unsure_words` | count of hedges: 可能/疑似/未验证/推测/假设/待确认/似乎/存疑 … |
| `evidence_marks` | count of replayable evidence: drive paths, URLs, `exit code`, `HTTP nnn`, `sha256`, `number + unit` (B/KB/MB/GB/ms/s/Hz) |
| `falsify_words` | count of hypothesis-questioning phrases: 不通/行不通/放弃/证伪/反例/死路/推翻/这条路 … |
| `template_hits` | occurrences of the `**好** ✓` / `（输出 ✓）` skeleton (markdown-bold aware) |
| `dup_share` | largest identical-segment share of the reasoning, split on `。！？；.!?;` and newlines |
| `pseudo_certainty` | `assert_words / (1 + evidence_marks + unsure_words)` |

## Labels

| label | rule | rationale |
|---|---|---|
| `collapse` | `action_words >= 3 AND tool_calls == 0 AND reasoning_chars >= 120` (**simulated action**), OR `tool_calls == 0 AND text_chars < 80 AND reasoning_chars >= 300` (**think-only**) | structurally provable: work was described but not executed |
| `suspect` | `template_hits >= 5` | the "OK ✓" skeleton dominates, but the step may still be harmless |
| `normal` | everything else | |

`collapse` takes precedence over `suspect`.

## Threshold justification

| threshold | value | why this value |
|---|---|---|
| `action_words >= 3` | 3 | a single verb ("check") is normal prose; three in one reasoning block with zero calls is not |
| `reasoning_chars >= 120` | 120 | below this, short legitimate answers would be misclassified (first test run used a 45-char fixture and produced a false negative — recorded here so it is not repeated) |
| `template_hits >= 5` | 5 | **absolute**, not a share: the worst step has 78 hits inside 3,757 chars (20%), so any proportion threshold either over-fires or never fires |
| `text_chars < 80` | 80 | think-only means no prose at all; 80 chars tolerates a one-line pointer |

## Measured distribution

```
steps      : 1,384
normal     : 1,100
suspect    :   274
collapse   :    10   (4 simulated-action, 10 think-only, overlapping)
```

## Known limitations

1. **Single trajectory, single model.** No cross-model generalisation claim is made.
2. **Lexical signals are language-specific.** The regexes are Chinese/English;
   other languages need their own verb lists.
3. **`suspect` is a heuristic.** It marks template-heavy reasoning, not proven
   collapse; precision was not independently adjudicated.
4. **Cannot detect "evidence present but wrong".** A fabricated file path raises
   `evidence_marks` exactly like a real one. Evidence must be replayed to be trusted.
5. **No human inter-annotator agreement.** Labels come from one fixed protocol;
   a second annotator would be needed for an IAA figure.