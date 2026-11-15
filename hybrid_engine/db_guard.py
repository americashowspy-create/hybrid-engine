"""Conservative offline database checks: no DB connections and no source execution."""
from __future__ import annotations

import re
from pathlib import Path

from .source_io import read_source
from .enumeration import Enumeration, enumerate_tree

SKIP_DIRS = frozenset({
    ".git", ".hg", ".svn", ".venv", "venv", "node_modules", "dist", "build",
    ".next", ".nuxt", ".hybrid", "__pycache__", ".pytest_cache", ".turbo",
    "coverage", ".cache", "vendor", "target",
})
SCAN_EXT = frozenset({".py", ".js", ".jsx", ".ts", ".tsx", ".sql", ".prisma", ".rules", ".json", ".toml", ".yml", ".yaml"})
CONFIG_NAMES = frozenset({"requirements.txt", "alembic.ini", "database.yml", "firestore.rules", "pyproject.toml", "package.json"})
MAX_FILES = 250
MAX_BYTES = 256 * 1024
MAX_FINDINGS = 500

PUBLIC_PRIVILEGED = re.compile(
    r"\b(?:VITE_|NEXT_PUBLIC_|EXPO_PUBLIC_)[A-Z0-9_]*(?:SERVICE_ROLE|DATABASE_URL|DB_PASSWORD|PRIVATE_KEY|SECRET_KEY)[A-Z0-9_]*\b",
    re.IGNORECASE,
)
OPEN_FIREBASE = re.compile(r"\ballow\s+(?:read|write|create|update|delete)(?:\s*,\s*(?:read|write|create|update|delete))*\s*:\s*if\s+true\s*;", re.IGNORECASE)
RLS_DISABLED = re.compile(r"\bALTER\s+TABLE\b[^;\n]*\bDISABLE\s+ROW\s+LEVEL\s+SECURITY\b", re.IGNORECASE)
OPEN_POLICY = re.compile(r"\bCREATE\s+POLICY\b(?:(?!;).){0,1500}?\b(?:USING|WITH\s+CHECK)\s*\(\s*true\s*\)", re.IGNORECASE | re.DOTALL)
MONEY_FLOAT_SQL = re.compile(r"\b(?:amount|balance|total|price|cost|valor|saldo|preco|pre[cç]o)\w*\b\s+(?:REAL|FLOAT\d*|DOUBLE\s+PRECISION)\b", re.IGNORECASE)
MONEY_FLOAT_PRISMA = re.compile(r"^\s*(?:amount|balance|total|price|cost|valor|saldo|preco)\w*\s+Float\b", re.IGNORECASE)
TIMESTAMP_NO_TZ = re.compile(r"\b(?:created_at|updated_at|paid_at|expires_at|data_criacao|data_pagamento)\b\s+TIMESTAMP\b(?!\s+WITH\s+TIME\s+ZONE)", re.IGNORECASE)
DESTRUCTIVE = re.compile(r"\b(?:DROP\s+TABLE|TRUNCATE\s+(?:TABLE\s+)?|ALTER\s+TABLE\b[^;\n]*\bDROP\s+COLUMN)\b", re.IGNORECASE)
HIGH_OFFSET = re.compile(r"\bOFFSET\s+(\d+)\b", re.IGNORECASE)
DEPENDENCIES = re.compile(r'@supabase/supabase-js|drizzle-orm|prisma|sqlalchemy|psycopg|pymongo|mongoose|firebase|"(?:pg|mysql2)"', re.IGNORECASE)

CATEGORIES = ("security", "backup", "cost", "transactions", "modeling", "migrations", "performance")
VERIFY_LIVE = {
    "security": "RLS, GRANT, network exposure and effective client permissions require authorized live checks.",
    "backup": "Backup existence, retention, and successful restoration cannot be proven from source files.",
    "cost": "Usage-based billing, real query frequency, and budget enforcement require provider metrics.",
    "transactions": "Multi-write atomicity needs application-specific review and failure-injection tests.",
    "modeling": "Actual schema constraints and existing data consistency require database inspection.",
    "migrations": "Schema drift between migrations and live database cannot be checked offline.",
    "performance": "Indexes and performance need real query workload and safe query plans.",
}


def _candidate(path: Path) -> bool:
    name = path.name
    # Local env files can hold live secrets. Scan example/template names only.
    if name.startswith(".env"):
        return name.endswith((".example", ".sample", ".template"))
    return path.suffix.lower() in SCAN_EXT or name in CONFIG_NAMES


def _signal(path: str, content: str) -> set[str]:
    low = path.lower()
    found = set()
    if low.startswith("supabase/") or "/supabase/" in low:
        found.add("supabase")
    if "/prisma/" in "/" + low or low.endswith(".prisma"):
        found.add("prisma")
    if "drizzle" in low:
        found.add("drizzle")
    if low.endswith(("firestore.rules", "firebase.json")):
        found.add("firebase")
    if low.endswith(".sql") or "migration" in low or low in ("alembic.ini", "database.yml"):
        found.add("sql-or-migrations")
    if low.endswith(("package.json", "pyproject.toml", "requirements.txt")) and DEPENDENCIES.search(content):
        found.add("database-dependency")
    return found


