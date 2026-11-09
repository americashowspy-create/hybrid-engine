# Workflow protocol

All flows honor a common cycle: **discover → assess → plan → act when authorized → verify → report**.

| Flow | Stages | Done only when |
| --- | --- | --- |
| AUDIT | inventory, scan, triage, report | Evidence and scan limitations recorded |
| AUDIT-FIX | inventory, investigate, regression test, branch fix, CI, PR | Fix and verification evidence recorded; otherwise open |
| DEBUG | reproduce, cause, regression test, minimal fix, verify | Original failure reproducibly fixed |
| BUILD | specification, acceptance, architecture, implementation, test, review | Acceptance tests pass with evidence |
| REVIEW | examine diff, risk, verification, comments | Findings traced to files and versions |
| STATUS | read state, report blockers and pending work | State represented without invented updates |
| AUTO | infer a flow, then follow it | Selected flow's gates satisfied |

## Adaptive planning

Small low-risk changes may use a compact spec and fewer stages. Security-sensitive changes require explicit validation for authentication, authorization, tenant isolation, secret handling, migrations, and rollback.

## Quality gates

- Specification/acceptance defined for new features.
- Root-cause evidence for bugs.
- No leaked secret values in reports.
- Tests recorded as PASS/FAIL/NOT_RUN with details.
- No silent push to default branch, merging, production publishing or destructive migrations.

The Python CLI generates **plans and reports**, not end-to-end source-code patches. An actual agent/executor is necessary to perform the implementation stages.
