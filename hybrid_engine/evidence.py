"""Human-readable, SHA-bound verification reports. No test execution or deployment."""
from __future__ import annotations

import json
from pathlib import Path


def render_report(result: dict) -> str:
    def safe(value: object) -> str:
        return str(value).replace("\r", " ").replace("\n", " ").replace("|", "/")[:220]

    lines = [
        "# Hybrid Engine — Independent PR verification",
        "",
        "- Repository: `" + safe(result.get("repo")) + "`",
        "- PR: #" + safe(result.get("pr_number")),
        "- PR head SHA: `" + safe(result.get("head_sha")) + "`",
        "- CI verdict: **" + safe(result.get("ci")) + "**",
        "- Merged: " + safe(result.get("merged")),
        "",
        "## Required-check policy",
        "",
    ]
    required = result.get("required_checks", [])
    missing = result.get("missing_required_checks", [])
    lines.extend(["- " + safe(x) for x in required] or ["- No explicit required-check names supplied"])
    if missing:
        lines.extend(["", "Missing required checks:", *["- " + safe(x) for x in missing]])
    lines.extend(["", "## Observed evidence", ""])
    for item in result.get("checks", []):
        lines.append("- " + safe(item.get("name")) + " — " + safe(item.get("outcome"))
                     + " (" + safe(item.get("source")) + ")")
    if not result.get("checks"):
        lines.append("- No checks were observed for this PR-head SHA.")
    lines.extend([
        "", "## Interpretation", "",
        "- Only current PR-head checks were inspected; no test commands were triggered.",
        "- A PASSED verdict covers observed checks only, not application, deployment or security.",
        "- No merge or deployment was performed.",
        "",
    ])
    return "\n".join(lines)


def save_report(result: dict, destination: Path) -> tuple[Path, Path]:
    if destination.suffix.lower() != ".json":
        raise ValueError("Report output path must end with .json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    markdown = destination.with_suffix(".md")
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown.write_text(render_report(result), encoding="utf-8")
    return destination, markdown
