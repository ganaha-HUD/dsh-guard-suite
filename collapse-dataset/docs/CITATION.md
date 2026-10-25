# Citation

If you use this dataset, please cite it as:

```bibtex
@dataset{dsh_collapse_2026,
  title  = {Session 3b54e160: A Single-Trajectory Dataset of Shrink-Collapse in an LLM Agent},
  author = {ganaha-HUD},
  year   = {2026},
  month  = {10},
  note   = {137 turns, 1,384 annotated assistant steps, 10 collapse events.
            Model: deepseek-flash. Includes full append-only log and all
            artifacts produced during the session.},
  url    = {https://github.com/ganaha-HUD/dsh-guard-suite}
}
```

## What to cite for each claim

| claim | cite |
|---|---|
| the shrink-collapse phenomenon | this dataset, `docs/METHOD.md` |
| expansion vs shrink distinction | this dataset, `docs/README.md` §Why this dataset exists |
| the guard blind spot (`0.80` vs `0.44`) | this dataset + `dsh-guard-repeat-output` v2.1.7 source (`outputs/data/`) |
| the intervention (TRACE gates) | `https://github.com/ganaha-HUD/dsh-guard-suite`, `PATCHES.md` |

## Scope statement

This is a **single trajectory**. It supports existence claims ("this failure mode
occurs and here is its exact shape"), not prevalence claims. Any rate, frequency
or cross-model statement requires additional sessions.

## Contact

Open an issue at https://github.com/ganaha-HUD/dsh-guard-suite for questions
about the annotation protocol or to request the raw pre-annotation features.