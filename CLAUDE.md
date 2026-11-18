# Claude Code — Hybrid Engine

Read [AGENTS.md](AGENTS.md) first. For broad project assessments also read [docs/PROJECT_AUDIT.md](docs/PROJECT_AUDIT.md). These files are the **single source of process rules**; this file is only a discovery bridge for Claude Code, not a separate policy.

The Hybrid Engine is a protocol and optional Python CLI, **not an autonomous background agent**. The human initiates each audit and decides whether any proposed improvements should be implemented.

When asked to use this framework on another project:

1. Identify the **target** project, its actual ref/SHA and your available filesystem/GitHub/terminal permissions. Do not silently assume the framework repo is the target.
2. Follow the requested mode: new-project planning, in-progress assessment or existing-project audit. Broad audit requests start **read-only** and cover all applicable dimensions in `docs/PROJECT_AUDIT.md`.
3. Run Hybrid CLI commands only if genuinely available. Report partial scans, inaccessible files, and tests not run. Keep confirmed findings separate from suspected risks.
4. Deliver an evidence-based report and prioritized improvement plan **before code changes**.
5. After a specific authorization, prepare changes on an isolated branch and verify them; PR Draft needs authorization. Never infer permission for merge, deploy, secrets, migrations or production changes.

For v0.11.1 candidate, a large `project-audit` may append a `workspace` report
from automatically bounded file batches. Report its per-file scope and cross-batch
limitations separately from the original assessment; do not claim pentest, live
database checks or project test execution. Honor any provider security gates.

When this repository is referenced by URL from **another working directory**, the agent must actually fetch/read these instructions with available access. Having a `CLAUDE.md` in the Hybrid repository does not make it automatically available to an unrelated project or grant GitHub permissions.
