"""Read-only repository inventory and conservative static security indicators."""
from __future__ import annotations

import os
import re
from pathlib import Path

from .source_io import read_source

SKIP_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "node_modules", "dist", "build",
    ".next", ".nuxt", ".hybrid", "__pycache__", ".pytest_cache", ".turbo", "coverage"
}
SCANNABLE = {".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".yml", ".yaml", ".env", ".sh", ".sql", ".go", ".rs"}
EXTRA_NAMES = {".env", ".env.local", ".env.production", "Dockerfile"}
MAX_BYTES = 256 * 1024
MAX_FILES = 3000

# Exact patterns only; anything flagged is a lead to validate, not a confirmed vulnerability.
PATTERNS = (
    ("PRIVATE_KEY", "critical", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), None),
    ("SUPABASE_SECRET", "critical", re.compile(r"\bsb_secret_[A-Za-z0-9_-]{10,}\b"), None),
    ("GITHUB_TOKEN", "critical", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b"), None),
    ("AWS_ACCESS_KEY", "high", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), None),
    ("JS_EVAL", "medium", re.compile(r"\beval\s*\("), {".js", ".jsx", ".ts", ".tsx"}),
    ("REACT_HTML_INJECTION", "medium", re.compile(r"\bdangerouslySetInnerHTML\b"), {".jsx", ".tsx"}),
)


def detect_stack(root: Path) -> list[str]:
    signals = {
        "Node.js": ("package.json",),
        "TypeScript": ("tsconfig.json",),
        "Python": ("pyproject.toml", "requirements.txt", "setup.py"),
        "Supabase": ("supabase/config.toml",),
        "Next.js": ("next.config.js", "next.config.mjs", "next.config.ts"),
        "Vite": ("vite.config.ts", "vite.config.js"),
        "Docker": ("Dockerfile", "docker-compose.yml", "compose.yml"),
    }
    return [name for name, paths in signals.items() if any((root / path).exists() for path in paths)]


def scan(root: Path, *, include_paths: set[str] | None = None) -> dict:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Target must be a directory")
    findings: list[dict] = []
    scanned = 0
    skipped = 0
    truncated = False

    walk_errors = []
    for current, dirs, filenames in os.walk(root, followlinks=False, onerror=walk_errors.append):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not (Path(current) / d).is_symlink())
        for filename in sorted(filenames):
            path = Path(current) / filename
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                continue
            if include_paths is not None:
                if relative not in include_paths:
                    continue
            elif path.suffix.lower() not in SCANNABLE and filename not in EXTRA_NAMES:
                continue
            if scanned >= MAX_FILES:
                truncated = True
                break
            try:
                if path.stat().st_size > MAX_BYTES:
                    skipped += 1
                    continue
                raw = read_source(root, relative, MAX_BYTES)
                if b"\x00" in raw:
                    skipped += 1
                    continue
                source = raw.decode("utf-8")
            except (OSError, UnicodeDecodeError):
                skipped += 1
                continue
            scanned += 1
            relative = path.relative_to(root).as_posix()
            for lineno, line in enumerate(source.splitlines(), 1):
                for key, severity, pattern, allowed in PATTERNS:
                    if allowed is not None and path.suffix.lower() not in allowed:
                        continue
                    if pattern.search(line):
                        findings.append({
                            "rule": key, "severity": severity, "path": relative, "line": lineno,
                            "confidence": "suspected",
                            "message": (
                                "HTML rendering sink observed; trace the HTML source and sanitizer. "
                                "Static or sanitized HTML may be intentional; exploitability is not verified."
                                if key == "REACT_HTML_INJECTION" else
                                "Potential issue: review this location; original value intentionally omitted."
                            )
                        })
        if truncated:
            break
    skipped += len(walk_errors)
    return {
        "target": str(root),
        "stack": detect_stack(root),
        "files_scanned": scanned,
        "files_skipped": skipped,
        "truncated": truncated,
        "findings": findings,
        "limitations": [
            "Heuristic static scan only; results may be false positives or false negatives.",
            "Does not validate RLS, authentication, application behavior, dependencies, or production security.",
            "Findings are not confirmed vulnerabilities; no secrets are included in output.",
        ],
    }
