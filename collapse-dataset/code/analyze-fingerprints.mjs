import fs from "node:fs";
import path from "node:path";
const OUT = "E:\\Deepseek_kolp\\workspace\\conv-20261024-73be8833";
const lines = fs.readFileSync(path.join(OUT, "session.v4.jsonl"), "utf8").split("\n").filter(l => l.trim());

function flat(c) { if (typeof c === "string") return c; if (!Array.isArray(c)) return ""; return c.map(x => typeof x === "string" ? x : (x.type === "text" || x.type === "reasoning" ? x.text || "" : "")).filter(Boolean).join("\n"); }

const ASSERT = /已完成|已完成|成功了|成功|可用|已就绪|已修复|已交付|证明|说明|就是|一定|必然|确定|显然|根本原因|毫无疑问|彻底|完全解决|跑通|一切正常/g;
const UNSURE = /可能|疑似|未验证|不确定|推测|假设|待确认|不确定|也许|大概|应该|似乎|疑似|没有验证|未证实|存疑/g;
const EVIDENCE = /[A-Za-z]:\\\\|\/\/|https?:\/\/|\b\d+\s*(B|KB|MB|GB|s|ms|Hz|frames)\b|exit code|HTTP\s*\d{3}|sha256|[0-9a-f]{16,}/gi;

let cur = null, step = null;
const rows = [];
let compactions = [];
for (const line of lines) {
  const o = JSON.parse(line); const d = o.data || {};
  if (o.type === "turn/start") { cur = d.turn; rows.push({ turn: cur, tools: 0, errs: 0, toolNames: [], reasoningChars: 0, textChars: 0, assertCount: 0, unsureCount: 0, evidenceCount: 0, fileWrites: 0, userText: "" }); continue; }
  if (o.type === "compaction/summary") {
    compactions.push({ turn: cur, shadowed: d.shadowedRange, tokens: d.shadowedTokenCount, seqs: (d.shadowedSeqs || []).length });
    continue;
  }
  const r = rows[rows.length - 1];
  if (!r) continue;
  if (o.type === "user/message") { r.userText += flat(d.content); }
  if (o.type === "tool/call") {
    r.tools++;
    const name = d.name || "";
    r.toolNames.push(name);
    const args = d.arguments || "";
    if (/write|edit|Set-Content|WriteAllText|Out-File|Copy-Item|New-Item|patch|create/i.test(name + " " + args.slice(0, 400))) r.fileWrites++;
  }
  if (o.type === "tool/result" && d.message?.isError) r.errs++;
  if (o.type === "assistant/message") {
    const c = d.message?.content || [];
    for (const part of c) {
      if (part.type === "reasoning") {
        const t = part.text || "";
        r.reasoningChars += t.length;
        r.assertCount += (t.match(ASSERT) || []).length;
        r.unsureCount += (t.match(UNSURE) || []).length;
        r.evidenceCount += (t.match(EVIDENCE) || []).length;
      } else if (part.type === "text") {
        const t = part.text || "";
        r.textChars += t.length;
        r.assertCount += (t.match(ASSERT) || []).length;
        r.unsureCount += (t.match(UNSURE) || []).length;
        r.evidenceCount += (t.match(EVIDENCE) || []).length;
      }
    }
  }
}

