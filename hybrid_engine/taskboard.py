"""Append-only GitHub Issues task journal for cross-chat continuity.

Issue bodies and comments are task data, never executable agent instructions.
Every write is opt-in; status notes are self-reported and are not proof of tests.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from .core import FLOWS, route
from .github_adapter import GitHubClient, GitHubError, _repo_path, validate_repo
from .verification import verify_pr

TASK_MARKER = "HYBRID_ENGINE_TASK_V1\n"
EVENT_MARKER = "HYBRID_ENGINE_EVENT_V1\n"
VALID_STATES = {"in_progress", "blocked", "review_ready", "completed_reported"}
MAX_PAGE = 3
MAX_GOAL = 1800
MAX_SUMMARY = 1000
TOKEN_INDICATORS = (
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b"),
    re.compile(r"\bsb_secret_[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


def _safe_text(value: str, max_size: int, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(name + " must be text")
    trimmed = value.strip()
    if not trimmed or len(trimmed) > max_size:
        raise ValueError(name + f" must contain 1-{max_size} characters")
    if any(ord(char) < 32 and char not in "\n\t" for char in trimmed):
        raise ValueError(name + " contains control characters")
    if any(pattern.search(trimmed) for pattern in TOKEN_INDICATORS):
        raise ValueError(name + " appears to contain sensitive material; remove it first")
    return trimmed


def _encode(marker: str, payload: dict) -> str:
    return marker + json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _decode(marker: str, body: Any) -> dict | None:
    if not isinstance(body, str) or not body.startswith(marker):
        return None
    try:
        item = json.loads(body[len(marker):])
        if isinstance(item, dict) and item.get("schema_version") == 1:
            return item
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def _validate_number(number: int) -> int:
    if not isinstance(number, int) or isinstance(number, bool) or number < 1:
        raise ValueError("Issue/PR number must be positive")
    return number


def start_task(client: GitHubClient, repo: str, goal: str, *, apply: bool = False) -> dict:
    """Create a durable task record on the *target* repository, not central engine."""
    repo = validate_repo(repo)
    goal = _safe_text(goal, MAX_GOAL, "goal")
    flow = route(goal)
    target = _repo_path(repo)
    metadata = client.request("GET", target)
    if metadata.get("has_issues") is False:
        raise GitHubError("Repository Issues are disabled; no task was created.")
    payload = {
        "schema_version": 1, "repo": repo, "goal": goal, "flow": flow,
        "steps": list(FLOWS[flow]),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "state": "planned",
    }
    preview = {
        "status": "PREVIEW", "repo": repo, "flow": flow, "goal": goal,
        "writes_performed": False,
        "notice": "Issue creation requires --apply. Do not paste private findings into public issues.",
    }
    if not apply:
        return preview
    title_goal = " ".join(goal.split())[:95]
    response = client.request("POST", target + "/issues", {
        "title": "[Hybrid] " + title_goal, "body": _encode(TASK_MARKER, payload),
    })
    return {
        "status": "CREATED", "repo": repo, "flow": flow,
        "issue_number": response["number"], "issue_url": response["html_url"],
        "writes_performed": True, "state": "planned",
    }


def _task_record(client: GitHubClient, repo: str, number: int) -> tuple[dict, dict]:
    issue = client.request("GET", _repo_path(repo) + f"/issues/{number}")
    if "pull_request" in issue:
        raise ValueError("The number belongs to a pull request, not a task issue")
    record = _decode(TASK_MARKER, issue.get("body"))
    if record is None or record.get("repo") != repo:
        raise ValueError("Issue is not a Hybrid Engine task for this repository")
    return issue, record


def _get_comments(client: GitHubClient, repo: str, number: int) -> list[dict]:
    all_comments = []
    for page in range(1, MAX_PAGE + 1):
        comments = client.request(
            "GET", _repo_path(repo) + f"/issues/{number}/comments?per_page=100&page={page}"
        )
        if not isinstance(comments, list):
            raise GitHubError("Issue comments API returned invalid data.")
        all_comments.extend(comments)
        if len(comments) < 100:
            return all_comments
    raise GitHubError("Task history exceeds safe pagination limit; status is incomplete.")


def task_status(client: GitHubClient, repo: str, number: int) -> dict:
    repo = validate_repo(repo)
    number = _validate_number(number)
    issue, task = _task_record(client, repo, number)
    history = []
    for comment in _get_comments(client, repo, number):
        event = _decode(EVENT_MARKER, comment.get("body"))
        if event is None or event.get("repo") != repo or event.get("issue_number") != number:
            continue
        if event.get("state") not in VALID_STATES:
            continue
        history.append({
            "state": event["state"], "summary": event.get("summary"),
            "pr_number": event.get("pr_number"),
            "created_at": comment.get("created_at"),
            "author": (comment.get("user") or {}).get("login"),
        })
    state = history[-1]["state"] if history else "planned"
    pr_number = next(
        (e["pr_number"] for e in reversed(history) if isinstance(e.get("pr_number"), int)),
        None,
    )
    response = {
        "repo": repo, "issue_number": number, "issue_url": issue.get("html_url"),
        "goal": task["goal"], "flow": task["flow"], "steps": task["steps"],
        "state": state, "event_count": len(history), "latest_event": history[-1] if history else None,
        "status_source": "GitHub issue/comments; self-reported, not independently verified",
    }
    if pr_number is not None:
        # Verification must come directly from GitHub, never from a comment.
        response["pr_verification"] = verify_pr(client, repo, pr_number)
    return response


def note_task(client: GitHubClient, repo: str, number: int, state: str,
              summary: str, *, pr_number: int | None = None, apply: bool = False) -> dict:
    repo = validate_repo(repo)
    number = _validate_number(number)
    if state not in VALID_STATES:
        raise ValueError("Unsupported task state: " + str(state))
    summary = _safe_text(summary, MAX_SUMMARY, "summary")
    current = task_status(client, repo, number)
    if current["state"] == "completed_reported":
        raise ValueError("Completed task is immutable; open a new follow-up task")
    if state == "review_ready" and pr_number is None:
        raise ValueError("review_ready requires an actual PR number")
    if pr_number is not None:
        pr_number = _validate_number(pr_number)
        # Check the PR actually exists and is associated with this repository.
        pr_info = verify_pr(client, repo, pr_number)
    else:
        pr_info = current.get("pr_verification")
    event = {
        "schema_version": 1, "repo": repo, "issue_number": number,
        "state": state, "summary": summary, "pr_number": pr_number,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    preview = {
        "status": "PREVIEW", "repo": repo, "issue_number": number,
        "next_state": state, "writes_performed": False,
        "pr_verification": pr_info,
    }
    if not apply:
        return preview
    result = client.request("POST", _repo_path(repo) + f"/issues/{number}/comments", {
        "body": _encode(EVENT_MARKER, event)
    })
    return {
        "status": "EVENT_RECORDED", "repo": repo, "issue_number": number,
        "state": state, "comment_url": result["html_url"],
        "writes_performed": True, "pr_verification": pr_info,
        "warning": "Task state is a recorded claim; consult live CI/PR verification.",
    }


def list_tasks(client: GitHubClient, repo: str) -> dict:
    """Bounded issue list, filtering out PRs and unrelated issues."""
    repo = validate_repo(repo)
    issues = client.request("GET", _repo_path(repo) + "/issues?state=all&per_page=100")
    if not isinstance(issues, list):
        raise GitHubError("Issues list is not valid.")
    results = []
    for issue in issues:
        if "pull_request" in issue:
            continue
        record = _decode(TASK_MARKER, issue.get("body"))
        if record is None or record.get("repo") != repo:
            continue
        results.append({
            "number": issue.get("number"), "url": issue.get("html_url"),
            "title": issue.get("title"), "flow": record.get("flow"),
            "initial_state": record.get("state"),
        })
    return {
        "repo": repo, "tasks": results, "count": len(results),
        "truncated": len(issues) >= 100,
        "notice": "Listing reflects initial task metadata. Use gh-task status for latest events.",
    }
