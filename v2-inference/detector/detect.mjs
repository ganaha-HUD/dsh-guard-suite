#!/usr/bin/env node
// detect.mjs - collapse detector v3.0
//
// v3.0 changes (detector-workorder-v3.0.md): judgment moves from vocabulary to
// structure. Three layers are reported side by side, no single boolean:
//   L1 literal   - turn-level 3-gram repetition (merged from inter-turn.mjs)
//   L2 skeleton  - function-word (function-character) 2-gram Jaccard
//   L3 behavior  - tool-name sequence statistics (descriptive only)
// Rule A (ruleA_v1 / ruleA_strict) is KEPT for backward compatibility but is
// AUXILIARY: no conclusion may be based on it (summary.ruleA_role = "auxiliary").
//
// Node.js single file, ESM, no third-party deps.
//
// Usage:
//   node detect.mjs --input <session.jsonl> --source dsh|api|local --out <dir>
//   node detect.mjs --input-dir <dir>       --source dsh --out <dir>
//   node detect.mjs --self-test [--out <dir>] [--log <file>]

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

// ---------------------------------------------------------------- vocabulary
// Verbatim from the requirements doc. Do not add or remove words.
const ACTION_RE = /检查|查看|搜索|搜一下|grep|读一下|看一下|验证一下|运行一下|执行一下|调用一下|排查|定位|确认一下|试试/gi;
const DONE_RE = /已完成|完成了|成功了|成功|已就绪|已修复|已交付|跑通|一切正常|没问题|可用/g;

// R5: capability-negation words. Diagnostic only, never a judgment input.
const NEGATION_RE = /无法|不能|做不到|做不了|没有工具|未成功|没办法|不具备/g;

// R4: function characters. HARD-CODED on purpose (work order section 4.5):
// making this configurable would create a new tuning knob.
const FUNC_CHARS = new Set([..."的了着过是在有和与或但而因为所以如果就才还再又也很都只把被让给对我你他它这那些个不没未无已能会可应须将要该当从到于其此即"]);

// R4: L2 longest-run segmentation parameter. Fixed, NOT configurable and NOT a
// judgment threshold; L2 mean/median/max stay continuous quantities.
const L2_RUN_THRESHOLD = 0.6;

// R4: signature characters of UTF-8 bytes decoded as GBK.
const MOJIBAKE_RE = /[鎴銆鐨鏄鍙鏂]/g;

const SEG = new Intl.Segmenter("zh", { granularity: "word" });

// --------------------------------------------------------------- thresholds
// R7: defaults are byte-for-byte identical to v2.1 defaults.
const DEFAULT_THRESHOLDS = {
  ruleB_share: 0.12,
  ruleB_count: 15,
  ruleA_text_max: 200,
  ruleA_reasoning_min: 120,
  skeleton_k: 10,
  inter_k: 10,
  inter_threshold: 0.6,
  inter_run_min: 3,
};
const THRESHOLD_KEYS = Object.keys(DEFAULT_THRESHOLDS);

function fail(msg) {
  console.error("ERROR: " + msg);
  process.exit(2);
}

// Partial override: missing keys keep the defaults. Illegal values still exit 2.
function loadThresholds(file) {
  if (!file) return { ...DEFAULT_THRESHOLDS };
  let raw;
  try {
    raw = fs.readFileSync(file, "utf8");
  } catch (e) {
    fail("cannot read --thresholds file: " + e.message);
  }
  let obj;
  try {
    obj = JSON.parse(raw);
  } catch (e) {
    fail("invalid JSON in --thresholds: " + e.message);
  }
  if (!obj || typeof obj !== "object" || Array.isArray(obj)) {
    fail("--thresholds must be a JSON object");
  }
  for (const k of Object.keys(obj)) {
    if (!THRESHOLD_KEYS.includes(k)) {
      fail("unknown threshold key: " + k + " (allowed: " + THRESHOLD_KEYS.join(", ") + ")");
    }
  }
  const out = { ...DEFAULT_THRESHOLDS };
  for (const k of THRESHOLD_KEYS) {
    if (!(k in obj)) continue; // partial override: missing keys keep the defaults
    const v = obj[k];
    if (typeof v !== "number" || !Number.isFinite(v) || v < 0) {
      fail("threshold " + k + " must be a finite non-negative number, got " + JSON.stringify(v));
    }
    out[k] = v;
  }
  return out;
}

// --------------------------------------------------------------- utilities
function countMatches(re, s) {
  const m = String(s || "").match(re);
  return m ? m.length : 0;
}

function tokenize(s) {
  const out = [];
  for (const piece of SEG.segment(String(s || ""))) {
    if (!piece.isWordLike) continue;
    const t = piece.segment.toLowerCase();
    if (t.trim()) out.push(t);
  }
  return out;
}

// share is shown with a FOURTH decimal only where three decimals would
// misrepresent the true ratio (the .0005 boundary, e.g. 9/240 = 0.0375).
// Every other value keeps its published 3-decimal form.
function roundShare(x) {
  const y = Number(x) * 1000;
  const frac = Math.abs(y - Math.floor(y));
  return Number(Number(x).toFixed(Math.abs(frac - 0.5) < 1e-6 ? 4 : 3));
}

function formatShare(x) {
  const s = Number(Number(x).toFixed(4)).toFixed(4);
  return s.endsWith("0") ? s.slice(0, -1) : s;
}

function round3(x) {
  return Number(Number(x).toFixed(3));
}

function round2(x) {
  return Number(Number(x).toFixed(2));
}
// ------------------------------------------------------------------ readers
// Layer 1: read + normalize to [{turn, step, reasoning, text, tool_calls, tools}]
// R5: tool NAMES are collected in appearance order; one line with two tools
// contributes two entries to the global sequence.

function finalizeStepMap(map) {
  const steps = [...map.values()].map((e) => ({
    turn: e.turn,
    step: e.step,
    reasoning: e.reasoning.join("\n"),
    reasoning_chunks: e.reasoning_chunks,
    text: e.text.join("\n"),
    tool_calls: e.tool_calls,
    tools: e.tools,
  }));
  steps.sort((a, b) => (a.turn - b.turn) || (a.step - b.step));
  return steps;
}

