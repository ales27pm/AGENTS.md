const { execFileSync } = require("node:child_process");
const { mkdtempSync, readFileSync, rmSync } = require("node:fs");
const { tmpdir } = require("node:os");
const { join, resolve } = require("node:path");

const ROOT = resolve(__dirname, "..");

function runAutodetect(fixtureDir) {
  const outputDir = mkdtempSync(join(tmpdir(), "autodetect-"));
  const outputFile = join(outputDir, "out");
  try {
    execFileSync(
      "bash",
      [
        "-c",
        `GITHUB_OUTPUT="${outputFile}" scripts/autodetect.sh "${fixtureDir}"`,
      ],
      {
        cwd: ROOT,
        stdio: "inherit",
      },
    );
    const content = readFileSync(outputFile, "utf8").trim();
    const map = {};
    for (const line of content.split("\n")) {
      if (!line) continue;
      const [key, ...rest] = line.split("=");
      map[key] = rest.join("=");
    }
    return map;
  } finally {
    rmSync(outputDir, { recursive: true, force: true });
  }
}

describe("autodetect.sh", () => {
  it("detects npm projects", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/node-npm"));
    expect(result.stack).toBe("node");
    expect(result.install).toBe("npm ci");
    expect(result.lint).toContain("npm run lint");
    expect(result.test).toBe("npm test --silent");
  });

  it("detects pnpm projects", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/node-pnpm"));
    expect(result.stack).toBe("node");
    expect(result.install).toBe("pnpm install --frozen-lockfile");
    expect(result.lint).toContain("pnpm");
  });

  it("detects poetry-based python projects", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/python-poetry"));
    expect(result.stack).toBe("python");
    expect(result.install.startsWith("poetry install")).toBe(true);
    expect(result.lint).toContain("ruff");
  });

  it("detects go projects", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/go"));
    expect(result.stack).toBe("go");
    expect(result.install).toBe("go mod download");
    expect(result.test).toContain("go test");
  });

  it("detects deno projects", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/deno"));
    expect(result.stack).toBe("deno");
    expect(result.install).toBe("deno cache");
    expect(result.lint).toContain("deno");
  });

  it("detects bun projects", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/bun"));
    expect(result.stack).toBe("bun");
    expect(result.install).toBe("bun install --frozen-lockfile");
    expect(result.typecheck).toContain("bun");
  });

  it("falls back to unknown for empty directories", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/unknown"));
    expect(result.stack).toBe("unknown");
    expect(result.install).toBe(":");
  });
});
