// Full annotation of every assistant step, for paper use.
// Every row carries `seq` so any claim can be traced back to the append-only log.
import fs from "node:fs";
import path from "node:path";

const SRC = "E:\\Deepseek_kolp\\workspace\\conv-20261024-73be8833\\session.v4.jsonl";
const OUT = "E:\\Deepseek_kolp\\deliverables\\conv-20261024-73be8833\\collapse-dataset\\annotations";
fs.mkdirSync(OUT, { recursive: true });

const ACTION = /检查|查看|搜索|搜一下|grep|读一下|看一下|验证一下|运行一下|执行一下|调用一下|排查|定位|确认一下|试试/gi;
const ASSERT = /已完成|成功了|成功|可用|已就绪|已修复|已交付|跑通|一切正常|没问题|证明|说明|就是|根本原因|彻底|完全/g;
const UNSURE = /可能|疑似|未验证|不确定|推测|假设|待确认|也许|大概|似乎|没有验证|未证实|存疑/g;
const EVID = /[A-Za-z]:[\\/]|https?:\/\/|exit code|HTTP\s*\d{3}|sha256|\b\d+(\.\d+)?\s*(B|KB|MB|GB|ms|s|Hz|frames)\b|[0-9a-f]{16,}/gi;
const FALSIFY = /不通|行不通|放弃|证伪|反例|死路|不可能|走不通|推翻|假设不成立|这条路|错在/g;
// This session writes `**好** ✓`: the gap between word and checkmark can hold markdown.
const TEMPLATE = /好[^\n]{0,6}✓|（输出[^\n]{0,4}✓）|\(输出[^\n]{0,4}✓\)/g;

const cnt = (re, s) => (s.match(re) || []).length;

function textOf(blocks, type) {
  if (!Array.isArray(blocks)) return "";
  return blocks.filter(b => b?.type === type && typeof b.text === "string").map(b => b.text).join("\n");
}

const events = fs.readFileSync(SRC, "utf8").split("\n").filter(l => l.trim()).map(l => JSON.parse(l));
const rows = [];
let curTurn = null;

for (const ev of events) {
  const d = ev.data || {};
  if (ev.type === "turn/start") { curTurn = d.turn; continue; }
  if (ev.type !== "assistant/message") continue;

  const blocks = d.message?.content || [];
  const reasoning = textOf(blocks, "reasoning");
  const text = textOf(blocks, "text");
  const toolCalls = blocks.filter(b => b?.type === "tool-call").length;
  const all = reasoning + "\n" + text;

  const actionWords = cnt(ACTION, reasoning);
  const assertWords = cnt(ASSERT, all);
  const unsureWords = cnt(UNSURE, all);
  const evidenceMarks = cnt(EVID, all);
  const falsifyWords = cnt(FALSIFY, all);
  const templateHits = cnt(TEMPLATE, reasoning);

  const segs = reasoning.split(/[\n。.!?；;]+/).map(s => s.trim()).filter(Boolean);
  const counts = new Map();
  for (const s of segs) counts.set(s, (counts.get(s) || 0) + 1);
  let top = "", topN = 0;
  for (const [k, v] of counts) if (v > topN) { topN = v; top = k; }
  const dupShare = segs.length ? topN / segs.length : 0;

  const simulated = actionWords >= 3 && toolCalls === 0 && reasoning.length >= 120;
  const thinkOnly = toolCalls === 0 && text.length < 80 && reasoning.length >= 300;
  const emptyStep = all.length === 0 && toolCalls === 0;
  // Absolute count, not a share: the worst step has 78 hits inside 3,757 chars (20%),
  // so any proportion threshold above ~0.05 either over-fires or never fires.
  const templateHeavy = templateHits >= 5;

  let label = "normal";
  let note = "";
  if (simulated) { label = "collapse"; note = "action words without any tool call (simulated execution)"; }
  else if (thinkOnly) { label = "collapse"; note = "reasoning with neither answer nor tool call"; }
  else if (emptyStep) { label = "suspect"; note = "empty step"; }
  else if (templateHeavy) { label = "suspect"; note = "template-heavy reasoning (OK/checkmarks)"; }

  rows.push({
    seq: ev.seq,
    turn: curTurn,
    step: d.step,
    message_id: d.message?.id ?? null,
    time: ev.time ? new Date(ev.time).toISOString() : null,
    reasoning_chars: reasoning.length,
    text_chars: text.length,
    chars: all.length,
    tool_calls: toolCalls,
    action_words: actionWords,
    assert_words: assertWords,
    unsure_words: unsureWords,
    evidence_marks: evidenceMarks,
    falsify_words: falsifyWords,
    template_hits: templateHits,
    top_phrase: top.slice(0, 80),
    top_phrase_count: topN,
    dup_share: +dupShare.toFixed(3),
    pseudo_certainty: +(assertWords / (1 + evidenceMarks + unsureWords)).toFixed(3),
    flags: [simulated && "simulated_action", thinkOnly && "think_only", emptyStep && "empty_step", templateHeavy && "template_heavy"].filter(Boolean),
    label,
    note,
  });
}

fs.writeFileSync(path.join(OUT, "steps.jsonl"), rows.map(r => JSON.stringify(r)).join("\n") + "\n", "utf8");

const header = ["seq","turn","step","time","reasoning_chars","text_chars","chars","tool_calls","action_words","assert_words","unsure_words","evidence_marks","falsify_words","template_hits","top_phrase","top_phrase_count","dup_share","pseudo_certainty","flags","label","note"];
const esc = v => { const s = String(v ?? ""); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
const csv = [header.join(",")].concat(rows.map(r => header.map(h => esc(Array.isArray(r[h]) ? r[h].join("|") : r[h])).join(","))).join("\n");
fs.writeFileSync(path.join(OUT, "steps.csv"), csv + "\n", "utf8");

const byLabel = {};
for (const r of rows) byLabel[r.label] = (byLabel[r.label] || 0) + 1;
const byFlag = {};
for (const r of rows) for (const f of r.flags) byFlag[f] = (byFlag[f] || 0) + 1;
console.log(JSON.stringify({ steps: rows.length, labels: byLabel, flags: byFlag }, null, 1));