function newStep(turn, step) {
  return { turn, step, reasoning: [], text: [], tool_calls: 0, reasoning_chunks: 0, tools: [] };
}

function pushToolNames(e, raw) {
  if (!raw || typeof raw !== "object") return;
  if (Array.isArray(raw.tools)) {
    for (const t of raw.tools) if (typeof t === "string" && t) e.tools.push(t);
  } else if (typeof raw.tool === "string" && raw.tool) {
    e.tools.push(raw.tool);
  }
}

// DSH session jsonl: {type, seq, time, data}
// - tool_calls = number of tool-call blocks inside assistant messages (NOT tool/call events)
// - never touch data.stream (huge raw chunk stream)
function readDsh(file) {
  const raw = fs.readFileSync(file, "utf8");
  const lines = raw.split("\n");
  const map = new Map();
  let curTurn = 0;
  let curStep = 0;
  let badLines = 0;
  let messageEvents = 0;
  let mojibake = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line || !line.trim()) continue; // blank line is a separator, not bad data
    let o;
    try {
      o = JSON.parse(line);
    } catch {
      badLines++;
      continue;
    }
    if (!o || typeof o !== "object") { badLines++; continue; }
    const d = o.data || {};

    if (o.type === "turn/start") {
      if (typeof d.turn === "number") curTurn = d.turn;
      continue;
    }
    if (o.type === "step/start") {
      if (typeof d.turn === "number") curTurn = d.turn;
      if (typeof d.step === "number") curStep = d.step;
      continue;
    }
    if (o.type !== "assistant/message") continue;
    messageEvents++;

    const turn = typeof d.turn === "number" ? d.turn : curTurn;
    const step = typeof d.step === "number" ? d.step : curStep;
    const key = turn + "\u0000" + step;
    let e = map.get(key);
    if (!e) { e = newStep(turn, step); map.set(key, e); }
    const blocks = d.message && Array.isArray(d.message.content) ? d.message.content : [];
    for (const b of blocks) {
      if (!b || typeof b !== "object") continue;
      if (b.type === "reasoning") {
        const txt = typeof b.text === "string" ? b.text : "";
        e.reasoning.push(txt);
        e.reasoning_chunks++;
        mojibake += countMatches(MOJIBAKE_RE, txt);
      } else if (b.type === "text") {
        const txt = typeof b.text === "string" ? b.text : "";
        e.text.push(txt);
        mojibake += countMatches(MOJIBAKE_RE, txt);
      } else if (b.type === "tool-call") {
        e.tool_calls++;
        if (typeof b.name === "string" && b.name) e.tools.push(b.name);
      }
    }
  }

  return { steps: finalizeStepMap(map), badLines, messageEvents, mojibake };
}

// V2 API format: one JSON object per line: {turn, step, reasoning, text, tool_calls, raw?}
function readApi(file) {
  const raw = fs.readFileSync(file, "utf8");
  const lines = raw.split("\n");
  const map = new Map();
  let badLines = 0;
  let mojibake = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line || !line.trim()) continue;
    let o;
    try {
      o = JSON.parse(line);
    } catch {
      badLines++;
      continue;
    }
    if (!o || typeof o.turn !== "number" || typeof o.step !== "number") { badLines++; continue; }
    const key = o.turn + "\u0000" + o.step;
    let e = map.get(key);
    if (!e) { e = newStep(o.turn, o.step); map.set(key, e); }
    const r = typeof o.reasoning === "string" ? o.reasoning : "";
    e.reasoning.push(r);
    e.reasoning_chunks++;
    e.text.push(typeof o.text === "string" ? o.text : "");
    e.tool_calls += Number(o.tool_calls || 0);
    pushToolNames(e, o.raw);
    mojibake += countMatches(MOJIBAKE_RE, r);
    mojibake += countMatches(MOJIBAKE_RE, typeof o.text === "string" ? o.text : "");
  }

  return { steps: finalizeStepMap(map), badLines, messageEvents: map.size, mojibake };
}

// R6 local format (qwen7b collector):
//   {"turn":1,"step":1,"reasoning":"<thought>","text":"","tool_calls":0,"raw":{...}}
// The work order calls the field "thought"; fixtures ship it as "reasoning".
// Accept both, prefer "thought". tool_calls comes from the collector verbatim.
function readLocal(file) {
  const raw = fs.readFileSync(file, "utf8");
  const lines = raw.split("\n");
  const map = new Map();
  let badLines = 0;
  let mojibake = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line || !line.trim()) continue;
    let o;
    try {
      o = JSON.parse(line);
    } catch {
      badLines++;
      continue;
    }
    if (!o || typeof o.turn !== "number" || typeof o.step !== "number") { badLines++; continue; }
    const key = o.turn + "\u0000" + o.step;
    let e = map.get(key);
    if (!e) { e = newStep(o.turn, o.step); map.set(key, e); }
    const thought = typeof o.thought === "string"
      ? o.thought
      : (typeof o.reasoning === "string" ? o.reasoning : "");
    const text = typeof o.text === "string" ? o.text : "";
    e.reasoning.push(thought);
    e.reasoning_chunks++;
    e.text.push(text);
    e.tool_calls += Number(o.tool_calls || 0);
    pushToolNames(e, o.raw);
    mojibake += countMatches(MOJIBAKE_RE, thought);
    mojibake += countMatches(MOJIBAKE_RE, text);
  }

  return { steps: finalizeStepMap(map), badLines, messageEvents: map.size, mojibake };
}

const READERS = { dsh: readDsh, api: readApi, local: readLocal };

