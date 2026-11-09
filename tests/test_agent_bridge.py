import unittest
from unittest.mock import patch
from hybrid_engine.agent_bridge import prepare, submit
from hybrid_engine.github_adapter import GitHubError

SHA = "a" * 40
OTHER = "b" * 40
BLOB = "c" * 40


def audit(**extra):
    return dict(source_sha=SHA, files_scanned=5, findings=[], truncated=False,
                files_skipped=0, files_unavailable=0, limitations=[], **extra)


def make_order(goal="HYBRID DEBUG: bug"):
    with patch("hybrid_engine.agent_bridge.remote_audit", return_value=audit()), \
         patch("hybrid_engine.agent_bridge.head_at", return_value=("main", SHA)):
        return prepare(object(), "acme/demo", goal, ref="main")


def manifest(**changes):
    result = {"schema_version": 1, "repo": "acme/demo", "base": "main",
              "expected_base_sha": SHA, "title": "fix: correct regression",
              "body": "Root cause and evidence", "changes": [
                  {"path": "src/app.ts", "expected_sha": BLOB, "content": "const ok = true;\n"}]}
    result.update(changes)
    return result


class AgentBridgeTests(unittest.TestCase):
    def test_work_order_pinned_and_unexecuted(self):
        item = make_order()
        self.assertEqual(item["base_sha"], SHA)
        self.assertEqual(item["evidence"]["tests"], "NOT_RUN")
        self.assertTrue(item["ready_for_proposal"])

    def test_audit_is_read_only(self):
        item = make_order("HYBRID AUDIT")
        self.assertFalse(item["ready_for_proposal"])
        with self.assertRaises(ValueError):
            submit(object(), item, manifest())

    def test_incomplete_audit_blocks(self):
        with patch("hybrid_engine.agent_bridge.remote_audit",
                   return_value=audit(truncated=True)), \
             patch("hybrid_engine.agent_bridge.head_at", return_value=("main", SHA)):
            order = prepare(object(), "acme/demo", "HYBRID DEBUG", ref="main")
        self.assertFalse(order["ready_for_proposal"])

    def test_changed_branch_blocks_preparation(self):
        with patch("hybrid_engine.agent_bridge.remote_audit", return_value=audit()), \
             patch("hybrid_engine.agent_bridge.head_at", return_value=("main", OTHER)):
            with self.assertRaises(GitHubError):
                prepare(object(), "acme/demo", "HYBRID DEBUG", ref="main")

    def test_preview_does_not_apply(self):
        with patch("hybrid_engine.agent_bridge.propose_changes",
                   return_value={"status": "PREVIEW", "files": ["src/app.ts"],
                                 "writes_performed": False}) as proposal:
            out = submit(object(), make_order(), manifest())
        self.assertEqual(out["status"], "PREVIEW")
        self.assertEqual(out["tests"], "NOT_RUN")
        self.assertFalse(proposal.call_args.kwargs["apply"])

    def test_explicit_apply_creates_draft_only(self):
        with patch("hybrid_engine.agent_bridge.propose_changes",
                   return_value={"status": "DRAFT_PR_CREATED", "pr_number": 9,
                                 "writes_performed": True}) as proposal:
            out = submit(object(), make_order(), manifest(), apply=True)
        self.assertEqual(out["pr_number"], 9)
        self.assertTrue(proposal.call_args.kwargs["apply"])
        self.assertEqual(out["production"], "UNCHANGED")

    def test_mismatch_rejected_before_network(self):
        for wrong in [{"repo": "other/demo"}, {"base": "other"},
                      {"expected_base_sha": OTHER}, {"expected_base_sha": None}]:
            with self.subTest(wrong=wrong), self.assertRaises(ValueError):
                submit(object(), make_order(), manifest(**wrong), apply=True)

    def test_invalid_work_order_rejected(self):
        order = make_order()
        order["kind"] = "untrusted"
        with self.assertRaises(ValueError):
            submit(object(), order, manifest())
