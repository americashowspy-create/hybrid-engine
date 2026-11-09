# Hybrid Engine

**Chat-first, agent-agnostic development orchestration** combining spec-driven planning, systematic debugging, security checks, quality gates, and persistent progress.

> **Status: v0.3 experimental / partial automation.** This is an independent orchestration layer inspired by [GitHub Spec Kit](https://github.com/github/spec-kit) and [Superpowers](https://github.com/obra/superpowers). It is **not** a fork or an official integration, and does not bundle either project's source code.

## In one minute

From a terminal with Python 3.11+:

```bash
python -m pip install .
hybrid init --target /path/to/your/project
hybrid inspect --target /path/to/your/project
hybrid run --target /path/to/your/project --intent "audite, corrija e teste" --tests
hybrid status --target /path/to/your/project
```

The `run` command **routes the request**, produces a durable execution plan, runs a safe static security scan, and optionally runs the project's existing test script. It **does not** autonomously edit arbitrary source code, merge PRs or deploy. Those require an authorized agent/executor, connected tools and their permissions.

## Use straight from ChatGPT

Send this repository URL and your target project URL to a ChatGPT conversation with GitHub access, then ask:

```text
Use the workflow in https://github.com/americashowspy-create/hybrid-engine/blob/main/AGENTS.md
Project: https://github.com/OWNER/REPOSITORY
Command: HYBRID AUTO
Goal: inspect the project, diagnose root causes, fix safe issues in a branch,
run the available tests and open a PR with evidence.
Never claim tests ran unless there is a run log.
Do not merge, deploy, or change production data without approval.
```

**Important:** A URL is documentation, not executable software or automatic permission. The assistant needs to read the instructions and use its connected GitHub and execution tools. In chat environments without a terminal, the agent can inspect, edit and create PRs if connected, but cannot honestly claim local tests have run. CI can provide verifiable results.

## GitHub adapter (v0.2)

New optional commands can inspect a GitHub repository remotely **without running its code**, or apply an explicitly reviewed multi-file change-set to a **new branch and draft PR**. No Codex or LLM API is needed. A scoped `GH_TOKEN` is required to access private repositories with this local CLI.

```bash
hybrid gh-audit --repo OWNER/REPO --ref main --output audit.json
hybrid gh-propose --manifest reviewed-changeset.json             # preview, NO writes
hybrid gh-propose --manifest reviewed-changeset.json --apply     # branch + DRAFT PR
```

See [GitHub adapter guide](docs/GITHUB_ADAPTER.md). The ChatGPT connector can use its own GitHub tools instead, without invoking this CLI or providing a token in conversation.

**This still does not automatically generate code fixes.** An authorized agent or developer must prepare and review each change-set; CI and runtime verification remain separate.

## GitHub task journal and CI verification (v0.3)

Works with GitHub Issues as a persistent task history across ChatGPT conversations.
No Codex or external agent API is required. All state-changing operations
default to **PREVIEW** and require `--apply` explicitly.

```bash
hybrid gh-task start --repo OWNER/REPO --goal "Audite o sistema"     # preview
hybrid gh-task start --repo OWNER/REPO --goal "Audite o sistema" --apply
hybrid gh-task list --repo OWNER/REPO
hybrid gh-task status --repo OWNER/REPO --issue 15
hybrid gh-task note --repo OWNER/REPO --issue 15 --state blocked --summary "Missing test credentials"
hybrid gh-task note --repo OWNER/REPO --issue 15 --state review_ready --summary "PR ready" --pr 16 --apply
hybrid gh-verify --repo OWNER/REPO --pr 16
```

Requires a GitHub token with Issues permissions for writes; use least privilege.
**Public repository issues are public**: do not put private security findings,
secrets or sensitive business data into task goals or summaries.

`gh-verify` consults the live PR-head SHA and its reported GitHub checks.
`PASSED` means the observed checks passed, **not** that all tests exist or
the application is safe. Neither command merges or deploys. See
[task journal guide](docs/TASK_JOURNAL.md).

## Commands

| Command (conversation) | CLI example | Intent |
| --- | --- | --- |
| HYBRID AUTO | `hybrid run --intent "auto: ..." --target .` | Select appropriate steps |
| HYBRID AUDIT | `hybrid run --intent "audit" --target .` | Security & quality triage |
| HYBRID AUDIT-FIX | `hybrid run --intent "audite e corrija" --target .` | Plan + scan; agent applies fixes |
| HYBRID DEBUG | `hybrid run --intent "corrija o bug" --target .` | Root-cause-first |
| HYBRID BUILD | `hybrid run --intent "crie uma funcionalidade" --target .` | Specification-first |
| HYBRID REVIEW | `hybrid run --intent "revise o PR" --target .` | Scope & change review |
| HYBRID STATUS | `hybrid status --target .` | Resume state |

## Deliverables

- `.hybrid/state.json`: last request, selected workflow, status and artifact paths.
- `.hybrid/plans/<id>.json`: machine-readable work plan with stages and quality gates.
- `.hybrid/reports/<id>.json`: security findings, stack detection, limitations and evidence (paths and line numbers, no secret values).
- `.hybrid/reports/<id>.md`: human-readable report.

## Safety defaults

- No production writes, merges or deploys.
- No automatic arbitrary shell command execution.
- Tests run **only** with `--tests`, using a recognized project test command; existing scripts should be reviewed because they may have side effects.
- Static scan is heuristic, is not a penetration test, and cannot prove a site secure. Sensitive findings are redacted.
- Every terminal status and CI claim must be backed by a real tool result.
- Work in an isolated branch and request review for meaningful modifications.

See [Architecture](docs/ARCHITECTURE.md), [workflow protocol](docs/WORKFLOWS.md), [security policy](docs/SECURITY.md), and [attribution](ACKNOWLEDGEMENTS.md).

## Development

```bash
python -m unittest discover -s tests -v
python -m hybrid --help
```

Licensed under MIT. Contributions and testing are welcome.