function warningsOf(parsed) {
  return parsed && parsed.mojibake >= 2 ? ["mojibake_suspected"] : [];
}
// --------------------------------------------------------------- layer 2
function analyzeStep(st, th) {
  const r = st.reasoning;
  const t = st.text;

  const toks = tokenize(r);

  // adjacent 2-grams
  const grams = new Map();
  const bump = (a, b) => {
    const k = a + "\u0001" + b;
    let e = grams.get(k);
    if (!e) { e = { a, b, n: 0 }; grams.set(k, e); }
    e.n++;
  };
  for (let i = 0; i + 1 < toks.length; i++) bump(toks[i], toks[i + 1]);

  let topPair = null;
  let topN = 0;
  for (const e of grams.values()) {
    if (e.n > topN) { topN = e.n; topPair = e; }
  }
  const share = toks.length ? topN / toks.length : 0;

  // longest_run is a DIAGNOSTIC field: strictly adjacent occurrences of the
  // top 2-gram. It never feeds ruleA/ruleB and is not a V2 dependent variable.
  let longest = 0;
  let cur = 0;
  if (topPair) {
    for (let i = 0; i + 1 < toks.length; i++) {
      if (toks[i] !== topPair.a || toks[i + 1] !== topPair.b) continue;
      if (i >= 2 && toks[i - 2] === topPair.a && toks[i - 1] === topPair.b) cur++;
      else cur = 1;
      if (cur > longest) longest = cur;
    }
  }

  const action_words = countMatches(ACTION_RE, r);
  const done_claims = countMatches(DONE_RE, r + "\n" + t);
  const reasoning_chars = r.length;
  const text_chars = t.length;
  const tool_calls = st.tool_calls;

  // v2.0/v2.1 rule A, UNCHANGED (work order section 4.1). It stays a diagnostic.
  const a1 = action_words >= 3 && tool_calls === 0 && reasoning_chars >= 120;
  const a2 = tool_calls === 0 && text_chars < 80 && reasoning_chars >= 300;
  const s1 = action_words >= 3 && tool_calls === 0 && reasoning_chars >= th.ruleA_reasoning_min && text_chars < th.ruleA_text_max && done_claims === 0;
  const s2 = tool_calls === 0 && text_chars < 80 && reasoning_chars >= 300 && done_claims === 0;

  return {
    turn: st.turn,
    step: st.step,
    reasoning_chars,
    text_chars,
    tokens: toks.length,
    tool_calls,
    action_words,
    done_claims,
    ruleA_v1: a1 || a2,
    ruleA_strict: s1 || s2,
    ruleB: share >= th.ruleB_share && topN >= th.ruleB_count && tool_calls === 0,
    // R2: word-free structural A. No task vocabulary involved.
    structure_A: tool_calls === 0 && reasoning_chars >= th.ruleA_reasoning_min,
    // R1: does the legacy vocabulary fire on this step (diagnostic only)?
    has_action_word: action_words > 0,
    top_2gram: topPair ? topPair.a + "|" + topPair.b : "",
    top_2gram_count: topN,
    share: roundShare(share),
    longest_run: longest,
    reasoning_chunks: st.reasoning_chunks || 0,
  };
}

function analyze(steps, th) {
  return steps.map((s) => analyzeStep(s, th));
}

// ------------------------------------------------------- layer 3 (structure)
function gramsChar(s, n) {
  const m = new Set();
  for (let i = 0; i + n <= s.length; i++) m.add(s.slice(i, i + n));
  return m;
}

function jaccard(a, b) {
  if (!a.size || !b.size) return 0;
  let inter = 0;
  for (const x of a) if (b.has(x)) inter++;
  return inter / (a.size + b.size - inter);
}

// max Jaccard of turn i against the previous k turns
function seriesMax(sets, k) {
  const out = [];
  for (let i = 0; i < sets.length; i++) {
    let mx = 0;
    for (let j = Math.max(0, i - k); j < i; j++) {
      const v = jaccard(sets[i], sets[j]);
      if (v > mx) mx = v;
    }
    out.push(mx);
  }
  return out;
}

function statsOf(vals) {
  const s = [...vals].sort((a, b) => a - b);
  const mean = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
  return {
    mean: round3(mean),
    median: s.length ? round3(s[Math.floor(s.length / 2)]) : 0,
    max: s.length ? round3(s[s.length - 1]) : 0,
  };
}

// L1 follows inter-turn.mjs exactly: values are rounded to 3 decimals BEFORE
// statistics, first turn excluded, run = consecutive turns >= threshold.
function longestRunOf(series, threshold) {
  let best = null;
  let cur = null;
  for (const x of series) {
    if (x.v >= threshold) {
      if (!cur) cur = { start: x.turn, end: x.turn, n: 1 };
      else { cur.end = x.turn; cur.n++; }
    } else if (cur) {
      if (!best || cur.n > best.n) best = cur;
      cur = null;
    }
  }
  if (cur && (!best || cur.n > best.n)) best = cur;
  return best;
}

function entropyOf(names) {
  const distinct = new Set(names).size;
  if (distinct <= 1) return 0;
  const counts = new Map();
  for (const n of names) counts.set(n, (counts.get(n) || 0) + 1);
  let H = 0;
  for (const c of counts.values()) {
    const p = c / names.length;
    H -= p * Math.log2(p);
  }
  return H;
}

function longestSameOf(names) {
  let best = 0;
  let cur = 0;
  let prev = null;
  for (const n of names) {
    if (n === prev) cur++;
    else { cur = 1; prev = n; }
    if (cur > best) best = cur;
  }
  return best;
}
function buildTurnRows(rows) {
  const byTurn = new Map();
  for (const r of rows) {
    let t = byTurn.get(r.turn);
    if (!t) {
      t = {
        turn: r.turn,
        steps: 0,
        tool_calls: 0,
        reasoning_chars: 0,
        tokens: 0,
        loop_steps: 0,
        ruleA_steps: 0,
        ruleB_steps: 0,
        both_steps: 0,
        max_share: 0,
        top_2gram: "",
      };
      byTurn.set(r.turn, t);
    }
    t.steps++;
    t.tool_calls += r.tool_calls;
    // turn-level reasoning_chars follows the reference turn-level caliber:
    // every reasoning chunk contributes its text plus one trailing newline.
    t.reasoning_chars += r.reasoning_chars + (r.reasoning_chunks || 0);
    t.tokens += r.tokens;
    if (r.ruleB) { t.loop_steps++; t.ruleB_steps++; }
    if (r.ruleA_v1) t.ruleA_steps++;
    if (r.ruleA_strict && r.ruleB) t.both_steps++;
    if (r.share > t.max_share) { t.max_share = r.share; t.top_2gram = r.top_2gram; }
  }
  return [...byTurn.values()].sort((a, b) => a.turn - b.turn);
}

