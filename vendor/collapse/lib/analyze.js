// Pure signal extraction for shrink-collapse detection.
// No DSH imports, no I/O: everything here is testable offline against a session log.

/** Verbs that imply an ACTION was taken. Used to catch simulated execution. */
export const ACTION_WORDS = /检查|查看|搜索|搜一下|grep|读一下|看一下|验证一下|运行一下|执行一下|调用一下|排查|定位|确认一下|试试/gi;

/** Words that assert a finished, verified state. */
export const ASSERT_WORDS = /已完成|成功了|成功|可用|已就绪|已修复|已交付|跑通|一切正常|没问题|证明|说明|就是|根本原因|彻底|完全/g;

/** Words that admit uncertainty. Their disappearance is itself a signal. */
export const UNSURE_WORDS = /可能|疑似|未验证|不确定|推测|假设|待确认|也许|大概|似乎|没有验证|未证实|存疑/g;

/** Concrete, replayable evidence markers. */
export const EVIDENCE_MARKS = /[A-Za-z]:[\\/]|https?:\/\/|exit code|HTTP\s*\d{3}|sha256|\b\d+(\.\d+)?\s*(B|KB|MB|GB|ms|s|Hz|frames)\b|[0-9a-f]{16,}/gi;

/** Language that questions the current hypothesis. Its absence predicts coherence collapse. */
export const FALSIFY_WORDS = /不通|行不通|放弃|证伪|反例|死路|不可能|走不通|推翻|假设不成立|这条路|错在/g;

const count = (re, text) => (text.match(re) || []).length;

function textOf(blocks, type) {
  if (!Array.isArray(blocks)) return "";
  return blocks.filter(b => b?.type === type && typeof b.text === "string").map(b => b.text).join("\n");
}

/**
 * Measure one assistant message.
 *
 * `toolCalls` is the load-bearing field: a step that claims work but emitted no
 * tool-call block did not do the work, however fluent its reasoning looked.
 */
export function analyzeAssistantMessage(message) {
  const blocks = message?.content;
  const reasoning = textOf(blocks, "reasoning");
  const text = textOf(blocks, "text");
  const toolCalls = Array.isArray(blocks) ? blocks.filter(b => b?.type === "tool-call").length : 0;
  const all = reasoning + "\n" + text;
  const actionWords = count(ACTION_WORDS, reasoning); // reasoning only: that is where simulation happens
  const assertWords = count(ASSERT_WORDS, all);
  const unsureWords = count(UNSURE_WORDS, all);
  const evidenceMarks = count(EVIDENCE_MARKS, all);
  const falsifyWords = count(FALSIFY_WORDS, all);
  const chars = all.length;
  return {
    toolCalls,
    reasoningChars: reasoning.length,
    textChars: text.length,
    chars,
    actionWords,
    assertWords,
    unsureWords,
    evidenceMarks,
    falsifyWords,
    pseudoCertainty: +(assertWords / (1 + evidenceMarks + unsureWords)).toFixed(3),
    simulated: actionWords >= 3 && toolCalls === 0 && reasoning.length >= 120,
    thinkOnly: toolCalls === 0 && text.length < 80 && reasoning.length >= 300,
    silent: chars === 0 && toolCalls === 0,
  };
}

/** Which assistant message is the most recent one in an outgoing context. */
export function lastAssistant(messages) {
  if (!Array.isArray(messages)) return undefined;
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    if (messages[i]?.role === "assistant") return messages[i];
  }
  return undefined;
}

/**
 * Judge the trailing window of steps.
 *
 * Deliberately ratio-based: absolute length is not a symptom (short answers are
 * normal), but "actions fell away while assertions stayed" is.
 */
