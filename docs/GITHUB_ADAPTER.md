# GitHub execution adapter (experimental v0.2)

An optional **standard-library Python** adapter for the Hybrid Engine. No Codex, OpenAI API key, Claude, or third-party model required.

## What works

- Read a GitHub repository **without cloning or running its code**, inspect a bounded source snapshot and produce redacted static findings.
- Validate a reviewed change-set against the **actual SHA of every target file**.
- Dry-run by default: validate inputs and check repository state but **write nothing**.
- With explicit `--apply`, create an atomic source commit on a new `hybrid/*` branch and open a **draft pull request**.
- Detect stale source files and reject edits; never write to `main` or merge a PR.

## What does not work (yet)

- No AI-generated code patches or autonomous remediation in this CLI. An authorized agent or engineer creates the reviewed change-set.
- No execution of remote tests; the remote audit reports `NOT_RUN`.
- No live site penetration testing, real RLS evaluation, dependency resolution, preview deployment or automatic production publication.
- GitHub access is subject to the active token's permissions. The ChatGPT GitHub connector has its own permissions and is not the same as this CLI's `GH_TOKEN`.

## Commands

Python 3.11+:

```bash
python -m pip install .
export GH_TOKEN=YOUR_PERSONAL_ACCESS_TOKEN   # scoped token; never commit it

# Read-only, redacted static audit (public repositories may work without token):
hybrid gh-audit --repo OWNER/REPOSITORY --ref main --output report.json

# Validate the proposed patch without changing GitHub:
hybrid gh-propose --manifest examples/changeset.example.json

# Only after reviewing the change-set and granting explicit approval:
hybrid gh-propose --manifest /path/to/changeset.json --apply
```

For a fine-grained GitHub token: audit needs **Contents: read**; draft-PR creation needs **Contents: read and write** plus **Pull requests: read and write** for the selected repository. Protect the token, use least privilege, and rotate it when necessary.

## Change-set JSON

```json
{
  "schema_version": 1,
  "repo": "OWNER/REPOSITORY",
  "base": "main",
  "title": "fix: explain the change",
  "body": "Why the change is safe, evidence and rollback notes.",
  "changes": [
    {"path": "src/example.ts", "expected_sha": null, "content": "export const example = true;\n"}
  ]
}
```

Set `expected_sha` to **null only for a file that does not yet exist**, otherwise use its current Git blob SHA. The SHA is checked at a pinned base commit. Protected paths (credentials, workflow files, Supabase migrations, key files) are deliberately excluded from this generic PR adapter.

Each apply creates **one commit** for all changed files on a fresh branch, then requests a **draft PR**. A failure opening the PR can leave the branch available for recovery. This never constitutes a test pass. Review CI results independently.

### Chat-first usage

In a ChatGPT conversation with a connected GitHub account you may write:

```text
Use https://github.com/americashowspy-create/hybrid-engine/blob/main/AGENTS.md
HYBRID AUDIT-FIX
Target: https://github.com/OWNER/REPOSITORY
Create a new branch, investigate, make the smallest approved fix, open a PR and show actual CI evidence.
Never merge or deploy unless separately authorized.
```

The assistant can use **its available connector tools directly** and does not need to run this CLI. The CLI is an additional execution option for local and CI environments, not a compulsory bridge.

## Safety limits

The remote audit downloads at most 250 source files, skips symlinks and large files, and refuses GitHub-truncated trees. It deliberately produces **incomplete coverage** on large repos. The output contains paths/line numbers and rule IDs, never matching secret contents. A clean result is not evidence that an application is secure.

The current dry-run performs remote **read** calls but no writes. Audits of unauthorized repositories and active probing against services are not supported.