// R3/R4/R5: the three structure layers plus the auxiliary block.
function buildStructure(steps, rows, th) {
  // Turn-level reasoning exactly as inter-turn.mjs aggregates it: every step's
  // reasoning joined with "\n", in (turn, step) order.
  const turnMap = new Map();
  for (const s of steps) {
    let t = turnMap.get(s.turn);
    if (!t) { t = { turn: s.turn, rs: [], tool_calls: 0, tools: [] }; turnMap.set(s.turn, t); }
    t.rs.push(s.reasoning);
    t.tool_calls += s.tool_calls;
    t.tools.push(...s.tools);
  }
  const turns = [...turnMap.values()].sort((a, b) => a.turn - b.turn)
    .map((t) => ({ turn: t.turn, reasoning: t.rs.join("\n"), tool_calls: t.tool_calls, tools: t.tools }));

  // ---- L1 literal: turn-level 3-gram Jaccard against previous inter_k turns.
  const g3 = turns.map((t) => gramsChar(t.reasoning, 3));
  const series1 = seriesMax(g3, th.inter_k).map((x) => round3(x));
  const vals1 = series1.slice(1);
  const st1 = statsOf(vals1);
  const L1 = {
    ruleB_steps: rows.filter((r) => r.ruleB).length,
    inter_turn: {
      k: th.inter_k,
      mean: st1.mean,
      median: st1.median,
      max: st1.max,
      turns_ge_threshold: vals1.filter((v) => v >= th.inter_threshold).length,
      longest_run: longestRunOf(turns.slice(1).map((t, i) => ({ turn: t.turn, v: series1[i + 1] })), th.inter_threshold),
    },
  };

  // ---- L2 skeleton: function-character 2-gram Jaccard against previous k turns.
  const skel = turns.map((t) => [...t.reasoning].filter((c) => FUNC_CHARS.has(c)).join(""));
  const g2 = skel.map((s) => gramsChar(s, 2));
  const series2 = seriesMax(g2, th.skeleton_k);
  const vals2 = series2.slice(1);
  const st2 = statsOf(vals2);
  const run2raw = longestRunOf(turns.slice(1).map((t, i) => ({ turn: t.turn, v: series2[i + 1] })), L2_RUN_THRESHOLD);
  const L2 = {
    k: th.skeleton_k,
    mean: st2.mean,
    median: st2.median,
    max: st2.max,
    // {start, n} per work order R6; segmentation only, not a judgment threshold
    longest_run: run2raw ? { start: run2raw.start, n: run2raw.n } : null,
  };

  // ---- L3 behavior: tool-name sequence, descriptive only (no thresholds).
  const names = [];
  for (const s of steps) for (const n of s.tools) names.push(n);
  const counts = new Map();
  for (const n of names) counts.set(n, (counts.get(n) || 0) + 1);
  let topTool = null;
  let topN = 0;
  for (const [n, c] of counts) if (c > topN) { topN = c; topTool = n; }
  const zeroSteps = rows.filter((r) => r.tool_calls === 0).length;
  const L3 = {
    calls: names.length,
    distinct_tools: counts.size,
    // Raw Shannon entropy in bits (the acceptance table's 1.80 has to be raw:
    // a normalized value cannot exceed 1). Described in the README.
    tool_entropy: names.length ? round2(entropyOf(names)) : 0,
    longest_same_tool: longestSameOf(names),
    top_tool: topTool,
    top_share: names.length ? round3(topN / names.length) : 0,
    // Step-level ratio (matches the acceptance table: 59/71 = 0.831).
    zero_tool_ratio: rows.length ? round3(zeroSteps / rows.length) : 0,
  };

  // ---- aux (diagnostic; never a conclusion).
  const totalChars = rows.reduce((n, r) => n + r.reasoning_chars, 0);
  let neg = 0;
  for (const s of steps) neg += countMatches(NEGATION_RE, s.reasoning);
  const aux = {
    ruleA_v1_steps: rows.filter((r) => r.ruleA_v1).length,
    structure_A_steps: rows.filter((r) => r.structure_A).length,
    negation_per_kchar: totalChars ? round2((neg * 1000) / totalChars) : 0,
  };

  return { L1_literal: L1, L2_skeleton: L2, L3_behavior: L3, aux };
}

function buildSummary(label, file, rows, turnRows, warnings, env, structure) {
  const byRule = (pred) => uniqSorted(rows.filter(pred).map((r) => r.turn));
  const loopTurns = byRule((r) => r.ruleB);
  const loopSet = new Set(loopTurns);

  const runs = [];
  for (const t of loopTurns) {
    const last = runs[runs.length - 1];
    if (last && t === last[1] + 1) last[1] = t;
    else runs.push([t, t]);
  }
  const longest = runs.length ? Math.max(...runs.map((x) => x[1] - x[0] + 1)) : 0;

  // first / recovery endpoints of the loop episode (R11 of v2.1)
  const firstLoop = loopTurns.length ? loopTurns[0] : null;
  let recovery = null;
  if (firstLoop !== null) {
    for (const t of turnRows.map((x) => x.turn)) {
      if (t > firstLoop && !loopSet.has(t)) { recovery = t; break; }
    }
  }

  return {
    meta: {
      label,
      file,
      turns: turnRows.length,
      steps: rows.length,
      generatedAt: env.generatedAt,
      thresholds: { ...env.thresholds },
      badLines: env.badLines || 0,
    },
    warnings: warnings || [],
    ruleA_role: "auxiliary",
    counts: {
      ruleA_v1_steps: rows.filter((r) => r.ruleA_v1).length,
      ruleA_strict_steps: rows.filter((r) => r.ruleA_strict).length,
      ruleB_steps: rows.filter((r) => r.ruleB).length,
      both_steps: rows.filter((r) => r.ruleA_strict && r.ruleB).length,
    },
    turns: {
      ruleA_v1: byRule((r) => r.ruleA_v1),
      ruleA_strict: byRule((r) => r.ruleA_strict),
      ruleB: loopTurns,
      both: byRule((r) => r.ruleA_strict && r.ruleB),
    },
    loop_run: {
      longest_consecutive_turns: longest,
      runs,
      first_loop_turn: firstLoop,
      recovery_turn: recovery,
      recovered: recovery !== null,
    },
    structure,
  };
}
function uniqSorted(nums) {
  return [...new Set(nums)].sort((a, b) => a - b);
}