export function evaluateWindow(window, thresholds) {
  if (!Array.isArray(window) || window.length === 0) return null;
  const recent = window.slice(-thresholds.windowSteps);
  const last = recent[recent.length - 1];

  // 1. Simulated execution: the single highest-precision signal.
  if (last.simulated && last.actionWords >= thresholds.simulatedActionWords) {
    return {
      kind: "SIMULATED-ACTION",
      severity: "intervene",
      detail: `reasoning mentions ${last.actionWords} action words but emitted 0 tool calls`,
      actionWords: last.actionWords,
      toolCalls: 0,
    };
  }

  // 2. Think-only: reasoning but neither prose nor action.
  if (last.thinkOnly && recent.filter(m => m.toolCalls === 0).length >= thresholds.thinkOnlyStreak) {
    return {
      kind: "THINK-ONLY",
      severity: "intervene",
      detail: `${recent.filter(m => m.toolCalls === 0).length} consecutive steps with no tool call and no visible answer`,
      steps: recent.filter(m => m.toolCalls === 0).length,
    };
  }

  const chars = recent.reduce((a, m) => a + m.chars, 0);
  if (chars < thresholds.minWindowChars) return null;
  const kChars = chars / 1000;
  const tools = recent.reduce((a, m) => a + m.toolCalls, 0);
  const evidence = recent.reduce((a, m) => a + m.evidenceMarks, 0);
  const asserts = recent.reduce((a, m) => a + m.assertWords, 0);
  const unsure = recent.reduce((a, m) => a + m.unsureWords, 0);
  const falsify = recent.reduce((a, m) => a + m.falsifyWords, 0);
  const pseudo = asserts / (1 + evidence + unsure);

  // 3. Action vacuum: work is claimed across the window but nothing was executed.
  if (tools === 0 && asserts >= 3) {
    return { kind: "ACTION-VACUUM", severity: "observe", detail: `${recent.length} steps, 0 tool calls, ${asserts} assertions`, assertions: asserts };
  }

  // 4. Pseudo-certainty: assertions outrun evidence and admitted uncertainty.
  if (pseudo >= thresholds.pseudoCertainty && asserts >= 6 && tools === 0) {
    return {
      kind: "PSEUDO-CERTAINTY",
      severity: "observe",
      detail: `assertions/(evidence+uncertainty) = ${pseudo.toFixed(2)} over ${recent.length} steps`,
      ratio: +pseudo.toFixed(2),
      evidenceDensity: +(evidence / kChars).toFixed(2),
    };
  }

  // 5. Coherence collapse: hypothesis questioning has stopped.
  if (thresholds.requireFalsification && falsify === 0 && recent.length >= thresholds.windowSteps && tools > 0) {
    return {
      kind: "NO-FALSIFICATION",
      severity: "observe",
      detail: `${recent.length} steps of active work with no falsification language`,
      steps: recent.length,
    };
  }
  return null;
}

/** The message injected ahead of the next step. Imperative, short, and unarguable. */
export function noticeText(verdict) {
  const head = {
    "SIMULATED-ACTION": `You described ${verdict.actionWords} actions in reasoning but actually called 0 tools.`,
    "THINK-ONLY": `The last ${verdict.steps} steps produced reasoning but no visible answer and no tool call.`,
    "ACTION-VACUUM": `${verdict.assertions} assertions were made with 0 tool calls behind them.`,
    "PSEUDO-CERTAINTY": `Assertion-to-evidence ratio is ${verdict.ratio} (evidence density ${verdict.evidenceDensity}/kchar).`,
    "NO-FALSIFICATION": `No step in the last ${verdict.steps} questioned its own hypothesis.`,
  }[verdict.kind] || verdict.detail;

  return [
    "[collapse-guard] " + head,
    "",
    "Thinking about a step is not performing it. For THIS step:",
    "1. Make at least one real tool call and put its result into the answer.",
    "2. Do not use \"OK / (output) / let me check\" as a substitute for the call.",
    "3. Every finished claim needs evidence: path+bytes, HTTP status, or exit code.",
    "4. If something is unverified, write UNVERIFIED. Do not fill the gap with confidence.",
  ].join("\n");
}