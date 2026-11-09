"""Local state persistence (no external account, database or cloud requirements)."""
from __future__ import annotations

import json
from pathlib import Path


def hybrid_dir(root: Path) -> Path:
    return root / ".hybrid"


def write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)
    return path


def read_state(root: Path) -> dict:
    path = hybrid_dir(root) / "state.json"
    if not path.exists():
        return {"status": "not_initialized", "last_run": None}
    return json.loads(path.read_text(encoding="utf-8"))


def initialize(root: Path) -> dict:
    directory = hybrid_dir(root)
    config = directory / "config.json"
    if not config.exists():
        write_json(config, {
            "schema_version": 1,
            "policy": {"production_changes": "approval_required", "shell_tests": "opt_in"},
            "agent": "agnostic",
        })
    state = directory / "state.json"
    if not state.exists():
        write_json(state, {"schema_version": 1, "status": "initialized", "last_run": None})
    return {"config": str(config), "state": str(state)}
