import contextlib
import io
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from hybrid_engine.cli import main


class CliTests(unittest.TestCase):
    def call(self, argv):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(argv)
        return status, json.loads(output.getvalue())

    def test_init_run_status(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(self.call(["init", "--target", temp])[0], 0)
            rc, result = self.call(["run", "--target", temp, "--intent", "HYBRID AUDIT"])
            self.assertEqual(rc, 0)
            self.assertEqual(result["tests_status"], "NOT_RUN")
            self.assertTrue(Path(result["report"]).exists())
            self.assertTrue(Path(result["plan"]).exists())
            rc, state = self.call(["status", "--target", temp])
            self.assertEqual(rc, 0)
            self.assertEqual(state["flow"], "audit")


    def test_gh_audit_cli_is_read_only(self):
        payload = {"mode": "remote-read-only", "tests": {"status": "NOT_RUN"}}
        with patch("hybrid_engine.cli.GitHubClient") as new_client, \
                patch("hybrid_engine.cli.remote_audit", return_value=payload) as handler:
            rc, result = self.call(["gh-audit", "--repo", "owner/repo", "--ref", "main"])
            self.assertEqual(rc, 0)
            self.assertEqual(result, payload)
            handler.assert_called_once_with(new_client.return_value, "owner/repo", "main")

    def test_gh_propose_dry_run_is_default(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "changes.json"
            path.write_text('{"schema_version": 1, "repo": "owner/repo"}')
            with patch("hybrid_engine.cli.GitHubClient"), \
                    patch("hybrid_engine.cli.propose_changes", return_value={"status": "PREVIEW"}) as handler:
                rc, result = self.call(["gh-propose", "--manifest", str(path)])
                self.assertEqual(rc, 0)
                self.assertEqual(result["status"], "PREVIEW")
                self.assertIs(handler.call_args.kwargs["apply"], False)

    def test_gh_propose_requires_explicit_apply(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "changes.json"
            path.write_text('{"schema_version": 1, "repo": "owner/repo"}')
            with patch("hybrid_engine.cli.GitHubClient"), \
                    patch("hybrid_engine.cli.propose_changes", return_value={"status": "DRAFT_PR_CREATED"}) as handler:
                rc, result = self.call(["gh-propose", "--manifest", str(path), "--apply"])
                self.assertEqual(rc, 0)
                self.assertEqual(result["status"], "DRAFT_PR_CREATED")
                self.assertIs(handler.call_args.kwargs["apply"], True)

    def test_inspect_does_not_write_state(self):
        with tempfile.TemporaryDirectory() as temp:
            rc, scan = self.call(["inspect", "--target", temp])
            self.assertEqual(rc, 0)
            self.assertEqual(scan["findings"], [])
            self.assertFalse((Path(temp) / ".hybrid").exists())


if __name__ == "__main__":
    unittest.main()
