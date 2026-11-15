import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from hybrid_engine.db_guard import scan_database
from hybrid_engine.cli import main
from hybrid_engine.core import route


class DatabaseGuardTests(unittest.TestCase):
    def test_empty_repo_no_evidence_and_unknown_checks(self):
        with tempfile.TemporaryDirectory() as temp:
            result = scan_database(Path(temp))
            self.assertEqual(result["status"], "NO_DATABASE_EVIDENCE")
            self.assertEqual(result["findings"], [])
            self.assertEqual(result["verification"]["backup"]["status"], "NOT_VERIFIED")

    def test_db_dependency_signal_and_unknown_live_checks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "package.json").write_text('{"dependencies":{"@supabase/supabase-js":"^2"}}')
            result = scan_database(root)
            self.assertEqual(result["status"], "DETECTED")
            self.assertIn("database-dependency", result["database_signals"])
            self.assertTrue(all(x["status"] == "NOT_VERIFIED" for x in result["verification"].values()))

    def test_security_modeling_migrations_performance_and_redaction(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "supabase" / "migrations").mkdir(parents=True)
            (root / "supabase" / "migrations" / "001.sql").write_text("""
                CREATE TABLE invoices (amount FLOAT, created_at TIMESTAMP);
                ALTER TABLE invoices DISABLE ROW LEVEL SECURITY;
                CREATE POLICY open_all ON invoices
                FOR SELECT USING (true);
                DROP TABLE legacy_records;
                SELECT id FROM invoices OFFSET 1000;
            """)
            (root / "firestore.rules").write_text("allow read, write: if true;")
            (root / ".env.example").write_text("VITE_SUPABASE_SERVICE_ROLE_KEY=PRIVATE_VALUE_SHOULD_NOT_LEAK\n")
            result = scan_database(root)
            rules = {x["rule"] for x in result["findings"]}
            self.assertTrue({"PUBLIC_PRIVILEGED_CONFIG", "FIREBASE_OPEN_RULE", "RLS_DISABLED",
                             "PERMISSIVE_SQL_POLICY", "MONEY_FLOAT", "TIMESTAMP_NO_TZ",
                             "DESTRUCTIVE_MIGRATION", "HIGH_OFFSET"} <= rules)
            self.assertNotIn("PRIVATE_VALUE_SHOULD_NOT_LEAK", json.dumps(result))

    def test_avoids_sql_comment_and_unrelated_float(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "schema.sql").write_text(
                "-- ALTER TABLE x DISABLE ROW LEVEL SECURITY;\n"
                "CREATE TABLE x (temperature FLOAT, amount NUMERIC, updated_at TIMESTAMPTZ);\n"
            )
            self.assertEqual(scan_database(root)["findings"], [])

    def test_symbolic_links_not_followed(self):
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as outside:
            root = Path(temp)
            foreign = Path(outside) / "danger.sql"
            foreign.write_text("ALTER TABLE x DISABLE ROW LEVEL SECURITY;")
            (root / "danger.sql").symlink_to(foreign)
            self.assertEqual(scan_database(root)["findings"], [])

    def test_bounded_and_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for i in range(255):
                (root / f"{i:03}.sql").write_text("SELECT 1;")
            result = scan_database(root)
            self.assertEqual(result["files_scanned"], 250)
            self.assertTrue(result["truncated"])
            self.assertEqual(result["status"], "INCOMPLETE")

    def test_prisma_float(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "schema.prisma").write_text("model Balance {\n  saldo Float\n}\n")
            result = scan_database(root)
            self.assertEqual([x["rule"] for x in result["findings"]], ["MONEY_FLOAT"])

    def test_db_audit_cli_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "schema.sql").write_text("CREATE TABLE invoices (amount FLOAT);\n")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                rc = main(["db-audit", "--target", str(root)])
            result = json.loads(output.getvalue())
            self.assertEqual(rc, 0)
            self.assertEqual(result["mode"], "static_read_only")
            self.assertEqual(sorted(x.name for x in root.iterdir()), ["schema.sql"])

    def test_run_auto_attaches_db_guard_without_tests(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "schema.prisma").write_text("model Sales {\n  price Float\n}\n")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                rc = main(["run", "--target", str(root), "--intent", "HYBRID AUTO"])
            state = json.loads(output.getvalue())
            report = json.loads(Path(state["report"]).read_text())
            self.assertEqual(rc, 0)
            self.assertEqual(report["tests"]["status"], "NOT_RUN")
            self.assertIn("db_guard", report)
            self.assertIn("MONEY_FLOAT", {x["rule"] for x in report["db_guard"]["findings"]})

    def test_explicit_db_audit_routing(self):
        self.assertEqual(route("HYBRID DB-AUDIT"), "db-audit")
        self.assertEqual(route("HYBRID AUTO"), "audit")


    def test_limited_findings_and_very_large_offset(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "load.sql").write_text(
                "SELECT 1 OFFSET " + "9" * 10000 + ";\n" + "SELECT 1 OFFSET 500;\n" * 700
            )
            result = scan_database(root)
            self.assertTrue(result["findings_truncated"])
            self.assertEqual(len(result["findings"]), 500)
            self.assertEqual(result["status"], "INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
