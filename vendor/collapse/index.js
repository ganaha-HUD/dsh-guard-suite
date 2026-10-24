/**
 * dsh-guard-collapse — host-side guard for SHRINK-collapse.
 *
 * ## The failure this exists for
 *
 * dsh-guard-repeat-output catches EXPANSION collapse: one phrase emitted 27,269
 * times. This plugin catches the opposite shape, measured on a real 137-turn
 * session (2026-10-24):
 *
 *   | metric            | first 36 turns | last 12 turns |
 *   |-------------------|----------------|---------------|
 *   | tool calls / turn |          10.31 |          1.25 |
 *   | chars / turn      |          9,879 |         1,527 |
 *   | evidence / kchar  |           4.34 |          2.40 |
 *   | assertions / kchar|           1.12 |          1.20 |
 *
 * The text got SHORTER and the assertions stayed LEVEL while actions vanished.
 * A repetition detector is blind to that by construction: nothing repeats an
 * unusual number of times, there is simply less and less doing.
 *
 * The cleanest single case: a turn where the user asked "check whether the
 * anti-collapse plugin is still active" and the model wrote `grep` five times in
 * reasoning, called nothing, emitted no prose, and finished in 3 seconds. That
 * step is EXACTLY the shape `SIMULATED-ACTION` names.
 *
 * ## What it does
 *
 * 1. DETECT — `agent/pre-step` receives the full outgoing message list, so the
 *    most recent assistant message's tool-call count is readable without an
 *    event bus. Ratios are computed over a rolling window of steps.
 * 2. INTERVENE — on conviction, one short imperative notice is prepended to the
 *    next step's messages. It does not ask the model to reflect (see below); it
 *    demands a specific action type.
 * 3. REPAIR — `/collapse-repair` shadows already-persisted empty steps so they
 *    stop priming the next one. `/collapse-report` prints the measurements.
 *
 * ## Why it does not ask the model to "reflect"
 *
 * Measured literature: without external feedback, LLM self-correction degrades
 * reasoning (Huang et al., 2310.01798), and chain-of-thought is often
 * post-hoc rationalisation rather than the real cause (Turpin et al., 2305.04388).
 * So the intervention never says "be more careful". It says "call a tool now",
 * which is externally checkable.
 *
 * ## Bounded blast radius
 *
 * At most `maxNoticesPerTurn` notices per turn. Every conviction is one JSON
 * line in the log. Repair never touches a message that owns tool calls (its
 * tool results would be orphaned), and never deletes: the append-only log keeps
 * every original byte.
 *
 * @module dsh-guard-collapse
 */

import { homedir } from "node:os";
import { dirname, isAbsolute, join, resolve, win32 } from "node:path";
import { analyzeAssistantMessage, lastAssistant, evaluateWindow, noticeText } from "./lib/analyze.js";
import { findCollapsedMessages, repairNote, evidenceGaps } from "./lib/repair.js";

export const name = "guard-collapse";

const SOURCE_PLUGIN = "dsh-guard-collapse";
const SOURCE_KIND = `plugin:${SOURCE_PLUGIN}`;

export const DEFAULTS = Object.freeze({
  /** How many recent steps the ratio window covers. */
  windowSteps: 6,
  /** Below this many characters in the window, ratios are too noisy to act on. */
  minWindowChars: 600,
  /** Action words in reasoning with zero tool calls: how many before convicting. */
  simulatedActionWords: 3,
  /** Consecutive tool-call-free steps before THINK-ONLY fires. */
  thinkOnlyStreak: 3,
  /** Assertions/(evidence+uncertainty) above which the step is pseudo-certain. */
  pseudoCertainty: 0.90,
  /** Whether to warn when a window of active work contains no falsification language. */
  requireFalsification: false,
  /** Notices injected per turn, hard cap. */
  maxNoticesPerTurn: 2,
  /** Evidence-backed assertions required before a turn may count as verified (report only). */
  reportTailSteps: 12,
  /** A THINK-ONLY step at least this long is worth repairing. */
  thinkOnlyRepairChars: 300,
  /** Model scope, substring match on the id. Empty = all models. */
  modelIncludes: Object.freeze(["deepseek"]),
  /** JSONL diagnostics. Relative paths resolve under $DSH_HOME. */
  logPath: "logs/dsh-guard-collapse.log",
  /** Register /collapse-repair and /collapse-report. */
  commands: true,
  /** Observe-only mode: log convictions but never inject a notice. */
  observeOnly: false,
});

function expandPath(value) {
  if (value === null || value === undefined) return null;
  const raw = String(value).trim();
  if (raw.length === 0) return null;
  if (raw === "~") return homedir();
  if (raw.startsWith("~/") || raw.startsWith("~\\")) return join(homedir(), raw.slice(2));
  if (/^[A-Za-z]:[\\/]/.test(raw)) return win32.normalize(raw);
  if (isAbsolute(raw)) return raw;
  const home = process.env.DSH_HOME ? resolve(process.env.DSH_HOME) : join(homedir(), ".dsh");
  return resolve(home, raw);
}

