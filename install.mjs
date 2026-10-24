// Install dsh-guard-suite into a DSH profile. Dry-run by default.
//   node install.mjs                  -> show what would change
//   node install.mjs --apply          -> copy + register
//   node install.mjs --apply --force  -> overwrite an existing copy
import fs from "node:fs";
import path from "node:path";
import os from "node:os";

const apply = process.argv.includes("--apply");
const force = process.argv.includes("--force");
const profile = process.argv.find(a => a.startsWith("--profile="))?.split("=")[1]
  || path.join(os.homedir(), ".dsh", "profiles", "desktop");
const here = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1"));
const pkgPath = path.join(profile, "package.json");

if (!fs.existsSync(pkgPath)) { console.error("profile package.json not found:", pkgPath); process.exit(2); }
const raw = fs.readFileSync(pkgPath, "utf8");
const pkg = JSON.parse(raw);
const bundles = pkg?.dsh?.profile?.bundles ?? [];
const target = path.join(profile, "node_modules", "dsh-guard-suite");
// The suite VENDORS repeat-output. If the standalone package is still a bundle,
// BOTH engines register llm/stream and every delta is inspected twice — and the
// standalone copy does not carry the four audit patches, so its dead budget
// would silently win wherever it runs first.
const standalone = bundles.includes("dsh-guard-repeat-output");
const replace = process.argv.includes("--replace-repeat");

console.log("profile   :", profile);
console.log("target    :", target);
console.log("installed :", fs.existsSync(target));
console.log("registered:", bundles.includes("dsh-guard-suite"));
console.log("standalone repeat-output in bundles:", standalone);
console.log("mode      :", apply ? (force ? "APPLY (force)" : "APPLY") : "dry-run");

if (standalone && !replace) {
  console.log("\nWARNING: `dsh-guard-repeat-output` is still a bundle. The suite already");
  console.log("vendors it, so leaving both enabled runs the repetition engine twice and");
  console.log("keeps the UNPATCHED copy in play. Re-run with --replace-repeat to remove");
  console.log("the standalone entry (the package stays in node_modules; only the bundle");
  console.log("registration is dropped).");
}

if (!apply) {
  console.log("\nNothing written. Re-run with --apply, then restart DSH.");
  console.log("Expected journal lines after restart:");
  console.log("  [guard-repeat-output] active (...)");
  console.log("  [guard-collapse] active (...)");
  console.log("  [guard-suite] active: guard-repeat-output@2.1.7 + guard-collapse@0.1.0");
  process.exit(0);
}

if (fs.existsSync(target) && !force) {
  console.error("\nTarget exists. Re-run with --force to overwrite.");
  process.exit(3);
}

fs.cpSync(here, target, { recursive: true, force: true });
if (standalone && replace) {
  const at = bundles.indexOf("dsh-guard-repeat-output");
  if (at >= 0) bundles.splice(at, 1);
  console.log("removed standalone dsh-guard-repeat-output from bundles");
}
if (!bundles.includes("dsh-guard-suite")) {
  bundles.push("dsh-guard-suite");
  pkg.dsh = pkg.dsh || {};
  pkg.dsh.profile = pkg.dsh.profile || {};
  pkg.dsh.profile.bundles = bundles;
}
fs.writeFileSync(pkgPath + ".bak-guard-suite", raw, "utf8");
fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + "\n", "utf8");
console.log("\nInstalled. Restart DSH and confirm the three [guard-*] lines in the journal.");
console.log("Then verify with: /collapse-report   and   /guard-cleanup");