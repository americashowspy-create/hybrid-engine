"""Public CLI: no dependency on Codex, a particular LLM, or a cloud provider."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .audit import scan
from .db_guard import scan_database
from .assessment import assess_project, assessment_markdown
from .advisor import advise, advice_markdown, load_assessment
from .advice_handoff import export_advice_package
from .evidence_bridge import import_evidence, evidence_markdown
from .auto_executor import run_auto
from .agent_bridge import prepare, submit
from .github_adapter import GitHubClient, GitHubError, propose_changes, remote_audit
from .core import make_plan, route
from .runner import run_tests
from .store import hybrid_dir, initialize, read_state, write_json
from .taskboard import list_tasks, note_task, start_task, task_status
from .verification import verify_pr
from .universal import run_universal
from .evidence import save_report
from .chat_package import export_chat_package, work_order_from_bundle


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
    if "db_guard" in report:
        db = report["db_guard"]
        lines += ["", "## DB Guard — offline static signals", "",
                  f"- Status: **{db['status']}**",
                  f"- Database signals: {', '.join(db['database_signals']) or 'none'}",
                  f"- Findings: {len(db['findings'])}", ""]
        for issue in db["findings"]:
            lines.append(f"- **{issue['severity']}** {issue['rule']} — {issue['path']}:{issue['line']} (suspected)")
        lines += ["", "### Not verified against a real database", ""]
        for category, item in db["verification"].items():
            lines.append(f"- {category}: **{item['status']}** — {item['reason']}")
        lines.append("")
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
    db_audit_parser = sub.add_parser("db-audit", help="Offline read-only database heuristics (no DB access)")
    db_audit_parser.add_argument("--target", type=Path, default=Path("."))
    db_audit_parser.add_argument("--output", type=Path, help="Optional JSON report path")

    assess_parser = sub.add_parser("assess", help="Offline unified project assessment (no code execution)")
    assess_parser.add_argument("--target", type=Path, default=Path("."))
    assess_parser.add_argument("--output", type=Path, help="Optional explicit report output path")
    assess_parser.add_argument("--format", choices=("json", "markdown"), default="json")

    advisor = sub.add_parser("advise", help="Offline implementation review orders from an assessment")
    advisor.add_argument("--report", type=Path, required=True)
    advisor.add_argument("--output", type=Path)
    advisor.add_argument("--format", choices=("json", "markdown"), default="json")

    bridge = sub.add_parser("evidence-import", help="Import bounded security evidence offline; never run tools")
    bridge.add_argument("--report", type=Path, action="append", required=True)
    bridge.add_argument("--expected-sha")
    bridge.add_argument("--output", type=Path)
    bridge.add_argument("--format", choices=("json", "markdown"), default="json")

    gh_audit = sub.add_parser("gh-audit", help="Read-only audit of an accessible GitHub repository")
    gh_audit.add_argument("--repo", required=True, help="owner/name")
    gh_audit.add_argument("--ref", help="Source branch or commit (default: default branch)")
    gh_audit.add_argument("--output", type=Path, help="Optional JSON report path")
    gh_audit.add_argument("--path", action="append", dest="scope_paths",
                          help="Exact file path; repeat to limit audit scope")

    gh_pr = sub.add_parser("gh-propose", help="Validate a change-set; optionally create a draft PR")
    gh_pr.add_argument("--manifest", required=True, type=Path, help="Reviewed JSON change-set")
    gh_pr.add_argument("--apply", action="store_true", help="Write an isolated branch and draft PR")

    gh_verify = sub.add_parser("gh-verify", help="Verify real PR-head CI evidence")
    gh_verify.add_argument("--repo", required=True, help="owner/name")
    gh_verify.add_argument("--pr", required=True, type=int, help="PR number")
    gh_verify.add_argument("--require-check", action="append", default=[],
                           help="Expected CI job or status context; repeat for required jobs")
    gh_verify.add_argument("--output", type=Path, help="Write JSON evidence and adjacent Markdown report")
    gh_verify.add_argument("--strict", action="store_true", help="Exit nonzero unless every required check passes")

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
    gh_auto.add_argument("--path", action="append", dest="scope_paths",
                         help="Exact audited file; include .gitignore for guarded remediation")

    gh_order = sub.add_parser("gh-workorder", help="Prepare a SHA-pinned AI-agent work order")
    gh_order.add_argument("--repo", required=True, help="owner/name")
    gh_order.add_argument("--goal", required=True, help="Task description")
    gh_order.add_argument("--ref", help="Base branch (defaults to repo default)")
    gh_order.add_argument("--output", type=Path, help="Optional JSON file output")
    gh_order.add_argument("--path", action="append", dest="scope_paths",
                          help="Exact file to audit; repeat for scoped work order")

    gh_exec = sub.add_parser("gh-execute", help="Preview an agent patch or create a draft PR")
    gh_exec_source = gh_exec.add_mutually_exclusive_group(required=True)
    gh_exec_source.add_argument("--order", type=Path, help="JSON work-order")
    gh_exec_source.add_argument("--bundle", type=Path, help="SHA-pinned chat package JSON")
    gh_exec.add_argument("--manifest", required=True, type=Path, help="Reviewed JSON change-set")
    gh_exec.add_argument("--apply", action="store_true", help="Opt in to draft PR creation")

    gh_agent = sub.add_parser("gh-agent", help="Opt-in agent-neutral stdio executor (draft PR only)")
    gh_agent.add_argument("--repo", required=True, help="owner/name")
    gh_agent.add_argument("--goal", required=True, help="HYBRID DEBUG, BUILD or AUDIT-FIX")
    gh_agent.add_argument("--ref", help="Existing base branch")
    gh_agent.add_argument("--path", action="append", dest="scope_paths", required=True,
                          help="Audited exact file; repeat for each source file")
    gh_agent.add_argument("--agent-bin", required=True, help="Trusted local executable; never a shell string")
    gh_agent.add_argument("--agent-arg", action="append", default=[], help="Additional argument; repeat")
    gh_agent.add_argument("--agent-env", action="append", default=[],
                          help="Explicit environment variable passed to agent, never GitHub tokens")
    gh_agent.add_argument("--timeout", type=int, default=180)
    gh_agent.add_argument("--apply", action="store_true", help="Opt-in isolated branch and draft PR")

    gh_chat = sub.add_parser("gh-chat-package", help="Write scoped SHA-pinned code bundle for a connected chat agent")
    gh_chat.add_argument("--repo", required=True, help="owner/name")
    gh_chat.add_argument("--goal", required=True, help="HYBRID DEBUG / AUDIT-FIX / BUILD goal")
    gh_chat.add_argument("--ref", help="Target branch (default: default branch)")
    gh_chat.add_argument("--path", action="append", dest="scope_paths", required=True,
                         help="Audited exact file path (repeat, max 20)")
    gh_chat.add_argument("--output", required=True, type=Path,
                         help="New private local JSON filename; no source code printed")

    advice_package = sub.add_parser("gh-advice-package", help="Read-only Advisor -> private SHA-pinned source bundle")
    advice_package.add_argument("--report", required=True, type=Path, help="Existing assessment v1 JSON")
    advice_package.add_argument("--order-id", required=True, help="One Advisor review order ID")
    advice_package.add_argument("--repo", required=True, help="owner/name (the code to independently verify)")
    advice_package.add_argument("--ref", help="Source branch (default: repository default)")
    advice_package.add_argument("--output", required=True, type=Path, help="New private JSON bundle file")

    args = parser.parse_args(argv)

    if args.command in ("gh-audit", "gh-propose", "gh-task", "gh-verify", "gh-auto", "gh-workorder", "gh-execute", "gh-agent", "gh-chat-package", "gh-advice-package"):
        try:
            client = GitHubClient()
            if args.command == "gh-audit":
                output = (remote_audit(client, args.repo, args.ref, scope_paths=args.scope_paths)
                          if args.scope_paths else remote_audit(client, args.repo, args.ref))
                if args.output:
                    write_json(args.output.expanduser(), output)
            elif args.command == "gh-propose":
                document = json.loads(args.manifest.read_text(encoding="utf-8"))
                output = propose_changes(client, document, apply=args.apply)
            elif args.command == "gh-verify":
                output = (verify_pr(client, args.repo, args.pr, required_checks=args.require_check)
                          if args.require_check else verify_pr(client, args.repo, args.pr))
                if args.output:
                    save_report(output, args.output.expanduser())
            elif args.command == "gh-auto":
                output = (run_auto(client, args.repo, args.intent, ref=args.ref,
                                   apply=args.apply, scope_paths=args.scope_paths)
                          if args.scope_paths else
                          run_auto(client, args.repo, args.intent, ref=args.ref, apply=args.apply))
            elif args.command == "gh-workorder":
                output = (prepare(client, args.repo, args.goal, ref=args.ref,
                                  scope_paths=args.scope_paths)
                          if args.scope_paths else prepare(client, args.repo, args.goal, ref=args.ref))
                if args.output:
                    write_json(args.output.expanduser(), output)
            elif args.command == "gh-advice-package":
                output = export_advice_package(
                    client, args.report, args.order_id, args.repo, args.output,
                    ref=args.ref,
                )
            elif args.command == "gh-chat-package":
                output = export_chat_package(
                    client, args.repo, args.goal, args.scope_paths, args.output,
                    ref=args.ref,
                )
            elif args.command == "gh-agent":
                output = run_universal(
                    client, args.repo, args.goal, args.scope_paths,
                    [args.agent_bin, *args.agent_arg],
                    ref=args.ref, apply=args.apply, timeout=args.timeout,
                    allow_env=args.agent_env,
                )
            elif args.command == "gh-execute":
                if args.bundle is not None:
                    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
                    order = work_order_from_bundle(bundle)
                else:
                    order = json.loads(args.order.read_text(encoding="utf-8"))
                manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
                output = submit(client, order, manifest, apply=args.apply)
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
            if args.command == "gh-verify" and args.strict and output.get("ci") != "PASSED":
                return 1
            return 0
        except (OSError, ValueError, GitHubError, KeyError, TypeError, json.JSONDecodeError) as exc:
            parser.exit(2, f"hybrid: {exc}\n")
    if args.command in {"advise", "evidence-import"}:
        try:
            output = (advise(load_assessment(args.report)) if args.command == "advise" else
                      import_evidence(args.report, args.expected_sha))
            rendered = ((advice_markdown(output) if args.command == "advise" else evidence_markdown(output)) if args.format == "markdown" else
                        json.dumps(output, ensure_ascii=False, indent=2) + "\n")
            if args.output:
                destination = args.output.expanduser()
                if destination.resolve() in {p.expanduser().resolve() for p in ([args.report] if args.command == "advise" else args.report)}:
                    raise ValueError("Advice output must not overwrite its input report")
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(rendered, encoding="utf-8")
            print(rendered, end="")
            return 0
        except (OSError, ValueError) as exc:
            parser.exit(2, f"hybrid: {exc}\n")
    try:
        root = args.target.expanduser().resolve(strict=True)
        if not root.is_dir():
            parser.error("--target must be a directory")
        if args.command == "db-audit":
            output = scan_database(root)
            if args.output:
                write_json(args.output.expanduser(), output)
        elif args.command == "assess":
            output = assess_project(root)
            if args.format == "markdown":
                rendered = assessment_markdown(output)
                if args.output:
                    destination = args.output.expanduser()
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_text(rendered, encoding="utf-8")
                print(rendered, end="")
                return 0
            if args.output:
                write_json(args.output.expanduser(), output)
        elif args.command == "init":
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
            db_guard = scan_database(root)
            tests = run_tests(root) if args.tests else {"status": "NOT_RUN", "reason": "Requires --tests"}
            report = {
                "schema_version": 1,
                "id": plan["id"], "target": str(root),
                "flow": route(args.intent), "plan": str(plan_path),
                "audit": audit, "tests": tests,
                "status": "needs_agent_execution" if plan["flow"] in ("build", "audit-fix", "debug", "review") else "reported",
            }
            if db_guard["database_signals"] or db_guard["findings"] or plan["flow"] == "db-audit":
                report["db_guard"] = db_guard
            report_path = write_json(paths / "reports" / (plan["id"] + ".json"), report)
            markdown_path = paths / "reports" / (plan["id"] + ".md")
            markdown_path.write_text(markdown_report(report, tests), encoding="utf-8")
            state = {
                "schema_version": 1, "status": report["status"], "last_run": plan["id"],
                "flow": plan["flow"], "plan": str(plan_path),
                "report": str(report_path), "report_markdown": str(markdown_path),
                "tests_status": tests["status"], "findings": len(audit["findings"]),
            }
            if "db_guard" in report:
                state["db_guard_status"] = db_guard["status"]
                state["db_guard_findings"] = len(db_guard["findings"])
            write_json(paths / "state.json", state)
            output = state
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(2, f"hybrid: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
