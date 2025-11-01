#!/usr/bin/env node
const { readdirSync, statSync } = require("node:fs");
const { join, relative } = require("node:path");
const { spawnSync } = require("node:child_process");

const repoRoot = process.cwd();
const shellFiles = [];

function visit(dir) {
  for (const entry of readdirSync(dir)) {
    if (entry === "node_modules" || entry.startsWith(".git")) continue;
    const abs = join(dir, entry);
    const info = statSync(abs);
    if (info.isDirectory()) {
      visit(abs);
    } else if (info.isFile() && entry.endsWith(".sh")) {
      shellFiles.push(abs);
    }
  }
}

visit(repoRoot);

if (shellFiles.length === 0) {
  console.log("No shell scripts to lint.");
  process.exit(0);
}

let failures = 0;

for (const file of shellFiles) {
  const result = spawnSync("bash", ["-n", file], { stdio: "inherit" });
  if (result.status !== 0) {
    console.error(`bash -n failed for ${relative(repoRoot, file)}`);
    failures += 1;
  }
}

if (failures > 0) {
  process.exitCode = 1;
  console.error(`${failures} shell script(s) failed bash -n validation.`);
} else {
  console.log(`Validated ${shellFiles.length} shell script(s) with bash -n.`);
}
