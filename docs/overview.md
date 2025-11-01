# Repository Overview

This repository captures the operational contract and automation scaffolding used to run repo-native AI coding agents.
The goal is to provide a reproducible playbook that can be dropped into any project and trusted to reason about code,
propose patches, and open high-signal pull requests with minimal human supervision.

## Core Components

- **Contracts** – `AGENTS.md`, `PLAYBOOK.md`, and `REPORTING.md` formalize how agents must behave, how workflows orchestrate
  them, and how they summarize findings.
- **Automation** – Reusable GitHub Actions workflows in `.github/workflows/` wire the contract into CI so humans can invoke the
  agent loop from pull requests, manual dispatches, or other repositories.
- **Quality Gates** – npm-driven lint (`markdownlint` + `bash -n`), TypeScript sanity checks, Jest regression tests for
  autodetect, and `.yamllint` for workflows keep automation deterministic.
- **Documentation** – The `docs/` directory deepens context for maintainers, platform engineers, and researchers extending the
  system.

## Lifecycle

1. **Detection** – `scripts/autodetect.sh` now covers Node (npm/pnpm/yarn/bun), Deno, Python (poetry/pdm/uv), Go, Rust, PHP,
   Ruby, Elixir, Android, and CMake, emitting install/lint/typecheck/test commands for CI consumers.
2. **Gating** – Lint, type checking, and tests run deterministically, capturing logs as artifacts for the agent to review.
3. **Reasoning** – An LLM receives the contract, schema, npm gate results, and execution logs to produce a compact report and a
   minimal patch.
4. **Validation** – Proposed changes are committed on a dedicated `ai/*` branch, revalidated, and pushed as a PR or draft.
5. **Feedback** – Reports are surfaced as PR comments, while artifacts remain available for deeper debugging.

## When to Modify the Contract

- Update `AGENTS.md` when onboarding to a new organization or when the default stack detection and guardrails need tuning.
- Extend `REPORTING.md` only if the downstream consumers of LettlReport data change.
- Adjust GitHub workflows when the orchestration logic or telemetry needs to evolve.

For day-to-day operations and maintenance, see [Maintenance Guide](./maintenance.md).