export function resolveConfig(raw) {
  const input = raw ?? {};
  const cfg = { ...DEFAULTS, ...input };
  cfg.windowSteps = Math.max(1, Number(cfg.windowSteps) || DEFAULTS.windowSteps);
  cfg.minWindowChars = Math.max(0, Number(cfg.minWindowChars) || DEFAULTS.minWindowChars);
  cfg.simulatedActionWords = Math.max(1, Number(cfg.simulatedActionWords) || DEFAULTS.simulatedActionWords);
  cfg.thinkOnlyStreak = Math.max(1, Number(cfg.thinkOnlyStreak) || DEFAULTS.thinkOnlyStreak);
  cfg.maxNoticesPerTurn = Math.max(0, Number(cfg.maxNoticesPerTurn) || 0);
  cfg.thinkOnlyRepairChars = Math.max(0, Number(cfg.thinkOnlyRepairChars) || 0);
  cfg.logPath = expandPath(cfg.logPath);
  cfg.modelIncludes = Array.isArray(cfg.modelIncludes) ? cfg.modelIncludes : DEFAULTS.modelIncludes;
  cfg.pseudoCertainty = Number(cfg.pseudoCertainty);
  return cfg;
}

function createNotice(text, summary) {
  return {
    id: globalThis.crypto.randomUUID(),
    role: "user",
    content: [{ type: "text", text }],
    source: { kind: SOURCE_KIND, form: "notice", summary },
  };
}

function isOurs(message) {
  return message?.source?.kind === SOURCE_KIND;
}

/** True for this plugin's notices AND any sibling dsh-guard-* notice. */
function isSiblingNotice(message) {
  const kind = String(message?.source?.kind ?? "");
  return isOurs(message) || kind.startsWith("plugin:dsh-guard-");
}

async function appendRecord(logPath, record) {
  if (logPath === null) return;
  try {
    const { mkdir, appendFile } = await import("node:fs/promises");
    await mkdir(dirname(logPath), { recursive: true });
    await appendFile(logPath, JSON.stringify(record) + "\n", "utf8");
  } catch {
    // Diagnostics must never become a control path.
  }
}

