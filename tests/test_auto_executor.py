"""No unintended writes, conservative remediation, and auditable results."""
import base64
import unittest
from unittest.mock import patch

from hybrid_engine.auto_executor import _read_gitignore, _suggest_gitignore, run_auto
from hybrid_engine.github_adapter import GitHubError

SHA = "a" * 40
BLOB = "b" * 40


class Client:
    def __init__(self, content=None, unsafe=False):
        self.content = content
        self.unsafe = unsafe
        self.calls = []

    def request(self, method, path, data=None, *, allow_404=False):
        self.calls.append((method, path))
        if "contents/.gitignore" in path:
            if self.content is None:
                return None
            if self.unsafe:
                return {"type": "symlink", "sha": BLOB}
            return {"type": "file", "sha": BLOB, "encoding": "base64",
                    "content": base64.b64encode(self.content.encode()).decode()}
        raise AssertionError(path)


def audit(**overrides):
    result = {"source_sha": SHA, "files_scanned": 5, "findings": [],
              "truncated": False, "files_unavailable": 0, "limitations": []}
    result.update(overrides)
    return result


class AutoExecutorTests(unittest.TestCase):
    def test_read_only_audit_never_proposes(self):
        with patch("hybrid_engine.auto_executor.remote_audit", return_value=audit()), \
                patch("hybrid_engine.auto_executor.propose_changes") as propose:
            result = run_auto(Client(), "acme/demo", "HYBRID AUDIT")
        self.assertEqual(result["status"], "AUDITED")
        self.assertFalse(result["writes_performed"])
        propose.assert_not_called()

    def test_apply_requires_explicit_fix_intent(self):
        with self.assertRaises(ValueError):
            run_auto(Client(), "acme/demo", "HYBRID AUDIT", apply=True)

    def test_dry_run_proposes_allowlisted_change(self):
        client = Client(content="node_modules/\n")
        with patch("hybrid_engine.auto_executor.remote_audit", return_value=audit()), \
                patch("hybrid_engine.auto_executor.head_at", return_value=("main", SHA)), \
                patch("hybrid_engine.auto_executor.propose_changes",
                      return_value={"status": "PREVIEW", "writes_performed": False}) as propose:
            result = run_auto(client, "acme/demo", "HYBRID AUDIT-FIX", ref="main")
        self.assertEqual(result["status"], "PREVIEW")
        self.assertEqual(result["test_evidence"], "NOT_RUN")
        self.assertEqual(result["proposed_fix"]["path"], ".gitignore")
        self.assertEqual(propose.call_args.kwargs, {"apply": False})
        manifest = propose.call_args.args[1]
        self.assertEqual(manifest["changes"][0]["expected_sha"], BLOB)
        self.assertIn(".env.*\n", manifest["changes"][0]["content"])
        self.assertTrue(all(method == "GET" for method, _ in client.calls))

    def test_explicit_apply_returns_draft_pr_state_only(self):
        client = Client(content=None)
        with patch("hybrid_engine.auto_executor.remote_audit", return_value=audit()), \
                patch("hybrid_engine.auto_executor.head_at", return_value=("main", SHA)), \
                patch("hybrid_engine.auto_executor.propose_changes",
                      return_value={"status": "DRAFT_PR_CREATED", "writes_performed": True,
                                    "pr_url": "https://github.com/acme/demo/pull/3"}) as propose:
            result = run_auto(client, "acme/demo", "HYBRID AUDIT-FIX", apply=True)
        self.assertTrue(result["writes_performed"])
        self.assertEqual(result["status"], "DRAFT_PR_CREATED")
        self.assertEqual(propose.call_args.kwargs, {"apply": True})
        self.assertIsNone(propose.call_args.args[1]["changes"][0]["expected_sha"])

    def test_no_change_means_no_pr(self):
        client = Client(content=".env\n.env.*\n!.env.example\n.hybrid/\n")
        with patch("hybrid_engine.auto_executor.remote_audit", return_value=audit()), \
                patch("hybrid_engine.auto_executor.head_at", return_value=("main", SHA)), \
                patch("hybrid_engine.auto_executor.propose_changes") as propose:
            result = run_auto(client, "acme/demo", "HYBRID AUDIT-FIX", apply=True)
        self.assertEqual(result["status"], "NO_SAFE_FIX_NEEDED")
        propose.assert_not_called()

    def test_incomplete_audit_blocks_apply(self):
        with patch("hybrid_engine.auto_executor.remote_audit", return_value=audit(truncated=True)):
            with self.assertRaises(GitHubError):
                run_auto(Client(), "acme/demo", "HYBRID AUDIT-FIX", apply=True)

    def test_stale_commit_blocks(self):
        with patch("hybrid_engine.auto_executor.remote_audit", return_value=audit()), \
                patch("hybrid_engine.auto_executor.head_at", return_value=("main", "c" * 40)):
            with self.assertRaises(GitHubError):
                run_auto(Client(), "acme/demo", "HYBRID AUDIT-FIX")

    def test_unsafe_gitignore_type_rejected(self):
        with self.assertRaises(GitHubError):
            _read_gitignore(Client(content="hello", unsafe=True), "acme/demo", SHA)

    def test_rules_idempotent_preserves_original(self):
        updated, missing = _suggest_gitignore("node_modules/")
        self.assertTrue(updated.startswith("node_modules/\n"))
        self.assertIn(".env", missing)
        same, none = _suggest_gitignore(updated)
        self.assertEqual(same, updated)
        self.assertEqual(none, [])