// ----------------------------------------------------------------- outputs
function csvCell(v) {
  const s = String(v);
  return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}

function stepsJsonl(rows) {
  return rows.map((r) => JSON.stringify({
    turn: r.turn,
    step: r.step,
    reasoning_chars: r.reasoning_chars,
    text_chars: r.text_chars,
    tokens: r.tokens,
    tool_calls: r.tool_calls,
    action_words: r.action_words,
    done_claims: r.done_claims,
    structure_A: r.structure_A,
    has_action_word: r.has_action_word,
    ruleA_v1: r.ruleA_v1,
    ruleA_strict: r.ruleA_strict,
    ruleB: r.ruleB,
    top_2gram: r.top_2gram,
    top_2gram_count: r.top_2gram_count,
    share: r.share,
    longest_run: r.longest_run,
  })).join("\n") + "\n";
}

const TURN_HEADER = "turn,steps,tool_calls,reasoning_chars,tokens,loop_steps,loop_turn,ruleA_steps,ruleB_steps,both_steps,max_share,top_2gram";

function turnsCsv(turnRows) {
  const out = [TURN_HEADER];
  for (const t of turnRows) {
    out.push([
      t.turn, t.steps, t.tool_calls, t.reasoning_chars, t.tokens,
      t.loop_steps, t.loop_steps > 0 ? "true" : "false",
      t.ruleA_steps, t.ruleB_steps, t.both_steps,
      formatShare(t.max_share), t.top_2gram,
    ].map(csvCell).join(","));
  }
  return out.join("\n") + "\n";
}

function writeText(file, text) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, text, "utf8"); // no BOM
}

function writeSessionOutputs(outDir, label, rows, turnRows, summary) {
  writeText(path.join(outDir, label + ".steps.jsonl"), stepsJsonl(rows));
  writeText(path.join(outDir, label + ".turns.csv"), turnsCsv(turnRows));
  writeText(path.join(outDir, label + ".summary.json"), JSON.stringify(summary, null, 2) + "\n");
}

// ------------------------------------------------------------------- label
function deriveLabel(file) {
  const base = path.basename(file).replace(/\.jsonl$/i, "");
  const head = base.split(/[-_.]/)[0];
  return head || base;
}

// ------------------------------------------------------------------- time
function generatedAtOf(opts) {
  if (opts.noTimestamp) return "";
  const epoch = process.env.SOURCE_DATE_EPOCH;
  if (epoch && /^\d+$/.test(epoch)) return new Date(Number(epoch) * 1000).toISOString();
  return new Date().toISOString();
}

// ------------------------------------------------------------------ driver
function listJsonl(dir) {
  const out = [];
  const walk = (d, depth) => {
    if (depth > 3) return;
    let ents;
    try { ents = fs.readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const e of ents) {
      const p = path.join(d, e.name);
      if (e.isDirectory()) walk(p, depth + 1);
      else if (e.isFile() && /\.jsonl$/i.test(e.name)) out.push(p);
    }
  };
  walk(dir, 0);
  return out.sort();
}

function groupNameOf(inputDir, file) {
  const rel = path.relative(inputDir, path.dirname(file));
  if (!rel || rel === ".") return "__root__";
  return rel.split(path.sep)[0];
}

function processOne(file, source, outDir, opts, usedLabels) {
  const t0 = Date.now();
  const parsed = READERS[source](file);
  const t1 = Date.now();
  const rows = analyze(parsed.steps, opts.thresholds);
  const structure = buildStructure(parsed.steps, rows, opts.thresholds);
  const t2 = Date.now();
  const turnRows = buildTurnRows(rows);
  let label = opts.label || deriveLabel(file);
  if (!opts.label && usedLabels && usedLabels.has(label)) {
    label = path.basename(file).replace(/\.jsonl$/i, "");
  }
  if (usedLabels) usedLabels.set(label, true);
  const summary = buildSummary(label, path.resolve(file), rows, turnRows, warningsOf(parsed), { ...opts, badLines: parsed.badLines }, structure);
  writeSessionOutputs(outDir, label, rows, turnRows, summary);
  return {
    label,
    file: path.resolve(file),
    summary,
    rows,
    stats: {
      parseMs: t1 - t0,
      analyzeMs: t2 - t1,
      badLines: parsed.badLines,
      messageEvents: parsed.messageEvents,
      mojibake: parsed.mojibake,
    },
  };
}

function mean(nums) {
  if (!nums.length) return 0;
  return nums.reduce((a, b) => a + b, 0) / nums.length;
}

