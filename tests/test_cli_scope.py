"""Scoped commands can be dispatched through the model-neutral CLI."""
import contextlib
import io
import json
import unittest
from unittest.mock import patch

from hybrid_engine.cli import main


class ScopedCLITests(unittest.TestCase):
    def invoke(self, args):
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture):
            status = main(args)
        return status, json.loads(capture.getvalue())

    def test_audit_passes_exact_path_list(self):
        with patch("hybrid_engine.cli.GitHubClient") as conn, \
             patch("hybrid_engine.cli.remote_audit",
                   return_value={"scope": {"complete": True}}) as audit:
            status, result = self.invoke(["gh-audit", "--repo", "acme/demo",
                                          "--path", ".gitignore"])
            self.assertEqual(status, 0)
            self.assertTrue(result["scope"]["complete"])
            audit.assert_called_once_with(conn.return_value, "acme/demo", None,
                                          scope_paths=[".gitignore"])

    def test_workorder_passes_scope_paths(self):
        with patch("hybrid_engine.cli.GitHubClient") as conn, \
             patch("hybrid_engine.cli.prepare",
                   return_value={"scope_limited": True}) as agent:
            status, result = self.invoke(["gh-workorder", "--repo", "acme/demo",
                                          "--goal", "HYBRID DEBUG", "--path", ".gitignore"])
            self.assertEqual(status, 0)
            self.assertTrue(result["scope_limited"])
            agent.assert_called_once_with(conn.return_value, "acme/demo",
                                          "HYBRID DEBUG", ref=None,
                                          scope_paths=[".gitignore"])

    def test_guarded_executor_restricts_scope(self):
        with patch("hybrid_engine.cli.GitHubClient") as conn, \
             patch("hybrid_engine.cli.run_auto",
                   return_value={"status": "PREVIEW"}) as auto:
            status, _ = self.invoke(["gh-auto", "--repo", "acme/demo",
                                     "--intent", "HYBRID AUDIT-FIX",
                                     "--path", ".gitignore"])
            self.assertEqual(status, 0)
            auto.assert_called_once_with(conn.return_value, "acme/demo", "HYBRID AUDIT-FIX",
                                         ref=None, apply=False, scope_paths=[".gitignore"])
