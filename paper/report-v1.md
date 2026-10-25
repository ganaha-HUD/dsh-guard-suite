# Delayed Collapse in an LLM Tool-Use Session: A Preliminary Case Study

**Author:** Fengzhe Xu (ganaha-HUD)
**Date:** 2026-10-25
**Status:** Draft v1.0 — empirical report, not a causal claim
**Data and code:** https://github.com/ganaha-HUD/dsh-guard-suite
**Dataset DOI:** 10.5281/zenodo.XXXXXXX  *(placeholder — replace after the Zenodo deposit is published)*

---

## Abstract

In a single 137-turn tool-use session, the assistant's per-step text output fell by roughly two thirds while the density of completion assertions stayed flat, and a recurring "OK ✓" template rose from essentially zero to twelve hits per step. The collapse was not immediate: it began about 25 turns after a persona block was injected mid-session, and only became frequent after the template had accumulated for another 25 turns. The same comparison yields a small effect size for tool-call density at the step level (Cliff's δ = 0.144) but a medium-to-large effect at the turn level (δ = 0.521), because the step-level variable is discrete and its median saturates at 1. A repetition guard with a calibrated conviction threshold of 0.80 fired zero times during the collapse; the maximum duplicate share observed was 0.44.

---

## 1. How this started

On 2026-10-24 I asked an assistant to check whether a plugin was still active. It answered in three seconds. The transcript looked like this: five occurrences of the word `grep` inside the reasoning channel, each followed by a checkmark, and not a single tool call. No prose either. The turn simply ended.

That was odd enough to investigate, but not enough to write anything about. What made it worth a report was the pattern. I exported the full session log, wrote a small parser, and found that the same shape — described work, no execution, confident tone — had been recurring for days.

This report does two things. First, it records what I measured, with the exact definitions, so the observation is on the record and can be checked or refuted. Second, it points out a statistical trap I walked into and then out of: the same data gives a small effect at one level of aggregation and a medium-to-large effect at another, and the reason is not noise.

I am not claiming that the persona caused the collapse. The data cannot support that, and Section 6 says why in detail.

---

## 2. Data

One session, `session-3b54e160`, from the DSH desktop application (Electron host, `deepseek-flash` via `deepseek-official`). It ran from 2026-09-28 to 2026-10-24 in a workspace on `E:\Deepseek`, on a Windows 11 machine with an Intel Core Ultra 5 338H and no discrete GPU.

The log is append-only and was written by the harness, not by the model. Totals:

| item | count |
|---|---|
| turns | 137 |
| events | 10,816 |
| assistant steps | 1,384 |
| tool calls | 1,393 |
| context compactions | 5 |

Three properties of the environment matter for interpretation, and all three are documented in the released package:

1. A set of rule files was active, injected into every request. They mandate where output files go and when certain tools must be used, which raises the baseline tool-call rate.
2. At turn 86, a 1,405-character persona block was inserted into the system prompt. Before that turn the global instruction file was 10,859 bytes; after it, 14,546.
3. `dsh-guard-repeat-output` v2.1.7, a repetition guard, was installed and running from 2026-10-20 onward.

The persona insertion is what makes this session interesting and also what makes it confounded. I treat it as a descriptive boundary, not as a treatment.

---

## 3. Definitions

Everything in this section is implemented in `annotate-session.mjs` in the released repository, so the definitions are executable rather than prose.

### 3.1 Unit of analysis

A **step** is one `assistant/message` event: the model output between two tool results. A turn may contain several steps. All 1,384 steps were annotated; there is no sampling.

Each row carries the event's `seq`, so any label can be traced back to the exact byte range in the append-only log.

### 3.2 Three quantities

**Tool calls.** The number of `tool-call` content blocks in the message. This is a count, and in this session it is usually 0 or 1.

**Characters.** The sum of characters in `reasoning` and `text` blocks. It measures how much the model produced, not how much of it was useful.

**Template hits.** Occurrences of a specific self-confirmation pattern. The literal form in the log is `**好** ✓` (markdown bold around a Chinese "good"), sometimes with `（输出 ✓）` interleaved. The first regex I wrote matched `好 ✓` and found nothing, because of the asterisks. The working pattern is:

