// Turn-level rollup so a reader can see WHERE the degradation starts and ends.
import fs from "node:fs";
import path from "node:path";

const DIR = "E:\\Deepseek_kolp\\deliverables\\conv-20261024-73be8833\\collapse-dataset\\annotations";
const rows = fs.readFileSync(path.join(DIR, "steps.jsonl"), "utf8").split("\n").filter(Boolean).map(JSON.parse);
const SRC = "E:\\Deepseek_kolp\\workspace\\conv-20261024-73be8833\\session.v4.jsonl";

// turn boundaries + user text (first user message of each turn)
const events = fs.readFileSync(SRC, "utf8").split("\n").filter(l => l.trim()).map(l => JSON.parse(l));
const turnMeta = new Map();
let cur = null;
for (const ev of events) {
  const d = ev.data || {};
  if (ev.type === "turn/start") { cur = { turn: d.turn, start: ev.time, firstUser: "", userMsgs: 0 }; turnMeta.set(d.turn, cur); continue; }
  if (!cur) continue;
  if (ev.type === "turn/end") { cur.end = ev.time; continue; }
  if (ev.type === "user/message") {
    const c = d.content;
    const txt = Array.isArray(c) ? c.filter(b => b.type === "text").map(b => b.text).join("") : "";
    cur.userMsgs += 1;
    if (!cur.firstUser && txt && !/^Time sampled|^Browser time zone|^Elapsed since/.test(txt)) cur.firstUser = txt.slice(0, 160).replace(/\s+/g, " ");
  }
}

const byTurn = new Map();
for (const r of rows) {
  if (!byTurn.has(r.turn)) byTurn.set(r.turn, { turn: r.turn, steps: 0, tool_calls: 0, chars: 0, reasoning_chars: 0, collapse_steps: 0, suspect_steps: 0, simulated: 0, think_only: 0, template_hits: 0 });
  const t = byTurn.get(r.turn);
  t.steps += 1;
  t.tool_calls += r.tool_calls;
  t.chars += r.chars;
  t.reasoning_chars += r.reasoning_chars;
  t.template_hits += r.template_hits;
  if (r.label === "collapse") t.collapse_steps += 1;
  if (r.label === "suspect") t.suspect_steps += 1;
  if (r.flags.includes("simulated_action")) t.simulated += 1;
  if (r.flags.includes("think_only")) t.think_only += 1;
}

const turns = [];
for (const t of [...byTurn.values()].sort((a, b) => a.turn - b.turn)) {
  const meta = turnMeta.get(t.turn) || {};
  const collapsed = t.collapse_steps > 0;
  turns.push({
    turn: t.turn,
    start: meta.start ? new Date(meta.start).toISOString() : null,
    end: meta.end ? new Date(meta.end).toISOString() : null,
    duration_s: meta.start && meta.end ? +((meta.end - meta.start) / 1000).toFixed(1) : null,
    user_msgs: meta.userMsgs ?? 0,
    first_user: meta.firstUser ?? "",
    steps: t.steps,
    tool_calls: t.tool_calls,
    tools_per_step: +(t.tool_calls / Math.max(1, t.steps)).toFixed(2),
    chars: t.chars,
    reasoning_chars: t.reasoning_chars,
    template_hits: t.template_hits,
    collapse_steps: t.collapse_steps,
    suspect_steps: t.suspect_steps,
    simulated: t.simulated,
    think_only: t.think_only,
    label: collapsed ? "collapse" : (t.suspect_steps > 0 ? "suspect" : "normal"),
  });
}

fs.writeFileSync(path.join(DIR, "turns.json"), JSON.stringify(turns, null, 1), "utf8");
const header = ["turn","start","end","duration_s","user_msgs","steps","tool_calls","tools_per_step","chars","reasoning_chars","template_hits","collapse_steps","suspect_steps","simulated","think_only","label","first_user"];
const esc = v => { const s = String(v ?? ""); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
fs.writeFileSync(path.join(DIR, "turns.csv"), [header.join(",")].concat(turns.map(t => header.map(h => esc(t[h])).join(","))).join("\n") + "\n", "utf8");

const collapsedTurns = turns.filter(t => t.label === "collapse").map(t => t.turn);
const suspectTurns = turns.filter(t => t.label === "suspect").map(t => t.turn);
console.log(JSON.stringify({
  turns: turns.length,
  collapse_turns: collapsedTurns,
  suspect_turn_count: suspectTurns.length,
  first_suspect_turn: suspectTurns[0] ?? null,
  last_collapse_turn: collapsedTurns[collapsedTurns.length - 1] ?? null,
}, null, 1));