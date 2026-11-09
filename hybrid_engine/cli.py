"""Public CLI: no dependency on Codex, a particular LLM, or a cloud provider."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .audit import scan
from .core import make_plan, route
from .runner import run_tests
from .store import hybrid_dir, initialize, read_state, write_json


def markdown_report(report: dict, test: dict) -> str:
    lines = [
        "# Hybrid Engine — Execution report",
        "", f"- Flow: **{report['flow']}**",
        f"- Target: `{report['target']}`",
        f"- Files scanned: {report['audit']['files_scanned']}",
        f"- Stack signals: {', '.join(report['audit']['stack']) or 'none'}",
        f"- Findings: {len(report['audit']['findings'])}",
        f"- Tests: **{test['status']}**",
        "", "## Findings", "",
    ]
    for issue in report["audit"]["findings"]:
        lines.append(f"- **{issue['severity']}** {issue['rule']} — `{issue['path']}:{issue['line']}` (suspected; validation required)")
    if not report["audit"]["findings"]:
        lines.append("No findings from the built-in rules (not proof of safety).")
    lines += ["", "## Limits", ""]
    lines += ["- " + value for value in report["audit"]["limitations"]]
    lines += ["- Code fixes, PR creation, deployment and complete verification require an authorized execution adapter."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hybrid", description="Agent-agnostic workflow orchestration")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("init", "inspect", "run", "status"):
        p = sub.add_parser(command)
        p.add_argument("--target", type=Path, default=Path("."))
        if command == "run":
            p.add_argument("--intent", required=True, help="Request in natural language; e.g. HYBRID AUDIT-FIX")
            p.add_argument("--tests", action="store_true", help="Explicitly run recognized project test scripts")
    args = parser.parse_args(argv)
    try:
        root = args.target.expanduser().resolve(strict=True)
        if not root.is_dir():
            parser.error("--target must be a directory")
        if args.command == "init":
            output = initialize(root)
        elif args.command == "inspect":
            output = scan(root)
        elif args.command == "status":
            output = read_state(root)
        else:
            initialize(root)
            plan = make_plan(args.intent, str(root))
            paths = hybrid_dir(root)
            plan_path = write_json(paths / "plans" / (plan["id"] + ".json"), plan)
            audit = scan(root)
            tests = run_tests(root) if args.tests else {"status": "NOT_RUN", "reason": "Requires --tests"}
            report = {
                "schema_version": 1,
                "id": plan["id"], "target": str(root),
                "flow": route(args.intent), "plan": str(plan_path),
                "audit": audit, "tests": tests,
                "status": "needs_agent_execution" if plan["flow"] in ("build", "audit-fix", "debug", "review") else "reported",
            }
            report_path = write_json(paths / "reports" / (plan["id"] + ".json"), report)
            markdown_path = paths / "reports" / (plan["id"] + ".md")
            markdown_path.write_text(markdown_report(report, tests), encoding="utf-8")
            state = {
                "schema_version": 1, "status": report["status"], "last_run": plan["id"],
                "flow": plan["flow"], "plan": str(plan_path),
                "report": str(report_path), "report_markdown": str(markdown_path),
                "tests_status": tests["status"], "findings": len(audit["findings"]),
            }
            write_json(paths / "state.json", state)
            output = state
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(2, f"hybrid: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
