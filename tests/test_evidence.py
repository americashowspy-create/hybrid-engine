"""CI evidence documents must report only observed SHA-bound checks."""
import json
import tempfile
import unittest
from pathlib import Path

from hybrid_engine.evidence import render_report, save_report


class EvidenceTests(unittest.TestCase):
    def test_emits_json_and_readable_markdown(self):
        report = {
            "repo": "acme/demo", "pr_number": 9, "head_sha": "a" * 40,
            "ci": "MISSING_REQUIRED", "merged": False,
            "required_checks": ["test", "security"],
            "missing_required_checks": ["security"],
            "checks": [{"name": "test", "outcome": "PASSED", "source": "check_run"}],
        }
        with tempfile.TemporaryDirectory() as temp:
            json_path, md_path = save_report(report, Path(temp) / "pr-9.json")
            self.assertEqual(json.loads(json_path.read_text()), report)
            self.assertIn("Missing required checks", md_path.read_text())
            self.assertIn("MISSING_REQUIRED", md_path.read_text())
            self.assertIn("a" * 40, md_path.read_text())

    def test_invalid_report_extension_is_rejected(self):
        with self.assertRaises(ValueError):
            save_report({}, Path("report.txt"))

    def test_untrusted_check_name_cannot_add_a_new_markdown_heading(self):
        report = {"checks": [{"name": "test\n# forged success", "outcome": "FAILED"}]}
        self.assertNotIn("\n# forged success", render_report(report))


if __name__ == "__main__":
    unittest.main()
