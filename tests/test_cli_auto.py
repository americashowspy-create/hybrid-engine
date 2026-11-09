import contextlib
import io
import json
import unittest
from unittest.mock import patch

from hybrid_engine.cli import main


class CliAutoTests(unittest.TestCase):
    def test_default_preview(self):
        output = io.StringIO()
        with patch("hybrid_engine.cli.GitHubClient") as client, \
                patch("hybrid_engine.cli.run_auto", return_value={"status": "PREVIEW"}) as execute, \
                contextlib.redirect_stdout(output):
            rc = main(["gh-auto", "--repo", "acme/demo",
                       "--intent", "HYBRID AUDIT-FIX"])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "PREVIEW")
        execute.assert_called_once_with(client.return_value, "acme/demo",
                                        "HYBRID AUDIT-FIX", ref=None, apply=False)

    def test_apply_flag_is_explicit(self):
        output = io.StringIO()
        with patch("hybrid_engine.cli.GitHubClient"), \
                patch("hybrid_engine.cli.run_auto", return_value={"status": "DRAFT_PR_CREATED"}) as execute, \
                contextlib.redirect_stdout(output):
            rc = main(["gh-auto", "--repo", "acme/demo",
                       "--intent", "HYBRID AUDIT-FIX", "--apply"])
        self.assertEqual(rc, 0)
        self.assertTrue(execute.call_args.kwargs["apply"])
