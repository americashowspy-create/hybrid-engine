# Hybrid Engine — Instructions for any AI coding agent

This document is a **portable protocol**. ChatGPT, Codex, Claude, Cursor, CLI and other capable agents may follow it. It is not an executable plugin and does not grant tools or credentials.

## One-command handshake

If a user provides this repository URL and says `HYBRID AUTO`, `AUDIT`, `AUDIT-FIX`, `DEBUG`, `BUILD`, `REVIEW` or `STATUS`, read this file and the user's target repository. If available, read `docs/WORKFLOWS.md`. Never pretend those files were loaded if not accessible.

1. Identify target repository, default branch, current state, current functionality, permissions and risk.
2. Route by user goal: status, audit, debug, build, review, or auto. Do not confuse an audit with permission to deploy.
3. For build: specify acceptance criteria and impact, then make a concise task plan; for a bug: reproduce or characterize before changing source.
4. Use **one canonical plan** per task; keep spec, decisions, tests and evidence in the target project. Do not duplicate competing task trackers.
5. Investigate security at an appropriate scope. Never publish secrets or exploitable vulnerability details in a public issue.
6. Implement on an isolated branch with smallest viable change when tools and user authorization permit. If execution tools are missing, prepare a concrete patch/PR or report blocker accurately.
7. Verify: run tests/CI if possible; distinguish *not run*, *failed*, and *passed*. Never infer a pass from creating a workflow.
8. Deliver commit/PR URLs, changed files, test evidence, remaining risks and next action. Never claim merged/deployed unless verified.
9. Do not change production data, delete resources, change secrets, merge or deploy production as side effects of a generic audit request. Seek specific approval for high-impact actions.

## Severity and blockers

- CONFIRMED: direct source/behavior evidence exists.
- SUSPECTED: heuristic indicator, requires manual validation.
- NOT_TESTED: tool/permission/environment missing.
- RESOLVED: evidence-backed re-test exists.

No agent implementation is mandatory. Codex is **optional**, not the backend.

## Chat-only fallback

If there is no shell/CI executor, use accessible GitHub connector actions for source inspection, branch commits and PRs, and mark runtime tests NOT_TESTED. If there is no repository write access, produce a patch and instructions rather than falsely claiming an update.

## Scope

Avoid gratuitous refactors, overengineering, and long approval loops. User intent and risk determine workflow depth.
