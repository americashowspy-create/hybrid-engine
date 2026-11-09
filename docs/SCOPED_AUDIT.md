# Exact-file scoped audits — Hybrid Engine v0.6

## Motivation

The default remote auditor intentionally inspects at most 250 source files.
That is not enough for projects such as MonitorSolar (over 300 eligible files).
A truncated audit remains **incomplete**, and cannot authorize automatic
repository-wide changes.

## Usage

\`\`\`bash
hybrid gh-audit --repo OWNER/REPO --ref main --path .gitignore
hybrid gh-workorder --repo OWNER/REPO --ref main \
  --goal "HYBRID AUDIT-FIX: protect environment files" \
  --path .gitignore --output order.json
hybrid gh-auto --repo OWNER/REPO \
  --intent "HYBRID AUDIT-FIX: secure ignore patterns" --path .gitignore
\`\`\`

Repeat \`--path\` for up to 20 exact **existing** UTF-8 files. The auditor
rejects missing, symlinked, oversized, duplicate and invalid paths. All reads
are pinned to a single commit SHA.

\`scope.mode = "exact_files"\`, \`scope.paths\`, and \`scope.complete\` are
included in the output. A complete scope means **only** those selected files
were readable and statically inspected. It never means that the entire
repository is secure.

For scoped work orders, \`gh-execute\` refuses edits to uninspected paths or
creation of uninspected new files. The existing per-file SHA validation,
expected branch SHA, authorization gate and draft-PR-only restrictions
remain mandatory.

No Tuya commands, cloud database writes, remote shell commands, production
deployments or automatic merges are introduced. No test is considered
PASSED until real, relevant execution evidence exists.