function median(nums) {
  if (!nums.length) return 0;
  const s = [...nums].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

function buildGroups(inputDir, entries) {
  const map = new Map();
  for (const e of entries) {
    const name = groupNameOf(inputDir, e.file);
    let g = map.get(name);
    if (!g) { g = []; map.set(name, g); }
    g.push(e.summary);
  }
  return [...map.entries()].sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0)).map(([name, list]) => {
    const loopTurns = list.map((s) => s.turns.ruleB.length);
    const strictSteps = list.map((s) => s.counts.ruleA_strict_steps);
    const runs = list.map((s) => s.loop_run.longest_consecutive_turns);
    const l2 = list.map((s) => s.structure.L2_skeleton.mean);
    return {
      name,
      n: list.length,
      ruleB_turns_mean: Number(mean(loopTurns).toFixed(2)),
      ruleB_turns_median: median(loopTurns),
      ruleA_strict_steps_mean: Number(mean(strictSteps).toFixed(2)),
      loop_run_mean: Number(mean(runs).toFixed(2)),
      loop_run_max: runs.length ? Math.max(...runs) : 0,
      L2_skeleton_mean: Number(mean(l2).toFixed(3)),
    };
  });
}
// ---------------------------------------------------------------- self-test
function loadExpected(explicit) {
  const here = path.dirname(fileURLToPath(import.meta.url));
  const p = explicit ? path.resolve(explicit) : path.join(here, "fixtures", "expected.json");
  let raw;
  try {
    raw = fs.readFileSync(p, "utf8");
  } catch (e) {
    fail("cannot read expected values: " + e.message);
  }
  let obj;
  try {
    obj = JSON.parse(raw);
  } catch (e) {
    fail("invalid JSON in " + p + ": " + e.message);
  }
  if (!obj || !Array.isArray(obj.sessions)) fail("expected.json must contain a sessions array");
  return { path: p, data: obj };
}

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");

function globBasename(dir, pattern) {
  let ents;
  try { ents = fs.readdirSync(dir, { withFileTypes: true }); } catch { return []; }
  const re = new RegExp("^" + pattern.replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*/g, ".*") + "$", "i");
  return ents.filter((e) => e.isFile() && re.test(e.name)).map((e) => path.join(dir, e.name)).sort();
}

function resolveInput(spec, extraRoot) {
  const candidates = [];
  if (path.isAbsolute(spec)) candidates.push(spec);
  else {
    if (extraRoot) candidates.push(path.resolve(extraRoot, spec));
    candidates.push(path.resolve(ROOT, spec));
    candidates.push(path.resolve(ROOT, "workspace", spec));
    candidates.push(path.resolve(ROOT, "data", spec));
    candidates.push(path.resolve(process.cwd(), spec));
  }
  for (const c of candidates) {
    if (c.includes("*")) {
      const hits = globBasename(path.dirname(c), path.basename(c));
      if (hits.length) return hits[0];
    } else if (fs.existsSync(c) && fs.statSync(c).isFile()) {
      return c;
    }
  }
  for (const root of [path.join(ROOT, "workspace"), path.join(ROOT, "data")]) {
    const hit = searchTree(root, path.basename(spec), 0);
    if (hit) return hit;
  }
  return null;
}

function searchTree(dir, pattern, depth) {
  if (depth > 4) return null;
  const hits = globBasename(dir, pattern);
  if (hits.length) return hits[0];
  let ents;
  try { ents = fs.readdirSync(dir, { withFileTypes: true }); } catch { return null; }
  for (const e of ents) {
    if (!e.isDirectory()) continue;
    const hit = searchTree(path.join(dir, e.name), pattern, depth + 1);
    if (hit) return hit;
  }
  return null;
}

