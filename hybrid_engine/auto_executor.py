"""Guarded, model-neutral GitHub executor with one deterministic remediation.

Not a generic self-writing AI agent. It can scan, select a supported *safe*
remediation, validate a pinned target and (with explicit opt-in) create a draft PR.
All other remediation is deferred to an authorized coding agent/reviewed changeset.
"""
from __future__ import annotations

import base64
import re
from urllib.parse import quote

from .core import make_plan, route
from .github_adapter import (
    GitHubClient, GitHubError, MAX_CHANGE_BYTES, SHA, _repo_path,
    head_at, propose_changes, remote_audit, validate_repo, validate_ref,
)

IGNORE_RULES = (".env", ".env.*", "!.env.example", ".hybrid/")
MAX_IGNORE_SIZE = 64 * 1024


def _read_gitignore(client: GitHubClient, repo: str, commit_sha: str) -> tuple[str, str | None]:
    """Read an existing regular UTF-8 file at the immutable commit."""
    response = client.request(
        "GET", _repo_path(repo) + "/contents/.gitignore?ref=" + quote(commit_sha, safe=""),
        allow_404=True,
    )
    if response is None:
        return "", None
    if not isinstance(response, dict) or response.get("type") != "file":
        raise GitHubError(".gitignore is not a regular file; manual review required.")
    sha = response.get("sha")
    if not isinstance(sha, str) or not SHA.fullmatch(sha):
        raise GitHubError("GitHub returned invalid .gitignore blob SHA.")
    if response.get("encoding") != "base64" or not isinstance(response.get("content"), str):
        raise GitHubError("GitHub returned unreadable .gitignore contents.")
    try:
        raw = base64.b64decode("".join(response["content"].split()), validate=True)
        if len(raw) > MAX_IGNORE_SIZE or b"\x00" in raw:
            raise ValueError("Oversize or binary file")
        content = raw.decode("utf-8")
    except (ValueError, UnicodeError) as exc:
        raise GitHubError(".gitignore cannot be safely edited; manual review required.") from None
    return content, sha


def _suggest_gitignore(existing: str) -> tuple[str, list[str]]:
    """Append exact missing protective patterns, keeping existing lines intact."""
    if "\r" in existing:
        raise GitHubError("Unusual .gitignore line endings require manual review.")
    if len(existing.encode("utf-8")) > MAX_IGNORE_SIZE:
        raise GitHubError(".gitignore exceeds the safe remediation size limit.")
    current = {line.strip() for line in existing.splitlines()}
    missing = [rule for rule in IGNORE_RULES if rule not in current]
    if not missing:
        return existing, []
    separator = "" if not existing or existing.endswith("\n") else "\n"
    updated = existing + separator + "\n".join(missing) + "\n"
    if len(updated.encode("utf-8")) > MAX_CHANGE_BYTES:
        raise GitHubError("Proposed change is too large.")
    return updated, missing


def run_auto(client: GitHubClient, repo: str, intent: str, *, ref: str | None = None,
             apply: bool = False) -> dict:
    """Audit arbitrary intents; apply only a narrowly allowlisted gitignore fix.

    Never runs downloaded code, generates arbitrary source edits, merges, deploys,
    or changes authentication. The result explicitly distinguishes plans from acts.
    """
    repo = validate_repo(repo)
    if not isinstance(intent, str) or not 1 <= len(intent.strip()) <= 1800:
        raise ValueError("--intent is required (1-1800 characters)")
    mode = route(intent)
    if apply and mode != "audit-fix":
        raise ValueError("--apply is only supported for an explicit audit-and-fix request.")
    if ref is not None:
        ref = validate_ref(ref)
        if SHA.fullmatch(ref) and apply:
            raise ValueError("--apply requires a branch ref, not a detached commit.")
    plan = make_plan(intent, "github:" + repo)
    audit = remote_audit(client, repo, ref)
    limited = audit.get("truncated", False) or audit.get("files_unavailable", 0) > 0
    output = {
        "mode": mode,
        "repo": repo,
        "intent": intent,
        "plan": {"flow": plan["flow"], "steps": [item["name"] for item in plan["steps"]]},
        "audit": {
            "source_sha": audit["source_sha"],
            "files_scanned": audit["files_scanned"],
            "findings": audit["findings"],
            "truncated": bool(limited),
            "limitations": audit["limitations"],
        },
        "test_evidence": "NOT_RUN",
        "writes_performed": False,
        "status": "AUDITED",
        "limitations": [
            "Only a safe .gitignore remediation is automated; other issues require an authorized agent.",
            "A draft PR is not evidence that the application is fixed or tested.",
        ],
    }
    if mode != "audit-fix":
        output["next_action"] = "Inspect findings and use an authorized executor for scoped code changes."
        return output
    if limited:
        output["status"] = "INCOMPLETE_AUDIT"
        output["next_action"] = "Resolve missing files/scan limits before making automated changes."
        if apply:
            raise GitHubError("Refusing automated changes after incomplete remote audit.")
        return output

    # Never fix based on a stale remote snapshot.
    branch, current_sha = head_at(client, repo, ref)
    if current_sha != audit["source_sha"]:
        raise GitHubError("Source branch changed during audit; retry with a fresh snapshot.")
    if SHA.fullmatch(branch):
        output["status"] = "READ_ONLY_REF"
        output["next_action"] = "Choose a branch to propose the safe remediation."
        return output

    original, file_sha = _read_gitignore(client, repo, current_sha)
    updated, missing = _suggest_gitignore(original)
    output["proposed_fix"] = {"type": "gitignore_protection", "path": ".gitignore",
                              "rules_added": missing, "does_not_untrack_secrets": True}
    if not missing:
        output["status"] = "NO_SAFE_FIX_NEEDED"
        output["next_action"] = "Review scan findings with an authorized coding agent."
        return output

    manifest = {
        "schema_version": 1, "repo": repo, "base": branch,
        "title": "chore(security): add missing safe ignore rules",
        "body": (
            "Hybrid Engine deterministic remediation. Adds only missing .gitignore rules; "
            "does not modify previously tracked files, revoke credentials, test code, or "
            "claim all vulnerabilities are fixed. Review the diff and CI before merging."
        ),
        "changes": [{"path": ".gitignore", "expected_sha": file_sha, "content": updated}],
    }
    outcome = propose_changes(client, manifest, apply=apply)
    output["proposal"] = outcome
    output["writes_performed"] = bool(outcome.get("writes_performed", False))
    output["status"] = "DRAFT_PR_CREATED" if output["writes_performed"] else "PREVIEW"
    output["next_action"] = (
        "Review draft PR and real CI; never merge/deploy without authorization."
        if output["writes_performed"]
        else "Review proposed rule changes; repeat with --apply only when authorized."
    )
    return output
