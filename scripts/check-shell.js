#!/usr/bin/env node
const { relative } = require("node:path");
const { spawnSync } = require("node:child_process");
const fg = require("fast-glob");

const repoRoot = process.cwd();
const shellFiles = fg.sync("**/*.sh", {
  cwd: repoRoot,
  ignore: [
    "node_modules/**",
    "vendor/**",
    ".git/**",
    ".venv/**",
    ".cache/**",
  ],
  dot: false,
});

if (shellFiles.length === 0) {
  console.log("No shell scripts to lint.");
  process.exit(0);
}

let failures = 0;

function run(command, args, file, label) {
  const result = spawnSync(command, args, { stdio: "inherit" });
  if (result.status !== 0) {
    console.error(`${label} failed for ${relative(repoRoot, file)}`);
    failures += 1;
  }
}

const hasShellcheck =
  spawnSync("bash", ["-c", "command -v shellcheck"], { stdio: "ignore" }).status ===
  0;

for (const file of shellFiles) {
  run("bash", ["-n", file], file, "bash -n");
  if (hasShellcheck) {
    run("shellcheck", [file], file, "shellcheck");
  }
}

if (!hasShellcheck) {
  console.warn(
    "shellcheck not found on PATH; only bash -n validation was performed.",
  );
}

if (failures > 0) {
  process.exitCode = 1;
  console.error(
    `${failures} shell script(s) failed validation (bash -n or shellcheck).`,
  );
} else {
  const toolSummary = hasShellcheck
    ? "bash -n and shellcheck"
    : "bash -n";
  console.log(
    `Validated ${shellFiles.length} shell script(s) with ${toolSummary}.`,
  );
}