def scan_database(root: Path, *, enumeration: Enumeration | None = None, reader=None) -> dict:
    """Inspect bounded text files only. Never run SQL or contact a database."""
    reader = reader or read_source
    root = Path(root).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Target must be a directory")
    findings = []
    signals = set()
    scanned = skipped = 0
    truncated = False
    findings_truncated = False
    tree = enumeration if enumeration is not None else enumerate_tree(root, SKIP_DIRS)
    for relative in tree.files:
        path = root / relative
        name = path.name
        if path.is_symlink() or not _candidate(path):
            continue
        if scanned >= MAX_FILES:
            truncated = True
            break
        try:
            if path.stat().st_size > MAX_BYTES:
                skipped += 1
                continue
            data = reader(root, path.relative_to(root).as_posix(), MAX_BYTES)
            if b"\x00" in data:
                skipped += 1
                continue
            content = data.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            skipped += 1
            continue
        scanned += 1
        rel = path.relative_to(root).as_posix()
        signals.update(_signal(rel, content))
        if name.startswith(".env"):
            # Inspect example variable names only, never values.
            content = "\n".join(line.split("=", 1)[0] for line in content.splitlines())
        sql = path.suffix.lower() == ".sql"
        firebase = name == "firestore.rules" or path.suffix.lower() == ".rules"
        for line_number, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", "//", "--", "*")):
                continue
            code = line.split("--", 1)[0] if sql else line

            def add(rule: str, category: str, severity: str, message: str):
                nonlocal findings_truncated
                if len(findings) >= MAX_FINDINGS:
                    findings_truncated = True
                    return
                findings.append({
                    "rule": rule, "category": category, "severity": severity,
                    "confidence": "suspected", "path": rel, "line": line_number,
                    "message": message,
                })

            if PUBLIC_PRIVILEGED.search(code):
                add("PUBLIC_PRIVILEGED_CONFIG", "security", "high", "Privileged database credential name appears under a public client-side variable prefix; verify actual exposure and rotate if disclosed.")
            if firebase and OPEN_FIREBASE.search(code):
                add("FIREBASE_OPEN_RULE", "security", "high", "Firestore rule appears to allow unrestricted access; review effective rules and authentication.")
            if sql and RLS_DISABLED.search(code):
                add("RLS_DISABLED", "security", "high", "SQL appears to disable row-level security; review applicability, roles, GRANTs and effective policies.")
            if (sql and MONEY_FLOAT_SQL.search(code)) or (path.suffix.lower() == ".prisma" and MONEY_FLOAT_PRISMA.search(code)):
                add("MONEY_FLOAT", "modeling", "medium", "Monetary field appears to use floating point; check whether NUMERIC or integer minor units are appropriate.")
            if sql and TIMESTAMP_NO_TZ.search(code):
                add("TIMESTAMP_NO_TZ", "modeling", "low", "Event timestamp appears to omit timezone; check intended semantics.")
            if sql and "migration" in rel.lower() and DESTRUCTIVE.search(code):
                add("DESTRUCTIVE_MIGRATION", "migrations", "high", "Migration contains potentially destructive SQL; require backup, rollback review and explicit approval.")
            if sql:
                match = HIGH_OFFSET.search(code)
                offset = (match.group(1).lstrip("0") or "0") if match else "0"
                if len(offset) > 3 or (len(offset) == 3 and offset >= "500"):
                    add("HIGH_OFFSET", "performance", "low", "Large fixed OFFSET may degrade pagination; confirm query usage and consider cursor pagination.")
        if sql:
            # Policy clauses are often split across lines; strip SQL line comments.
            uncommented = "\n".join(line.split("--", 1)[0] for line in content.splitlines())
            for match in OPEN_POLICY.finditer(uncommented):
                if len(findings) >= MAX_FINDINGS:
                    findings_truncated = True
                    break
                findings.append({
                    "rule": "PERMISSIVE_SQL_POLICY", "category": "security", "severity": "high",
                    "confidence": "suspected", "path": rel,
                    "line": uncommented.count("\n", 0, match.start()) + 1,
                    "message": "SQL policy appears to allow all rows for a policy operation; review roles, GRANTs and intended access.",
                })
        if findings_truncated:
            break
    skipped += tree.errors + tree.special_files_excluded
    truncated = truncated or tree.truncated
    priority = {area: pos for pos, area in enumerate(CATEGORIES)}
    findings.sort(key=lambda item: (priority[item["category"]], item["path"], item["line"], item["rule"]))
    return {
        "schema_version": 1, "mode": "static_read_only",
        "status": "INCOMPLETE" if truncated or skipped or findings_truncated else "DETECTED" if signals or findings else "NO_DATABASE_EVIDENCE",
        "database_signals": sorted(signals), "files_scanned": scanned,
        "files_skipped": skipped, "enumeration": tree.coverage(), "truncated": truncated, "findings_truncated": findings_truncated, "findings": findings,
        "verification": {category: {"status": "NOT_VERIFIED", "reason": VERIFY_LIVE[category]} for category in CATEGORIES},
        "limitations": [
            "Static heuristic signals are not confirmed vulnerabilities or a complete database audit.",
            "No connection, SQL, network probes, application code, or existing test scripts were executed.",
            "No live .env files, secrets, query results, or matched source excerpts appear in this report.",
            "Missing findings do not prove RLS, backups, costs, atomicity, schema or performance are safe.",
            f"At most {MAX_FILES} candidate files, {MAX_BYTES} bytes per file and {MAX_FINDINGS} findings are collected.",
        ],
    }
