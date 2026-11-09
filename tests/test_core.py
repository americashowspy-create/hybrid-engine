import tempfile
import unittest
from pathlib import Path

from hybrid_engine.core import make_plan, route
from hybrid_engine.audit import scan
from hybrid_engine.store import initialize, read_state
from hybrid_engine.runner import choose_test_command, run_tests


class RouterTests(unittest.TestCase):
    def test_explicit(self):
        self.assertEqual(route("HYBRID BUILD: corrigir e auditar"), "build")
        self.assertEqual(route("HYBRID AUDIT-FIX"), "audit-fix")

    def test_auto_intents(self):
        self.assertEqual(route("audite e corrija o projeto"), "audit-fix")
        self.assertEqual(route("corrija o bug da automação"), "debug")
        self.assertEqual(route("crie uma funcionalidade"), "build")
        self.assertEqual(route("veja as pendências"), "status")

    def test_plan_steps(self):
        plan = make_plan("HYBRID DEBUG", "example")
        self.assertEqual(plan["flow"], "debug")
        self.assertIn("root_cause", [step["name"] for step in plan["steps"]])


class AuditorTests(unittest.TestCase):
    def test_secret_redacted_and_public_key_not_flagged(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "package.json").write_text('{"scripts":{}}')
            (root / "index.ts").write_text(
                "const pub = 'sb_publishable_abcdefghijklm';\n"
                "const secret = 'sb_secret_abcdefghijklm';\n"
                "eval('1+1');\n", encoding="utf-8")
            data = scan(root)
            self.assertIn("Node.js", data["stack"])
            self.assertEqual({f["rule"] for f in data["findings"]}, {"SUPABASE_SECRET", "JS_EVAL"})
            self.assertNotIn("sb_secret_abcdefghijklm", str(data))

    def test_no_follow_symlink(self):
        with tempfile.TemporaryDirectory() as rootdir, tempfile.TemporaryDirectory() as outside:
            root = Path(rootdir)
            (Path(outside) / "secret.js").write_text("eval('bad')")
            (root / "linked").symlink_to(outside, target_is_directory=True)
            self.assertEqual(scan(root)["files_scanned"], 0)


class StateTests(unittest.TestCase):
    def test_init_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            initialize(root)
            initialize(root)
            self.assertEqual(read_state(root)["status"], "initialized")

    def test_test_output_is_not_saved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "pyproject.toml").write_text("[project]\nname='demo'\n")
            (root / "tests").mkdir()
            (root / "tests" / "test_example.py").write_text(
                "import unittest\nclass TestExample(unittest.TestCase):\n"
                "    def test_case(self):\n        print('secret must never appear in report')\n"
            )
            data = run_tests(root)
            self.assertEqual(data["status"], "PASS")
            self.assertNotIn("secret must never appear in report", str(data))

    def test_no_implicit_test_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertIsNone(choose_test_command(Path(temp)))


if __name__ == "__main__":
    unittest.main()