function agg(list) {
  const n = list.length;
  const sum = k => list.reduce((a, x) => a + x[k], 0);
  return {
    turns: n, tools: sum("tools"), errs: sum("errs"), fileWrites: sum("fileWrites"),
    reasoningChars: sum("reasoningChars"), textChars: sum("textChars"),
    assertCount: sum("assertCount"), unsureCount: sum("unsureCount"), evidenceCount: sum("evidenceCount"),
  };
}
const phases = {
  "P1 TTS (T91-117)": rows.filter(r => r.turn >= 91 && r.turn <= 117),
  "P2 OmniVoice (T118-125)": rows.filter(r => r.turn >= 118 && r.turn <= 125),
  "P3 decision+collapse (T126-137)": rows.filter(r => r.turn >= 126 && r.turn <= 137),
};
const summary = {};
for (const [k, v] of Object.entries(phases)) {
  const a = agg(v);
  summary[k] = {
    ...a,
    evidencePerKChar: +(a.evidenceCount / (Math.max(1, a.reasoningChars + a.textChars) / 1000)).toFixed(2),
    assertPerKChar: +(a.assertCount / (Math.max(1, a.reasoningChars + a.textChars) / 1000)).toFixed(2),
    unsurePerKChar: +(a.unsureCount / (Math.max(1, a.reasoningChars + a.textChars) / 1000)).toFixed(2),
    toolsPerTurn: +(a.tools / a.turns).toFixed(2),
    fileWritesPerTurn: +(a.fileWrites / a.turns).toFixed(2),
    toolErrRate: +(a.errs / Math.max(1, a.tools)).toFixed(3),
  };
}

// suspicion: high assertion, low evidence
const scored = rows.filter(r => r.turn >= 91 && (r.assertCount + r.textChars) > 0).map(r => ({
  turn: r.turn,
  assert: r.assertCount,
  unsure: r.unsureCount,
  evidence: r.evidenceCount,
  chars: r.reasoningChars + r.textChars,
  tools: r.tools,
  fileWrites: r.fileWrites,
  pseudoScore: +(r.assertCount / (1 + r.evidenceCount)).toFixed(2),
})).sort((a, b) => b.pseudoScore - a.pseudoScore).slice(0, 12);

// hypothesis falsification language
const FALSIFY = /不通|行不通|放弃|证伪|反例|死路|不可能|走不通|推翻|假设不成立|这条路/g;
const falsifyHits = [];
for (const line of lines) {
  const o = JSON.parse(line);
  if (o.type !== "assistant/message") continue;
  const t = flat(o.data?.message?.content);
  const m = t.match(FALSIFY);
  if (m) falsifyHits.push({ turn: o.data?.turn, hits: m.slice(0, 6) });
}
const byTurn = {};
for (const h of falsifyHits) byTurn[h.turn] = (byTurn[h.turn] || 0) + h.hits.length;

// user mentions of 自陷
const userSelfTrap = [];
for (const line of lines) {
  const o = JSON.parse(line);
  if (o.type === "user/message") {
    const t = flat(o.data?.content);
    if (t.includes("自陷")) userSelfTrap.push({ turn: o.data?.turn, text: t.slice(0, 80) });
  }
}

const report = { summary, scored, compactions, falsifyByTurn: byTurn, userSelfTrap };
fs.writeFileSync(path.join(OUT, "fingerprint-report.json"), JSON.stringify(report, null, 1), "utf8");
const out = [];
out.push("== PHASE SUMMARY ==");
out.push(JSON.stringify(summary, null, 1));
out.push("");
out.push("== TOP PSEUDO-CERTAINTY TURNS (assert / (1+evidence)) ==");
for (const s of scored) out.push(`T${s.turn}  assert=${s.assert} evidence=${s.evidence} unsure=${s.unsure} chars=${s.chars} tools=${s.tools} writes=${s.fileWrites} score=${s.pseudoScore}`);
out.push("");
out.push("== COMPACTIONS ==");
for (const c of compactions) out.push(`T${c.turn} shadowed=${JSON.stringify(c.shadowed)} tokens=${c.tokens} seqs=${c.seqs}`);
out.push("");
out.push("== FALSIFICATION LANGUAGE by turn ==");
out.push(JSON.stringify(byTurn));
out.push("");
out.push("== USER '自陷' mentions ==");
for (const u of userSelfTrap) out.push(`T${u.turn}: ${u.text.replace(/\n/g," ")}`);
fs.writeFileSync(path.join(OUT, "fingerprint-report.txt"), out.join("\n"), "utf8");
console.log("written");