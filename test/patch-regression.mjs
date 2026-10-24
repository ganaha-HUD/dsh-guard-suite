// Regression for the four guard-suite patches against the vendored repeat engine.
// Drives the REAL llm/stream + agent/pre-step seams.
//
// NOTE on counting: there are TWO continuation paths — agent.inject() (stream
// side) and the messages returned by agent/pre-step (backstop). A budget test
// that counts only the first is wrong; both are measured and summed here.
import assert from "node:assert";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { apply } from "../vendor/repeat/index.js";

function harness(config) {
  const handlers = new Map();
  const state = { injected: 0 };
  const agent = { id: "A", inject() { state.injected += 1; } };
  const ctx = {
    on(e, fn) { if (!handlers.has(e)) handlers.set(e, []); handlers.get(e).push(fn); },
    get(n) { return n === "agents" ? { get: () => agent } : undefined; },
    inject() {},
    logger: { info() {}, warn() {}, error() {} },
  };
  apply(ctx, { logPath: null, copyDir: null, ...config });
  return { handlers, state, agent };
}

async function* repeated() { yield { type: "reasoning-delta", text: "好。".repeat(700) }; }

async function runStream(handler, opts = {}) {
  const it = handler({ sessionId: "s1", model: "deepseek-flash", ...opts }, async function* () { yield* repeated(); });
  const out = [];
  for await (const c of it) out.push(c);
  return out;
}

// Returns how many notices the backstop put into the admitted messages.
async function runPreStep(handler, agent, turn) {
  const out = await handler({ agent, messages: [], turn }, async () => ({ kind: "enter", messages: [] }));
  return out.messages?.length ?? 0;
}

async function collapseOnce(handlers, agent) {
  const h = handlers.get("llm/stream")[0];
  await runStream(h); await runStream(h); await runStream(h);
}

function total(h, agent, backstop) { return h.state.injected + backstop; }

// --- case 1: default budget (1) ---
{
  const h = harness({});
  await collapseOnce(h.handlers, h.agent);
  let back = await runPreStep(h.handlers.get("agent/pre-step")[0], h.agent, 2);
  const first = total(h, h.agent, back);
  await collapseOnce(h.handlers, h.agent);
  back += await runPreStep(h.handlers.get("agent/pre-step")[0], h.agent, 3);
  const after = total(h, h.agent, back);
  assert.equal(first, 1, `round 1 must inject exactly 1, got ${first}`);
  assert.equal(after, 1, `budget 1 must stay at 1 across rounds, got ${after}`);
  console.log("case 1 PASS  budget=1 -> 1 continuation across 2 wrap-ups");
}

// --- case 2: budget 0 ---
{
  const h = harness({ maxTruncationsPerTurn: 0 });
  await collapseOnce(h.handlers, h.agent);
  let back = await runPreStep(h.handlers.get("agent/pre-step")[0], h.agent, 2);
  await collapseOnce(h.handlers, h.agent);
  back += await runPreStep(h.handlers.get("agent/pre-step")[0], h.agent, 3);
  assert.equal(total(h, h.agent, back), 0, "budget 0 must never inject");
  console.log("case 2 PASS  budget=0 -> 0 continuations (config accepted)");
}

// --- case 3: budget 2 ---
{
  const h = harness({ maxTruncationsPerTurn: 2 });
  let back = 0;
  for (let turn = 2; turn <= 4; turn += 1) {
    await collapseOnce(h.handlers, h.agent);
    back += await runPreStep(h.handlers.get("agent/pre-step")[0], h.agent, turn);
  }
  assert.equal(total(h, h.agent, back), 2, "budget 2 must allow exactly two");
  console.log("case 3 PASS  budget=2 -> 2 continuations across 3 wrap-ups");
}

// --- case 4: out-of-scope logged once, stream untouched ---
{
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "guard-patch-"));
  const logPath = path.join(dir, "guard.log");
  const h = harness({ logPath });
  const out = await runStream(h.handlers.get("llm/stream")[0], { model: "some-other-model" });
  assert.equal(out.length, 1, "out-of-scope stream must pass through untouched");
  await runStream(h.handlers.get("llm/stream")[0], { model: "some-other-model" });
  // appendRecord is fire-and-forget by design; give it a turn to land.
  await new Promise(r => setTimeout(r, 200));
  const lines = fs.readFileSync(logPath, "utf8").trim().split("\n").filter(Boolean);
  assert.equal(lines.length, 1, "must log once per session");
  assert.match(lines[0], /out-of-scope/);
  console.log("case 4 PASS  out-of-scope logged once, stream untouched");
  fs.rmSync(dir, { recursive: true, force: true });
}

// --- case 5: negative budget rejected loudly ---
{
  assert.throws(() => harness({ maxTruncationsPerTurn: -1 }), /must be an integer >= 0/);
  console.log("case 5 PASS  negative budget rejected at load");
}

console.log("ALL PATCH CASES PASS");