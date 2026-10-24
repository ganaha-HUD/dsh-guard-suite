// Retroactive repair for sessions that already collapsed in the SHRINK direction.
//
// WHY THIS IS A DIFFERENT REPAIR THAN /guard-cleanup
// /guard-cleanup removes enormous degenerate blocks (100k+ chars of one phrase).
// The shrink collapse leaves the opposite residue: short, plausible,
// confident-looking steps that did nothing. They are small enough to survive
// every length-based filter, and they are exactly what primes the next step to
// do nothing as well. Removing them lowers the "doing nothing is normal" prior.

import { analyzeAssistantMessage } from "./analyze.js";

/**
 * Find assistant messages that claimed action but emitted no tool call.
 *
 * @param {readonly object[]} events - contiguous session events.
 * @param {object} thresholds - resolved config.
 * @returns {Array<{seq, turn, step, reason, chars, actionWords}>} oldest first.
 */
export function findCollapsedMessages(events, thresholds) {
  const found = [];
  for (const event of events) {
    if (event?.type !== "assistant/message") continue;
    const message = event.data?.message;
    if (!message) continue;
    const m = analyzeAssistantMessage(message);
    if (m.toolCalls > 0) continue; // never shadow a message that owns tool results
    if (m.simulated) {
      found.push({
        seq: event.seq, turn: event.data.turn, step: event.data.step,
        reason: "SIMULATED-ACTION", chars: m.chars, actionWords: m.actionWords,
      });
    } else if (m.thinkOnly && m.reasoningChars >= thresholds.thinkOnlyRepairChars) {
      found.push({
        seq: event.seq, turn: event.data.turn, step: event.data.step,
        reason: "THINK-ONLY", chars: m.chars, actionWords: m.actionWords,
      });
    }
  }
  return found;
}

/** Replacement text that keeps the turn index but refuses to replay the empty step. */
export function repairNote(entry) {
  if (entry.reason === "SIMULATED-ACTION") {
    return [
      "[collapse-guard] This step was removed: it described actions in reasoning "
      + `(turn ${entry.turn}, step ${entry.step}, ${entry.actionWords} action words) `
      + "but called no tool and produced no result.",
      "Nothing was verified here. Do not treat this step as done work; re-do it with a real call.",
    ].join("\n");
  }
  return [
    "[collapse-guard] This step was removed: it produced "
    + `${entry.chars} characters of reasoning at turn ${entry.turn}, step ${entry.step} `
    + "with neither an answer nor a tool call.",
    "Treat the surrounding task as still open.",
  ].join("\n");
}

/**
 * Summarise unverified claims in the tail of a session, for the repair report.
 * Heuristic on purpose: it lists candidates for a human to check, never asserts they are wrong.
 */
export function evidenceGaps(events, tailSteps = 12) {
  const assistants = events.filter(e => e?.type === "assistant/message").slice(-tailSteps);
  const gaps = [];
  for (const event of assistants) {
    const m = analyzeAssistantMessage(event.data?.message);
    if (m.assertWords === 0) continue;
    if (m.evidenceMarks >= m.assertWords) continue;
    gaps.push({
      turn: event.data?.turn,
      step: event.data?.step,
      assertions: m.assertWords,
      evidence: m.evidenceMarks,
      toolCalls: m.toolCalls,
    });
  }
  return gaps;
}