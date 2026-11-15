"""Deterministic, offline project assessment; no application code execution or network."""
from __future__ import annotations

import hashlib
import html
import os
from pathlib import Path

from .audit import SCANNABLE, SKIP_DIRS, scan
from .db_guard import scan_database
from .source_io import read_source

MAX_FILES = 250
MAX_BYTES = 256 * 1024
LONG_FILE_LINES = 500
DUPLICATE_MIN_BYTES = 1024
SOURCE_SUFFIXES = frozenset({".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs"})
SCAN_NAMES = frozenset({"Dockerfile", "pyproject.toml", "requirements.txt", "package.json",
                        "tsconfig.json", "vite.config.ts", "vite.config.js"})
LOCKFILES = ("package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml",
             "yarn.lock", "bun.lock", "bun.lockb")
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
GUIDANCE = {
    "REACT_HTML_INJECTION": (
        "A React HTML rendering sink was observed; exploitability is not established.",
        "Trace the HTML source, interpolation and sanitizer. Static trusted HTML may need no change; "
        "test untrusted paths before choosing sanitization or text rendering.",
        "Document the trust boundary and test hostile HTML where input is untrusted."),
    "LARGE_SOURCE_FILE": (
        "Review whether this file combines unrelated responsibilities.",
        "Identify coherent modules and propose a small behavior-preserving split.",
        "Existing behavior and relevant tests remain unchanged."),
    "EXACT_DUPLICATE_SOURCE": (
        "Two eligible source files have identical content.",
        "Verify the files serve the same purpose before proposing consolidation.",
        "Imports, build outputs and affected tests continue working."),
    "NO_TESTS_DETECTED": (
        "No conventional test files were seen in the bounded source inventory.",
        "Locate the actual test strategy and add a small regression test if absent.",
        "A documented and runnable test covers one critical behavior."),
    "MISSING_JS_LOCKFILE": (
        "A root package manifest exists without a recognized lockfile.",
        "Identify the intended package manager and commit its reproducible lockfile.",
        "A clean install follows the project's supported package manager."),
    "PUBLIC_PRIVILEGED_CONFIG": (
        "A client-exposed variable name appears to reference privileged credentials.",
        "Verify actual exposure; keep privileged credentials on the server.",
        "No privileged value reaches client bundles or public responses."),
    "PERMISSIVE_SQL_POLICY": (
        "A static SQL policy may permit unrestricted row access.",
        "Review intended roles and effective RLS/GRANT settings in an authorized environment.",
        "Role-specific access tests confirm intended isolation."),
    "RLS_DISABLED": (
        "SQL appears to disable row-level security.",
        "Review role permissions, intended access and effective RLS before changing SQL.",
        "Authorized access tests confirm expected row isolation."),
    "DESTRUCTIVE_MIGRATION": (
        "A migration contains a potentially destructive statement.",
        "Review data preservation, backups and a tested rollback on a disposable database.",
        "Migration and rollback are validated outside production."),
}
DEFAULT_GUIDANCE = (
    "The source contains a heuristic indicator, not a verified defect.",
    "Inspect the cited location and confirm applicability before proposing a small fix.",
    "A targeted test or authorized inspection confirms the behavior after review.",
)


def _inventory(root: Path) -> tuple[list[str], int, int, bool, bool]:
    """Find bounded eligible files without opening any real .env file."""
    found: list[str] = []
    ignored_sensitive = 0
    skipped = 0
    truncated = False
    has_tests = False
    walk_errors = []
    for current, dirs, files in os.walk(root, followlinks=False, onerror=walk_errors.append):
        dirs[:] = sorted(d for d in dirs
                         if d not in SKIP_DIRS and not (Path(current) / d).is_symlink())
        for name in sorted(files):
            path = Path(current) / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                continue
            if name.startswith(".env"):
                ignored_sensitive += 1
                continue
            suffix = path.suffix.lower()
            if suffix not in SCANNABLE and suffix not in {".toml", ".prisma", ".rules"} and name not in SCAN_NAMES:
                continue
            if len(found) >= MAX_FILES:
                truncated = True
                break
            try:
                if path.stat().st_size > MAX_BYTES:
                    skipped += 1
                    continue
            except OSError:
                skipped += 1
                continue
            found.append(rel)
            has_tests = has_tests or (suffix in SOURCE_SUFFIXES and _is_test_source(rel))
        if truncated:
            break
    skipped += len(walk_errors)
    return found, skipped, ignored_sensitive, truncated, has_tests


