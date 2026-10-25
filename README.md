># Delayed Collapse in an LLM Tool-Use Session

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23632998.svg)](https://doi.org/10.5281/zenodo.23632998)

> **This repository has three parts.**
>
> | path | what it is |
> |---|---|
> | `index.js`, `vendor/`, `cordis.patch.yml` | the DSH guard plugin (documented below) |
> | [`collapse-dataset/`](./collapse-dataset/) | annotated dataset: 137 turns, 1,384 assistant steps, full log, experimental context |
> | [`paper/`](./paper/) | technical report — *Delayed Collapse in an LLM Tool-Use Session* (EN / ZH, md + docx + html) |
>
> Start with [`collapse-dataset/docs/README.md`](./collapse-dataset/docs/README.md) if you came for the data,
> or with [`paper/report-v1.md`](./paper/report-v1.md) if you came for the write-up.

---
# dsh-guard-suite

Two collapse guards for [DSH](https://github.com/deepseek-ai) in one install: the
**expansion** collapse everyone knows, and the **shrink** collapse almost nothing
watches for.

---

## The two failure shapes

| | **Expansion** | **Shrink** |
|---|---|---|
| Looks like | one phrase emitted 27,269 times, 1.37M chars of scroll | text gets shorter, tool calls vanish, assertions stay level |
| Why it is hard | obvious once it happens | nothing repeats, so every length/repetition detector is blind |
| Engine | `vendor/repeat` — `dsh-guard-repeat-output` 2.1.7, audited and patched | `vendor/collapse` — `dsh-guard-collapse` 0.1.0 |

The shrink shape was measured on a real 137-turn session (2026-10-24):

| metric | first 36 turns | last 12 turns |
|---|---|---|
| tool calls / turn | 10.31 | **1.25** |
| chars / turn | 9,879 | **1,527** |
| evidence markers / kchar | 4.34 | **2.40** |
| assertions / kchar | 1.12 | **1.20** |

Actions fell 88%, text fell 85%, assertions did not move. The clearest single case:
a turn where the user asked "check whether the anti-collapse plugin is still
active" and the model wrote `grep` five times in reasoning, called nothing,
emitted no prose, and finished in 3 seconds.

---

## Signals

| Signal | Rule | Action |
|---|---|---|
| `SIMULATED-ACTION` | >=3 action verbs in reasoning, **0 tool-call blocks** | inject a notice |
| `THINK-ONLY` | >=3 consecutive steps with no prose and no tool call | inject a notice |
| `ACTION-VACUUM` | 0 tool calls with >=3 assertions in the window | log only |
| `PSEUDO-CERTAINTY` | assertions/(evidence+uncertainty) >= 0.90, 0 tool calls | log only |
| `NO-FALSIFICATION` | a working window with no "this path is wrong" language | log only (off) |

Only the first two interrupt. Calibrated on 1,384 real steps: ratio-based signals
produced 166 false positives, structural signals produced 0. A low-precision
signal on the notice channel is worse than no signal.

---

## Install

### Desktop app — local import (recommended)

1. Download the release tarball `dsh-guard-suite-0.1.1.tgz`
2. Settings -> Plugins -> local import -> pick the tarball
3. Restart DSH

### Manual

```powershell
node install.mjs --apply --replace-repeat
```

Then restart. `--replace-repeat` removes the standalone `dsh-guard-repeat-output`
from `dsh.profile.bundles`, because this package already vendors it — leaving both
enabled runs the repetition engine twice and keeps the **unpatched** copy in play.

### Verify

The startup `console.log` lines are not captured anywhere useful on the desktop
build, so verify by command presence:

```
/collapse-report    # ratios for the last 12 steps + unverified assertions
/collapse-repair    # shadow already-persisted empty steps
/guard-cleanup      # shadow already-persisted giant repetition blocks
```

If `/collapse-report` exists, the suite is loaded.

---

## What the intervention says

```
[collapse-guard] You described 5 actions in reasoning but actually called 0 tools.

Thinking about a step is not performing it. For THIS step:
1. Make at least one real tool call and put its result into the answer.
2. Do not use "OK / (output) / let me check" as a substitute for the call.
3. Every finished claim needs evidence: path+bytes, HTTP status, or exit code.
4. If something is unverified, write UNVERIFIED.
```

It never asks the model to reflect. Without external feedback, self-correction
degrades reasoning ([Huang et al., 2310.01798](https://arxiv.org/abs/2310.01798)),
and chain-of-thought is often post-hoc rationalisation
([Turpin et al., 2305.04388](https://arxiv.org/abs/2305.04388)). The intervention
demands an externally checkable action instead.

---

## Patches to the vendored engine

The vendored `dsh-guard-repeat-output` is **not** a verbatim copy. Four defects
were found by reading the source and driving its real seams:

| # | defect | effect |
|---|---|---|
| P1 | `maxTruncationsPerTurn` was dead config — the counter was initialised and reset, never incremented, never read | the documented per-turn continuation budget never existed |
| P2 | the `agent/pre-step` backstop did not consult that budget | even after P1, it put the continuation back |
| P3 | an out-of-scope model was skipped **silently** | "never fired" was indistinguishable from "never ran" |
| P4 | `maxTruncationsPerTurn: 0` was rejected by validation | the only way to disable it was an unrelated switch |

See [`PATCHES.md`](./PATCHES.md) for evidence, fix sites and regression tests.
Three known blind spots are documented there and deliberately **not** patched.

---

## Limits

1. Single-session, single-model calibration. Re-tune before trusting it elsewhere.
2. It catches "no evidence", not "fake evidence".
3. Sycophancy is only partly measurable.
4. Semantic repetition (different words, same claim) is out of scope by design.
5. The `text` channel is observe-only by default; enable it explicitly if you need it.

A smoke alarm, not a firefighter.

---

## License

MIT — see [`LICENSE`](./LICENSE).

This package vendors MIT-licensed third-party code. See
[`THIRD-PARTY-NOTICES.md`](./THIRD-PARTY-NOTICES.md); the upstream license is
retained unmodified at `vendor/repeat/LICENSE`.
---

## Related Work & Concept Overlap

After publishing the preprint, subsequent literature searches revealed highly relevant works that require acknowledgment and clarification of this report's scope:

*   **Training-time template collapse:** *RAGEN-2 (Wang et al., ICML 2026)* describes "template collapse" occurring during RL training, driven by low reward signal-to-noise ratios. This differs from the present report, which observes a similar contraction during *inference*, triggered by context dynamics (persona injection).
*   **Theoretical framing of agency collapse:** *Figurelli (2026)* (Zenodo: `10.5281/zenodo.18601688`) proposed the *Agency Collapse Hypothesis*, describing "state-claim failures". This overlaps conceptually with our observed "simulated execution". However, Figurelli provided a theoretical framework, whereas this report provides a fully annotated, step-by-step empirical quantification (1,384 steps).
*   **Incident-level vs. step-level analysis:** *arXiv `2606.14589`* provides a longitudinal taxonomy of "silent failures" in production agents. Its unit of analysis is the *incident*, whereas this report captures the *step-level temporal dynamics* (the delayed collapse structure).
*   **Persona injection impact:** *arXiv `2509.03730`* (*The Personality Illusion*) finds limited immediate behavioral impact from persona injection. This complements our findings: while immediate behavioral shifts may be minimal, this session demonstrates that persona injection can initiate a delayed, systemic degradation via template accumulation over multiple turns.

This report's primary contributions are: (1) **Quantifying the delayed temporal structure**; (2) highlighting the **step-level vs. turn-level effect size reversal** (Cliff's δ = 0.144 vs. 0.521); and (3) providing a **quantitative precursor signal** (94.4% probability of collapse within 20 turns after a `suspect` turn).
