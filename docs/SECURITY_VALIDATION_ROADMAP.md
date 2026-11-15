# Security Validation + Pentest Gate — FUTURE PHASE (design only)

> **Not implemented.** This page records the architecture and admission gates for an eventual security-validation phase. It does not enable scanners, install skills, authorize active tests, or modify the current `hybrid assess` behavior. Follow [Issue #14](https://github.com/americashowspy-create/hybrid-engine/issues/14) for scope and acceptance criteria.

## Why this belongs in Hybrid Engine

Hybrid Engine currently provides bounded offline static findings (general audit, DB Guard) and a v0.10 assessment prototype. These outputs **do not verify** exploitability, effective authorization, actual RLS, or security of running applications.

The future security layer should **validate risk evidence**, then hand confirmed or unresolved issues to the existing AI Implementation Advisor and SHA-checked branch/PR workflow. It should not become a second product, a required third-party provider, or an implicit active scanner.

## Product sequence and boundaries

1. **v0.10 Audit Intelligence:** finish normalizing static findings, recommendations, coverage and honest `NOT_VERIFIED` statuses; existing [Issue #13](https://github.com/americashowspy-create/hybrid-engine/issues/13).
2. **AI Implementation Advisor:** transform reviewed findings into actionable, scoped, reversible work orders.
3. **Security Validation (future, staged):**
   - Phase A: report contracts, offline JSON/SARIF ingestion, redaction, provenance and de-duplication using synthetic fixtures.
   - Phase B: **optional** deterministic scanners and code-review agents under isolated, permissioned execution.
   - Phase C: independent confirmation on a disposable test environment; optional Supabase Advisors **read-only** with separate permission.
   - Phase D: authorized DAST/pentest on isolated staging using optional Strix integration; never as a default command.
4. **Later:** opt-in recurring scans only after gated workflows have been validated; no implicit authorization or scheduled probing.

Version numbers and delivery dates for these future phases are intentionally unset.

## Tool fit: adapters, not bundled dependencies

| Component | Appropriate role | Hard boundary |
| --- | --- | --- |
| Built-in scanner + DB Guard | Free, offline source leads and coverage | Not a pentest; does not attest to live RLS |
| Optional deterministic SAST/dependency/secret tools | Reproducible signals with pinned binaries, no LLM required | Review supply chain, install and offline/online behavior individually |
| [Cloudflare Security Audit Skill](https://github.com/cloudflare/security-audit-skill) | Structured, source-first agent audit with independent validation | Requires a capable coding agent; safe sandbox for any target execution; otherwise `NEEDS_VALIDATION` |
| [Codex Security](https://github.com/openai/codex-security) | Optional provider for code/diff analysis, validation and exported findings | Provider access, authentication, billing and network policies are external; not a framework requirement |
| [Supabase Advisors](https://supabase.com/docs/guides/observability/advisors) | Optional observed DB security/performance signals | Explicit project selection, read-only metadata privileges; no production mutations or secret exposure |
| [Strix](https://github.com/usestrix/strix) | Dynamic, controlled validation of web/API issues on staging | Active probing only after a **separate signed-off test scope** and enforceable network/safety gates |

Do not vendor these projects into the Hybrid Engine core. Do not make the base Python package require Docker, credentials, APIs, paid plans, Codex or cloud runners. Third-party installers and skills are not automatically trustworthy or version pinned; review them before any installation and never run `curl | bash` or unreviewed `npx latest` inside an assessment.

## Proposed opt-in command semantics (NOT IMPLEMENTED)

- `HYBRID SECURITY-AUDIT`: source assessment plus optional import/run of explicitly enabled **non-invasive** analyzers; read-only by default.
- `HYBRID PENTEST`: **always explicitly invoked**, invokes a constrained external executor after authorization and staging validation.
- `HYBRID AUTO` and `hybrid assess` must **never** enable pentest or access live production automatically.

These are protocol proposals, not commands available in the current CLI.

## Shared evidence contract

Use the existing assessment structure rather than a new risk database:

- Findings: stable ID/fingerprint, rule, category, severity, source, tool version, target Git SHA, location, confidence and proof metadata (redacted), no secrets or raw exploit payloads in generic reports.
- Evidence lifecycle: `SUSPECTED`, `NEEDS_VALIDATION`, `CONFIRMED_IN_ISOLATION`, `CONFIRMED_IN_STAGING`, `FALSE_POSITIVE_REVIEWED`, `NOT_TESTED`.
- Coverage: file inventory, network target allowlist, excluded paths, truncation, scan duration and result status `INCOMPLETE` or `BLOCKED` when appropriate.
- Deduplicate by underlying issue and affected trust boundary while preserving each tool's individual evidence and contradictory findings.
- Recommendations feed the existing Advisor; no patch, PR, merge, deploy or security-policy change without separate authorization.
- Report formats: JSON and Markdown first; SARIF import/export only where technically verified.

A tool's claim of "validated" is not itself enough for `CONFIRMED_IN_STAGING`: require reproducible, scoped evidence and independent review where possible.

## Threat-aware execution gate for future DAST

**No test starts unless all gates below pass. Missing gate => `BLOCKED` / `NOT_RUN`.**

- Explicit, per-run permission from the asset owner; exact URLs/hosts and allowed operations, testing window, named staging environment and contact for emergency stop.
- Separate disposable staging with **synthetic users/data** and isolated database; no production Supabase, Turo, Vercel production domains, third-party APIs, real payment/email/SMS endpoints, or customer accounts.
- Runtime-enforced domain/IP/DNS/port allowlists, egress restrictions, anti-SSRF and DNS rebinding protection, resource limits, rate limits, request/time/cost caps and a working kill switch. A prompt-level instruction alone is insufficient.
- No destructive requests, persistent modification, denial-of-service, credential theft, lateral movement or third-party probing. Isolate, monitor and discard the sandbox.
- No real secrets in prompt, scan result, logs or external SaaS uploads. Uploading proprietary source to cloud tools requires deliberate review of permissions, retention and price.
- Versions and installer hashes pinned and reviewed. If the external tool cannot respect the envelope, refuse active execution.
- All cloud/provider costs, permission requirements and result limitations must be shown **before** scanning.

## Proposed validation progression

1. Synthetic fixtures: valid/invalid reports, conflicting tool findings, duplicate vulnerabilities, redaction of tokens and hostile or oversized parser inputs.
2. Local simulated scan on deliberately vulnerable sample code and throwaway database, with networking disabled.
3. Provider adapters under sandbox, verifying zero surprise network access and correct `NOT_TESTED` handling when unavailable.
4. Strix test in intentionally vulnerable **staging** with measured bounds; verify safety-stop behavior before any real project pilot.
5. Only after approval, try Fun Holidays or Radar Artístico **clones/staging** (auth/tenant isolation, RLS, Edge Functions, API exposure) using test identities and synthetic records. No production probe as part of this roadmap.

## Explicit exclusions

No implementation in v0.10; no mandatory skill installation; no direct cloud scanning; no new GitHub Actions workflows while billing is blocked; no automatic tests of URLs; no exploitation of live services; no production migrations, secret access, auto-remediation, or unreviewed PR merging.

**Decision:** Adopt a **defense-in-depth, adapter-based security-validation architecture** later. The first future security increment should be an **offline evidence bridge**, not immediate integration of an active pentesting agent.
