# Architecture — v0.2.0

## Layer model

1. **Protocol / agent adapters**: AGENTS.md and portable markdown instructions. ChatGPT-first, no mandatory Codex.
2. **Router / Spec Engine**: `hybrid_engine.core` interprets user intent and chooses a single workflow with stages and gates.
3. **Security Engine**: `hybrid_engine.audit` performs low-impact repository checks, recognizes likely secrets, flags dynamic-code hazards, and reports stack evidence.
4. **Runner**: `hybrid_engine.runner` executes only recognized local test commands after explicit opt-in and collects real subprocess status.
5. **Continuity**: `hybrid_engine.store` writes JSON plans, security reports, and state in `.hybrid/`. These are local files; decide whether to commit selected artifacts.
6. **GitHub adapter**: optional authenticated read-only remote inventory, SHA-checked reviewed change-set, single atomic commit, isolated branch, draft PR; GitHub connector can independently perform the equivalent chat steps.
7. **GitHub / CI**: pull requests for code changes, workflow checks as independent evidence.

The Core does **not** automatically load and execute external prompt instructions. External frameworks remain optional and independently versioned.

## Future phases

- Scoped, permissioned executor integration for GitHub API/CLI, optional MCP adapters and machine-readable tool contracts.
- Safe fix suggestions with structured patches and human/agent review.
- Pluggable linters (Gitleaks, Opengrep, OWASP ZAP in passive mode), using pinned versions and constrained execution.
- **Security Validation + Pentest Gate**: future optional security adapter architecture with read-only report ingestion, independent validation and opt-in staging-only active scans. Detailed future design: [Security Validation roadmap](SECURITY_VALIDATION_ROADMAP.md) ([Issue #14](https://github.com/americashowspy-create/hybrid-engine/issues/14)); **not implemented or permitted by HYBRID AUTO**.
- Advanced capability detection; target-project-specific policy; persistent cross-chat state and audit histories; CI validation against fixture repositories.

No production deployment is included in the MVP.

## Optional deterministic executor (v0.4)

`auto_executor.run_auto` selects a workflow from the intent and uses an existing
read-only GitHub audit plus pinned commit checks. For an explicit `audit-fix`
intent, it can propose missing protective `.gitignore` patterns, and **only**
with `--apply` create an isolated draft PR via the existing GitHub adapter.
It rejects truncated audits, stale snapshots and unsafe file encodings.
It does not silently install software, execute source, call an LLM or claim
security fixes outside its specific rule.

## Agent-neutral code handoff (v0.5)

The `agent_bridge` module outputs bounded read-only repository findings,
routing, task steps and source SHA in JSON. A capable connected AI agent prepares
the actual source patch and tests. `gh-execute` rejects stale or mismatched
manifests and, only with explicit opt-in, opens a draft PR through the GitHub
adapter. No LLM API dependency, token in the chat, automatic merge, deploy or
arbitrary shell execution is included.
