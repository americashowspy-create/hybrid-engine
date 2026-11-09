"""Work order cannot mutate anything outside the explicitly audited scope."""
import unittest
from unittest.mock import patch

from hybrid_engine.agent_bridge import prepare, submit

BASE = "a" * 40
BLOB = "b" * 40


def report(*, complete=True):
    return {
        "source_sha": BASE, "files_scanned": 1,
        "findings": [], "truncated": False, "files_skipped": 0,
        "files_unavailable": 0, "limitations": ["Scoped, not repository-wide"],
        "scope": {"mode": "exact_files", "paths": [".gitignore"],
                  "complete": complete, "notice": "only one file"},
    }


def order(*, complete=True):
    with patch("hybrid_engine.agent_bridge.remote_audit", return_value=report(complete=complete)) as auditor, \
         patch("hybrid_engine.agent_bridge.head_at", return_value=("main", BASE)):
        item = prepare(object(), "acme/demo", "HYBRID AUDIT-FIX",
                       ref="main", scope_paths=[".gitignore"])
        auditor.assert_called_once()
        self_args = auditor.call_args
        assert self_args.kwargs["scope_paths"] == [".gitignore"]
        return item


def manifest(path=".gitignore", expected=BLOB):
    return {"schema_version": 1, "repo": "acme/demo", "base": "main",
            "expected_base_sha": BASE, "title": "chore: protected environment files",
            "body": "Defensive git hygiene", "changes": [
                {"path": path, "expected_sha": expected, "content": ".env\n"}]}


class AgentScopeTests(unittest.TestCase):
    def test_prepares_scoped_task_without_claiming_global_coverage(self):
        work = order()
        self.assertTrue(work["ready_for_proposal"])
        self.assertTrue(work["scope_limited"])
        self.assertEqual(work["scope"]["paths"], [".gitignore"])
        self.assertEqual(work["base_sha"], BASE)

    def test_incomplete_scope_blocks(self):
        work = order(complete=False)
        self.assertFalse(work["ready_for_proposal"])
        with self.assertRaises(ValueError):
            submit(object(), work, manifest(), apply=True)

    def test_out_of_scope_patch_rejected_before_network(self):
        work = order()
        with self.assertRaisesRegex(ValueError, "outside"):
            submit(object(), work, manifest(path="src/other.ts"), apply=True)

    def test_new_file_not_allowed_in_scope(self):
        with self.assertRaisesRegex(ValueError, "cannot create"):
            submit(object(), order(), manifest(expected=None), apply=True)

    def test_existing_scoped_path_can_be_previewed(self):
        with patch("hybrid_engine.agent_bridge.propose_changes",
                   return_value={"status": "PREVIEW", "writes_performed": False,
                                 "files": [".gitignore"]}) as proposer:
            result = submit(object(), order(), manifest())
            self.assertEqual(result["status"], "PREVIEW")
            self.assertFalse(proposer.call_args.kwargs["apply"])

    def test_mismatched_commit_is_blocked(self):
        data = manifest()
        data["expected_base_sha"] = "f" * 40
        with self.assertRaises(ValueError):
            submit(object(), order(), data)
