"""The AI-facing project audit must remain read-only and label evidence honestly."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from hybrid_engine.cli import main
from hybrid_engine.project_audit import project_audit


class ProjectAuditTests(unittest.TestCase):
    def test_local_report_composes_assessment_and_advice_without_target_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "sample"
            root.mkdir()
            (root / "app.py").write_text("def health():\n    return True\n", encoding="utf-8")
            before = sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))
            result = project_audit(root)
            after = sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))
            self.assertEqual(before, after)
            self.assertEqual(result["kind"], "hybrid.project-audit.v1")
            self.assertEqual(result["mode"], "static_read_only")
            self.assertIn("coverage", result)
            self.assertEqual(result["assessment"]["mode"], "static_read_only")
            self.assertEqual(result["advisor"]["kind"], "implementation_advice")
            self.assertEqual(result["tests"]["status"], "NOT_RUN")
            self.assertFalse(result["advisor"]["ready_for_proposal"])
            self.assertEqual(result["changes"]["target_files_modified"], 0)
            self.assertEqual(result["dimensions"]["tests_reliability"], "NOT_RUN")

    def test_cli_output_written_only_to_explicit_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "sample"
            root.mkdir()
            (root / "README.md").write_text("# Sample\n", encoding="utf-8")
            report = Path(temp) / "report.json"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["project-audit", "--target", str(root),
                                  "--output", str(report)])
            self.assertEqual(exit_code, 0)
            result = json.loads(stdout.getvalue())
            self.assertEqual(json.loads(report.read_text(encoding="utf-8")), result)
            self.assertFalse((root / ".hybrid").exists())
            self.assertEqual(result["target"], str(root.resolve()))
            self.assertIn(result["coverage"]["status"], {"BOUNDED_COMPLETE", "INCOMPLETE"})
            self.assertIn(result["dimensions"]["database"], {"PARTIAL_STATIC", "NOT_DETECTED"})

    def test_cli_rejects_output_inside_audited_project(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = root / "report.json"
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    main(["project-audit", "--target", str(root), "--output", str(report)])
            self.assertEqual(raised.exception.code, 2)
            self.assertFalse(report.exists())


if __name__ == "__main__":
    unittest.main()
