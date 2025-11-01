# Maintenance Guide

This guide distills operational practices for maintainers shepherding the agent workflows.

## Checklists

### Weekly

- **Inspect workflow runs**: Review `agent-orchestrate` executions for failures. Regenerate API keys if repeated auth errors appear.
- **Verify secrets**: Confirm `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` are scoped to the correct environments and have not expired.
- **Refresh dependencies**: Update reusable actions (e.g., `actions/checkout`, `actions/setup-node`) to the latest minor version when changelogs mention security fixes.
- **Run local gates**: Execute `npm run lint`, `npm run typecheck`, and `npm test` to ensure the repo-native tooling and autodetect regression suite remain green.

### Monthly

- **Run dry-runs**: Trigger `workflow_dispatch` in analyze mode on a representative repository to ensure prompts and gating logic still align with expectations.
- **Audit contracts**: Re-read `AGENTS.md` and `REPORTING.md` for drift. Tighten constraints rather than broadening them when new risks are identified.
- **Document learnings**: Capture production incidents or novel playbook adjustments in `docs/operations-log.md` (create on demand) to build institutional memory.

## Common Tasks

### Updating Stack Detection

Use `scripts/autodetect.sh` as the single source of truth. Extend it with additional heuristics (e.g., Bazel, Swift Package Manager) and ensure new commands follow the lint → typecheck → tests ordering mandated by the contract.

1. Add detection logic guarded by presence checks for new manifest files.
2. Add or update fixtures under `fixtures/` and extend `__tests__/autodetect.test.js` to lock in behaviour.
3. Emit human-friendly log lines to stderr to simplify debugging in Actions.
4. Update the README and `docs/workflows.md` to reflect new capabilities.

### Rotating Models

If you migrate to a new LLM provider or model:

1. Update default values in `.github/workflows/agent-orchestrate.yml`.
2. Ensure `make_pr` consumers are aware of the change; mention it in the PR summary.
3. Capture any provider-specific limits (rate, context length) in `docs/workflows.md`.

### Onboarding a New Repository

1. Copy this repository or import the workflows and contracts as a subtree.
2. Configure secrets in the target repository.
3. Run `yamllint .github/workflows` locally to validate formatting before opening PRs.
4. Trigger the agent in analyze mode to generate a baseline report.

## Incident Response

1. **Identify scope** – Determine whether failures stem from the target repository, the agent workflow, or upstream providers.
2. **Collect artifacts** – Download the workflow artifacts for logs, prompts, and the generated report.
3. **Mitigate** – Re-run jobs with debugging flags, temporarily disable auto-commit behaviour, or rotate credentials as needed.
4. **Post-incident** – Document findings in `docs/operations-log.md` and raise follow-up issues or PRs.

---

For further architectural details, see [Workflows Reference](./workflows.md) and [Repository Overview](./overview.md).
