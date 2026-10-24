/**
 * dsh-guard-suite — one install, both collapse directions.
 *
 * Why a suite and not a source merge:
 *   dsh-guard-repeat-output is a calibrated, production-verified plugin (v2.1.7,
 *   thresholds measured across 1,546 sessions). Rewriting it into another file
 *   would trade a maintained upstream for a local fork. Instead this package
 *   vendors both engines UNCHANGED under ./vendor and composes them in one
 *   apply, so there is one directory to install and still two upgradable parts.
 *
 * Division of labour:
 *   EXPANSION  (one phrase x27,269)      -> vendor/repeat, stream-level, cuts live
 *   SHRINK     (actions vanish, tone stays) -> vendor/collapse, step-level, injects
 *
 * Coexistence was measured, not assumed: with one host ctx both register cleanly
 * (llm/stream 1, agent/pre-step 2, three slash commands) and the collapse engine
 * skips its notice when a sibling dsh-guard-* notice is already on the step
 * (2 -> 2 instead of 2 -> 3). Without that rule the model received two
 * contradictory instructions in one step.
 *
 * @module dsh-guard-suite
 */
import { apply as applyRepeat, name as repeatName } from "./vendor/repeat/index.js";
import { apply as applyCollapse, name as collapseName } from "./vendor/collapse/index.js";

export const name = "guard-suite";

export const VENDORED = Object.freeze({
  "dsh-guard-repeat-output": "2.1.7+p4",
  "dsh-guard-collapse": "0.1.0",
});

export function apply(ctx, config) {
  const cfg = config ?? {};
  // Order matters: repeat is registered first so its stream wrapper is the
  // outermost one. collapse runs inside it and therefore sees the messages that
  // repeat has already admitted.
  applyRepeat(ctx, cfg.repeat ?? {});
  applyCollapse(ctx, cfg.collapse ?? {});
  console.log(`[${name}] active: ${repeatName}@${VENDORED["dsh-guard-repeat-output"]} + ${collapseName}@${VENDORED["dsh-guard-collapse"]}`);
}