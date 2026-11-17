"""Offline Advisor -> SHA-pinned, review-only chat package handoff.

A finding is a heuristic, never a verified fix. This adapter does not invoke an
agent, create patches, publish source, write GitHub, merge, or deploy.
"""
from __future__ import annotations

from pathlib import Path
import re

from .advisor import SECRET_RULES, advise, load_assessment
from .chat_package import export_chat_package
from .github_adapter import GitHubClient, validate_change_path


ORDER_ID = re.compile(r"advice-[0-9a-f]{16}\Z")


def export_advice_package(
    client: GitHubClient,
    report: Path,
    order_id: str,
    repo: str,
    output: Path,
    *,
    ref: str | None = None,
) -> dict:
    """Export an existing work order using the GitHub snapshot/scoped bundle gate.

    An offline assessment cannot establish that its findings match the current
    repository. The connected adapter independently audits a bounded exact-file
    scope and pins the returned source to a current GitHub branch SHA.
    """
    report = Path(report).expanduser()
    output = Path(output).expanduser()
    if report.resolve() == output.resolve():
        raise ValueError("Package output must not overwrite its assessment report.")
    if not isinstance(order_id, str) or ORDER_ID.fullmatch(order_id) is None:
        raise ValueError("Select one valid Advisor order ID (advice- plus 16 hex digits).")

    plan = advise(load_assessment(report))
    if plan["coverage"] != "BOUNDED_COMPLETE" or plan["status"] != "REVIEW_REQUIRED":
        raise ValueError("Incomplete or blocked Advisor output cannot produce a source package.")

    chosen = next((item for item in plan["work_orders"] if item["id"] == order_id), None)
    if chosen is None:
        raise ValueError("Advisor order ID not found in the supplied assessment.")
    if chosen["status"] != "PROPOSED_NOT_APPLIED" or chosen["workflow"]["flow"] != "audit-fix":
        raise ValueError("Only unblocked audit-fix orders support a source package.")
    finding = chosen["evidence"]
    if finding["source"] == "evidence_bridge" or finding["rule"] in SECRET_RULES:
        raise ValueError("External claims and potential secrets require independent private review.")

    paths = chosen["likely_files"]
    if not isinstance(paths, list) or not 1 <= len(paths) <= 20:
        raise ValueError("An Advisor package requires 1-20 exact source paths.")
    # Reject protected paths before any network access; no automatic scope expansion.
    paths = sorted({validate_change_path(path) for path in paths})
    if not 1 <= len(paths) <= 20:
        raise ValueError("Invalid Advisor file scope.")

    # Only validated fixed-format IDs/rules enter the agent goal, never source
    # prose or potentially hostile paths from the untrusted assessment.
    goal = (
        f"HYBRID AUDIT-FIX: independently verify suspected rule {finding['rule']} "
        f"(finding {finding['id']}; assessment {plan['assessment_fingerprint']}). "
        "Assessment is unverified context; inspect fresh source, tests and intended "
        "behavior. If confirmed, prepare the smallest reviewed change-set only. "
        "Do not apply, merge, deploy or change production."
    )
    result = export_chat_package(client, repo, goal, paths, output, ref=ref)
    return {
        **result,
        "advisor_order": order_id,
        "assessment_fingerprint": plan["assessment_fingerprint"],
        "assessment_to_github_match": "NOT_VERIFIED",
        "finding": "HEURISTIC_REVIEW_REQUIRED",
        "changes": "NOT_APPLIED",
        "manifest": "NOT_CREATED",
        "next": "Independently verify the finding against bundled source, then author and review a manifest; gh-execute is preview-only without --apply.",
    }
