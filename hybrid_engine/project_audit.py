"""Read-only entry point combining bounded assessment and implementation advice.

The result is a baseline for an authorized AI reviewer, not a full security audit.
No target code, tests, database queries, or network operations are executed.
"""
from __future__ import annotations

from pathlib import Path

from .assessment import MAX_FILES, assess_project
from .advisor import advise
from .db_guard import MAX_FILES as DB_MAX_FILES
from .workspace_audit import audit_workspace


def project_audit(target: Path, *, auto_scope: bool = True) -> dict:
    """Collect one baseline, then optional bounded file batches if truncated."""
    assessment = assess_project(target)
    advice = advise(assessment)
    coverage = assessment["coverage"]
    needs_batches = bool(
        auto_scope and coverage["truncated"]
        and (coverage["candidate_files"] >= MAX_FILES
             or coverage["db_files_scanned"] >= DB_MAX_FILES)
    )
    workspace = audit_workspace(target) if needs_batches else None
    has_database = bool(
        assessment.get("database_signals")
        or any(item.get("source") == "db_guard" for item in assessment.get("findings", []))
        or (workspace is not None and
            (workspace["database_signals"] or any(
                item["source"] == "db_guard" for item in workspace["findings"])))
    )

    # This matrix describes *tool capabilities*, not a claim that every topic
    # has been thoroughly reviewed. The connected agent performs further review.
    matrix = {
        "architecture": "PARTIAL_STATIC",
        "code_dependencies": "PARTIAL_STATIC",
        "database": "PARTIAL_STATIC" if has_database else "NOT_DETECTED",
        "security_privacy": "PARTIAL_STATIC",
        "tests_reliability": "NOT_RUN",
        "performance_operations": "NOT_VERIFIED",
        "documentation_continuity": "NOT_VERIFIED",
    }
    report = {
        "schema_version": 1,
        "kind": "hybrid.project-audit.v1",
        "mode": "static_read_only",
        "target": assessment["target"],
        "status": assessment["status"],
        "coverage": assessment["coverage"],
        "dimensions": matrix,
        "assessment": assessment,
        "advisor": advice,
        "tests": {"status": "NOT_RUN", "reason": "Project scripts are never executed."},
        "changes": {"status": "NOT_APPLIED", "target_files_modified": 0},
        "limitations": [
            "Read-only baseline only; use docs/PROJECT_AUDIT.md for a multi-dimensional human/agent review.",
            "Static scan may be incomplete or truncated; inspect coverage before conclusions.",
            "PARTIAL_STATIC does not imply full verification or a security certification.",
            "No live RLS/GRANT tests, production access, runtime tests, model calls, or PR creation.",
            "Review and authorize each proposed change separately.",
            "Root assessment and its Advisor keep their original status; consult workspace separately when batches were executed.",
        ],
    }
    if workspace is not None:
        report["workspace"] = workspace
    return report