def _is_test_source(path: str) -> bool:
    """Identify ordinary test paths; real credential matches still remain findings."""
    parts = Path(path).parts
    name = parts[-1] if parts else ""
    return (any(part in ("test", "tests", "__tests__") for part in parts[:-1])
            or name.startswith("test_")
            or name.endswith(("_test.py", ".test.js", ".test.ts", ".test.tsx",
                              ".spec.js", ".spec.ts", ".spec.tsx", ".test.jsx", ".spec.jsx",
                              "_test.go", "_test.rs")))


def _is_generated_supabase_types(path: Path, source: str) -> bool:
    """Narrow signature; a filename alone is insufficient to classify generated code."""
    return (path.name == "database.types.ts"
            and "export type Database =" in source
            and "__InternalSupabase" in source)


def _finding(source: str, rule: str, severity: str, category: str,
             path: str, line: int, message: str) -> dict:
    key = f"{source}:{rule}:{path}:{line}"
    return {
        "id": hashlib.sha256(key.encode("utf-8")).hexdigest()[:16],
        "source": source, "rule": rule, "severity": severity,
        "category": category, "confidence": "suspected",
        "context": "test_source" if _is_test_source(path) else "application_source",
        "path": path, "line": line, "message": message,
    }


def _architecture(root: Path, candidates: list[str], *, has_tests: bool,
                  inventory_truncated: bool) -> tuple[list[dict], int, int]:
    results: list[dict] = []
    hashes: dict[str, str] = {}
    source_count = 0
    skipped = 0
    generated_size_excluded = 0
    for rel in candidates:
        path = root / rel
        if path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        try:
            content = read_source(root, rel, MAX_BYTES)
            if b"\x00" in content:
                skipped += 1
                continue
            source = content.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            skipped += 1
            continue
        source_count += 1
        line_count = len(source.splitlines())
        if line_count > LONG_FILE_LINES:
            if _is_generated_supabase_types(path, source):
                generated_size_excluded += 1
            else:
                results.append(_finding(
                    "architecture", "LARGE_SOURCE_FILE", "low", "architecture",
                    rel, 1, f"Source file has {line_count} lines; review cohesion before refactoring."))
        if len(content) >= DUPLICATE_MIN_BYTES:
            digest = hashlib.sha256(content).hexdigest()
            if digest in hashes:
                results.append(_finding(
                    "architecture", "EXACT_DUPLICATE_SOURCE", "medium", "architecture",
                    rel, 1, "Eligible source is byte-identical to another file; verify intent."))
            else:
                hashes[digest] = rel
    if source_count and not has_tests and not inventory_truncated:
        results.append(_finding(
            "architecture", "NO_TESTS_DETECTED", "low", "quality",
            ".", 1, "No conventional test files found in the bounded inventory; verify test coverage."))
    if (root / "package.json").is_file() and not (root / "package.json").is_symlink():
        if not any((root / name).is_file() and not (root / name).is_symlink() for name in LOCKFILES):
            results.append(_finding(
                "architecture", "MISSING_JS_LOCKFILE", "medium", "quality",
                "package.json", 1, "No recognized root JavaScript package lockfile was found."))
    return results, skipped, generated_size_excluded


