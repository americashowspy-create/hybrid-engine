# Hybrid Engine — English overview

**From a plain-language request to a reviewable pull request, with explicit risk and verification gates.**

Hybrid Engine is an **v0.10.0 offline beta, agent-, interface-, and provider-neutral workflow** that combines its own implementation of planning, systematic debugging, review, safety gates and evidence-based delivery. It helps an authorized coding agent inspect repositories, establish scope, prepare a small patch, report evidence and open a **draft PR** when permitted.

**[Português](../README.md)** · [Portable agent protocol](../AGENTS.md) · [ChatGPT AUTO guide](CHATGPT_AUTO.md) · [Security](SECURITY.md) · [Contribution guide](../CONTRIBUTING.md)

> It is **not** a native plugin for any AI platform, an independent LLM, a security certification or an official integration of third-party frameworks. Code editing requires an actual agent with appropriate tools and permissions. The optional Python CLI does not generate arbitrary patches.

## Quick start — any capable AI agent

Use a **chat assistant with repository tools**, a **coding agent / IDE** or an optional **Python CLI**. The workflow is portable; actual GitHub write and terminal capabilities depend on the selected environment.

Open a fresh session or a repository checkout, explicitly ask the agent to read `AGENTS.md` and the [universal execution protocol](AGENT_AUTO.md), and replace the placeholder URL:

```text
HYBRID AUTO v0.10.0

Framework:
https://github.com/americashowspy-create/hybrid-engine

Target:
https://github.com/OWNER/REPOSITORY

Read AGENTS.md and docs/AGENT_AUTO.md.
Inspect the target branch, current SHA and open PRs.
Investigate one evidenced low-risk issue. If authorized, implement the
smallest safe fix on an isolated branch, run available safe tests and
open a DRAFT PR with diagnosis, evidence, limitations and rollback.

Do not merge, deploy, change credentials or touch production.
Do not claim a test passed unless it actually ran.
Report blocked permissions and missing tools explicitly.
```

A URL grants neither execution tools nor repository access. Read-only integrations cannot create PRs by themselves. This protocol does **not** mean every agent platform has completed independent integration testing.

## Available capabilities

| Capability | Description |
| --- | --- |
| Intent routing | AUTO / AUDIT / AUDIT-FIX / DEBUG / BUILD / REVIEW / STATUS workflows |
| Static source assessment | Heuristic security/quality indicators, with coverage limitations |
| Durable local output | `.hybrid/` plans, findings and status |
| SHA-bound handoff | Exact-file scope, source bundle and reviewed change-set validation |
| Guarded GitHub adapter | Read-only preview by default; explicit `--apply` opens **draft PR only** |
| CI evidence | `gh-verify` inspects actual PR-head checks, does not run CI |
| Optional GitHub Issues journal | Read/update task notes with explicit authorization |
| Optional local agent | JSON-over-stdio protocol to a trusted executable |

The remote broad audit has a 250-file cap. Scoped bundles are restricted to 1–20 regular text files (up to 64 KiB each). Running an external agent binary does **not** automatically sandbox it.

## Optional Python CLI

Requires Python 3.11+. From a local checkout:

```bash
python3 -m pip install .
hybrid --version
hybrid init --target /path/to/project
hybrid inspect --target /path/to/project
hybrid run --target /path/to/project --intent "audit the repository"
hybrid status --target /path/to/project
```

`hybrid run` prepares an audit and a plan; optional `--tests` executes recognized existing project test commands **after you review them for side effects**. It does not write code.

For an authorized GitHub token in your local environment (`GH_TOKEN` for private repos):

```bash
hybrid gh-audit --repo OWNER/REPOSITORY --ref main
hybrid gh-chat-package --repo OWNER/REPOSITORY \
  --goal "HYBRID DEBUG: fix a specific bug" \
  --path src/app.py --output /tmp/agent-bundle.json
hybrid gh-execute --bundle /tmp/agent-bundle.json \
  --manifest /tmp/reviewed-change.json
# Explicit --apply is required to request a draft PR.
```

A separate agent/developer must supply and review the change-set JSON. The bundle contains source code: keep it private.

## Security, cost and maturity

**v0.10.0 offline beta validation:** 251/251 Python 3.11 tests passed on the maintainer's Mac. A separate Radar Artístico checkout produced 12 suspected findings and 12 review orders with `BOUNDED_COMPLETE` scoped coverage and no repository changes. The hosted CI is **NOT VERIFIED** because GitHub Actions failed without retrievable logs while its included usage was exhausted. Earlier v0.9: 135 Python tests passed; its previous Radar pilot reported six suspected SQL policy findings.

- No automatic production deployment, merging or secret changes.
- No claim that static heuristics replace penetration testing or access-control validation.
- Local/offline tests do not consume GitHub-hosted Actions minutes; other execution services may have independent fees.
- Test results and CI are separate. Missing/pending checks are **not** passed checks.
- v0.8's Python suite passed **124 offline tests**, including four end-to-end tests against a **simulated GitHub client**; see [PR #9](https://github.com/americashowspy-create/hybrid-engine/pull/9). Real third-party GitHub projects require separate pilots.

**Private beta:** This repository is currently private; invitations are required to read it. Testers should use their **own** repositories and permissions. Feedback is welcome via [CONTRIBUTING.md](../CONTRIBUTING.md).

## More documentation

[Universal agent protocol](AGENT_AUTO.md) · [Full Portuguese README](../README.md) · [Workflow stages](WORKFLOWS.md) · [GitHub adapter](GITHUB_ADAPTER.md) · [Universal executor](UNIVERSAL_EXECUTOR.md) · [Evidence & task journal](TASK_JOURNAL.md)

Independent project implementing its own planning, diagnosis, review and verification workflows; **not** a fork or official integration of third-party frameworks. See [acknowledgements](../ACKNOWLEDGEMENTS.md). [MIT License](../LICENSE).
