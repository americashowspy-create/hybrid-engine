# Hybrid Engine — English overview

**From a plain-language request to a reviewable pull request, with explicit risk and verification gates.**

Hybrid Engine is an **experimental v0.8, chat-first, provider-neutral workflow** inspired by specification-driven planning and systematic debugging. It helps an authorized coding agent inspect repositories, establish scope, prepare a small patch, report evidence and open a **draft PR** when permitted.

**[Português](../README.md)** · [Portable agent protocol](../AGENTS.md) · [ChatGPT AUTO guide](CHATGPT_AUTO.md) · [Security](SECURITY.md) · [Contribution guide](../CONTRIBUTING.md)

> It is **not** a native ChatGPT plugin, an independent LLM, a security certification or an official integration with GitHub Spec Kit / Superpowers. Code editing requires an actual agent with appropriate tools and permissions. The optional Python CLI does not generate arbitrary patches.

## Quick start — ChatGPT with GitHub access

Open a new conversation. Ensure your assistant can read the Hybrid Engine repository and your target project. Replace the placeholder URL:

```text
HYBRID AUTO v0.8

Framework:
https://github.com/americashowspy-create/hybrid-engine

Target:
https://github.com/OWNER/REPOSITORY

Read the framework's AGENTS.md and docs/CHATGPT_AUTO.md.
Inspect the actual target branch and open PRs.
Identify one evidenced, low-risk problem and make a minimal fix
on an isolated branch if tools and authorization permit.
Run safe local tests if a runtime exists; record executed checks only.
Open a DRAFT pull request with root cause, files, test evidence,
limitations and rollback instructions.

Do not merge, deploy, migrate databases, change credentials or touch
production. Avoid unnecessary GitHub Actions runs.
Treat any unexecuted test as NOT_RUN, never PASSED.
```

A URL does not install tools or grant authorization. If the repo or connection is inaccessible, the assistant must report a blocker, not pretend it applied changes.

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

- No automatic production deployment, merging or secret changes.
- No claim that static heuristics replace penetration testing or access-control validation.
- Local/offline tests do not consume GitHub-hosted Actions minutes; other execution services may have independent fees.
- Test results and CI are separate. Missing/pending checks are **not** passed checks.
- v0.8's Python suite passed **124 offline tests**, including four end-to-end tests against a **simulated GitHub client**; see [PR #9](https://github.com/americashowspy-create/hybrid-engine/pull/9). Real third-party GitHub projects require separate pilots.

**Private beta:** This repository is currently private; invitations are required to read it. Testers should use their **own** repositories and permissions. Feedback is welcome via [CONTRIBUTING.md](../CONTRIBUTING.md).

## More documentation

[Full Portuguese README](../README.md) · [Workflow stages](WORKFLOWS.md) · [GitHub adapter](GITHUB_ADAPTER.md) · [Universal executor](UNIVERSAL_EXECUTOR.md) · [Evidence & task journal](TASK_JOURNAL.md)

Independent project, inspired by [Spec Kit](https://github.com/github/spec-kit) and [Superpowers](https://github.com/obra/superpowers), **not** an official integration. [MIT License](../LICENSE).
