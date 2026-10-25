# Experimental Context and Confounders

> 中文版：[`CONFOUNDERS.zh-CN.md`](./CONFOUNDERS.zh-CN.md)

This dataset is not a clean-room model evaluation. It is one operator's real
working session, with rules, a persona and tooling injected while it ran. Anyone
drawing conclusions from it must account for the following.

## 1. Runtime

| item | value |
|---|---|
| Host | DSH desktop (Electron), `deepseek-flash` via `deepseek-official` |
| Context injection | `AGENTS.md` is re-injected **every turn** (global layer) |
| File policy | `danger-full-access` for most of the session |
| Approvals | disabled |

## 2. Rule files in force (`context/policy/`)

| file | role |
|---|---|
| `output-storage-policy.md` + `storage-policy.json` | where artifacts must be written (six category dirs, per-conversation subdir, ASCII naming) |
| `ai-tool-policy.md` + `ai-tools.json` | mandatory invocation rules for the 8 local vision/AI tools |
| `lceda-eda-policy.md` + `lceda-eda.json` | EDA automation rules (not exercised in the collapse window) |
| `memory-points.md` | cross-session "lessons learned" index, referenced by the global rules |
| `conversation-registry.json` | conversation metadata |

**These rules change tool-call patterns by design**: the storage policy forces a
`New-ConversationWorkspace.ps1` call and category-specific write paths, which is
one reason tool-call counts per turn are high in the early session.

## 3. Persona injection at turn 86 — the main confounder

At **T86 (2026-10-21 07:05)**, the operator injected a 1,405-character character
sheet ("DSH · 大肥鱼"), reproduced verbatim in
[`context/persona-injection-turn86.md`](../context/persona-injection-turn86.md).

Before/after system prompt snapshots are in `context/agents-md/`:

| snapshot | size | meaning |
|---|---|---|
| `before-persona-20261021-070551.md` | 10,859 B | T1–T85: no persona |
| `after-persona-20261021-130248.md` | 14,546 B | T86 onward: persona present |

### What this means for the labels

- **All 10 `collapse` steps occur after T86** (turns 112, 113, 125, 127, 128, 130,
  132, 134, 136 — plus one earlier at T27).
- **T27 is a collapse BEFORE the persona existed.** Therefore the persona is
  **not necessary** for shrink-collapse to occur.
- Whether it is a contributing factor cannot be established from one session.
  It is a plausible accelerator (more role-play, more "thinking aloud", less
  action), but this dataset cannot separate that from the growing context.

**Do not claim "the persona caused the collapse."** The honest statement is:
*the collapse window overlaps with the persona period, and one collapse predates it.*

## 4. Tools available

`context/tools/` contains the five helper scripts the rules require
(workspace creation, policy install, self-check, rule backup, README template).
Their existence raises the baseline tool-call rate; the shrink collapse is
visible *despite* them, not because tools were unavailable.

## 5. Other context that changed mid-session

- **Context compaction ran 5 times** (T29, T46, T62, T78, T109), each shadowing
  277k–412k tokens. After T109 the model reasoned over summaries, not raw turns.
- **`dsh-guard-repeat-output` v2.1.7 was installed and active** from 2026-10-20;
  it logged zero convictions during the collapse (see README).
- **Local tool policy** required running local vision tools on-device; this does
  not affect the collapse but shapes the tool mix.

## 6. How to control for this

1. Re-run the same task without the persona block, with the same rules — this
   isolates the persona effect.
2. Re-run with the persona but without the storage rules — isolates the rule effect.
3. Compare pre/post T86 windows within this session (already separable via
   `annotations/steps.csv` filtered by `turn <= 85` vs `turn >= 86`).

## 7. Privacy and disclosure

- All paths (`E:\Deepseek`, `D:\AI_file`, `C:\Users\...`) are the operator's own
  environment and are retained because they are needed to verify claims.
- **No credentials, tokens, API keys or third-party personal data** are present;
  verified by regex scan over every file in the package.
- The persona text is operator-authored role-play, not third-party IP.
- Conversation content is the operator's own prompts plus model output.