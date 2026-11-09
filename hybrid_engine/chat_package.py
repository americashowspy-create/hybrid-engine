"""Export a reviewable, SHA-pinned source bundle for a connected chat coding agent.

Never invokes a model, prints source, changes a repository, merges or deploys.
The bundle is deliberately kept in a private local file, not in CI logs.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .agent_bridge import prepare
from .github_adapter import GitHubClient
from .universal import source_package


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
    """Recover an audited order from a chat package without trusting fake scopes."""
    if not isinstance(bundle, dict) or bundle.get("protocol") != "hybrid.agent-stdio.v1":
        raise ValueError("Unsupported chat package protocol")
    order, sources = bundle.get("work_order"), bundle.get("sources")
    if not isinstance(order, dict) or not isinstance(sources, list) or not sources:
        raise ValueError("Malformed chat package")
    scope = order.get("scope")
    paths = scope.get("paths") if isinstance(scope, dict) else None
    if (not isinstance(paths, list) or len(paths) != len(sources)
            or not all(isinstance(item, dict) and isinstance(item.get("path"), str)
                       for item in sources)
            or set(paths) != {item["path"] for item in sources}):
        raise ValueError("Chat package source files differ from the audited scope")
    return order
