# v2-inference

Code and derived tables for the inference-time replication (October 2026): 64 sessions,
two models, a 2×2 design on persona presence and tool failure rate.

The write-up is a separate record. This directory holds what is needed to re-run the
analysis and to check the numbers.

---

## What is here

| Path | What it is |
|---|---|
| `detector/detect.mjs` | collapse-detector v3.0 — three layers of structural indicators (literal overlap, functional-word skeleton, behavioural counts), no word lists in the decision path |
| `detector/expected.json` | the ten reference cases with their expected values; `node detect.mjs --self-test` checks all 148 assertions |
| `collection/run_api_experiment.py` | the collection harness used for all 64 sessions; drives DeepSeek, MiMo or Kimi through a fixed 30-stage task script |
| `analysis/*.py` | metric computation, the two estimation levels (session ANOVA and turn-level GEE), permutation tests, ICC, the loop profile, and the PDF build |
| `tables/turnlevel.csv` | 3,840 rows, one per turn; the input to every turn-level model |
| `tables/anova3-records.csv` | 64 rows, one per session; the input to every session-level model |
| `analysis/anova3_fixed.py` | the corrected session-level ANOVA: recomputes Type III under both typ=2 and sum-to-zero typ=3 and asserts they agree |
| `analysis/check_truncation.py` | counts turns cut off by the five-step cap (285 of 3,840, all adverse) |
| `analysis/truncation_sensitivity.py` | refits the interaction with the truncated turns dropped |
| `analysis/perm_resid.py` | the interaction-only permutation: the null model is the full 2×2×2 minus the persona × regime column, its residuals are shuffled and added back; gives p = .013 / .018 |
| `analysis/perm_interaction.py` | **deprecated**: shuffles persona labels (destroying the main effect) and keeps a fixed cell coefficient; its p = .094 / .176 are retracted |
| `errata/` | the two errata and the review response for v2.1 |

## The raw logs

The 64 session logs (`.jsonl` plus the harness `.log`) are **not** in this repository.
They ship inside the Zenodo audit package for the V2 paper, together with a MANIFEST that
lists every claimed value and a `checksums.sha256`. The two CSVs here are the same ones
that package contains.

## Before you run anything

Every script hardcodes the author's local root. Change these first:

| Script | Constant | Should point at |
|---|---|---|
| `collection/run_api_experiment.py` | `EX` | the directory holding `persona-V1-T86.txt`, `tasks-staged-cn.jsonl`, `lang-lock-cn.txt`, `tools-*.json` |
| `collection/run_api_experiment.py` | `OUT_ROOT2` | where session files should be written |
| `analysis/build_turnlevel.py` | `BASE` | the directory holding `api2/` and `mimo/` (the raw logs) |
| `analysis/analyze_formal.py`, `permutation_test.py`, `anova3.py`, `loop_profile.py`, `l1_language_check.py`, `verify_*.py` | `ROOT` / `BASE` | the same directory, or the one holding the two CSVs |
| `analysis/md2pdf.py` | `--src`, `--outdir` | given on the command line; also expects headless Edge at the path in `EDGE` |

Formulas in the PDF are rendered with matplotlib mathtext in a STIX serif face; the
converter sets that explicitly, because the matplotlib default (DejaVu Sans) makes
identifiers like `tool_calls` look like code.

## How the adversity factor is coded

See [ENV_CODING.md](./ENV_CODING.md). In short: the design matrix carries
`C(adversity)[T.shun]`, so the indicator is `D = (env == "shun")`, and a positive
coefficient means the working regime has the higher outcome.

## Reproduction checkpoints

If a re-run disagrees with the paper, these are the values that should match first:

| Quantity | Value |
|---|---|
| sessions / turns | 64 / 3,840 |
| calls, DeepSeek A-shun / A-ni / B-shun / B-ni | 25.12 / 56.88 / 17.75 / 91.12 |
| calls, MiMo A-shun / A-ni / B-shun / B-ni | 24.88 / 93.25 / 48.62 / 168.50 |
| ICC(1), L1 / L2 / calls / zero_tool | 0.172 / 0.113 / 0.354 / 0.204 |
| effective n, same four | 345 / 502 / 176 / 295 |
| L1 model effect, turn-level GEE | +0.0904 (SE 0.0192, p = 2.5e-6) |
| L1 model effect, session ANOVA | F = 12.92, p = .0007, partial η² = .188 |
| zero-tool regime effect, GEE | +0.9233 (SE 0.3131, p = .0032), OR = 2.52 |

Two conventions matter when re-deriving these:

1. `calls` counts tool names **expanded** — a step that issues two calls contributes two.
2. Row 1 of `turnlevel.csv` carries `L1 = 0` by construction (no predecessor). Every
   published analysis keeps that row. Dropping it moves the GEE coefficient from
   +0.0904 to +0.0920, with the p value unchanged.

## A note on line endings

The two CSVs here are stored with LF. The copies inside the Zenodo package are CRLF, as
produced on Windows. The values are identical; only the byte-level checksum differs.

## Licence

Code: MIT, as the rest of this repository. The tables are released under CC BY 4.0.

## Corrections in v2.1 (29 October 2026)

`analysis/anova3.py` originally called `anova_lm(..., typ=3)` on treatment-coded factors.
That call does not return Type III sums of squares; on this balanced design it returned
values that were neither the reference-cell contrast nor the marginal one, and every
session-level F in v2.0 was wrong (the regime effect on the zero-tool share was 9.51,
not 97.06). The file now uses `typ=2`, which on a balanced design equals Type III.
`anova3_fixed.py` computes both routes and asserts they agree.

Three further defects are recorded in `errata/`: the sign of the persona coefficient,
the conflation of the turn-level `zero_tool` with the step-level `zero_ratio`, and the
disclosure of the five-step cap. See `errata/ERRATUM-v2.1-20261029.md`.

**Tag:** `v2.1.1` points at the commit that contains this note.

**Tag:** `v2.1.3` replaces `v2.1.2`. v2.1.2's `perm_resid.py` kept only the main effects in its null model, which let the other interactions leak into the residuals; v2.1.3 removes exactly the persona × regime column.
