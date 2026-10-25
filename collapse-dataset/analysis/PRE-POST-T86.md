# Pre/Post T86 Persona-Injection Comparison

> 中文版：[`PRE-POST-T86.zh-CN.md`](./PRE-POST-T86.zh-CN.md)

## Headline

After persona injection, **template formation begins**; collapse follows once that
template has accumulated for roughly 25 turns. The middle variable — template
accumulation — must not be skipped.

> Not "the persona caused collapse 25 turns later". The data only establishes this
> temporal ordering; attribution requires the control arm in
> `docs/CONFOUNDERS.md` §6.

## Data

| group | turns | steps |
|---|---|---|
| pre (T1–85) | 85 | 926 |
| post (T86–137) | 52 | 458 |

## Per-step metrics

| metric | pre | post | change |
|---|---|---|---|
| tool calls / step | 1.06 | 0.90 | −15% |
| chars / step | 2,725 | 904 | −67% |
| template hits / step | 0.04 | 11.96 | 0 → 12 |
| evidence / kchar | 2.33 | 3.91 | +68% |
| assertions / kchar | 0.549 | 1.096 | +100% |

## Statistics (Mann-Whitney U)

| metric | pre median | post median | p | Cliff's δ | effect |
|---|---|---|---|---|---|
| tool_calls | 1.00 | 1.00 | 2.0e−10 | **+0.144** | small |
| chars | 2,110 | 741 | 1.5e−65 | **+0.564** | medium–large |
| template_hits | 0 | 7 | 2.5e−157 | **−0.664** | **large** |
| falsify_words | 0 | 0 | 0.036 | −0.027 | negligible |

The counter-intuitive row is tool calls: the median does not move and the effect
size is small. **After the persona, the model still calls tools; each step simply
gets much shorter and much more template-heavy.**

## Band trend (the important part)

| band | steps | tools/step | chars/step | template/step | collapses |
|---|---|---|---|---|---|
| T1–40 | 412 | 1.16 | 3,782 | 0.00 | 1 |
| T41–85 | 514 | 0.98 | 1,877 | 0.07 | 0 |
| T86–110 | 213 | 0.90 | 1,034 | 4.99 | **0** |
| T111–137 | 245 | 0.90 | 792 | 18.02 | **9** |

```
T86 persona → template appears → 25 turns of accumulation → T111 collapse
```

This is a **delayed** relationship, not an immediate one. Any causal claim that
skips the middle band would contradict the data.

## Relation to the "−88% tool calls" figure

`README.md` reports 10.31 → 1.25 tool calls per **turn**, comparing the first 36
turns with the last 12. That is a different cut from pre/post T86:

| cut | tool calls |
|---|---|
| first 36 vs last 12 turns | 10.31 → 1.25 (−88%) |
| per step, pre vs post T86 | 1.06 → 0.90 (−15%), but steps/turn fell 10.9 → 8.8 |

Both are correct; **state which cut you use** or the numbers appear to disagree.

## What the data supports / does not support

The middle panel also shows something the report must concede: **characters per
step decline monotonically from T1** (≈4,500 at T1 → 1,877 for T41–85 → 792 for
T111–137).

So there are three phenomena on three timescales:

- **text shortening** is a long-run trend that predates the persona;
- **template formation** is the persona-period change (0.04 → 12, abrupt);
- **collapse** is a third stage that needs template density ≈18/step.

Do not attribute all three to the persona.

Supports:
- persona ↔ template formation (δ = −0.664, large)
- template accumulation precedes collapse (T86–110 vs T111–137)

Does not support:
- "persona caused collapse" (T86–110 has persona, zero collapse)
- "persona stopped tool use" (−15% only)
- "collapse was sudden" (chars decline monotonically: 3,782 → 1,877 → 1,034 → 792)

## Robustness: step-level vs turn-level

Steps within a turn are not independent (each conditions on the previous one), so
step-level Mann-Whitney p-values are anti-conservative. Re-running on per-turn
means (pre 82 turns / post 52 turns):

| metric | step-level δ | turn-level δ | step p | turn p |
|---|---|---|---|---|
| tool_calls | **+0.144 (small)** | **+0.521 (medium–large)** | 2.0e−10 | 3.6e−07 |
| chars | +0.564 | +0.828 | 1.5e−65 | 7.6e−16 |
| template_hits | −0.664 | **−0.986 (very large)** | 2.5e−157 | 5.5e−25 |
| falsify_words | −0.027 | −0.161 | 0.036 | 0.051 |

Direction and significance survive at the turn level; template formation actually
strengthens (δ −0.664 → −0.986).

**Tool calls reverse**: small at step level (0.144), medium–large at turn level
(0.521). `tool_calls` is a discrete value that is 1 in most steps, so the step-level
median saturates and hides between-turn differences; averaging per turn exposes them.

Correct statement:

> The per-step decline in tool-call density is a small effect (δ=0.144) but a
> medium–large effect per turn (δ=0.521, n=82/52). **Effect size depends on the
> aggregation unit; report both.**

(Turn-level n is 82/52; treat it as robustness support, not primary evidence.)

## suspect is a precursor of collapse

In the post group, `suspect` covers 59.61% of steps while `collapse` covers 1.97%.
Quantified transition:

| condition | ≤1 turn | ≤3 | ≤5 | ≤10 | ≤20 |
|---|---|---|---|---|---|
| currently suspect | 16.7% | 27.8% | 38.9% | 66.7% | **94.4%** |
| baseline (non-suspect) | 6.5% | 10.5% | 15.3% | 27.4% | 44.4% |
| ratio | 2.6× | 2.6× | 2.5× | 2.4× | 2.1× |

**After a suspect turn, the probability of collapse within 20 turns is 94.4% vs a
44.4% baseline.**

Suspect run lengths are also informative:

| run length | starts | collapse | gap |
|---|---|---|---|
| 16 turns | T96 | T112 | 1 |
| 11 turns | T114 | T125 | 1 |
| 1 turn | T126 | T127 | 1 |
| 1 turn | T129 | T130 | 1 |
| 1 turn | T131 | T132 | 1 |
| 1 turn | T133 | T134 | 1 |

**Early phase: long incubation (16, 11 turns). Late phase: collapse on the next
turn.** This supports "shrink is a process, not a switch" — suspect accumulates
first, then converts rapidly.

## Limits

Single session, no control arm; time and persona are confounded (context also grew
and compaction ran 5 times); one pre-persona collapse (T27) exists. For attribution,
run the control described in `docs/CONFOUNDERS.md` §6.

## Artefacts

- `pre-post-persona.json` — all numbers
- `band-summary.csv` — band rollup
- `stats-tests.json` — test results
- `fig-behavior-over-turns.png` — three series with T86 and T111 marked