def assess_project(target: Path) -> dict:
    """Inspect source conservatively and produce reviewable, non-executable advice."""
    root = Path(target).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Target must be a directory")
    candidates, skipped, ignored_sensitive, truncated, has_tests = _inventory(root)
    general = scan(root, include_paths=set(candidates))
    database = scan_database(root)
    architecture, arch_skipped, generated_size_excluded = _architecture(
        root, candidates, has_tests=has_tests, inventory_truncated=truncated)
    findings = [
        _finding("audit", item["rule"], item["severity"], "security",
                 item["path"], item["line"], item["message"])
        for item in general["findings"]
    ]
    findings.extend(
        _finding("db_guard", item["rule"], item["severity"], item["category"],
                 item["path"], item["line"], item["message"])
        for item in database["findings"])
    findings.extend(architecture)
    findings.sort(key=lambda x: (SEVERITY_ORDER.get(x["severity"], 9),
                                 x["context"] == "test_source",
                                 x["category"], x["path"], x["line"], x["rule"], x["id"]))

    recommendations = []
    for item in findings:
        why, action, acceptance = GUIDANCE.get(item["rule"], DEFAULT_GUIDANCE)
        recommendations.append({
            "finding_id": item["id"],
            "priority": "P1_REVIEW" if item["severity"] in ("critical", "high") else
                        "P2_REVIEW" if item["severity"] == "medium" else "P3_REVIEW",
            "why": why, "action": action, "acceptance": acceptance,
            "review_note": (
                "This is test source; verify whether the match is a synthetic fixture. "
                "A genuine secret committed in tests remains a high-priority risk."
                if item["context"] == "test_source" else
                "Review applicability in the deployed application and intended access scope."
            ),
            "validation": "Validate with targeted tests or authorized read-only checks; not executed.",
            "rollback": "Revert only an eventual separately approved code change.",
            "status": "PROPOSED_NOT_APPLIED",
        })

    incomplete = (truncated or skipped > 0 or arch_skipped > 0 or
                  general["truncated"] or general["files_skipped"] > 0 or
                  database["status"] == "INCOMPLETE")
    status = "INCOMPLETE" if incomplete else "REVIEW_REQUIRED" if findings else "NO_FINDINGS"
    return {
        "schema_version": 1, "mode": "static_read_only", "status": status,
        "target": str(root), "stack": general["stack"],
        "coverage": {
            "scope": "bounded_local_tree", "status": "INCOMPLETE" if incomplete else "BOUNDED_COMPLETE",
            "candidate_files": len(candidates), "general_files_scanned": general["files_scanned"],
            "general_files_skipped": general["files_skipped"],
            "architecture_files_skipped": arch_skipped,
            "generated_types_excluded_from_size_rule": generated_size_excluded,
            "inventory_files_skipped": skipped, "sensitive_env_files_excluded": ignored_sensitive,
            "db_files_scanned": database["files_scanned"],
            "db_files_skipped": database["files_skipped"],
            "truncated": truncated or general["truncated"] or database["truncated"],
            "db_findings_truncated": database["findings_truncated"],
        },
        "database_signals": database["database_signals"],
        "summary": {
            "application_source_findings": sum(
                x["context"] == "application_source" for x in findings),
            "test_source_findings": sum(
                x["context"] == "test_source" for x in findings),
        },
        "findings": findings, "recommendations": recommendations,
        "verification": {
            "tests": {"status": "NOT_RUN", "reason": "Assessment never executes project tests."},
            "live_database": database["verification"],
            "runtime": {"status": "NOT_VERIFIED", "reason": "No application or network execution."},
        },
        "limitations": [
            "Static bounded heuristics only; findings are suspected, not proven vulnerabilities.",
            "NO_FINDINGS is not a security certification or a claim of full coverage.",
            "Only recognized files within the bounded scan were inspected; skipped/truncated work is incomplete.",
            "Test-code findings stay visible and are never automatically dismissed as fake secrets.",
            "Generated Supabase types can be exempted from the size heuristic, not other security rules.",
            "Secrets and matched source code excerpts are never included in the report.",
            "No real .env file, production database, network API, application script or test is accessed.",
            "Recommendations require a capable authorized agent and separate review before implementation.",
        ],
    }


def assessment_markdown(report: dict) -> str:
    """Render a compact human-readable summary without source snippets."""
    lines = [
        "# Hybrid Engine — Project Assessment", "",
        f"- Status: **{report['status']}**",
        f"- Coverage: **{report['coverage']['status']}**",
        f"- Stack signals: {', '.join(report['stack']) or 'none'}",
        f"- Findings: {len(report['findings'])}",
        f"- Application-source findings: {report['summary']['application_source_findings']}",
        f"- Test-source findings: {report['summary']['test_source_findings']}",
        "- Project tests: **NOT_RUN**", "",
        "## Review findings", "",
    ]
    for item, advice in zip(report["findings"], report["recommendations"]):
        safe_path = markdown_text(item["path"])
        lines.extend([
            f"### {item['rule']} — {advice['priority']}",
            f"- Location: {safe_path}:{item['line']}",
            f"- Confidence: **{item['confidence']}** ({item['source']})",
            f"- Context: {item['context']}",
            f"- Review: {advice['review_note']}",
            f"- Action: {advice['action']}",
            f"- Acceptance: {advice['acceptance']}", "",
        ])
    if not report["findings"]:
        lines.append("No findings from the implemented rules; this is not proof of safety.")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    return "\n".join(lines) + "\n"


def markdown_text(value: str) -> str:
    """Render untrusted metadata as text, never HTML or Markdown directives."""
    value = " ".join(value.split())
    value = html.escape(value, quote=True)
    for character in "\\`*_{}[]()#+-.!|":
        value = value.replace(character, "\\" + character)
    return value
