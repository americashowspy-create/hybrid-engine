"""Public CLI: no dependency on Codex, a particular LLM, or a cloud provider."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .audit import scan
from .auto_executor import run_auto
from .github_adapter import GitHubClient, GitHubError, propose_changes, remote_audit
from .core import make_plan, route
from .runner import run_tests
from .store import hybrid_dir, initialize, read_state, write_json
from .taskboard import list_tasks, note_task, start_task, task_status
from .verification import verify_pr


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
    gh_audit = sub.add_parser("gh-audit", help="Read-only audit of an accessible GitHub repository")
    gh_audit.add_argument("--repo", required=True, help="owner/name")
    gh_audit.add_argument("--ref", help="Source branch or commit (default: default branch)")
    gh_audit.add_argument("--output", type=Path, help="Optional JSON report path")

    gh_pr = sub.add_parser("gh-propose", help="Validate a change-set; optionally create a draft PR")
    gh_pr.add_argument("--manifest", required=True, type=Path, help="Reviewed JSON change-set")
    gh_pr.add_argument("--apply", action="store_true", help="Write an isolated branch and draft PR")

    gh_verify = sub.add_parser("gh-verify", help="Verify real PR-head CI evidence")
    gh_verify.add_argument("--repo", required=True, help="owner/name")
    gh_verify.add_argument("--pr", required=True, type=int, help="PR number")

    gh_task = sub.add_parser("gh-task", help="Durable task journal in GitHub Issues")
    gh_task.add_argument("action", choices=("start", "list", "status", "note"))
    gh_task.add_argument("--repo", required=True, help="owner/name")
    gh_task.add_argument("--goal", help="Task objective for start")
    gh_task.add_argument("--issue", type=int, help="Task issue number for status or note")
    gh_task.add_argument("--state", choices=("in_progress", "blocked", "review_ready", "completed_reported"))
    gh_task.add_argument("--summary", help="Progress summary for note")
    gh_task.add_argument("--pr", type=int, help="Optional PR associated with note")
    gh_task.add_argument("--apply", action="store_true", help="Explicitly allow start or note writes")

    gh_auto = sub.add_parser("gh-auto", help="Read-only workflow routing with optional guarded draft PR")
    gh_auto.add_argument("--repo", required=True, help="owner/name")
    gh_auto.add_argument("--intent", required=True, help="Natural language: HYBRID AUDIT-FIX ...")
    gh_auto.add_argument("--ref", help="Branch to audit (defaults to repo default)")
    gh_auto.add_argument("--apply", action="store_true", help="Opt in to a limited safe fix via draft PR")

    args = parser.parse_args(argv)

    if args.command in ("gh-audit", "gh-propose", "gh-task", "gh-verify", "gh-auto"):
        try:
            client = GitHubClient()
            if args.command == "gh-audit":
                output = remote_audit(client, args.repo, args.ref)
                if args.output:
                    write_json(args.output.expanduser(), output)
            elif args.command == "gh-propose":
                document = json.loads(args.manifest.read_text(encoding="utf-8"))
                output = propose_changes(client, document, apply=args.apply)
            elif args.command == "gh-verify":
                output = verify_pr(client, args.repo, args.pr)
            elif args.command == "gh-auto":
                output = run_auto(client, args.repo, args.intent, ref=args.ref, apply=args.apply)
            elif args.action == "start":
                if not args.goal:
                    raise ValueError("gh-task start requires --goal")
                output = start_task(client, args.repo, args.goal, apply=args.apply)
            elif args.action == "list":
                output = list_tasks(client, args.repo)
            elif args.action == "status":
                if args.issue is None:
                    raise ValueError("gh-task status requires --issue")
                output = task_status(client, args.repo, args.issue)
            else:
                if args.issue is None or not args.state or not args.summary:
                    raise ValueError("gh-task note requires --issue, --state and --summary")
                output = note_task(client, args.repo, args.issue, args.state,
                                   args.summary, pr_number=args.pr, apply=args.apply)
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return 0
        except (OSError, ValueError, GitHubError, KeyError, TypeError, json.JSONDecodeError) as exc:
            parser.exit(2, f"hybrid: {exc}\n")
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