```
好[^\n]{0,6}✓|（输出[^\n]{0,4}✓）|\(输出[^\n]{0,4}✓\)
```

This is a deliberately narrow target: it catches the confirmation loop, not general repetition. That the model writes markdown bold around a checkmark is itself worth noting: it is fabricating the *appearance* of a completed step, which is the same move as fabricating a tool call, one layer up.

### 3.3 Labels

A step is labeled `collapse` when either condition holds:

- **simulated execution:** at least three action verbs appear in the reasoning (检查, 查看, 搜索, grep, 验证, 执行, 排查 …), no tool call was made, and the reasoning is at least 120 characters;
- **think-only:** no tool call, fewer than 80 characters of prose, and at least 300 characters of reasoning.

A step is labeled `suspect` when `template_hits >= 5` but neither collapse condition holds. Everything else is `normal`. `collapse` takes precedence over `suspect`.

The 120-character floor exists because my first test fixture was 45 characters and silently produced a false negative. The 5-hit threshold is absolute rather than proportional because the worst step contains 78 hits inside 3,757 characters — about 20% — so any proportion threshold either fires constantly or never fires.

### 3.4 Boundaries

Two turns are used as boundaries throughout:

- **T86**, where the persona block was inserted;
- **T111**, where collapse frequency jumps.

`pre` means T1–T85 (926 steps), `post` means T86–T137 (458 steps).

---

## 4. Results

### 4.1 The shape of the run

![behavior over turns](./figures/fig-behavior-over-turns.png)

Splitting the run into four bands makes the timing visible:

| band | steps | tool calls / step | chars / step | template hits / step | collapses |
|---|---|---|---|---|---|
| T1–40 | 412 | 1.16 | 3,782 | 0.00 | 1 |
| T41–85 | 514 | 0.98 | 1,877 | 0.07 | 0 |
| T86–110 | 213 | 0.90 | 1,034 | 4.99 | 0 |
| T111–137 | 245 | 0.90 | 792 | 18.02 | 9 |

Three observations, in order of how confident I am about them.

Characters per step decline monotonically from the first band. This is the trend I trust most, because it starts long before the persona and continues past it. Whatever caused it, it was already operating at turn 1.

Template hits behave differently. They are essentially absent until T86, then appear at about 5 per step, then jump to 18 per step after T111. That step change coincides with the persona insertion.

Collapses are absent from T86–110 despite the template already being present. They appear only in the last band. So the ordering is persona → template → collapse, with a gap of roughly 25 turns between the first two steps of that chain.

### 4.2 Pre/post comparison

| metric | pre mean | post mean | change |
|---|---|---|---|
| tool calls / step | 1.06 | 0.90 | −15% |
| chars / step | 2,725 | 904 | −67% |
| template hits / step | 0.04 | 11.96 | from 0 to 12 |
| assertions / kchar | 0.55 | 1.10 | +100% |

The assertion density doubling while characters fall is the combination that makes the output look confident and empty at the same time.

### 4.3 The part I got wrong first

My initial statistical comparison treated each of the 926 and 458 steps as an independent sample and ran Mann-Whitney U. It produced p = 2e-10 for tool calls, which looks decisive.

It is not, for two reasons.

First, steps within a turn are not independent. Each step conditions on the previous one; a turn is a chain, not a bag. Treating them as independent inflates the effective sample size and deflates p-values. This is pseudo-replication.

Second, and more interesting, the step-level effect size for tool calls is small: Cliff's δ = 0.144. The median does not move at all (1 → 1). The variable is discrete, most steps call exactly one tool, and the median saturates.

Aggregating to the turn level and repeating the test fixes both problems at once:

| metric | step δ | turn δ | step p | turn p |
|---|---|---|---|---|
| tool calls | **+0.144 (small)** | **+0.521 (medium–large)** | 2.0e−10 | 3.6e−07 |
| chars | +0.564 | +0.828 | 1.5e−65 | 7.6e−16 |
| template hits | −0.664 | **−0.986 (very large)** | 2.5e−157 | 5.5e−25 |
| falsification words | −0.027 | −0.161 | 0.036 | 0.051 |

