"""Smoke and permission semantics for the chat-friendly task commands."""
import contextlib
import io
import json
import unittest
from unittest.mock import patch

from hybrid_engine.cli import main


class ChatCliTests(unittest.TestCase):
    def invoke(self, args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(args)
        return code, json.loads(output.getvalue())

    def test_verify_binds_repo_and_pr(self):
        expected = {"ci": "PASSED", "head_sha": "a" * 40}
        with patch("hybrid_engine.cli.GitHubClient") as gh, \
                patch("hybrid_engine.cli.verify_pr", return_value=expected) as verify:
            code, result = self.invoke(["gh-verify", "--repo", "acme/demo", "--pr", "7"])
        self.assertEqual(code, 0)
        self.assertEqual(result, expected)
        verify.assert_called_once_with(gh.return_value, "acme/demo", 7)

    def test_start_does_not_apply_unless_opted_in(self):
        with patch("hybrid_engine.cli.GitHubClient"), \
                patch("hybrid_engine.cli.start_task", return_value={"status": "PREVIEW"}) as start:
            code, result = self.invoke(["gh-task", "start", "--repo", "acme/demo", "--goal", "Audite a API"])
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "PREVIEW")
        self.assertIs(start.call_args.kwargs["apply"], False)

    def test_start_opt_in(self):
        with patch("hybrid_engine.cli.GitHubClient"), \
                patch("hybrid_engine.cli.start_task", return_value={"status": "CREATED"}) as start:
            code, result = self.invoke(["gh-task", "start", "--repo", "acme/demo", "--goal", "Audite a API", "--apply"])
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "CREATED")
        self.assertIs(start.call_args.kwargs["apply"], True)

    def test_note_default_preview_and_optional_pr(self):
        with patch("hybrid_engine.cli.GitHubClient"), \
                patch("hybrid_engine.cli.note_task", return_value={"status": "PREVIEW"}) as note:
            code, result = self.invoke(["gh-task", "note", "--repo", "acme/demo",
                                        "--issue", "12", "--state", "review_ready",
                                        "--summary", "PR available", "--pr", "3"])
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "PREVIEW")
        note.assert_called_once()
        self.assertEqual(note.call_args.kwargs, {"pr_number": 3, "apply": False})

    def test_list_and_status_route_read_only(self):
        with patch("hybrid_engine.cli.GitHubClient"), \
                patch("hybrid_engine.cli.list_tasks", return_value={"tasks": []}) as listing, \
                patch("hybrid_engine.cli.task_status", return_value={"state": "planned"}) as status:
            self.assertEqual(self.invoke(["gh-task", "list", "--repo", "acme/demo"])[0], 0)
            self.assertEqual(self.invoke(["gh-task", "status", "--repo", "acme/demo", "--issue", "2"])[0], 0)
            listing.assert_called_once()
            status.assert_called_once()
