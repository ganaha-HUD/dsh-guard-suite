import fs from "node:fs";
import path from "node:path";
const file = process.argv[2];
const tailN = Number(process.argv[3] || 12);
const raw = fs.readFileSync(file, "utf8");
const lines = raw.split("\n").filter(l => l.trim());

const ACTION_WORDS = /grep|检查一下|查看一下|搜索一下|搜一下|读一下|看一下|验证一下|运行一下|执行一下|调用一下|试试|排查|定位/g;
const ASSERT = /已完成|成功了|成功|可用|已就绪|已修复|已交付|跑通|一切正常|没问题|证明|说明|就是|根本原因|彻底|完全/g;
const UNCERTAIN = /可能|疑似|未验证|不确定|推测|假设|待确认|也许|大概|应该|似乎|没有验证|未证实|存疑/g;
const EVIDENCE = /[A-Za-z]:[\\/]|https?:\/\/|exit code|HTTP\s*\d{3}|sha256|\b\d+(\.\d+)?\s*(B|KB|MB|GB|ms|s|Hz|frames)\b|[0-9a-f]{16,}/gi;
const FALSIFY = /不通|行不通|放弃|证伪|反例|死路|不可能|走不通|推翻|假设不成立|这条路|错在/g;

function flat(c) { if (typeof c === "string") return c; if (!Array.isArray(c)) return ""; return c.map(x => typeof x === "string" ? x : (x.type === "text" || x.type === "reasoning" ? x.text || "" : "")).filter(Boolean).join("\n"); }
const cnt = (re, s) => (s.match(re) || []).length;

let cur = null;
const turns = [];
for (const line of lines) {
  let o; try { o = JSON.parse(line); } catch { continue; }
  const d = o.data || {};
  if (o.type === "turn/start") { cur = { turn: d.turn, tools: 0, errs: 0, reasoning: 0, text: 0, assert: 0, unsure: 0, evidence: 0, actionWords: 0, falsify: 0, wrote: 0 }; turns.push(cur); continue; }
  if (!cur) continue;
  if (o.type === "tool/call") {
    cur.tools++;
    const a = (d.arguments || "");
    if (/write|edit|Set-Content|WriteAllText|Out-File|Copy-Item|New-Item|patch/i.test((d.name||"") + a.slice(0, 600))) cur.wrote++;
  } else if (o.type === "tool/result") { if (d.message?.isError) cur.errs++; }
  else if (o.type === "assistant/message") {
    for (const part of (d.message?.content || [])) {
      if (part.type !== "reasoning" && part.type !== "text") continue;
      const t = part.text || "";
      if (part.type === "reasoning") { cur.reasoning += t.length; cur.actionWords += cnt(ACTION_WORDS, t); } else cur.text += t.length;
      cur.assert += cnt(ASSERT, t); cur.unsure += cnt(UNCERTAIN, t); cur.evidence += cnt(EVIDENCE, t); cur.falsify += cnt(FALSIFY, t);
    }
  }
}
const R = t => {
  const c = Math.max(1, t.reasoning + t.text);
  return { tools: t.tools, k: +(c/1000).toFixed(1), ev: +(t.evidence/(c/1000)).toFixed(2), as: +(t.assert/(c/1000)).toFixed(2), un: +(t.unsure/(c/1000)).toFixed(2), pseudo: +(t.assert/(1+t.evidence+t.unsure)).toFixed(2), fal: t.falsify, aw: t.actionWords };
};

// phase split: first half of turns after index 90 vs tail
const tail = turns.slice(-tailN);
const head = turns.slice(Math.max(0, turns.length - tailN*4), turns.length - tailN);
const sum = (arr, f) => arr.reduce((a,x)=>a+f(x),0);
function phase(arr) {
  const c = sum(arr, x => x.reasoning + x.text) || 1;
  return {
    turns: arr.length,
    toolsPerTurn: +(sum(arr,x=>x.tools)/arr.length).toFixed(2),
    writesPerTurn: +(sum(arr,x=>x.wrote)/arr.length).toFixed(2),
    evidenceD: +(sum(arr,x=>x.evidence)/(c/1000)).toFixed(2),
    assertD: +(sum(arr,x=>x.assert)/(c/1000)).toFixed(2),
    charsPerTurn: Math.round(c/arr.length),
    falsifyPerTurn: +(sum(arr,x=>x.falsify)/arr.length).toFixed(2),
  };
}
const A = phase(head), B = phase(tail);
const degradation = {
  tools: A.toolsPerTurn ? +((B.toolsPerTurn - A.toolsPerTurn)/A.toolsPerTurn*100).toFixed(0) : null,
  evidence: A.evidenceD ? +((B.evidenceD - A.evidenceD)/A.evidenceD*100).toFixed(0) : null,
  chars: A.charsPerTurn ? +((B.charsPerTurn - A.charsPerTurn)/A.charsPerTurn*100).toFixed(0) : null,
  falsify: A.falsifyPerTurn ? +((B.falsifyPerTurn - A.falsifyPerTurn)/A.falsifyPerTurn*100).toFixed(0) : null,
};

console.log("== PHASE COMPARE (prev block vs tail " + tailN + ") ==");
console.log("prev:", JSON.stringify(A));
console.log("tail:", JSON.stringify(B));
console.log("delta%:", JSON.stringify(degradation));

console.log("\n== TAIL " + tailN + " TURNS ==");
console.log("turn  tools  chars  evidenceD  assertD  unsureD  pseudo  falsify  actionWords");
for (const t of tail) {
  const r = R(t);
  console.log(`${String(t.turn).padStart(4)}  ${String(r.tools).padStart(5)}  ${String(r.k).padStart(5)}  ${String(r.ev).padStart(9)}  ${String(r.as).padStart(7)}  ${String(r.un).padStart(7)}  ${String(r.pseudo).padStart(6)}  ${String(r.fal).padStart(7)}  ${String(r.aw).padStart(11)}`);
}

console.log("\n== SIMULATED-ACTION TURNS (action words in reasoning, zero tools) ==");
for (const t of turns) if (t.actionWords >= 3 && t.tools === 0) console.log(`  T${t.turn}  actionWords=${t.actionWords}  reasoning=${t.reasoning}  text=${t.text}`);