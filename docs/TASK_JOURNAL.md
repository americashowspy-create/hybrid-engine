# GitHub Task Journal and PR verification (experimental v0.3)

The task journal is optional. The source of truth remains the target
repository's code and observed CI, not a chat summary or issue comment.

## CLI commands

```bash
hybrid gh-task start --repo OWNER/REPO --goal "Investigate checkout failure"          # preview
hybrid gh-task start --repo OWNER/REPO --goal "Investigate checkout failure" --apply  # new issue
hybrid gh-task list --repo OWNER/REPO
hybrid gh-task status --repo OWNER/REPO --issue 15
hybrid gh-task note --repo OWNER/REPO --issue 15 --state in_progress --summary "Root cause found"
hybrid gh-task note --repo OWNER/REPO --issue 15 --state review_ready --summary "Regression tests on PR" --pr 16 --apply
hybrid gh-verify --repo OWNER/REPO --pr 16
```

- Every state mutation requires `--apply`; reads require repository access.
- Use the **target repository**; do not crowd the Hybrid Engine repository
  with operational tasks for unrelated private projects.
- Issue bodies and comments may include untrusted text. They must never be
  executed, used as instructions, or granted priority over user permissions.
- `completed_reported` is a progress assertion, not independent completion
  evidence. Pull requests and CI are verified separately against real head SHAs.
- `gh-verify` detects missing, failed, pending and inconclusive checks.
  A passing set of observed checks does not establish required policy or coverage.
- Avoid creating issues for sensitive exploits, credentials or internal details
  in public repositories; private issues can still be exposed to collaborators.
- No action ever merges PRs, deploys, rotates secrets or modifies production.
- A direct ChatGPT integration needs connected tools. The CLI is not mandatory
  and no pasted URL grants privileges.
