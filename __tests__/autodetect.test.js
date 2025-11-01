const { spawnSync } = require("node:child_process");
const { existsSync, mkdtempSync, readFileSync, rmSync } = require("node:fs");
const { tmpdir } = require("node:os");
const { join, resolve } = require("node:path");

const ROOT = resolve(__dirname, "..");

function runAutodetect(fixtureDir) {
  const outputDir = mkdtempSync(join(tmpdir(), "autodetect-"));
  const outputFile = join(outputDir, "out");
  try {
    const result = spawnSync(
      "bash",
      [
        "-c",
        `GITHUB_OUTPUT="${outputFile}" scripts/autodetect.sh "${fixtureDir}"`,
      ],
      {
        cwd: ROOT,
        encoding: "utf8",
      },
    );

    let outputs;
    if (existsSync(outputFile)) {
      const content = readFileSync(outputFile, "utf8").trim();
      outputs = {};
      for (const line of content.split("\n")) {
        if (!line) continue;
        const [key, ...rest] = line.split("=");
        outputs[key] = rest.join("=");
      }
    }

    return { ...result, outputs };
  } finally {
    rmSync(outputDir, { recursive: true, force: true });
  }
}

describe("autodetect.sh", () => {
  it("detects npm projects", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/node-npm"));
    expect(result.status).toBe(0);
    expect(result.outputs.stack).toBe("node");
    expect(result.outputs.install).toBe("npm ci");
    expect(result.outputs.lint).toContain("npm run lint");
    expect(result.outputs.test).toBe("npm test --silent");
  });

  it("detects pnpm projects", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/node-pnpm"));
    expect(result.status).toBe(0);
    expect(result.outputs.stack).toBe("node");
    expect(result.outputs.install).toBe("pnpm install --frozen-lockfile");
    expect(result.outputs.lint).toContain("pnpm");
  });

  it("detects uv-based python projects", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/python-uv"));
    expect(result.status).toBe(0);
    expect(result.outputs.stack).toBe("python");
    expect(result.outputs.install).toContain("uv sync");
    expect(result.outputs.lint).toContain("uv run ruff");
  });

  it("detects pdm-based python projects", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/python-pdm"));
    expect(result.status).toBe(0);
    expect(result.outputs.stack).toBe("python");
    expect(result.outputs.install).toContain("pdm install");
    expect(result.outputs.lint).toContain("pdm run ruff");
  });

  it("detects poetry-based python projects", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/python-poetry"));
    expect(result.status).toBe(0);
    expect(result.outputs.stack).toBe("python");
    expect(result.outputs.install.startsWith("poetry install")).toBe(true);
    expect(result.outputs.lint).toContain("ruff");
  });

  it("detects go projects", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/go"));
    expect(result.status).toBe(0);
    expect(result.outputs.stack).toBe("go");
    expect(result.outputs.install).toBe("go mod download");
    expect(result.outputs.test).toContain("go test");
  });

  it("detects deno projects", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/deno"));
    expect(result.status).toBe(0);
    expect(result.outputs.stack).toBe("deno");
    expect(result.outputs.install).toBe("deno cache");
    expect(result.outputs.lint).toContain("deno");
  });

  it("detects bun projects", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/bun"));
    expect(result.status).toBe(0);
    expect(result.outputs.stack).toBe("bun");
    expect(result.outputs.install).toBe("bun install --frozen-lockfile");
    expect(result.outputs.typecheck).toContain("bun");
  });

  it("detects composer-based php projects", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/php"));
    expect(result.status).toBe(0);
    expect(result.outputs.stack).toBe("php");
    expect(result.outputs.install).toContain("composer install");
    expect(result.outputs.lint).toContain("phpcs");
  });

  it("detects ruby projects", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/ruby"));
    expect(result.status).toBe(0);
    expect(result.outputs.stack).toBe("ruby");
    expect(result.outputs.install).toContain("bundle install");
    expect(result.outputs.lint).toContain("rubocop");
  });

  it("detects elixir projects", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/elixir"));
    expect(result.status).toBe(0);
    expect(result.outputs.stack).toBe("elixir");
    expect(result.outputs.install).toBe("mix deps.get");
    expect(result.outputs.test).toBe("mix test");
  });

  it("detects android projects", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/android"));
    expect(result.status).toBe(0);
    expect(result.outputs.stack).toBe("android");
    expect(result.outputs.install).toContain("gradlew dependencies");
    expect(result.outputs.test).toContain("gradlew test");
  });

  it("detects cmake projects", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/cmake"));
    expect(result.status).toBe(0);
    expect(result.outputs.stack).toBe("cmake");
    expect(result.outputs.test).toContain("ctest");
  });

  it("handles missing package.json gracefully", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/missing-package-json"));
    expect(result.status).toBe(0);
    expect(result.outputs.stack).toBe("unknown");
    expect(result.outputs.install).toBe(":");
  });

  it("handles malformed package.json without throwing", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/malformed-package-json"));
    expect(result.status).toBe(0);
    expect(result.outputs.stack).toBe("node");
    expect(result.outputs.install).toBe("npm ci");
  });

  it("prefers pnpm when lockfiles conflict", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/conflicting-lockfiles"));
    expect(result.status).toBe(0);
    expect(result.outputs.install).toContain("pnpm install");
  });

  it("handles incomplete fixtures by falling back to defaults", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/incomplete-fixture"));
    expect(result.status).toBe(0);
    expect(result.outputs.stack).toBe("node");
    expect(result.outputs.install).toBe("npm ci");
  });

  it("fails with a helpful error when the repo root is missing", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/does-not-exist"));
    expect(result.status).not.toBe(0);
    expect(result.stderr).toContain("error: repository root");
  });

  it("falls back to unknown for empty directories", () => {
    const result = runAutodetect(resolve(ROOT, "fixtures/unknown"));
    expect(result.status).toBe(0);
    expect(result.outputs.stack).toBe("unknown");
    expect(result.outputs.install).toBe(":");
  });
});
