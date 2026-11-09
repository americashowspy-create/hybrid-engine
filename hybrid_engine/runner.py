"""Explicit, bounded execution of recognized project test commands."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def choose_test_command(root: Path) -> list[str] | None:
    if (root / "tests").is_dir() and any((root / x).exists() for x in ("pyproject.toml", "requirements.txt", "setup.py")):
        return [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
    package = root / "package.json"
    if package.is_file():
        try:
            scripts = json.loads(package.read_text(encoding="utf-8")).get("scripts", {})
        except (ValueError, OSError, TypeError):
            return None
        if isinstance(scripts, dict) and isinstance(scripts.get("test"), str) and shutil.which("npm"):
            return ["npm", "test", "--", "--run"]
    return None


def run_tests(root: Path, *, timeout: int = 180) -> dict:
    cmd = choose_test_command(root)
    if cmd is None:
        return {"status": "NOT_RUN", "reason": "No supported project test runner found."}
    try:
        result = subprocess.run(cmd, cwd=root, text=True, capture_output=True,
                                timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "FAIL", "command": cmd, "reason": type(exc).__name__}
    return {
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "command": cmd, "exit_code": result.returncode,
        "output_tail": (result.stdout + "\n" + result.stderr)[-4000:],
    }
