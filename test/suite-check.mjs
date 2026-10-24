// Suite regression: (1) both engines bind on one ctx, (2) the shrink engine still
// convicts the known T134 case through the suite, (3) sibling notices do not stack.
import assert from "node:assert";
import fs from "node:fs";
import { pathToFileURL } from "node:url";
import { apply, name, VENDORED } from "../index.js";
import { analyzeAssistantMessage, evaluateWindow } from "../vendor/collapse/lib/analyze.js";
import { resolveConfig, DEFAULTS } from "../vendor/collapse/index.js";

const handlers = new Map();
const commands = [];
const ctx = {
  on(evt, fn) { if (!handlers.has(evt)) handlers.set(evt, []); handlers.get(evt).push(fn); },
  get() { return undefined; },
  inject(_s, cb) { cb({ commands: { register(c) { commands.push(c); } } }); },
  logger: { info() {}, warn() {}, error() {} },
};

apply(ctx, { repeat: { logPath: null, copyDir: null }, collapse: { logPath: null } });
console.log("suite name:", name, "vendored:", JSON.stringify(VENDORED));
console.log("listeners:", [...handlers.entries()].map(([k, v]) => `${k}=${v.length}`).join(" "));
console.log("commands:", commands.map(c => c.name).sort().join(", "));

assert.equal(name, "guard-suite");
assert.equal(handlers.get("llm/stream").length, 1, "repeat stream wrapper bound");
assert.equal(handlers.get("agent/pre-step").length, 2, "both step guards bound");
assert.deepEqual(commands.map(c => c.name).sort(), ["collapse-repair", "collapse-report", "guard-cleanup"]);

const chain = handlers.get("agent/pre-step");
async function run(initial, agent, messages, turn) {
  let i = 0;
  const terminal = async () => initial;
  const step = async () => (i >= chain.length ? terminal() : chain[i++]({ agent, messages, turn }, step));
  return step();
}

const longReasoning = "用户要求检查防概率自陷的插件和规则是否生效。让我先 grep 一下规则文件，再 检查 插件目录，然后 查看 AGENTS.md，再 搜索 自陷关键字，最后 验证 配置。"
  + "好 ✓（输出 ✓）".repeat(8);
const sim = { role: "assistant", id: "sim-1", content: [{ type: "reasoning", text: longReasoning }] };
const agentA = { id: "A", session: { id: "sA", surface: { nodes: [] }, append() {} } };
const outA = await run({ kind: "enter", messages: [{ role: "user", content: [] }] }, agentA, [{ role: "user", content: [] }, sim], 134);
assert.equal(outA.messages.length, 2, "shrink notice injected through suite");
assert.equal(outA.messages[0].source.kind, "plugin:dsh-guard-collapse");
console.log("injected through suite:", outA.messages[0].content[0].text.split("\n")[0]);

// sibling already present -> no stacking
const sibling = { role: "user", id: "sib", content: [{ type: "text", text: "wrap up" }], source: { kind: "plugin:dsh-guard-repeat-output", form: "notice", summary: "x" } };
const agentB = { id: "B", session: { id: "sB", surface: { nodes: [] }, append() {} } };
const sim2 = { ...sim, id: "sim-2" };
const outB = await run({ kind: "enter", messages: [sibling, { role: "user", content: [] }] }, agentB, [{ role: "user", content: [] }, sim2], 135);
assert.equal(outB.messages.length, 2, "must not stack a second guard notice");
console.log("sibling notice present -> no stacking (2 -> 2)");

// (3) replay the real session through the vendored shrink engine
const file = process.argv[2];
if (file) {
  const cfg = resolveConfig(DEFAULTS);
  const events = fs.readFileSync(file, "utf8").split("\n").filter(l => l.trim()).map(l => JSON.parse(l));
  const assistants = events.filter(e => e?.type === "assistant/message");
  const window = [];
  const hits = [];
  for (const e of assistants) {
    const m = analyzeAssistantMessage(e.data?.message);
    window.push(m);
    if (window.length > cfg.windowSteps * 3) window.splice(0, window.length - cfg.windowSteps * 3);
    const v = evaluateWindow(window, cfg);
    if (v && v.severity === "intervene") hits.push({ turn: e.data?.turn, kind: v.kind });
  }
  const t134 = hits.some(h => h.turn === 134 && h.kind === "SIMULATED-ACTION");
  console.log(`replay: ${assistants.length} steps -> ${hits.length} interventions (${hits.map(h=>h.kind).join(",")})`);
  assert.ok(t134, "T134 must still be convicted through the vendored engine");
  assert.ok(hits.length <= 12, "intervention count must stay low-precision-free");
}
console.log("SUITE PASS");