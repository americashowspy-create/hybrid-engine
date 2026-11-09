"""CLI integration for optional AI-agent work orders."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hybrid_engine.cli import main


class BridgeCLI(unittest.TestCase):
    def invoke(self, argv):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            rc = main(argv)
        return rc, json.loads(output.getvalue())

    def test_prepare_outputs_work_order(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch("hybrid_engine.cli.GitHubClient"), \
             patch("hybrid_engine.cli.prepare", return_value={"kind": "hybrid.agent-work-order"}) as handler:
            output = Path(temp) / "order.json"
            status, result = self.invoke(["gh-workorder", "--repo", "acme/demo",
                                          "--goal", "HYBRID DEBUG", "--output", str(output)])
            self.assertEqual(status, 0)
            self.assertEqual(result, json.loads(output.read_text()))
            self.assertEqual(handler.call_args.kwargs["ref"], None)

    def test_execute_preview_is_default(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch("hybrid_engine.cli.GitHubClient"), \
             patch("hybrid_engine.cli.submit", return_value={"status": "PREVIEW"}) as handler:
            order = Path(temp) / "order.json"
            manifest = Path(temp) / "manifest.json"
            order.write_text("{}")
            manifest.write_text("{}")
            status, result = self.invoke(["gh-execute", "--order", str(order),
                                          "--manifest", str(manifest)])
            self.assertEqual(status, 0)
            self.assertEqual(result["status"], "PREVIEW")
            self.assertFalse(handler.call_args.kwargs["apply"])

    def test_execute_apply_explicit(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch("hybrid_engine.cli.GitHubClient"), \
             patch("hybrid_engine.cli.submit", return_value={"status": "DRAFT_PR_CREATED"}) as handler:
            order = Path(temp) / "order.json"
            manifest = Path(temp) / "manifest.json"
            order.write_text("{}")
            manifest.write_text("{}")
            status, result = self.invoke(["gh-execute", "--order", str(order),
                                          "--manifest", str(manifest), "--apply"])
            self.assertEqual(status, 0)
            self.assertTrue(handler.call_args.kwargs["apply"])