The template effect survives and strengthens. The character effect also strengthens. But tool calls reverse direction in magnitude: small at the step level, medium-to-large per turn.

The explanation is unglamorous. Averaging a mostly-binary variable across steps inside a turn compresses it toward 1 — a classic discretization artifact. Averaging across turns preserves the between-turn variation that the collapse actually consists of. The collapse is a property of turns becoming shorter and emptier, not of individual steps calling fewer tools.

So the honest statement is the awkward one: the effect size depends on the aggregation unit, and both numbers should be reported. Reporting only the turn-level figure would overstate the per-step behavioural change; reporting only the step-level figure would hide it.

### 4.4 The precursor signal

The `suspect` label turns out to be more useful than I expected. In the post period it covers 59.6% of steps while `collapse` covers 1.97%. Most steps enter the template-heavy state without fully collapsing.

Conditional on a suspect turn, the probability of a collapse within k turns:

| condition | ≤1 | ≤3 | ≤5 | ≤10 | ≤20 |
|---|---|---|---|---|---|
| suspect turn | 16.7% | 27.8% | 38.9% | 66.7% | **94.4%** |
| baseline | 6.5% | 10.5% | 15.3% | 27.4% | 44.4% |

![suspect to collapse](./figures/fig-suspect-to-collapse.png)

The gap is the point. Even after twenty turns the baseline stays below 45%, while a single suspect turn pushes the probability past 94%. Template density is the sensitive precursor; the failure rate lags it by many turns.

The run lengths are also informative. The first two collapse events are preceded by 16 and 11 consecutive suspect turns. After T126, every collapse is preceded by exactly one suspect turn. The incubation period shrinks until collapse happens on the next turn.

This is the strongest argument in the data that shrink is a process rather than a switch. It also suggests a cheap monitoring rule: watch the template rate, not the failure rate.

### 4.5 What the existing guard saw

Nothing.

`dsh-guard-repeat-output` 2.1.7 convicts when the duplicate share of a window reaches 0.80 and the distinct k-gram ratio falls below 0.30. Over the entire collapse window its log contains zero records. The maximum duplicate share I measured in this session is 0.44.

That is not a bug in the guard. It was built for a different failure: one phrase emitted 27,269 times, 1.37 million characters. Shrink-collapse produces no such signature because the text is getting shorter, not longer.

---

## 5. Discussion

### 5.1 Three timescales

The data separates into three processes that happen at different rates, and conflating them is the main interpretive risk in this session.

Text length declines continuously from turn 1. It is the slowest process and the least attributable to any single event.

Template formation starts at T86 and is abrupt. This is the only process that lines up cleanly with the persona insertion.

Collapse is rare until template density reaches roughly 18 per step, then becomes frequent. It is a downstream effect.

If I had only looked at the pre/post aggregate, I would have attributed all three to the persona. The band table is what prevents that mistake.

### 5.2 Why the step-level test was misleading

Pseudo-replication is a familiar problem, but the interesting part here is that it interacted with discretisation.

With a continuous variable, aggregating to a coarser unit reduces n and widens confidence intervals, but the point estimate usually stays put. With a variable that is binary for most observations, the coarser-unit mean carries information the finer-unit median throws away. The median of a mostly-one indicator is one, before and after, regardless of how much the mean moved.

I would not have caught this if I had only reported p-values. The effect size is what exposed it.

### 5.3 What this suggests for monitoring

If the mechanism hypothesis is right — template accumulation eventually contaminating the step-level decision about whether work was done — then the observable to monitor is the template rate, not the failure count.

The conversion numbers support a concrete threshold: once a turn is template-heavy, the probability of collapse within twenty turns is 94%. That is enough lead time to intervene, and the intervention need not be sophisticated. In a companion implementation I use a notice that demands one real tool call, on the grounds that telling the model to "be more careful" is unverifiable and, per the self-correction literature, often counterproductive.

### 5.4 Relation to existing work

Repetition in neural generation is well documented, but the documented shape is expansion: degenerate loops that grow. Text degeneration under greedy decoding, unlikelihood training to suppress repetition, and the guard I tested all assume the output gets longer.

