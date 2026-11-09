# Universal agent executor — experimental v0.7

The Hybrid Engine can now drive **a trusted, locally installed agent of any
provider** through a simple JSON-over-stdio adapter. ChatGPT with an authorized
GitHub connector can follow the same protocol directly without installing a CLI.
Codex is **optional**, not a dependency. No API subscription is bundled.

## Safe sequence

1. Audit *only specified exact files* on a pinned GitHub commit.
2. Read those files with blob SHAs into a bounded source package.
3. Send the package via stdin to the **explicitly selected executable**.
4. Accept a proposed JSON change-set via stdout. The agent is responsible for
   investigation and authoring; no provider-specific API is presumed.
5. Run the existing SHA, file scope, branch and manifest validation gate.
6. Default to **PREVIEW**. With `--apply`, create an isolated **draft PR only**.
7. Independently run project CI, then evaluate PR-head checks against a named
   required-check policy. Never merge or deploy automatically.

## Command

```bash
# Example placeholder adapter. The adapter must read JSON stdin and emit
# a complete reviewed change-set JSON on stdout; a normal prose response fails.
hybrid gh-agent --repo OWNER/REPO \
  --goal "HYBRID DEBUG: repair a read-only UI bug" \
  --path src/components/Status.tsx \
  --agent-bin /path/to/trusted-agent-adapter

# Explicit GitHub write permission only for a new draft PR:
hybrid gh-agent --repo OWNER/REPO \
  --goal "HYBRID DEBUG: repair a read-only UI bug" \
  --path src/components/Status.tsx \
  --agent-bin /path/to/trusted-agent-adapter --apply
```

The agent adapter can use any model/CLI, or be a simple reviewed deterministic
program. It is given a JSON object:

```json
{
  "schema_version": 1,
  "protocol": "hybrid.agent-stdio.v1",
  "work_order": {"repo":"OWNER/REPO","base":"main","base_sha":"..."},
  "sources": [{"path":"src/app.ts","expected_sha":"...","content":"..."}],
  "output_contract": {"schema_version":1,"repo":"OWNER/REPO","base":"main","expected_base_sha":"..."},
  "safety": ["..."]
}
```

Its stdout must conform to the `gh-execute` change-set schema in
[AGENT_HANDOFF.md](AGENT_HANDOFF.md). An incorrect, out-of-scope, stale or
unreviewed manifest is rejected. A provider must be independently configured
to produce code; an unauthenticated local CLI does not conjure a model.

## Evidence-based verification

```bash
hybrid gh-verify --repo OWNER/REPO --pr 42 \
  --require-check "Frontend checks (read-only)" \
  --require-check "Edge Deno static checks (no cloud access)" \
  --require-check "postgrest-contract" \
  --output reports/pr-42.json --strict
```

The command writes `reports/pr-42.json` and `reports/pr-42.md`. It exits
non-zero in strict mode unless **all named checks** were observed as passed
for the current PR-head SHA and no other observed check failed or stayed
pending. A CI workflow must actually run; this command cannot trigger a
manual workflow or invent evidence. A green check is not a runtime guarantee.

## Security and limits

- Exact scopes only (1–20 regular files). Each source file <=64 KiB UTF-8.
- Protected paths (credentials, workflow files, migrations) are not sent.
- No shell evaluation, automatic dependency installation, merge or deploy.
- The agent is launched with a temporary HOME and minimal environment;
  GitHub credentials are not inherited. Selected model credentials can be
  explicitly passed with `--agent-env OPENAI_API_KEY`, for example.
- **A local agent binary is not sandboxed**: it could still access the
  machine/network using its process privileges. Install and invoke only
  trusted adapters in an isolated execution environment when possible.
- Source code is untrusted data, not agent instructions. Only a connected
  or configured agent can reason and generate a patch.
- Never pass secrets or private data to an external model without permission.
- `--apply` is GitHub-write opt-in, not permission to operate production.

No universal coding capability is promised in ChatGPT sessions without an
authorized code-edit connector or trusted external executable. The repository
records what was actually checked, not imagined autonomous test results.
