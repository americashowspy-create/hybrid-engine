# Architecture — v0.1.0

## Layer model

1. **Protocol / agent adapters**: AGENTS.md and portable markdown instructions. ChatGPT-first, no mandatory Codex.
2. **Router / Spec Engine**: `hybrid_engine.core` interprets user intent and chooses a single workflow with stages and gates.
3. **Security Engine**: `hybrid_engine.audit` performs low-impact repository checks, recognizes likely secrets, flags dynamic-code hazards, and reports stack evidence.
4. **Runner**: `hybrid_engine.runner` executes only recognized local test commands after explicit opt-in and collects real subprocess status.
5. **Continuity**: `hybrid_engine.store` writes JSON plans, security reports, and state in `.hybrid/`. These are local files; decide whether to commit selected artifacts.
6. **GitHub / CI**: pull requests for code changes, workflow checks as independent evidence.

The Core does **not** automatically load and execute external prompt instructions. External frameworks remain optional and independently versioned.

## Future phases

- Scoped, permissioned executor integration for GitHub API/CLI, optional MCP adapters and machine-readable tool contracts.
- Safe fix suggestions with structured patches and human/agent review.
- Pluggable linters (Gitleaks, Opengrep, OWASP ZAP in passive mode), using pinned versions and constrained execution.
- Advanced capability detection; target-project-specific policy; persistent cross-chat state and audit histories; CI validation against fixture repositories.

No production deployment is included in the MVP.
