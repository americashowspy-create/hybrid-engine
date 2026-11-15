"""Offline assessment contract and regression tests for the v0.10 development branch."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from hybrid_engine.assessment import assess_project, assessment_markdown
from hybrid_engine.cli import main


def rule_set(report):
    return {entry["rule"] for entry in report["findings"]}


class AssessmentTests(unittest.TestCase):
    def test_empty_project_stable_and_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            before = list(root.iterdir())
            result = assess_project(root)
            self.assertEqual(result, assess_project(root))
            self.assertEqual(result["status"], "NO_FINDINGS")
            self.assertEqual(result["mode"], "static_read_only")
            self.assertEqual(result["findings"], [])
            self.assertEqual(result["recommendations"], [])
            self.assertEqual(result["verification"]["tests"]["status"], "NOT_RUN")
            self.assertEqual(result["verification"]["live_database"]["backup"]["status"],
                             "NOT_VERIFIED")
            self.assertEqual(list(root.iterdir()), before)

    def test_sql_findings_are_suspected_and_have_recommendations(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "schema.sql").write_text(
                "ALTER TABLE customers DISABLE ROW LEVEL SECURITY;\n"
                "CREATE POLICY public_read ON customers FOR SELECT USING (true);\n"
            )
            result = assess_project(root)
            self.assertIn("RLS_DISABLED", rule_set(result))
            self.assertIn("PERMISSIVE_SQL_POLICY", rule_set(result))
            self.assertEqual(len(result["findings"]), len(result["recommendations"]))
            self.assertTrue(all(x["confidence"] == "suspected" for x in result["findings"]))
            self.assertTrue(all(x["status"] == "PROPOSED_NOT_APPLIED"
                                for x in result["recommendations"]))
            self.assertEqual(result["verification"]["live_database"]["security"]["status"],
                             "NOT_VERIFIED")

    def test_long_source_and_exact_duplicate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shared = "export const value = 1;\n" * 60
            (root / "first.ts").write_text(shared)
            (root / "second.ts").write_text(shared)
            (root / "long.py").write_text("x = 1\n" * 501)
            result = assess_project(root)
            self.assertIn("LARGE_SOURCE_FILE", rule_set(result))
            self.assertIn("EXACT_DUPLICATE_SOURCE", rule_set(result))
            self.assertIn("NO_TESTS_DETECTED", rule_set(result))
            duplicates = [x for x in result["findings"]
                          if x["rule"] == "EXACT_DUPLICATE_SOURCE"]
            self.assertEqual(len(duplicates), 1)
            self.assertEqual(duplicates[0]["path"], "second.ts")

    def test_conventional_tests_prevent_missing_test_warning(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "app.py").write_text("def answer(): return 42\n")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text("def test_answer(): assert True\n")
            self.assertNotIn("NO_TESTS_DETECTED", rule_set(assess_project(root)))

    def test_missing_js_lockfile_is_only_a_suspicion(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "package.json").write_text('{"name":"example"}')
            result = assess_project(root)
            self.assertIn("MISSING_JS_LOCKFILE", rule_set(result))
            (root / "package-lock.json").write_text('{"lockfileVersion":3}')
            self.assertNotIn("MISSING_JS_LOCKFILE", rule_set(assess_project(root)))

    def test_real_env_files_are_not_read_or_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            secret = "SENSITIVE_TEST_TOKEN_DO_NOT_EMIT"
            (root / ".env").write_text("GITHUB_TOKEN=" + secret + "\n")
            (root / ".env.production").write_text("DB_PASSWORD=" + secret + "\n")
            (root / ".env.example").write_text("VITE_SUPABASE_SERVICE_ROLE_KEY=" + secret + "\n")
            result = assess_project(root)
            rendered = json.dumps(result)
            self.assertNotIn(secret, rendered)
            self.assertIn("PUBLIC_PRIVILEGED_CONFIG", rule_set(result))
            self.assertEqual(result["coverage"]["sensitive_env_files_excluded"], 3)
            self.assertEqual(result["coverage"]["general_files_scanned"], 0)

    def test_symlinks_are_not_followed(self):
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as outside:
            root = Path(temp)
            foreign = Path(outside) / "evil.js"
            foreign.write_text("eval(untrusted);\n")
            (root / "evil.js").symlink_to(foreign)
            (root / "external").symlink_to(Path(outside), target_is_directory=True)
            result = assess_project(root)
            self.assertEqual(result["findings"], [])
            self.assertEqual(result["coverage"]["candidate_files"], 0)

    def test_binary_source_yields_incomplete_not_a_clean_bill(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "binary.js").write_bytes(b"\x00" + b"a" * 200)
            result = assess_project(root)
            self.assertEqual(result["status"], "INCOMPLETE")
            self.assertEqual(result["coverage"]["status"], "INCOMPLETE")
            self.assertEqual(result["findings"], [])

    def test_more_than_250_candidate_files_is_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for number in range(253):
                (root / f"m{number:03}.py").write_text("x = 1\n")
            result = assess_project(root)
            self.assertTrue(result["coverage"]["truncated"])
            self.assertEqual(result["coverage"]["candidate_files"], 250)
            self.assertEqual(result["status"], "INCOMPLETE")

    def test_stable_finding_ids_and_no_source_snippets(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "app.ts").write_text("eval(sensitiveValue);\n")
            a = assess_project(root)
            b = assess_project(root)
            self.assertEqual(a["findings"], b["findings"])
            self.assertIn("JS_EVAL", rule_set(a))
            self.assertNotIn("sensitiveValue", json.dumps(a))
            self.assertTrue(all(len(item["id"]) == 16 for item in a["findings"]))

    def test_cli_json_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "app.py").write_text("value = 42\n")
            before = sorted(p.name for p in root.iterdir())
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = main(["assess", "--target", str(root)])
            self.assertEqual(rc, 0)
            report = json.loads(out.getvalue())
            self.assertEqual(report["mode"], "static_read_only")
            self.assertEqual(sorted(p.name for p in root.iterdir()), before)
            self.assertFalse((root / ".hybrid").exists())

    def test_cli_markdown_and_explicit_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            root.mkdir()
            (root / "app.py").write_text("value = 42\n")
            output = Path(temp) / "reports" / "assessment.md"
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = main(["assess", "--target", str(root), "--format", "markdown",
                           "--output", str(output)])
            self.assertEqual(rc, 0)
            self.assertIn("Project Assessment", out.getvalue())
            self.assertEqual(output.read_text(), out.getvalue())
            self.assertFalse((root / ".hybrid").exists())
            self.assertNotIn("Tests: **PASSED**", out.getvalue())


if __name__ == "__main__":
    unittest.main()