export function apply(ctx, rawConfig) {
  const cfg = resolveConfig(rawConfig);
  const modelIncludes = cfg.modelIncludes.map(s => String(s).trim().toLowerCase()).filter(Boolean);
  const states = new WeakMap();

  function inScope(model) {
    if (modelIncludes.length === 0) return true;
    const id = String(model ?? "").trim().toLowerCase();
    if (id.length === 0) return false;
    return modelIncludes.some(p => id.includes(p));
  }

  function stateFor(agent) {
    let s = states.get(agent);
    if (s === undefined) {
      s = { window: [], seen: new Set(), turn: null, notices: 0, fired: new Set() };
      states.set(agent, s);
    }
    return s;
  }

  function log(record) {
    void appendRecord(cfg.logPath, { time: new Date().toISOString(), ...record });
  }

  ctx.on("agent/pre-step", async ({ agent, messages, turn }, next) => {
    const state = stateFor(agent);
    if (state.turn !== turn) {
      state.turn = turn;
      state.notices = 0;
    }

    // Fresh human input is new information; it deserves a clean notice budget.
    if (Array.isArray(messages) && messages.some(m => m?.source?.kind === "user")) state.notices = 0;

    const last = lastAssistant(messages);
    let verdict = null;
    if (last && !state.seen.has(last.id)) {
      state.seen.add(last.id);
      const metrics = analyzeAssistantMessage(last);
      state.window.push(metrics);
      if (state.window.length > cfg.windowSteps * 3) state.window = state.window.slice(-cfg.windowSteps * 3);
      verdict = evaluateWindow(state.window, cfg);
      if (verdict) {
        log({
          event: "collapse-detected",
          sessionId: String(agent.id ?? ""),
          turn,
          kind: verdict.kind,
          detail: verdict.detail,
          toolCalls: metrics.toolCalls,
          chars: metrics.chars,
          actionWords: metrics.actionWords,
        });
      }
    }

    const decision = await next();
    if (verdict === null || decision.kind !== "enter") return decision;
    // Ratio-only verdicts are logged and reported but never interrupt: measured
    // false-positive rate on the calibration session was 166/1384 steps, which
    // would have made the notice channel noise. Only structurally provable
    // signals (simulated action, think-only) are allowed to inject.
    if (verdict.severity !== "intervene") return decision;
    if (cfg.observeOnly) return decision;
    if (state.notices >= cfg.maxNoticesPerTurn) return decision;
    // Interop with sibling guards: if any dsh-guard-* notice is already in this
    // step (repeat-output''s wrap-up continuation, or our own from a prior pass),
    // do not stack a second instruction. Measured: without this rule two guards
    // put 2 notices on one step, which reads as contradictory orders.
    if (decision.messages.some(isSiblingNotice)) return decision;

    const key = `${turn}:${verdict.kind}`;
    if (state.fired.has(key)) return decision;
    state.fired.add(key);
    state.notices += 1;

    log({ event: "collapse-notice", turn, kind: verdict.kind, budgetUsed: state.notices });

    return {
      ...decision,
      messages: [
        createNotice(noticeText(verdict), `collapse-guard: ${verdict.kind} at turn ${turn}`),
        ...decision.messages,
      ],
    };
  });

  async function readSession(invocation) {
    const sessionQuery = typeof ctx.get === "function" ? ctx.get("sessionQuery") : undefined;
    if (sessionQuery === undefined) return { error: `${name}: sessionQuery service is not mounted` };
    const session = invocation?.agent?.session;
    if (session === undefined) return { error: `${name}: no session on the invoking agent` };
    const snapshot = await sessionQuery.readSession(session.id);
    return { session, snapshot };
  }

  async function runReport(invocation) {
    const got = await readSession(invocation);
    if (got.error) return { kind: "error", text: got.error };
    const { snapshot } = got;
    const assistants = snapshot.events.filter(e => e?.type === "assistant/message");
    const tail = assistants.slice(-cfg.reportTailSteps);
    const metrics = tail.map(e => analyzeAssistantMessage(e.data?.message));
    const chars = metrics.reduce((a, m) => a + m.chars, 0) || 1;
    const tools = metrics.reduce((a, m) => a + m.toolCalls, 0);
    const evidence = metrics.reduce((a, m) => a + m.evidenceMarks, 0);
    const asserts = metrics.reduce((a, m) => a + m.assertWords, 0);
    const unsure = metrics.reduce((a, m) => a + m.unsureWords, 0);
    const simulated = metrics.filter(m => m.simulated).length;
    const empty = metrics.filter(m => m.toolCalls === 0).length;
    const gaps = evidenceGaps(snapshot.events, cfg.reportTailSteps);

    const lines = [
      `${name}: last ${tail.length} steps of this session`,
      `- tools ${tools} (${(tools / Math.max(1, tail.length)).toFixed(2)}/step), zero-tool steps ${empty}`,
      `- chars ${chars}, evidence ${(evidence / (chars / 1000)).toFixed(2)}/kchar, assertions ${(asserts / (chars / 1000)).toFixed(2)}/kchar`,
      `- pseudo-certainty ${(asserts / (1 + evidence + unsure)).toFixed(2)} (lower is better)`,
      `- simulated-execution steps ${simulated}`,
    ];
    if (gaps.length > 0) {
      lines.push(`- unverified assertions in ${gaps.length} step(s): ` + gaps.slice(-5).map(g => `T${g.turn}/s${g.step}(${g.assertions} assert, ${g.evidence} evidence)`).join(", "));
    }
    return { kind: "success", text: lines.join("\n") };
  }

  async function runRepair(invocation) {
    const got = await readSession(invocation);
    if (got.error) return { kind: "error", text: got.error };
    const { session, snapshot } = got;
    const found = findCollapsedMessages(snapshot.events, cfg);
    if (found.length === 0) return { kind: "success", text: `${name}: no collapsed steps found in this session.` };

    const surface = new Set(session.surface?.nodes ?? []);
    let replaced = 0;
    let skippedOffSurface = 0;
    let removedChars = 0;
    for (const entry of found) {
      if (!surface.has(entry.seq)) { skippedOffSurface += 1; continue; }
      try {
        session.append("user/message", createNotice(repairNote(entry), `collapse-guard repair: ${entry.reason}`), {
          surfaceOp: { op: "replace", startSeq: entry.seq, endSeq: entry.seq },
          sourceEventSeqs: [entry.seq],
        });
        replaced += 1;
        removedChars += entry.chars;
        log({ event: "collapse-repair", sessionId: session.id, seq: entry.seq, turn: entry.turn, reason: entry.reason, chars: entry.chars });
      } catch (error) {
        ctx.logger?.warn?.(`${name}: repair failed for seq ${entry.seq}: ${String(error)}`);
      }
    }
    const parts = [
      `${name}: scanned ${snapshot.events.length} events, found ${found.length} empty step(s).`,
      `Replaced ${replaced} (${removedChars} chars) on the model-visible surface.`,
    ];
    if (skippedOffSurface > 0) parts.push(`Skipped ${skippedOffSurface} already shadowed.`);
    parts.push("Original bytes remain in the append-only log.");
    return { kind: "success", text: parts.join(" ") };
  }

  if (cfg.commands) {
    if (typeof ctx.inject !== "function") {
      ctx.logger?.info?.(`${name}: ctx.inject unavailable; commands not registered`);
    } else {
      ctx.inject(["commands"], commandCtx => {
        commandCtx.commands.register({
          name: "collapse-report",
          description: "Show action/evidence/assertion ratios for the recent steps of this session",
          handler: runReport,
        });
        commandCtx.commands.register({
          name: "collapse-repair",
          description: "Remove already-persisted empty steps (simulated actions) so they stop priming the next one",
          handler: runRepair,
        });
        ctx.logger?.info?.(`${name}: /collapse-report and /collapse-repair registered`);
      });
    }
  }

  console.log(`[${name}] active (window=${cfg.windowSteps} steps, observeOnly=${cfg.observeOnly}, logPath=${cfg.logPath ?? "null"})`);
}