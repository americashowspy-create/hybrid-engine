"""v0.11.2 coverage totals, strict CI exit and opt-in private file manifest."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hybrid_engine.cli import main
from hybrid_engine.project_audit import project_audit
from hybrid_engine.workspace_audit import build_file_manifest


class ProjectAuditCoverageV0112Tests(unittest.TestCase):
    def make_project(self, root: Path, count: int = 260) -> None:
        root.mkdir(parents=True, exist_ok=True)
        for n in range(count):
            (root / f"a{n:03d}.py").write_text("value = 1\n", encoding="utf-8")

    def cli(self, *arguments: str) -> tuple[int, dict]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main(list(arguments))
        return result, json.loads(output.getvalue())

    def test_legacy_summary_discloses_enumerated_and_pending_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            self.make_project(root)
            (root / "zz_test.sql").write_text(
                "ALTER TABLE accounts DISABLE ROW LEVEL SECURITY;\n")
            code, output = self.cli("project-audit", "--target", str(root),
                                    "--no-auto-scope", "--output", str(Path(tmp) / "legacy.json"))
            self.assertEqual(code, 0)
            self.assertEqual(output["enumerated_files"], 261)
            self.assertEqual(output["eligible_files"], 261)
            self.assertEqual(output["assigned_files"], 250)
            self.assertEqual(output["pending_files"], 11)
            self.assertEqual(output["general_files_scanned"], 250)
            self.assertEqual(output["effective_coverage"], "INCOMPLETE")
            self.assertFalse(output["manifest_included"])
            self.assertNotIn("workspace_status", output)
            report = json.loads((Path(tmp) / "legacy.json").read_text())
            self.assertEqual(report["coverage_summary"]["scope"], "initial_assessment")
            self.assertNotIn("file_manifest", report)
            self.assertNotIn("workspace", report)

    def test_auto_summary_uses_completed_workspace_not_initial_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            self.make_project(root)
            (root / "zz_test.sql").write_text(
                "ALTER TABLE accounts DISABLE ROW LEVEL SECURITY;\n")
            report = Path(tmp) / "report.json"
            code, output = self.cli("project-audit", "--target", str(root),
                                    "--strict-coverage", "--output", str(report))
            self.assertEqual(code, 0)
            self.assertEqual(output["coverage"], "INCOMPLETE")
            self.assertEqual(output["workspace_coverage"], "BOUNDED_COMPLETE")
            self.assertEqual(output["effective_coverage"], "BOUNDED_COMPLETE")
            self.assertEqual(output["enumerated_files"], 261)
            self.assertEqual(output["eligible_files"], 261)
            self.assertEqual(output["assigned_files"], 261)
            self.assertEqual(output["pending_files"], 0)
            self.assertEqual(output["partitions"], 2)
            details = json.loads(report.read_text())
            self.assertEqual(details["coverage_summary"]["first_pass_candidate_files"], 250)
            self.assertEqual(details["advisor"]["status"], "BLOCKED")
            self.assertIn("RLS_DISABLED",
                          {item["rule"] for item in details["workspace"]["findings"]})

    def test_strict_legacy_exits_one_but_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            self.make_project(root)
            path = Path(tmp) / "legacy.json"
            code, output = self.cli("project-audit", "--target", str(root),
                                    "--no-auto-scope", "--strict-coverage",
                                    "--output", str(path))
            self.assertEqual(code, 1)
            self.assertTrue(path.is_file())
            self.assertEqual(output["effective_coverage"], "INCOMPLETE")
            self.assertEqual(json.loads(path.read_text())["coverage_summary"]["unassigned_files"], 10)

    def test_strict_workspace_over_budget_exits_one_and_preserves_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            self.make_project(root)
            output = Path(tmp) / "cap.json"
            with patch("hybrid_engine.workspace_audit.MAX_PARTITIONS", 1):
                code, stdout = self.cli("project-audit", "--target", str(root),
                                        "--strict-coverage", "--output", str(output))
            self.assertEqual(code, 1)
            self.assertEqual(stdout["effective_coverage"], "INCOMPLETE")
            self.assertEqual(stdout["pending_files"], 10)
            report = json.loads(output.read_text())
            self.assertEqual(report["workspace"]["coverage"]["unassigned_files"], 10)

    def test_strict_mode_passes_small_no_findings_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            root.mkdir()
            (root / "app.py").write_text("x = 1\n")
            code, output = self.cli("project-audit", "--target", str(root),
                                    "--strict-coverage", "--output", str(Path(tmp) / "result.json"))
            self.assertEqual(code, 0)
            self.assertEqual(output["effective_coverage"], "BOUNDED_COMPLETE")
            self.assertEqual(output["eligible_files"], 1)
            self.assertEqual(output["pending_files"], 0)

    def test_manifest_is_opt_in_and_excludes_private_env_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            self.make_project(root)
            (root / "zz.sql").write_text(
                "ALTER TABLE accounts DISABLE ROW LEVEL SECURITY;\n")
            (root / ".env.private").write_text("VERY_PRIVATE_VALUE=123\n")
            before = sorted(x.name for x in root.iterdir())
            path = Path(tmp) / "report.json"
            code, stdout = self.cli("project-audit", "--target", str(root),
                                    "--include-file-manifest", "--output", str(path))
            self.assertEqual(code, 0)
            self.assertTrue(stdout["manifest_included"])
            details = json.loads(path.read_text())
            self.assertEqual(sorted(x.name for x in root.iterdir()), before)
            manifest = details["file_manifest"]
            self.assertEqual(len(manifest["batches"]), 2)
            self.assertEqual(len(manifest["batches"][0]["paths"]), 250)
            self.assertEqual(len(manifest["batches"][1]["paths"]), 11)
            self.assertEqual(manifest["unassigned_paths"], [])
            self.assertIn("zz.sql", manifest["batches"][1]["paths"])
            self.assertEqual(manifest["omitted_paths"], 0)
            self.assertNotIn(".env.private", json.dumps(details))
            self.assertNotIn("VERY_PRIVATE_VALUE", json.dumps(details))

    def test_manifest_legacy_mode_lists_unassigned_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            self.make_project(root)
            (root / "zz.sql").write_text("SELECT 1;\n")
            path = Path(tmp) / "legacy.json"
            code, _ = self.cli("project-audit", "--target", str(root),
                               "--no-auto-scope", "--include-file-manifest",
                               "--output", str(path))
            self.assertEqual(code, 0)
            m = json.loads(path.read_text())["file_manifest"]
            self.assertEqual(len(m["batches"]), 1)
            self.assertEqual(len(m["batches"][0]["paths"]), 250)
            self.assertEqual(len(m["unassigned_paths"]), 11)
            self.assertIn("zz.sql", m["unassigned_paths"])
            self.assertNotIn("workspace", json.loads(path.read_text()))

    def test_reject_manifest_without_report_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("x=1\n")
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    main(["project-audit", "--target", str(root),
                          "--include-file-manifest"])
            self.assertEqual(error.exception.code, 2)

    def test_reject_manifest_output_inside_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("x=1\n")
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    main(["project-audit", "--target", str(root),
                          "--include-file-manifest", "--output", str(root / "report.json")])
            self.assertEqual(error.exception.code, 2)
            self.assertFalse((root / "report.json").exists())

    def test_bounded_manifest_prioritizes_pending_paths(self):
        with patch("hybrid_engine.workspace_audit.MAX_MANIFEST_PATHS", 3):
            m = build_file_manifest([(1, ["a.py", "b.py", "c.py", "d.py"])],
                                    ["e.py", "f.py"], [])
        self.assertEqual(m["unassigned_paths"], ["e.py", "f.py"])
        self.assertEqual(m["batches"][0]["paths"], ["a.py"])
        self.assertEqual(m["batches"][0]["omitted"], 3)
        self.assertEqual(m["listed_paths"], 3)
        self.assertEqual(m["omitted_paths"], 3)
        self.assertTrue(m["truncated"])

    def test_oversized_file_count_and_manifest_are_truthful(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            self.make_project(root)
            (root / "zz.py").write_bytes(b"z" * (256 * 1024 + 1))
            result = project_audit(root, include_manifest=True)
            c = result["coverage_summary"]
            self.assertEqual(c["effective_status"], "INCOMPLETE")
            self.assertEqual(c["unreadable_or_oversized_files"], 1)
            self.assertEqual(c["eligible_files"], 260)
            self.assertIn("zz.py", result["file_manifest"]["unreadable_or_oversized_paths"])

    def test_default_does_not_disclose_manifest_even_on_large_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_project(root)
            report = project_audit(root)
            self.assertNotIn("file_manifest", report)
            self.assertEqual(report["coverage_summary"]["assigned_files"], 260)


if __name__ == "__main__":
    unittest.main()
