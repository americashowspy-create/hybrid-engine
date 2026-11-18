"""Multi-batch project audit contract: exact paths, bounds, evidence, no writes."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hybrid_engine.assessment import assess_project
from hybrid_engine.cli import main
from hybrid_engine.db_guard import scan_database
from hybrid_engine.project_audit import project_audit
from hybrid_engine.workspace_audit import audit_workspace


class WorkspaceAuditTests(unittest.TestCase):
    def _project(self, root: Path, n: int = 252):
        for i in range(n):
            (root / f"a{i:03}.py").write_text("value = 1\n", encoding="utf-8")

    def test_small_project_retains_v011_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("value = 1\n")
            result = project_audit(root)
            self.assertNotIn("workspace", result)
            self.assertEqual(result["coverage"]["status"], "BOUNDED_COMPLETE")
            self.assertEqual(result["tests"]["status"], "NOT_RUN")

    def test_flat_directory_above_250_is_audited_in_two_batches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._project(root)
            (root / "z-last.js").write_text("eval(input);\n")
            (root / ".env.production").write_text("NEVER_READ_THIS_SECRET=ABC\n")
            before = sorted(p.name for p in root.iterdir())
            result = project_audit(root)
            self.assertEqual(before, sorted(p.name for p in root.iterdir()))
            self.assertEqual(result["coverage"]["status"], "INCOMPLETE")
            self.assertEqual(result["advisor"]["status"], "BLOCKED")
            scoped = result["workspace"]
            self.assertEqual(scoped["coverage"]["status"], "BOUNDED_COMPLETE")
            self.assertEqual(scoped["coverage"]["partitions"], 2)
            self.assertEqual(scoped["coverage"]["eligible_files"], 253)
            self.assertEqual(scoped["coverage"]["assigned_files"], 253)
            self.assertEqual(scoped["coverage"]["unassigned_files"], 0)
            self.assertEqual(scoped["coverage"]["private_env_files_excluded"], 1)
            self.assertEqual(sum(p["selected_files"] for p in scoped["partitions"]), 253)
            self.assertIn("z-last.js", [f["path"] for f in scoped["findings"]])
            self.assertNotIn("NEVER_READ_THIS_SECRET", json.dumps(result))
            self.assertEqual(scoped["execution"]["project_tests"], "NOT_RUN")
            self.assertEqual(scoped["coverage"]["cross_partition_import_graph"], "NOT_VERIFIED")

    def test_late_sql_file_still_reaches_db_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._project(root)
            (root / "z.sql").write_text("ALTER TABLE accounts DISABLE ROW LEVEL SECURITY;\n")
            report = project_audit(root)["workspace"]
            self.assertIn("RLS_DISABLED", {f["rule"] for f in report["findings"]})
            self.assertIn("sql-or-migrations", report["database_signals"])
            self.assertEqual(report["coverage"]["status"], "BOUNDED_COMPLETE")

    def test_max_partition_budget_is_honestly_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._project(root)
            with patch("hybrid_engine.workspace_audit.MAX_PARTITIONS", 1):
                report = audit_workspace(root)
            self.assertEqual(report["status"], "INCOMPLETE")
            self.assertEqual(report["coverage"]["assigned_files"], 250)
            self.assertEqual(report["coverage"]["unassigned_files"], 2)
            self.assertEqual(report["coverage"]["status"], "INCOMPLETE")

    def test_large_unreadable_source_never_creates_false_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._project(root)
            (root / "zz.py").write_bytes(b"a" * (256 * 1024 + 1))
            report = audit_workspace(root)
            self.assertEqual(report["status"], "INCOMPLETE")
            self.assertEqual(report["coverage"]["unreadable_or_oversized_files"], 1)

    def test_scoped_assessment_rejects_unknown_or_duplicate_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("ok = True\n")
            with self.assertRaises(ValueError):
                assess_project(root, scope_paths=["../outside.py"])
            with self.assertRaises(ValueError):
                assess_project(root, scope_paths=["app.py", "app.py"])
            result = assess_project(root, scope_paths=["app.py"])
            self.assertEqual(result["coverage"]["scope"], "selected_local_files")
            self.assertEqual(result["coverage"]["selected_files"], 1)

    def test_db_guard_scoped_scan_never_includes_unselected_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "open.sql").write_text("ALTER TABLE x DISABLE ROW LEVEL SECURITY;\n")
            (root / "safe.sql").write_text("SELECT 1;\n")
            report = scan_database(root, include_paths={"safe.sql"})
            self.assertEqual(report["findings"], [])
            self.assertEqual(report["files_scanned"], 1)

    def test_cli_auto_scope_and_explicit_disable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            self._project(root)
            output_path = Path(tmp) / "workspace.json"
            with contextlib.redirect_stdout(io.StringIO()) as output:
                rc = main(["project-audit", "--target", str(root), "--output", str(output_path)])
            self.assertEqual(rc, 0)
            summary = json.loads(output.getvalue())
            details = json.loads(output_path.read_text())
            self.assertEqual(summary["partitions"], 2)
            self.assertEqual(summary["workspace_coverage"], "BOUNDED_COMPLETE")
            self.assertEqual(details["workspace"]["coverage"]["eligible_files"], 252)
            with contextlib.redirect_stdout(io.StringIO()) as output:
                rc = main(["project-audit", "--target", str(root), "--no-auto-scope",
                           "--output", str(output_path)])
            self.assertEqual(rc, 0)
            self.assertNotIn("workspace", json.loads(output_path.read_text()))
            self.assertNotIn("partitions", json.loads(output.getvalue()))

    def test_deterministic_under_identical_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._project(root)
            first = audit_workspace(root)
            again = audit_workspace(root)
            self.assertEqual(first, again)


if __name__ == "__main__":
    unittest.main()
