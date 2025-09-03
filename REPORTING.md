# REPORTING.md

## LettlReport v1 (max 1200 chars summary)
```md
# Agent Report v${N}
Context: <short 1-line context>
Top Finding(s):
- <#1> <one line>
- <#2> <one line optional>
Likely Root Cause:
- <one line>
Action Plan (next iteration):
1) <smallest viable fix>
2) <validation step>
Artifacts:
- logs: <artifact name(s)>
- patch: <artifact name or "inline in PR">
Notes: <optional 1-liner; no secrets; no stack dumps>

Rules
•Keep the Summary block ≤ 1200 chars (workflow will enforce).
•Artifacts must be uploaded; do not paste logs into the summary.
•Use consistent file names: lint.log, typecheck.log, tests.log, patch.diff, PR_BODY.md.
```

---
