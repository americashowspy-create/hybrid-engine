# Hybrid Engine

**Chat-first, agent-agnostic development orchestration** combining spec-driven planning, systematic debugging, security checks, quality gates, and persistent progress.

> **Status: v0.8 experimental / ChatGPT source bundles, optional agent executor and evidence gates.** This is an independent orchestration layer inspired by [GitHub Spec Kit](https://github.com/github/spec-kit) and [Superpowers](https://github.com/obra/superpowers). It is **not** a fork or an official integration, and does not bundle either project's source code.

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

## ChatGPT-first one-command workflow (v0.8 experimental)

Paste the target URL in ChatGPT together with:

```text
HYBRID AUTO
Projeto: https://github.com/OWNER/REPOSITORY
Audite, encontre um problema fundamentado, corrija em uma branch,
teste com evidências disponíveis e entregue uma PR draft.
Não faça merge ou deploy em produção.
```

An agent with connected GitHub tools can perform the inspected, SHA-bound
source changes directly **without Codex**. This is a portable instruction
protocol, not an executable ChatGPT plugin: external tools and their
permissions must actually be available. No unrestricted automatic fixing is
claimed. If GitHub Actions quota is exhausted, tests stay `CI_NOT_RUN`
rather than falsely passing.

The optional CLI now packages scoped source privately for another agent:

```bash
hybrid gh-chat-package --repo OWNER/REPO \
  --goal "HYBRID DEBUG: repair the bug" --path src/example.py \
  --output /tmp/hybrid-chat.json
hybrid gh-execute --bundle /tmp/hybrid-chat.json \
  --manifest /tmp/reviewed-changeset.json
# Only when authorized: add --apply to open a draft PR, never merge.
```

[ChatGPT AUTO protocol](docs/CHATGPT_AUTO.md). Package output is 0600
and contains private code; do not commit/share it with an unapproved provider.

## GitHub adapter (v0.2)

New optional commands can inspect a GitHub repository remotely **without running its code**, or apply an explicitly reviewed multi-file change-set to a **new branch and draft PR**. No Codex or LLM API is needed. A scoped `GH_TOKEN` is required to access private repositories with this local CLI.

```bash
hybrid gh-audit --repo OWNER/REPO --ref main --output audit.json
hybrid gh-propose --manifest reviewed-changeset.json             # preview, NO writes
hybrid gh-propose --manifest reviewed-changeset.json --apply     # branch + DRAFT PR
```

See [GitHub adapter guide](docs/GITHUB_ADAPTER.md). The ChatGPT connector can use its own GitHub tools instead, without invoking this CLI or providing a token in conversation.

**This still does not automatically generate code fixes.** An authorized agent or developer must prepare and review each change-set; CI and runtime verification remain separate.


## Universal agent adapter and evidence gates (experimental v0.7)

A provider-neutral stdio protocol now lets a **trusted local agent executable**
receive a SHA-pinned, exact-file source package and return its reviewed JSON
patch. The existing gate permits **only a draft PR with explicit `--apply`**.
ChatGPT may continue using authorized GitHub tools directly; Codex and model
APIs are not mandatory.

```bash
hybrid gh-agent --repo OWNER/REPO --goal "HYBRID DEBUG: repair issue" \
  --path src/app.py --agent-bin /path/to/trusted-adapter
# Preview by default; --apply creates only a draft PR.
hybrid gh-verify --repo OWNER/REPO --pr 42 \
  --require-check "test" --output reports/42.json --strict
```

This is a transport/protocol, **not a built-in LLM model**. Without an installed
agent, a ChatGPT GitHub connector, or other code-writing capability, the
framework cannot invent fixes. Agents are not sandboxed automatically.
`gh-verify` reads real PR-head evidence and never runs or fabricates CI.
See [universal executor](docs/UNIVERSAL_EXECUTOR.md).

## Exact-file scope for larger repositories (v0.6)

The default full-source audit retains a conservative 250-file cap. For larger
projects (such as MonitorSolar), use **explicit exact-file scoping**, without
pretending the entire repository was checked:

```bash
hybrid gh-audit --repo OWNER/REPO --path .gitignore
hybrid gh-workorder --repo OWNER/REPO --goal "HYBRID AUDIT-FIX: secure ignore rules" --path .gitignore --output order.json
hybrid gh-auto --repo OWNER/REPO --intent "HYBRID AUDIT-FIX" --path .gitignore
```

The audit response includes `scope.mode=exact_files`, the specific paths and
`scope.complete`. The agent patch gate rejects files outside the audit scope,
and scoped work orders cannot create uninspected files. A scope of one file is
**not** a full security audit. The default read-only command without `--path`
still reports incomplete coverage on large repos; no bypass was introduced.
See [Scoped audit guide](docs/SCOPED_AUDIT.md).

## AI-agent work orders (v0.5)

A CLI or ChatGPT agent can prepare a **commit-pinned work order**,
investigate source, create a reviewed change-set and submit it via an evidence gate.
**Codex is optional; no model API is bundled or required.**

```bash
hybrid gh-workorder --repo OWNER/REPO --goal "HYBRID DEBUG: corrigir bug" --output order.json
# Have an authorized coding agent inspect source and author a reviewed change-set:
hybrid gh-execute --order order.json --manifest reviewed-change.json          # PREVIEW
hybrid gh-execute --order order.json --manifest reviewed-change.json --apply  # draft PR
hybrid gh-verify --repo OWNER/REPO --pr 123
```

The JSON change-set must contain `expected_base_sha` matching the work order
and the actual Git blob SHA for each existing file. A changed branch or file
invalidates the proposal. None of these commands automatically generates
arbitrary fixes or tests the running application. ChatGPT can perform equivalent
operations through its connected GitHub tools instead of this CLI.
See [Agent handoff guide](docs/AGENT_HANDOFF.md).

## Guarded automatic execution (v0.4)

One command can route the request, inspect source and (if explicitly requested)
open a **draft PR for one narrowly defined deterministic remediation**:

```bash
hybrid gh-auto --repo OWNER/REPO --intent "HYBRID AUDIT-FIX: audite e corrija"             # preview
hybrid gh-auto --repo OWNER/REPO --intent "HYBRID AUDIT-FIX: audite e corrija" --apply    # guarded PR
hybrid gh-auto --repo OWNER/REPO --intent "HYBRID AUDIT"                                  # read-only
```

Only missing protective **.gitignore rules** are automatically modified in v0.4.
No other application bug, RLS flaw, token leak or test failure is magically fixed.
The executor will not run downloaded code, change production, or merge PRs.
Use the agent-agnostic workflow instructions in `AGENTS.md` for more complex
changes, and verify CI independently. See [executor guide](docs/AUTO_EXECUTOR.md).

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