The failure here is the opposite. I propose calling the two shapes **Expansion-collapse**
(the documented one: output grows and repeats until truncated) and **Shrink-collapse**
(the one observed here: output contracts toward template while assertion density holds).
The naming matters because the two require different detectors; a threshold tuned for
one is blind to the other, as Section 4.5 shows with a concrete number.

The closest relatives in the literature are not about repetition at all: self-correction without external feedback degrading reasoning, chain-of-thought that rationalises rather than reports, sycophancy toward user framing, and calibration that only appears when explicitly elicited. All four describe a model that produces plausible text disconnected from ground truth. Shrink-collapse is that disconnection measured over time.

---

## 6. Limitations

This is one session. It establishes that the pattern occurred and gives exact definitions for it. It does not establish prevalence, and no rate should be quoted without qualification.

The persona insertion is confounded with time and context length. The session also grew longer, compaction ran five times, and the task mix changed. Separating these requires a control arm that does not exist yet.

There is no inter-annotator agreement. The labels come from one fixed protocol applied by one annotator. A second annotator on 10% of the steps would be the minimum for a formal claim.

The signals are lexical and language-specific. The verb lists are Chinese and English; other languages would need their own.

The evidence metric counts path-like strings and numeric-with-unit patterns. A fabricated path raises it exactly like a real one. Nothing here distinguishes evidence from the appearance of evidence.

Finally, the direction of the effect for tool calls depends on the aggregation unit, as Section 4.3 shows. Any single number quoted from this dataset for that variable is incomplete.

---

## 7. Next step

The obvious experiment is a within-task A/B: same prompt sequence, same tool set, with and without the persona block. If the template rate diverges while the character trend does not, the persona hypothesis gains support. If both diverge together, the persona is a proxy for something else.

I intend to run that. Until then, this document should be cited as an observation, not as a mechanism.

---

## 8. Data and code

Everything is in one repository:

- `annotate-session.mjs` — produces the labels from the raw log
- `summarize-turns.mjs` — turn-level rollup
- `collapse-check.mjs` — the detector used in the companion implementation
- `annotations/steps.jsonl` — 1,384 annotated steps
- `session/session.v4.jsonl` — the decompressed log
- `docs/CONFOUNDERS.md` — the environment and its confounds
- `analysis/` — the statistics and the figure in this report

The session log contains only my own prompts and model output. Paths are retained because the claims depend on them; no credentials or third-party personal data are present, which was checked by scanning every file in the package.

---

## Appendix A. Annotation rules, verbatim

**Action verbs** (counted in reasoning only):
检查, 查看, 搜索, 搜一下, grep, 读一下, 看一下, 验证一下, 运行一下, 执行一下, 调用一下, 排查, 定位, 确认一下, 试试

**Completion assertions** (counted in reasoning and text):
已完成, 成功了, 成功, 可用, 已就绪, 已修复, 已交付, 跑通, 一切正常, 没问题, 证明, 说明, 就是, 根本原因, 彻底, 完全

**Hedges:**
可能, 疑似, 未验证, 不确定, 推测, 假设, 待确认, 也许, 大概, 似乎, 没有验证, 未证实, 存疑

**Falsification language:**
不通, 行不通, 放弃, 证伪, 反例, 死路, 不可能, 走不通, 推翻, 假设不成立, 这条路, 错在

**Evidence markers:**
drive-letter paths, URLs, `exit code`, `HTTP nnn`, `sha256`, and number-plus-unit pairs (B, KB, MB, GB, ms, s, Hz, frames).

## Appendix B. Why the compressed session log needs a splitter

The compressed original of the session log (`session.v4.jsonl.zstd`, 12.7 MB) is
5,990 concatenated zstd frames. A single call to `zlib.zstdDecompressSync` returns
only the first frame — 192 bytes of session header. This cost me an hour and is
worth writing down for anyone who obtains the compressed form elsewhere.

**That file is not shipped with this dataset.** During the session a configuration
dump printed a live `DEEPSEEK_API_KEY`, and the value landed in the log. The
compressed original still carries it, and re-compressing would change the bytes
without removing the secret. The plain-text log in `session/` is the redacted one:
a single substitution of the key for `sk-***REDACTED***`, touching a configuration
listing rather than a reasoning step, so no annotation or statistic in this report
changes.