"""Permissioned GitHub adapter: remote read-only audit and reviewed change-set PRs.

This code never invokes a coding agent, runs repository source, merges or deploys.
"""
from __future__ import annotations

import base64
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import uuid4

from .audit import MAX_BYTES, SCANNABLE, EXTRA_NAMES, SKIP_DIRS, scan

REPOSITORY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+$")
SHA = re.compile(r"^[0-9a-f]{40}$")
REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
MAX_REMOTE_FILES = 250
MAX_CHANGES = 20
MAX_CHANGE_BYTES = 256 * 1024


class GitHubError(RuntimeError):
    """Safe-to-display GitHub interaction error; never includes request secrets."""


class GitHubClient:
    """Small standard-library GitHub REST client, suitable for dependency injection."""

    def __init__(self, token: str | None = None, *, timeout: int = 15):
        self._token = token if token is not None else (
            os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
        )
        self.timeout = timeout

    def request(self, method: str, path: str, data: dict | None = None, *, allow_404: bool = False):
        if method not in ("GET", "POST"):
            raise ValueError("Unsupported GitHub API operation")
        if not path.startswith("/repos/") or "://" in path or any(c in path for c in "\r\n"):
            raise ValueError("Invalid GitHub API path")
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "HybridEngine/0.2",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = "Bearer " + self._token
        body = json.dumps(data).encode("utf-8") if data is not None else None
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = Request("https://api.github.com" + path, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if allow_404 and exc.code == 404:
                return None
            raise GitHubError(
                "GitHub API returned HTTP %d (verify repository, token scopes and access)." % exc.code
            ) from None
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise GitHubError("GitHub API request failed (%s)." % type(exc).__name__) from None


def validate_repo(repo: str) -> str:
    if not isinstance(repo, str) or not REPOSITORY.fullmatch(repo):
        raise ValueError("Repository must have the form owner/name")
    return repo


def validate_ref(ref: str) -> str:
    if not isinstance(ref, str) or not REF.fullmatch(ref) or ".." in ref or "//" in ref or ref.endswith(("/", ".lock")):
        raise ValueError("Unsafe Git reference")
    return ref


def safe_repo_path(raw: str) -> str:
    if not isinstance(raw, str) or not raw or "\\" in raw or "\x00" in raw or raw.startswith("/"):
        raise ValueError("Invalid repository path")
    path = PurePosixPath(raw)
    if str(path) != raw or any(part in (".", "..") for part in raw.split("/")):
        raise ValueError("Unsafe repository path")
    if path.parts[0].lower() in (".git", ".hybrid"):
        raise ValueError("Git internals and local state cannot be modified")
    return raw


def validate_change_path(raw: str) -> str:
    path = safe_repo_path(raw)
    lower = path.lower()
    parts = [part.lower() for part in PurePosixPath(path).parts]
    if (parts[:2] == [".github", "workflows"]
            or any(part.startswith(".env") for part in parts)
            or ("supabase" in parts and "migrations" in parts)
            or lower.endswith((".pem", ".key", ".p12", ".pfx"))):
        raise ValueError("Sensitive path requires a separate manually reviewed workflow: " + path)
    return path


def _repo_path(repo: str) -> str:
    return "/repos/" + validate_repo(repo)


def head_at(client: GitHubClient, repo: str, ref: str | None) -> tuple[str, str]:
    base = _repo_path(repo)
    if ref is None:
        metadata = client.request("GET", base)
        ref = metadata["default_branch"]
    ref = validate_ref(ref)
    if SHA.fullmatch(ref):
        return ref, ref
    response = client.request("GET", base + "/git/ref/heads/" + quote(ref, safe="/"))
    sha = response["object"]["sha"]
    if not SHA.fullmatch(sha):
        raise GitHubError("GitHub returned an invalid commit SHA")
    return ref, sha


def remote_audit(client: GitHubClient, repo: str, ref: str | None = None) -> dict:
    """Download a bounded, read-only source snapshot into a temporary directory."""
    base = _repo_path(repo)
    ref_name, sha = head_at(client, repo, ref)
    commit = client.request("GET", base + "/git/commits/" + sha)
    tree_sha = commit["tree"]["sha"]
    if not SHA.fullmatch(tree_sha):
        raise GitHubError("GitHub returned an invalid tree SHA")
    tree = client.request("GET", base + "/git/trees/" + tree_sha + "?recursive=1")
    if tree.get("truncated"):
        raise GitHubError("GitHub truncated the repository tree; full audit unavailable.")
    candidates = []
    for item in tree.get("tree", []):
        if item.get("type") != "blob" or item.get("mode") == "120000":
            continue
        try:
            path = safe_repo_path(item["path"])
        except (KeyError, ValueError):
            continue
        name = PurePosixPath(path)
        if any(part in SKIP_DIRS for part in name.parts[:-1]):
            continue
        if name.suffix.lower() not in SCANNABLE and name.name not in EXTRA_NAMES:
            continue
        if item.get("size", 0) > MAX_BYTES:
            continue
        if not SHA.fullmatch(str(item.get("sha", ""))):
            continue
        candidates.append((path, item["sha"]))

    limited = len(candidates) > MAX_REMOTE_FILES
    selected = candidates[:MAX_REMOTE_FILES]
    unavailable = 0
    with tempfile.TemporaryDirectory(prefix="hybrid-remote-") as tmp:
        root = Path(tmp)
        for path, blob_sha in selected:
            blob = client.request("GET", base + "/git/blobs/" + blob_sha)
            if blob.get("encoding") != "base64":
                unavailable += 1
                continue
            try:
                content = base64.b64decode(blob["content"], validate=False)
            except (ValueError, KeyError):
                unavailable += 1
                continue
            if len(content) > MAX_BYTES or b"\x00" in content:
                unavailable += 1
                continue
            dest = root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
        output = scan(root)
    output["target"] = "github:" + repo + "@" + ref_name
    output["source_sha"] = sha
    output["mode"] = "remote-read-only"
    output["source_files"] = len(candidates)
    output["files_unavailable"] = unavailable
    output["truncated"] = bool(limited or output["truncated"])
    if limited or unavailable:
        output["limitations"].append(
            "Remote audit incomplete: file cap or unreadable files; do not interpret missing findings as safe."
        )
    output["tests"] = {"status": "NOT_RUN", "reason": "Remote source inspection never executes code."}
    return output


def validate_changeset(data: dict) -> dict:
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("change-set must be an object with schema_version: 1")
    repo = validate_repo(data.get("repo"))
    base = validate_ref(data.get("base", "main"))
    if SHA.fullmatch(base):
        raise ValueError("The PR base must be a branch, not a commit SHA")
    title = data.get("title")
    if not isinstance(title, str) or not 5 <= len(title) <= 160:
        raise ValueError("PR title must be 5-160 characters")
    body = data.get("body", "")
    if not isinstance(body, str) or len(body) > 10000:
        raise ValueError("Invalid PR body")
    changes = data.get("changes")
    if not isinstance(changes, list) or not 1 <= len(changes) <= MAX_CHANGES:
        raise ValueError("Change-set must contain 1-20 files")
    seen = set()
    normalized = []
    for item in changes:
        if not isinstance(item, dict):
            raise ValueError("Each change must be an object")
        path = validate_change_path(item.get("path"))
        if path in seen:
            raise ValueError("Duplicate path in change-set: " + path)
        seen.add(path)
        expected = item.get("expected_sha", "MISSING")
        if expected is not None and (not isinstance(expected, str) or not SHA.fullmatch(expected)):
            raise ValueError("expected_sha must be a 40-char Git blob SHA or null for a new file")
        if expected == "MISSING":
            raise ValueError("expected_sha is required for optimistic concurrency")
        content = item.get("content")
        if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_CHANGE_BYTES:
            raise ValueError("Each file must contain UTF-8 text <= 256KiB")
        normalized.append({"path": path, "expected_sha": expected, "content": content})
    return {"repo": repo, "base": base, "title": title, "body": body, "changes": normalized}


def propose_changes(client: GitHubClient, document: dict, *, apply: bool = False) -> dict:
    """Verify all expected file SHAs before optional atomic commit and draft PR."""
    change_set = validate_changeset(document)
    repo, base_ref = change_set["repo"], change_set["base"]
    prefix = _repo_path(repo)
    _, base_sha = head_at(client, repo, base_ref)
    for item in change_set["changes"]:
        path = quote(item["path"], safe="/")
        current = client.request(
            "GET", prefix + "/contents/" + path + "?ref=" + base_sha, allow_404=True
        )
        if item["expected_sha"] is None:
            if current is not None:
                raise GitHubError("Expected new file already exists: " + item["path"])
        elif (not isinstance(current, dict) or current.get("type") != "file"
              or current.get("sha") != item["expected_sha"]):
            raise GitHubError("File changed or unavailable; rebase required: " + item["path"])

    preview = {
        "status": "PREVIEW", "repo": repo, "base": base_ref, "base_sha": base_sha,
        "files": [item["path"] for item in change_set["changes"]],
        "writes_performed": False, "tests": "NOT_RUN",
    }
    if not apply:
        return preview

    base_commit = client.request("GET", prefix + "/git/commits/" + base_sha)
    base_tree_sha = base_commit["tree"]["sha"]
    existing_tree = client.request("GET", prefix + "/git/trees/" + base_tree_sha + "?recursive=1")
    if existing_tree.get("truncated"):
        raise GitHubError("GitHub truncated base tree; refusing to change file modes blindly.")
    modes = {entry["path"]: entry["mode"] for entry in existing_tree.get("tree", [])
             if entry.get("type") == "blob" and entry.get("mode") in ("100644", "100755")}
    for item in change_set["changes"]:
        if item["expected_sha"] is not None and item["path"] not in modes:
            raise GitHubError("Unable to verify file mode: " + item["path"])
    entries = []
    for item in change_set["changes"]:
        blob = client.request("POST", prefix + "/git/blobs", {
            "content": base64.b64encode(item["content"].encode("utf-8")).decode("ascii"),
            "encoding": "base64",
        })
        entries.append({"path": item["path"], "mode": modes.get(item["path"], "100644"),
                        "type": "blob", "sha": blob["sha"]})
    tree = client.request("POST", prefix + "/git/trees", {
        "base_tree": base_commit["tree"]["sha"], "tree": entries
    })
    commit = client.request("POST", prefix + "/git/commits", {
        "message": change_set["title"], "tree": tree["sha"], "parents": [base_sha]
    })
    new_sha = commit["sha"]
    if not SHA.fullmatch(new_sha):
        raise GitHubError("GitHub returned an invalid new commit SHA")
    branch = "hybrid/" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:6]
    client.request("POST", prefix + "/git/refs", {
        "ref": "refs/heads/" + branch, "sha": new_sha
    })
    try:
        pr = client.request("POST", prefix + "/pulls", {
            "title": change_set["title"], "body": change_set["body"],
            "head": branch, "base": base_ref, "draft": True
        })
    except GitHubError as exc:
        raise GitHubError("Commit pushed to branch " + branch + " but draft PR creation failed. " + str(exc)) from None
    return {
        "status": "DRAFT_PR_CREATED", "repo": repo, "base": base_ref,
        "branch": branch, "commit_sha": new_sha, "pr_url": pr["html_url"],
        "pr_number": pr["number"], "files": preview["files"],
        "writes_performed": True, "tests": "NOT_RUN",
        "notice": "PR created, not merged; check independent CI results before approval."
    }
