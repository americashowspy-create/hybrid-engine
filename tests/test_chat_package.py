"""Portable chat bundle must remain scoped, private and entirely read-only."""
import json
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hybrid_engine.chat_package import build_chat_package, export_chat_package, work_order_from_bundle

SHA = "a" * 40
ORDER = {
    "repo": "acme/demo", "base": "main", "base_sha": SHA,
    "ready_for_proposal": True,
    "scope": {"mode": "exact_files", "paths": ["src/demo.py"], "complete": True},
}
BUNDLE = {
    "schema_version": 1, "protocol": "hybrid.agent-stdio.v1",
    "work_order": ORDER,
    "sources": [{"path": "src/demo.py", "expected_sha": "b" * 40,
                 "content": "SECRET_CODE_CONTENT = 'private'\n"}],
}


class ChatPackageTests(unittest.TestCase):
    def test_bundle_recovers_exact_work_order(self):
        self.assertEqual(work_order_from_bundle(BUNDLE), ORDER)
        with self.assertRaises(ValueError):
            work_order_from_bundle({**BUNDLE, "protocol": "unknown"})
        with self.assertRaises(ValueError):
            work_order_from_bundle({**BUNDLE, "sources": [{"path": "other.py"}]})

    def test_requires_exact_file_paths(self):
        with self.assertRaises(ValueError):
            build_chat_package(object(), "acme/demo", "HYBRID DEBUG", [])

    def test_no_executor_called_and_scope_is_forwarded(self):
        with patch("hybrid_engine.chat_package.prepare", return_value=ORDER) as prepare, \
             patch("hybrid_engine.chat_package.source_package", return_value=BUNDLE) as source:
            result = build_chat_package(object(), "acme/demo", "HYBRID DEBUG",
                                        ["src/demo.py"], ref="main")
        self.assertEqual(result["protocol"], "hybrid.agent-stdio.v1")
        self.assertEqual(prepare.call_args.kwargs,
                         {"ref": "main", "scope_paths": ["src/demo.py"]})
        source.assert_called_once()

    def test_incomplete_audit_blocks_source_export(self):
        blocked = {**ORDER, "ready_for_proposal": False}
        with patch("hybrid_engine.chat_package.prepare", return_value=blocked), \
             patch("hybrid_engine.chat_package.source_package") as source:
            with self.assertRaises(ValueError):
                build_chat_package(object(), "acme/demo", "HYBRID DEBUG", ["src/demo.py"])
        source.assert_not_called()

    def test_file_private_and_result_never_prints_source(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch("hybrid_engine.chat_package.build_chat_package", return_value=BUNDLE):
            output = Path(temp) / "bundle.json"
            report = export_chat_package(object(), "acme/demo", "HYBRID DEBUG",
                                         ["src/demo.py"], output)
            self.assertEqual(json.loads(output.read_text()), BUNDLE)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            self.assertEqual(report["status"], "PACKAGE_EXPORTED")
            self.assertEqual(report["github_writes"], False)
            self.assertEqual(report["tests"], "NOT_RUN")
            self.assertNotIn("SECRET_CODE_CONTENT", json.dumps(report))
            self.assertEqual(report["base_sha"], SHA)

    def test_refuses_overwriting_existing_file_without_calling_github(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "bundle.json"
            output.write_text("PRESERVE")
            with patch("hybrid_engine.chat_package.build_chat_package") as builder:
                with self.assertRaises(ValueError):
                    export_chat_package(object(), "acme/demo", "HYBRID DEBUG",
                                        ["src/demo.py"], output)
                builder.assert_not_called()
            self.assertEqual(output.read_text(), "PRESERVE")

    def test_refuses_symlink_and_unusual_extension(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "other.json"
            source.write_text("SAFE")
            link = Path(temp) / "link.json"
            link.symlink_to(source)
            for path in [link, Path(temp) / "code.md"]:
                with self.subTest(path=path), self.assertRaises(ValueError):
                    export_chat_package(object(), "acme/demo", "HYBRID BUILD",
                                        ["src/demo.py"], path)
            self.assertEqual(source.read_text(), "SAFE")


if __name__ == "__main__":
    unittest.main()
