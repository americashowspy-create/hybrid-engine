"""Bounded deterministic multi-batch project assessment without target writes.

Batches are exact paths under one trusted root, not copies or subdirectory
reinterpretations. This deliberately does not certify cross-batch graphs.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from .assessment import MAX_BYTES, MAX_FILES, SCAN_NAMES, _inventory, assess_project
from .advisor import advise
from .audit import SCANNABLE, SKIP_DIRS
from .db_guard import MAX_FILES as DB_MAX_FILES, _candidate as db_candidate
from .enumeration import enumerate_tree
from .source_io import SourceReader

MAX_PARTITIONS = 16
MAX_FINDINGS = 1000
MAX_ORDERS = 1000
BATCH_SIZE = min(MAX_FILES, DB_MAX_FILES)
MAX_MANIFEST_PATHS = 4096


def eligible_inventory(target: Path) -> tuple:
    """Enumerate paths and metadata only; never read source or private env files."""
    root = Path(target).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Target must be a directory")
    tree = enumerate_tree(root, SKIP_DIRS)
    eligible = []
    unreadable = []
    excluded_secret_env = 0
    for rel in sorted(tree.files):
        path = root / rel
        name = path.name
        # Private .env files are excluded before touching metadata/content.
        if name.startswith(".env") and not db_candidate(path):
            excluded_secret_env += 1
            continue
        if (path.suffix.lower() not in SCANNABLE
                and path.suffix.lower() not in {".toml", ".prisma", ".rules"}
                and name not in SCAN_NAMES and not db_candidate(path)):
            continue
        if path.is_symlink():
            unreadable.append(rel)
            continue
        try:
            if path.stat().st_size > MAX_BYTES:
                unreadable.append(rel)
                continue
        except OSError:
            unreadable.append(rel)
            continue
        eligible.append(rel)
    return root, tree, eligible, unreadable, excluded_secret_env


def build_file_manifest(partitions: list[tuple[int, list[str]]],
                        unassigned: list[str], unreadable: list[str]) -> dict:
    """Explicitly opt-in, bounded disclosure of relative paths only.

    Give pending paths priority so the manifest remains useful when the
    source inventory is larger than the disclosure limit.
    """
    remaining = MAX_MANIFEST_PATHS
    pending = unassigned[:remaining]
    remaining -= len(pending)
    unread = unreadable[:remaining]
    remaining -= len(unread)
    batches = []
    for number, paths in partitions:
        displayed = paths[:remaining]
        remaining -= len(displayed)
        batches.append({"number": number, "paths": displayed,
                        "omitted": len(paths) - len(displayed)})
    listed = len(pending) + len(unread) + sum(len(p["paths"]) for p in batches)
    total = len(unassigned) + len(unreadable) + sum(len(paths) for _, paths in partitions)
    return {
        "schema_version": 1,
        "kind": "hybrid.file-manifest.v1",
        "disclosure": "explicit_opt_in_relative_paths_only",
        "max_paths": MAX_MANIFEST_PATHS,
        "listed_paths": listed,
        "omitted_paths": total - listed,
        "truncated": listed < total,
        "unassigned_paths": pending,
        "unreadable_or_oversized_paths": unread,
        "batches": batches,
    }


def single_pass_coverage(target: Path, assessment: dict, *,
                         include_manifest: bool = False) -> tuple[dict, dict | None]:
    """Summarize the *primary* assessment; do not call DB scans exhaustive."""
    root, tree, eligible, unreadable, excluded_secret_env = eligible_inventory(target)
    selected, _, _, _, _ = _inventory(root, tree)
    selected_set = set(selected)
    unassigned = [p for p in eligible if p not in selected_set]
    coverage = assessment["coverage"]
    summary = {
        "schema_version": 1,
        "scope": "initial_assessment",
        "enumerated_regular_files": len(tree.files),
        "enumeration_complete": not tree.truncated and tree.errors == 0,
        "eligible_files": len(eligible),
        "assigned_files": len(selected),
        "unassigned_files": len(unassigned),
        "unreadable_or_oversized_files": len(unreadable),
        "private_env_files_excluded": excluded_secret_env,
        "general_files_scanned": coverage["general_files_scanned"],
        "db_files_scanned": coverage["db_files_scanned"],
        "effective_status": coverage["status"],
        "note": ("Unassigned counts files outside the primary assessment candidate set; "
                 "DB Guard has a separate bounded scan, and neither count implies runtime verification."),
    }
    manifest = (build_file_manifest([(1, selected)], unassigned, unreadable)
                if include_manifest else None)
    return summary, manifest


def audit_workspace(target: Path, *, include_manifest: bool = False) -> dict:
    """Review eligible files in safe bounded batches under a single root.

    BOUNDED_COMPLETE covers eligible per-file heuristics only. Not a claim
    about cross-batch graphs, effective RLS, runtime or production security.
    """
    root, tree, eligible, unreadable, excluded_secret_env = eligible_inventory(target)
    skipped_or_unreadable = len(unreadable)

    capacity = BATCH_SIZE * MAX_PARTITIONS
    path_fingerprint = hashlib.sha256("\\n".join(eligible).encode("utf-8")).hexdigest()
    assigned = eligible[:capacity]
    unassigned = len(eligible) - len(assigned)
    reader = SourceReader(root)
    partitions = []
    findings = {}
    orders = {}
    database_signals = set()
    truncated_evidence = False
    for offset in range(0, len(assigned), BATCH_SIZE):
        paths = assigned[offset:offset + BATCH_SIZE]
        report = assess_project(root, scope_paths=paths, enumeration=tree,
                                reader=reader)
        advice = advise(report)
        database_signals.update(report["database_signals"])
        for item in report["findings"]:
            if item["id"] not in findings:
                if len(findings) >= MAX_FINDINGS:
                    truncated_evidence = True
                else:
                    findings[item["id"]] = item
        for item in advice["work_orders"]:
            if item["id"] not in orders:
                if len(orders) >= MAX_ORDERS:
                    truncated_evidence = True
                else:
                    orders[item["id"]] = item
        partitions.append({
            "number": len(partitions) + 1,
            "selected_files": len(paths),
            "first_path": paths[0],
            "last_path": paths[-1],
            "assessment_status": report["status"],
            "coverage_status": report["coverage"]["status"],
            "general_files_scanned": report["coverage"]["general_files_scanned"],
            "db_files_scanned": report["coverage"]["db_files_scanned"],
            "findings": len(report["findings"]),
            "advisor_status": advice["status"],
            "source_tests": "NOT_RUN",
        })

    complete = (
        not tree.truncated and tree.errors == 0 and tree.special_files_excluded == 0
        and skipped_or_unreadable == 0 and unassigned == 0
        and not truncated_evidence
        and all(part["coverage_status"] == "BOUNDED_COMPLETE"
                for part in partitions)
    )
    status = ("INCOMPLETE" if not complete else
              "REVIEW_REQUIRED" if findings else "NO_FINDINGS")
    result = {
        "schema_version": 1,
        "kind": "hybrid.workspace-audit.v1",
        "mode": "static_read_only",
        "target": str(root),
        "status": status,
        "coverage": {
            "scope": "partitioned_eligible_files",
            "status": "BOUNDED_COMPLETE" if complete else "INCOMPLETE",
            "enumeration": tree.coverage(),
            "eligible_files": len(eligible),
            "enumerated_regular_files": len(tree.files),
            "inventory_path_sha256": path_fingerprint,
            "inventory_hash_scope": "paths_only_not_file_contents",
            "assigned_files": len(assigned),
            "unassigned_files": unassigned,
            "unreadable_or_oversized_files": skipped_or_unreadable,
            "private_env_files_excluded": excluded_secret_env,
            "partitions": len(partitions),
            "limits": {"files_per_partition": BATCH_SIZE,
                       "partitions": MAX_PARTITIONS,
                       "max_eligible_files": capacity,
                       "findings": MAX_FINDINGS, "work_orders": MAX_ORDERS},
            "cross_partition_import_graph": "NOT_VERIFIED",
            "evidence_truncated": truncated_evidence,
        },
        "partitions": partitions,
        "database_signals": sorted(database_signals),
        "findings": sorted(findings.values(), key=lambda x: (
            {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["severity"], 9),
            x["path"], x["line"], x["rule"], x["id"])),
        "work_orders": sorted(orders.values(), key=lambda x: (x["priority"], x["id"])),
        "execution": {
            "static_assessments": len(partitions),
            "advisor_runs": len(partitions),
            "project_tests": "NOT_RUN",
            "database_access": "NOT_ACCESSED",
            "network": "NOT_USED",
            "repository_changes": "NONE",
            "source_sha": "NOT_VERIFIED",
        },
        "limitations": [
            "Coverage is bounded to enumerated eligible files and partition-local analysis.",
            "Cross-partition imports, import cycles and duplicate sources are NOT_VERIFIED.",
            "Package/SQL findings can reflect historical files; effective live state is NOT_VERIFIED.",
            "No tests, exploit attempts, database connections, application code or network calls run.",
            "Findings are suspected static indicators, not verified vulnerabilities.",
            "A complete file inventory does not certify operational or security completeness.",
            "Advisor orders are proposals only; source SHAs, approvals and runtime tests are separate.",
        ],
    }
    if include_manifest:
        numbered_batches = [(n + 1, assigned[n * BATCH_SIZE:(n + 1) * BATCH_SIZE])
                            for n in range(len(partitions))]
        result["file_manifest"] = build_file_manifest(
            numbered_batches, eligible[capacity:], unreadable)
    return result
