# Hybrid Engine

**Chat-first, agent-agnostic development orchestration** combining spec-driven planning, systematic debugging, security checks, quality gates, and persistent progress.

> **Status: MVP / experimental.** This is an independent orchestration layer inspired by [GitHub Spec Kit](https://github.com/github/spec-kit) and [Superpowers](https://github.com/obra/superpowers). It is **not** a fork or an official integration, and does not bundle either project's source code.

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
