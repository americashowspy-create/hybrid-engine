"""Deterministic routing and workflow planning; independent of any coding agent."""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from uuid import uuid4


FLOWS: dict[str, tuple[str, ...]] = {
    "audit": ("inventory", "security_scan", "triage", "report"),
    "db-audit": ("inventory", "db_static_scan", "db_risk_triage", "limitations", "report"),
    "audit-fix": ("inventory", "reproduce", "security_scan", "regression_test", "isolated_fix", "verify", "pull_request"),
    "debug": ("reproduce", "root_cause", "regression_test", "minimal_fix", "verify"),
    "build": ("specification", "acceptance_criteria", "architecture", "implementation", "tests", "review"),
    "review": ("inspect_changes", "risk_assessment", "test_evidence", "review_report"),
    "status": ("read_state", "report_blockers"),
}
GATES = ("evidence_required", "no_unverified_success", "no_unauthorized_production_change")


def normalize(value: str) -> str:
    stripped = unicodedata.normalize("NFKD", value)
    return "".join(c for c in stripped if not unicodedata.combining(c)).lower()


def route(intent: str) -> str:
    """Select one workflow. Explicit command tokens take precedence."""
    s = normalize(intent)
    explicit = re.search(r"\bhybrid\s+(db-audit|audit-fix|audit|debug|build|review|status|auto)\b", s)
    if explicit and explicit.group(1) != "auto":
        return explicit.group(1)
    if re.search(r"\b(status|progresso|pendencias|retomar)\b", s):
        return "status"
    if (re.search(r"\b(audit|audite|auditar|auditoria|scan|seguranca|security)\b", s)
            and re.search(r"\b(corrig|corrij|fix|repar|consert|resolver)\w*", s)):
        return "audit-fix"
    if re.search(r"\b(audit|audite|auditar|auditoria|scan|seguranca|security)\b", s):
        return "audit"
    if re.search(r"\b(debug|bug|erro|falha|quebr|corrig|consert|repar)\w*", s):
        return "debug"
    if re.search(r"\b(review|revis|pr|pull request)\w*", s):
        return "review"
    if re.search(r"\b(build|crie|criar|implementar|desenvolv|adicionar|nova func|feature)\w*", s):
        return "build"
    return "audit"


def make_plan(intent: str, project: str) -> dict:
    flow = route(intent)
    return {
        "schema_version": 1,
        "id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project": project,
        "intent": intent,
        "flow": flow,
        "steps": [{"name": name, "status": "pending"} for name in FLOWS[flow]],
        "gates": list(GATES),
        "status": "planned",
        "limitations": ["Plan creation does not imply source code changes or test execution."],
    }
