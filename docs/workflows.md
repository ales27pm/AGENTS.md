# Workflows Reference

This document explains how the GitHub Actions workflows cooperate to run the agent loop.

## agent-orchestrate

Primary entry point triggered by pull requests or manual dispatches.

1. **Checkout**: Retrieves the repository with history for diff-aware reasoning.
2. **Stack detection**: Delegated to `scripts/autodetect.sh`, which now covers Node, Bun, Deno, Python (poetry/pdm/uv), Go, Rust,
   PHP, Ruby, Elixir, Android, and CMake, emitting standardized outputs consumed by later steps.
3. **Environment setup**: Installs language runtimes on demand based on detected stack.
4. **Gates**: Runs lint, typecheck, and tests sequentially. Logs are stored under `artifacts/`. For this repository the commands
   resolve to `npm run lint`, `npm run typecheck`, and `npm test`, mirroring local developer ergonomics.
5. **Prompt construction**: Builds a context package combining the contract, reporting schema, and log metadata.
6. **LLM call**: Uses Anthropic or OpenAI to produce a LettlReport and optional diff.
7. **Branch + PR management**: Applies the diff on branch `ai/auto-fix`, runs validations, and opens/updates a PR.
8. **Artifacts**: Uploads prompt, logs, and report for human audit.

## agent-pr-comment

Triggered when `agent-orchestrate` completes successfully. Downloads the latest artifacts and posts the report
as a comment on the originating PR. This keeps the discussion thread synchronized with the agent's findings.

## agent-reusable

Exposes `agent-orchestrate` as a `workflow_call` reusable workflow. Other repositories can invoke the agent loop by
passing API keys as secrets and overriding the target model or summary budget.

## Extending the Automation

- **New providers**: Add mutually-exclusive steps after the Anthropic block. Ensure environment variables are named clearly and logs redact secrets.
- **Extra gates**: Append additional commands (e.g., security scanners) after tests. Keep them opt-in or guard them with repository metadata.
- **Custom prompts**: Modify `scripts/render-prompt.sh` (or add one if absent) so updates remain centralized.

Refer to [Maintenance Guide](./maintenance.md) for operational advice and [Repository Overview](./overview.md) for high-level context.
