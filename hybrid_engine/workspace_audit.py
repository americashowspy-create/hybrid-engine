"""Bounded deterministic multi-batch project assessment without target writes.

Batches are exact paths under one trusted root, not copies or subdirectory
reinterpretations. This deliberately does not certify cross-batch graphs.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from .assessment import MAX_BYTES, MAX_FILES, SCAN_NAMES, assess_project
from .advisor import advise
from .audit import SCANNABLE, SKIP_DIRS
from .db_guard import MAX_FILES as DB_MAX_FILES, _candidate as db_candidate
from .enumeration import enumerate_tree
from .source_io import SourceReader

MAX_PARTITIONS = 16
MAX_FINDINGS = 1000
MAX_ORDERS = 1000
BATCH_SIZE = min(MAX_FILES, DB_MAX_FILES)


def audit_workspace(target: Path) -> dict:
    """Review eligible regular files in bounded exact-path groups.

    BOUNDED_COMPLETE refers only to per-file heuristics across enumerated
    eligible files. It does not prove complete cross-module architecture,
    effective database policy, runtime behavior or security.
    """
    root = Path(target).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Target must be a directory")
    tree = enumerate_tree(root, SKIP_DIRS)
    eligible = []
    skipped_or_unreadable = 0
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
            skipped_or_unreadable += 1
            continue
        try:
            if path.stat().st_size > MAX_BYTES:
                skipped_or_unreadable += 1
                continue
        except OSError:
            skipped_or_unreadable += 1
            continue
        eligible.append(rel)

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
    return {
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
