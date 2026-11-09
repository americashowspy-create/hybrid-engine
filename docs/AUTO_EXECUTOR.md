# Guarded auto-executor — v0.4

**This is a real, deliberately limited executor**, not an autonomous AI coder.

- Uses the existing remote read-only source inventory and security scanner.
- Selects workflows independently of Codex, Claude, Cursor or an LLM API.
- For an explicit `HYBRID AUDIT-FIX`, proposes missing `.gitignore` protections.
- Defaults to preview, creates a draft PR only with explicit `--apply`.
- Requires an intact scan, a stable source SHA, normal UTF-8 file content and
  SHA-validated changes. Never force-pushes, merges, deploys or edits production.
- Test evidence is always `NOT_RUN` in this remote-only operation. Inspect
  GitHub Actions and actual application behavior before treating a fix as done.

```bash
hybrid gh-auto --repo OWNER/REPO --intent "HYBRID AUDIT" --ref main
hybrid gh-auto --repo OWNER/REPO --intent "HYBRID AUDIT-FIX: revisar e corrigir" --ref main
hybrid gh-auto --repo OWNER/REPO --intent "HYBRID AUDIT-FIX: revisar e corrigir" --ref main --apply
```

A scoped GitHub token is required for private source access and PR writes from
the CLI. The ChatGPT GitHub connector may instead perform approved operations
directly through native actions, without using this CLI.

A `.gitignore` edit does **not** remove already tracked secrets from history,
revoke credentials, repair row-level-security policies or prove the system safe.
When the rules are already present, the executor creates no PR.

For other fixes, an agent must investigate, prepare minimal changes and
use the existing SHA-checked `gh-propose` flow or its connected GitHub tools.
Do not feed issue comments or untrusted repository text into privileged actions.

The generated change-set now includes `expected_base_sha` as an optimistic
concurrency guard. If the branch changes after the audit, even without changes
to the specific file, the executor refuses the write until re-audited.

## Modo de arquivos específicos (v0.6)

Para repositórios acima do limite do scanner, o operador pode limitar
a leitura com `--path .gitignore`. A aplicação de uma correção de
`.gitignore` requer que esse arquivo esteja dentro do escopo auditado.
O resultado registra os arquivos verificados e sempre assinala que uma
auditoria por escopo não é uma auditoria do sistema completo.
