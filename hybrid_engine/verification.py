"""Independent GitHub PR check evaluator.

Returns evidence, not a guarantee of correct application behavior.
"""
from __future__ import annotations

import re

from .github_adapter import GitHubClient, GitHubError, _repo_path, validate_repo

COMMIT_SHA = re.compile(r"^[a-f0-9]{40}$")
CHECKS_LIMIT = 100


def verify_pr(client: GitHubClient, repo: str, number: int, *, required_checks: list[str] | None = None) -> dict:
    """Verify PR-head CI without treating missing checks as success.

    For a fork or private repo, check availability depends on token scopes and the
    repository in which the check suite was created.
    """
    validate_repo(repo)
    required = [] if required_checks is None else required_checks
    if (not isinstance(required, list) or len(required) > 30
            or any(not isinstance(name, str) or not 1 <= len(name) <= 120 for name in required)
            or len(set(required)) != len(required)):
        raise ValueError("required_checks must be a distinct list of up to 30 check names.")
    if not isinstance(number, int) or isinstance(number, bool) or number < 1:
        raise ValueError("PR number must be a positive integer")
    prefix = _repo_path(repo)
    pr = client.request("GET", f"{prefix}/pulls/{number}")
    head = pr["head"]["sha"]
    if not isinstance(head, str) or not COMMIT_SHA.fullmatch(head):
        raise GitHubError("GitHub returned an invalid PR-head commit SHA.")

    checks = client.request(
        "GET", f"{prefix}/commits/{head}/check-runs?filter=latest&per_page={CHECKS_LIMIT}"
    )
    statuses = client.request("GET", f"{prefix}/commits/{head}/status")
    runs = checks.get("check_runs", [])
    contexts = statuses.get("statuses", [])
    if not isinstance(runs, list) or not isinstance(contexts, list):
        raise GitHubError("Malformed checks response.")
    incomplete = checks.get("total_count", len(runs)) > len(runs)

    evidence = []
    states = []
    for check in runs:
        # The API can return checks for the same SHA that are not from this PR.
        if check.get("head_sha") not in (None, head):
            continue
        status = check.get("status", "unknown")
        conclusion = check.get("conclusion")
        outcome = (
            "PENDING" if status != "completed"
            else "PASSED" if conclusion == "success"
            else "FAILED" if conclusion in ("failure", "timed_out", "cancelled", "action_required")
            else "INCONCLUSIVE"
        )
        states.append(outcome)
        evidence.append({
            "source": "check_run", "name": str(check.get("name", ""))[:120],
            "outcome": outcome, "conclusion": conclusion,
            "url": check.get("html_url"),
        })
    for status in contexts:
        state = status.get("state")
        outcome = (
            "PASSED" if state == "success"
            else "FAILED" if state in ("failure", "error")
            else "PENDING" if state == "pending"
            else "INCONCLUSIVE"
        )
        states.append(outcome)
        evidence.append({
            "source": "commit_status", "name": str(status.get("context", ""))[:120],
            "outcome": outcome, "conclusion": state,
            "url": status.get("target_url"),
        })

    observed_names = {item["name"] for item in evidence}
    missing_checks = [name for name in required if name not in observed_names]
    if incomplete:
        verdict = "INCOMPLETE"
    elif not states:
        verdict = "NOT_RUN"
    elif "FAILED" in states:
        verdict = "FAILED"
    elif missing_checks:
        verdict = "MISSING_REQUIRED"
    elif "PENDING" in states:
        verdict = "PENDING"
    elif "INCONCLUSIVE" in states:
        verdict = "INCONCLUSIVE"
    else:
        verdict = "PASSED"

    merged = pr.get("merged") is True
    return {
        "repo": repo, "pr_number": number,
        "pr_url": pr.get("html_url", f"https://github.com/{repo}/pull/{number}"),
        "head_sha": head, "pr_state": pr.get("state"),
        "merged": merged, "merge_commit_sha": pr.get("merge_commit_sha") if merged else None,
        "ci": verdict, "check_count": len(evidence),
        "required_checks": required, "missing_required_checks": missing_checks,
        "checks": evidence,
        "limitations": [
            "Only checks and statuses discoverable for the current PR-head SHA are evaluated.",
            "PASSED means observable reported checks succeeded, not that production works.",
            "Only explicitly provided --require-check names define a required-check policy.",
        ],
    }
