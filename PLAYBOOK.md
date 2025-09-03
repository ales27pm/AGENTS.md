# 🧭 PLAYBOOK.md (how the loop runs in Actions)

```markdown
# PLAYBOOK

## Flow
1. Checkout → Autodetect tools & commands.
2. Run: lint → typecheck → tests (continue-on-error to collect signals).
3. Build `LettlReport v1` (size-bounded) + generate minimal patch (if clear).
4. If patch present: new branch → apply → re-run gates.
5. If gates green: open PR (ready). Else: PR as draft + attach artifacts.
6. Upload artifacts; print compact summary for copy-paste into chat.

## Safety
- `permissions:` set per job; default read-only; escalate minimally when creating PRs.
- PR-only changes: never push to default branch.
- All logs as artifacts; redact secrets; no external network beyond LLM API and package registries if needed.

## Reuse
- Core logic provided as reusable workflow (`workflow_call`) so other repos can call it with:
  - inputs: model name, max tokens, allow-format, allow-dep-updates
  - secrets: API key (provider)
```
