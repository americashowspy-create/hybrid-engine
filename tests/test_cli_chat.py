"""CLI routes for the chat-only source package and existing safe PR gate."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hybrid_engine.cli import main


class ChatCliTests(unittest.TestCase):
    def invoke(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(argv)
        return code, json.loads(buf.getvalue())

    def test_bundle_cli_does_not_print_source(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch("hybrid_engine.cli.GitHubClient"), \
             patch("hybrid_engine.cli.export_chat_package",
                   return_value={"status": "PACKAGE_EXPORTED", "tests": "NOT_RUN"}) as exporter:
            out = Path(directory) / "bundle.json"
            code, data = self.invoke([
                "gh-chat-package", "--repo", "acme/demo", "--goal", "HYBRID DEBUG",
                "--path", "src/demo.py", "--output", str(out),
            ])
        self.assertEqual(code, 0)
        self.assertEqual(data["status"], "PACKAGE_EXPORTED")
        self.assertNotIn("sources", data)
        self.assertEqual(exporter.call_args.kwargs["ref"], None)

    def test_execute_accepts_valid_bundle_and_remains_preview(self):
        order = {"repo": "acme/demo", "scope": {"paths": ["src/demo.py"]}}
        bundle = {
            "protocol": "hybrid.agent-stdio.v1", "work_order": order,
            "sources": [{"path": "src/demo.py"}],
        }
        manifest = {"schema_version": 1}
        with tempfile.TemporaryDirectory() as directory:
            b, m = Path(directory) / "bundle.json", Path(directory) / "manifest.json"
            b.write_text(json.dumps(bundle), encoding="utf-8")
            m.write_text(json.dumps(manifest), encoding="utf-8")
            with patch("hybrid_engine.cli.GitHubClient"), \
                 patch("hybrid_engine.cli.submit",
                       return_value={"status": "PREVIEW"}) as submit:
                code, result = self.invoke([
                    "gh-execute", "--bundle", str(b), "--manifest", str(m),
                ])
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "PREVIEW")
        self.assertEqual(submit.call_args.args[1], order)
        self.assertFalse(submit.call_args.kwargs["apply"])

    def test_refuses_order_and_bundle_together(self):
        with self.assertRaises(SystemExit) as err:
            main(["gh-execute", "--order", "a.json", "--bundle", "b.json",
                  "--manifest", "c.json"])
        self.assertEqual(err.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