function runSelfTest(opts, log) {
  const t0 = Date.now();
  log("=== collapse-detector v3.0 self-test ===");
  log("node    : " + process.version + "   Intl.Segmenter: " + (typeof Intl.Segmenter === "function" ? "ok" : "MISSING"));

  const exp = loadExpected(opts.expected);
  log("expected: " + exp.path);

  let checks = 0;
  let failed = 0;
  let passCases = 0;
  const caseRows = new Map();

  for (const sess of exp.data.sessions) {
    const file = resolveInput(sess.input, opts.inputDir);
    if (!file) {
      log("[" + sess.label + "] FAIL  input not found: " + sess.input);
      checks++;
      failed++;
      continue;
    }
    const t1 = Date.now();
    const parsed = READERS[sess.sourceType || "dsh"](file);
    const rows = analyze(parsed.steps, DEFAULT_THRESHOLDS);
    const structure = buildStructure(parsed.steps, rows, DEFAULT_THRESHOLDS);
    const turnRows = buildTurnRows(rows);
    const summary = buildSummary(sess.label, path.resolve(file), rows, turnRows, warningsOf(parsed), {
      generatedAt: "",
      thresholds: DEFAULT_THRESHOLDS,
      badLines: parsed.badLines,
    }, structure);
    const ms = Date.now() - t1;
    caseRows.set(sess.label, rows);

    const problems = [];
    const chk = (name, got, want) => {
      checks++;
      const g = JSON.stringify(got);
      const w = JSON.stringify(want);
      if (g !== w) { failed++; problems.push(name + ": got " + g + " want " + w); }
    };

    if (sess.steps != null) chk("steps", summary.meta.steps, sess.steps);
    if (sess.turns != null) chk("turns", summary.meta.turns, sess.turns);
    for (const k of Object.keys(sess.counts || {})) chk(k, summary.counts[k], sess.counts[k]);
    for (const k of Object.keys(sess.turnsList || {})) chk("turns." + k, summary.turns[k], sess.turnsList[k]);

    if (sess.ruleB_top_2gram != null) {
      const tops = [...new Set(rows.filter((r) => r.ruleB).map((r) => r.top_2gram))];
      chk("ruleB.top_2gram", tops, [sess.ruleB_top_2gram]);
    }
    if (sess.all_tool_calls != null) {
      const vals = [...new Set(rows.map((r) => r.tool_calls))];
      chk("all_tool_calls", vals, [sess.all_tool_calls]);
    }
    if (sess.ruleB_share_min != null) {
      const shares = rows.filter((r) => r.ruleB).map((r) => r.share);
      checks++;
      if (!shares.length || Math.min(...shares) < sess.ruleB_share_min - 0.001) {
        failed++;
        problems.push("ruleB.share_min: " + (shares.length ? Math.min(...shares) : "none") + " want >= " + sess.ruleB_share_min);
      }
    }
    if (sess.ruleB_share_max != null) {
      const shares = rows.filter((r) => r.ruleB).map((r) => r.share);
      checks++;
      if (!shares.length || Math.max(...shares) > sess.ruleB_share_max + 0.001) {
        failed++;
        problems.push("ruleB.share_max: " + (shares.length ? Math.max(...shares) : "none") + " want <= " + sess.ruleB_share_max);
      }
    }

    // R3/R4/R5 structure expectations
    if (sess.structure) {
      const S = sess.structure;
      if (S.L2_mean != null) chk("L2_skeleton.mean", summary.structure.L2_skeleton.mean, S.L2_mean);
      if (S.inter_turn) {
        const got = summary.structure.L1_literal.inter_turn;
        for (const k of Object.keys(S.inter_turn)) chk("L1.inter_turn." + k, got[k], S.inter_turn[k]);
      }
      if (S.L3) {
        const got = summary.structure.L3_behavior;
        for (const k of Object.keys(S.L3)) chk("L3_behavior." + k, got[k], S.L3[k]);
      }
    }

    // share precision guard
    {
      checks++;
      const viol = rows.filter((r) => {
        const decimals = (String(r.share).split(".")[1] || "").length;
        const boundary = Math.round(r.share * 10000) % 10 === 5;
        return decimals > 4 || (boundary && decimals !== 4);
      });
      if (viol.length) {
        failed++;
        problems.push("share precision: " + viol.length + " step(s) violate the 4-decimal boundary rule");
      }
    }

    const ok = problems.length === 0;
    if (ok) passCases++;
    const note = sess.note ? "  (" + sess.note + ")" : "";
    const L = summary.structure;
    log("[" + sess.label + "] " + (ok ? "PASS" : "FAIL") + "  " + (ms / 1000).toFixed(2) + "s  " +
      "steps " + summary.meta.steps +
      " | A_v1 " + summary.counts.ruleA_v1_steps + " " + JSON.stringify(summary.turns.ruleA_v1) +
      " | A_strict " + summary.counts.ruleA_strict_steps +
      " | B " + summary.counts.ruleB_steps + " " + JSON.stringify(summary.turns.ruleB) +
      " | both " + summary.counts.both_steps +
      " | L2 " + L.L2_skeleton.mean +
      " | L3 " + L.L3_behavior.calls + "/" + L.L3_behavior.tool_entropy + "/" + L.L3_behavior.longest_same_tool +
      note);
    for (const p of problems) log("        DIFF " + p);

    if (ms > 15000) {
      checks++;
      failed++;
      log("        DIFF parse+analyze " + ms + "ms exceeds 15000ms budget");
    }

    if (opts.out) writeSessionOutputs(opts.out, sess.label, rows, turnRows, summary);
  }

  log("--- step detail ---");
  for (const d of exp.data.details || []) {
    const rows = caseRows.get(d.label) || [];
    const r = rows.find((x) => x.turn === d.turn && x.step === d.step);
    checks++;
    if (!r) {
      failed++;
      log("[" + d.label + " " + d.turn + ":" + d.step + "] FAIL step not found");
      continue;
    }
    const bad = [];
    if (d.reasoning_chars != null && r.reasoning_chars !== d.reasoning_chars) bad.push("reasoning_chars " + r.reasoning_chars + "!=" + d.reasoning_chars);
    if (d.tokens != null && r.tokens !== d.tokens) bad.push("tokens " + r.tokens + "!=" + d.tokens);
    if (d.top_2gram != null && r.top_2gram !== d.top_2gram) bad.push("top_2gram " + JSON.stringify(r.top_2gram) + "!=" + JSON.stringify(d.top_2gram));
    if (d.top_2gram_count != null && r.top_2gram_count !== d.top_2gram_count) bad.push("top_2gram_count " + r.top_2gram_count + "!=" + d.top_2gram_count);
    if (d.share != null) {
      if (d.share_exact) {
        if (r.share !== d.share) bad.push("share " + r.share + "!=" + d.share + " (exact)");
      } else if (Math.abs(r.share - d.share) > 0.05) {
        bad.push("share " + r.share + "!=" + d.share + " (tol 0.05)");
      }
    }
    if (bad.length) {
      failed++;
      log("[" + d.label + " " + d.turn + ":" + d.step + "] FAIL " + bad.join("; "));
    } else {
      log("[" + d.label + " " + d.turn + ":" + d.step + "] ok  tokens " + r.tokens + " | top " + r.top_2gram + " x" + r.top_2gram_count + " | share " + r.share);
    }
  }

  const total = ((Date.now() - t0) / 1000).toFixed(2);
  log("RESULT: " + (failed === 0 ? "PASS" : "FAIL") + " (" + passCases + "/" + exp.data.sessions.length + " cases)   checks " + (checks - failed) + "/" + checks + "   elapsed " + total + "s");
  return { ok: failed === 0, checks, failed };
}
// --------------------------------------------------------------------- CLI
const HELP = [
  "collapse detector v3.0 - structure layers (L1 literal / L2 skeleton / L3 behavior)",
  "",
  "  node detect.mjs --input <session.jsonl> --source dsh|api|local --out <dir>",
  "  node detect.mjs --input-dir <dir>       --source dsh --out <dir>",
  "  node detect.mjs --self-test [--out <dir>] [--log <file>]",
  "",
  "  --source dsh|api|local  input format (default: dsh)",
  "  --thresholds <json-file>  override thresholds; partial override is fine,",
  "                            missing keys keep defaults, inline JSON is NOT supported",
  "                            (ruleB_share, ruleB_count, ruleA_text_max, ruleA_reasoning_min,",
  "                             skeleton_k, inter_k, inter_threshold, inter_run_min)",
  "  --label <name>          override derived label (single-file mode)",
  "  --no-timestamp          write an empty generatedAt (byte-identical reruns)",
  "  --log <file>            also write the printed lines to a UTF-8 log file",
].join("\n");

function parseArgs(argv) {
  const a = { source: "dsh" };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    const need = (name) => {
      const v = argv[++i];
      if (v === undefined) throw new Error("missing value for " + name);
      return v;
    };
    if (k === "--self-test") a.selfTest = true;
    else if (k === "--input") a.input = need(k);
    else if (k === "--input-dir") a.inputDir = need(k);
    else if (k === "--source") a.source = need(k);
    else if (k === "--out") a.out = need(k);
    else if (k === "--label") a.label = need(k);
    else if (k === "--thresholds") a.thresholdsFile = need(k);
    else if (k === "--expected") a.expected = need(k);
    else if (k === "--no-timestamp") a.noTimestamp = true;
    else if (k === "--log") a.log = need(k);
    else if (k === "--help" || k === "-h") a.help = true;
    else throw new Error("unknown argument: " + k);
  }
  return a;
}

