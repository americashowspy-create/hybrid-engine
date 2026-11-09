"""Export a reviewable, SHA-pinned source bundle for a connected chat coding agent.

Never invokes a model, prints source, changes a repository, merges or deploys.
The bundle is deliberately kept in a private local file, not in CI logs.
"""
from __future__ import annotations

import json
import os
import hashlib
from pathlib import Path

from .agent_bridge import KIND, MUTATING, prepare
from .github_adapter import GitHubClient, SHA, validate_change_path, validate_ref, validate_repo
from .universal import MAX_SOURCE_BYTES, source_package


def build_chat_package(client: GitHubClient, repo: str, goal: str,
                       paths: list[str], *, ref: str | None = None) -> dict:
    """Prepare an audit- and SHA-bound source bundle, with no GitHub writes."""
    if not isinstance(paths, list) or not paths:
        raise ValueError("Explicit exact-file paths are required for a chat package.")
    order = prepare(client, repo, goal, ref=ref, scope_paths=paths)
    if order.get("ready_for_proposal") is not True:
        raise ValueError("Chat package needs a complete scoped mutating work order.")
    return source_package(client, order)


def export_chat_package(client: GitHubClient, repo: str, goal: str,
                        paths: list[str], output: Path,
                        *, ref: str | None = None) -> dict:
    """Write source to a new user-owned private JSON file; stdout gets metadata only."""
    output = Path(output).expanduser()
    if output.suffix.lower() != ".json":
        raise ValueError("Chat package output must end with .json")
    if not output.parent.is_dir():
        raise ValueError("Chat package output directory must already exist")
    if output.is_symlink() or output.exists():
        raise ValueError("Refusing to overwrite an existing chat package")
    bundle = build_chat_package(client, repo, goal, paths, ref=ref)
    # No shell, no implicit directories, no overwrite, owner-read/write only.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    handle = os.open(output, flags, 0o600)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(bundle, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    order = bundle["work_order"]
    return {
        "status": "PACKAGE_EXPORTED",
        "repo": order["repo"],
        "base": order["base"],
        "base_sha": order["base_sha"],
        "scope_paths": [item["path"] for item in bundle["sources"]],
        "output": str(output),
        "protocol": bundle["protocol"],
        "agent": "NOT_INVOKED",
        "tests": "NOT_RUN",
        "github_writes": False,
        "notice": "Output contains private source. Do not commit, paste into logs, or send to an unapproved provider.",
        "next": "Have an authorized agent author a reviewed manifest; preview with gh-execute; draft PR only with --apply.",
    }


def work_order_from_bundle(bundle: dict) -> dict:
    """Reject tampered or incomplete source bundles before entering the PR gate.

    GitHub verifies current SHAs again during submission. These early checks
    prevent a hand-edited or truncated file from masquerading as an audited
    export. They do not authenticate the work-order author.
    """
    if (not isinstance(bundle, dict) or type(bundle.get("schema_version")) is not int
            or bundle["schema_version"] != 1
            or bundle.get("protocol") != "hybrid.agent-stdio.v1"):
        raise ValueError("Unsupported chat package schema or protocol")
    order, sources = bundle.get("work_order"), bundle.get("sources")
    if not isinstance(order, dict) or not isinstance(sources, list):
        raise ValueError("Malformed chat package")
    if (type(order.get("schema_version")) is not int or order["schema_version"] != 1
            or order.get("kind") != KIND or order.get("flow") not in MUTATING
            or order.get("ready_for_proposal") is not True
            or not isinstance(order.get("audit"), dict)
            or order["audit"].get("complete") is not True):
        raise ValueError("Package contains an incomplete or read-only work order")
    validate_repo(order.get("repo"))
    base = validate_ref(order.get("base"))
    sha = order.get("base_sha")
    if not isinstance(sha, str) or not SHA.fullmatch(sha) or SHA.fullmatch(base):
        raise ValueError("Invalid base SHA in work order")
    scope = order.get("scope")
    if (not isinstance(scope, dict) or scope.get("mode") != "exact_files"
            or scope.get("complete") is not True):
        raise ValueError("Package requires a complete exact-file audit")
    paths = scope.get("paths")
    if (not isinstance(paths, list) or not 1 <= len(paths) <= 20
            or not all(isinstance(path, str) for path in paths)
            or len(set(paths)) != len(paths) or len(paths) != len(sources)):
        raise ValueError("Invalid file scope")
    for path in paths:
        validate_change_path(path)
    seen = set()
    for item in sources:
        if not isinstance(item, dict):
            raise ValueError("Malformed source in chat package")
        path, blob_sha, content = (item.get("path"), item.get("expected_sha"),
                                   item.get("content"))
        if not isinstance(path, str) or path not in paths or path in seen:
            raise ValueError("Chat package source files differ from the audited scope")
        seen.add(path)
        if not isinstance(blob_sha, str) or not SHA.fullmatch(blob_sha) or not isinstance(content, str):
            raise ValueError("Invalid source blob or content")
        data = content.encode("utf-8")
        if len(data) > MAX_SOURCE_BYTES or b"\x00" in data:
            raise ValueError("Source exceeds text/size limits")
        header = b"blob " + str(len(data)).encode("ascii") + b"\x00"
        if hashlib.sha1(header + data).hexdigest() != blob_sha:
            raise ValueError("Source content does not match the audited Git blob SHA")
    if seen != set(paths):
        raise ValueError("Missing audited source files")
    return order
