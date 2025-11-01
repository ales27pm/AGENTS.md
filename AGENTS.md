# AGENTS.md — Contract for Repo-Native AI Agents

## Mission (immutable)

Operate **only** inside this repository. Be secure, deterministic, and reversible.

- **Sandbox**: Use CI runners only. No local machine requirements.
- **Rollback**: Never push to default branch. Open PRs with minimal diffs.
- **Guardrails**: Redact secrets; do not access external services unless explicitly whitelisted.

## Autodetect (discover what you need at runtime)

Run `scripts/autodetect.sh` to emit the canonical lint/typecheck/test commands into `$GITHUB_OUTPUT`.

- Raspberry Pi benchmarking now emits JSON (`rpi4/bench/pi_bench.py`) consumed by the Textual dashboard. When
  modifications touch `rpi4/` or `automation/ui_app.py`, regenerate the summary before final validation so dashboards stay
  consistent.

- Script already covers Node (npm/pnpm/yarn/bun), Deno, Python (pip/poetry/pdm/uv), Go, Rust, Android, PHP, Ruby, Elixir, and CMake.
- Extend the script—not the workflows—when onboarding new ecosystems; keep commands ordered lint → typecheck → tests.
- If the stack remains `unknown`, list ≥2 plausible toolchains in the report and request direction before patching.

## Iteration Loop (strict order)

1. **Analyze**: run lint → typecheck → tests (or nearest equivalents).
2. **Report**: produce `REPORTING.md` format (<= 1200 chars summary).
3. **Plan**: propose smallest viable patch (minimal blast radius).
4. **Patch**: apply patch on new branch `ai/<slug>`.
5. **Validate**: re-run gates; if any fail → new report (v+1) with next steps.
6. **PR**: open PR only if all mandatory gates pass OR as **draft** with failures attached.
7. **Learn**: shrink subsequent reports; discard non-pertinent details; keep objectives.

## Gates (default; autodetect substitutes allowed)

- Lint must pass.
- Typecheck must pass (if configured).
- Tests must pass or be improved with focused fixes/regression tests.
- Formatting must be clean (or auto-formatted in branch).

## Reporting Contract (LettlReport v1)

Output a single markdown block shaped exactly like `REPORTING.md#LettlReport-v1`.

- **Strict budget**: summary ≤ 1200 chars; include ≥1 actionable next step.
- **Noise filter**: keep only root-cause signals (top 1-3 issues).
- **Never** paste full logs; attach as artifacts; include artifact names only.

## PR Rules

- Conventional commit titles (e.g., `fix(api): handle None user`).
- Description: brief WHAT/WHY, gates table, artifact links.
- Never change files under `third_party/` or `migrations/` unless instructed.

## Security

- Use least-privilege `GITHUB_TOKEN` and job-scoped permissions.
- No plaintext secrets in diffs, comments, or reports (mask or omit).
- If dependency updates are required, prefer patch/minor; flag majors for review.

## Self-Improvement (bounded)

- You may update **only this file’s** `Autodetect`, `Gates`, or `Reporting Contract` sections via PR
  to enhance precision and brevity — ensure the entire AGENTS.md stays < 50 KB.
- Prefer deletions over additions; never bloat.

Why this shape?
•Treats AGENTS.md as a README for agents so tools know where to look and how to behave. ⁣
•Keeps safety, rollback, and least-privilege front-and-center for GitHub Actions. ⁣