function main() {
  let args;
  try {
    args = parseArgs(process.argv.slice(2));
  } catch (e) {
    console.error("ERROR: " + e.message);
    console.error(HELP);
    process.exit(2);
  }
  if (args.help) { console.log(HELP); process.exit(0); }
  if (!Object.prototype.hasOwnProperty.call(READERS, args.source)) {
    console.error("ERROR: --source must be dsh, api or local");
    process.exit(2);
  }
  if (args.selfTest && args.thresholdsFile) {
    console.error("ERROR: --self-test always uses the default thresholds (expected values are calibrated for them)");
    process.exit(2);
  }

  const opts = {
    selfTest: !!args.selfTest,
    input: args.input,
    inputDir: args.inputDir,
    source: args.source,
    out: args.out,
    label: args.label,
    expected: args.expected,
    noTimestamp: !!args.noTimestamp,
    log: args.log,
    thresholds: args.selfTest ? { ...DEFAULT_THRESHOLDS } : loadThresholds(args.thresholdsFile),
    generatedAt: generatedAtOf(args),
  };

  const logLines = [];
  const log = (s) => { logLines.push(s); console.log(s); };
  const flushLog = () => {
    if (!opts.log) return;
    try { writeText(path.resolve(opts.log), logLines.join("\n") + "\n"); }
    catch (e) { console.error("WARN: cannot write log: " + e.message); }
  };

  if (opts.selfTest) {
    const res = runSelfTest(opts, log);
    flushLog();
    process.exit(res.ok ? 0 : 1);
  }

  if (!opts.out) {
    console.error("ERROR: --out <dir> is required");
    process.exit(2);
  }
  const outDir = path.resolve(opts.out);
  if (fs.existsSync(outDir)) {
    if (!fs.statSync(outDir).isDirectory()) {
      console.error("ERROR: --out exists and is not a directory: " + outDir);
      process.exit(2);
    }
    log("overwriting: " + outDir);
  }

  if (opts.input) {
    if (!fs.existsSync(opts.input)) {
      console.error("ERROR: input not found: " + opts.input);
      process.exit(2);
    }
    try {
      const r = processOne(opts.input, opts.source, outDir, opts, new Map());
      log("[" + r.label + "] steps " + r.summary.meta.steps + " | turns " + r.summary.meta.turns +
        " | A_v1 " + r.summary.counts.ruleA_v1_steps + " | A_strict " + r.summary.counts.ruleA_strict_steps +
        " | B " + r.summary.counts.ruleB_steps + " | both " + r.summary.counts.both_steps +
        " | L2 " + r.summary.structure.L2_skeleton.mean +
        " | L3 " + r.summary.structure.L3_behavior.calls + "/" + r.summary.structure.L3_behavior.tool_entropy +
        " | parse " + r.stats.parseMs + "ms analyze " + r.stats.analyzeMs + "ms | badLines " + r.stats.badLines +
        " | warnings " + JSON.stringify(r.summary.warnings));
      log("written: " + outDir);
    } catch (e) {
      console.error("ERROR: " + e.message);
      process.exit(1);
    }
    flushLog();
    return;
  }

  if (opts.inputDir) {
    if (!fs.existsSync(opts.inputDir)) {
      console.error("ERROR: input dir not found: " + opts.inputDir);
      process.exit(2);
    }
    const inputDir = path.resolve(opts.inputDir);
    const files = listJsonl(inputDir);
    if (!files.length) {
      console.error("ERROR: no .jsonl files under " + opts.inputDir);
      process.exit(2);
    }
    const used = new Map();
    const entries = [];
    const sessions = [];
    const errors = [];
    const t0 = Date.now();
    for (const f of files) {
      try {
        const r = processOne(f, opts.source, outDir, opts, used);
        entries.push({ file: r.file, summary: r.summary });
        sessions.push(r.summary);
        log("[" + groupNameOf(inputDir, r.file) + "/" + r.label + "] steps " + r.summary.meta.steps +
          " | A_v1 " + r.summary.counts.ruleA_v1_steps + " | A_strict " + r.summary.counts.ruleA_strict_steps +
          " | B " + r.summary.counts.ruleB_steps + " | both " + r.summary.counts.both_steps +
          " | L2 " + r.summary.structure.L2_skeleton.mean + " | " + r.stats.parseMs + "ms");
      } catch (e) {
        errors.push({ file: path.resolve(f), error: e.message });
        log("[ERROR] " + f + ": " + e.message);
      }
    }
    const total = {
      files: sessions.length,
      steps: sessions.reduce((n, s) => n + s.meta.steps, 0),
      ruleA_v1_steps: sessions.reduce((n, s) => n + s.counts.ruleA_v1_steps, 0),
      ruleA_strict_steps: sessions.reduce((n, s) => n + s.counts.ruleA_strict_steps, 0),
      ruleB_steps: sessions.reduce((n, s) => n + s.counts.ruleB_steps, 0),
      both_steps: sessions.reduce((n, s) => n + s.counts.both_steps, 0),
      loop_turns: sessions.reduce((n, s) => n + s.turns.ruleB.length, 0),
    };
    const groups = buildGroups(inputDir, entries);
    writeText(path.join(outDir, "group.json"), JSON.stringify({
      generatedAt: opts.generatedAt,
      source: opts.source,
      thresholds: opts.thresholds,
      files: sessions,
      groups,
      total,
      errors,
    }, null, 2) + "\n");
    log("");
    log("group: " + total.files + " files, " + total.steps + " steps, " + groups.length + " group(s), " + ((Date.now() - t0) / 1000).toFixed(2) + "s");
    log("written: " + outDir);
    flushLog();
    if (errors.length) process.exit(1);
    return;
  }

  console.error("ERROR: one of --input, --input-dir or --self-test is required");
  console.error(HELP);
  process.exit(2);
}

main();