"""Universal agent tests run fully offline: no tokens, cloud or production."""
import base64
import json
import os
import sys
import unittest
from unittest.mock import patch

from hybrid_engine.universal import invoke_agent, run_universal, source_package
from hybrid_engine.github_adapter import GitHubError

COMMIT = "a" * 40
BLOB = "b" * 40


def order():
    return {
        "repo": "acme/demo", "base": "main", "base_sha": COMMIT,
        "ready_for_proposal": True, "scope": {
            "mode": "exact_files", "paths": ["src/example.py"], "complete": True,
        },
    }


class FakeClient:
    def request(self, method, path):
        assert method == "GET"
        assert "/contents/src/example.py?ref=" + COMMIT in path
        return {
            "type": "file", "encoding": "base64", "sha": BLOB,
            "content": base64.b64encode(b"value = 1\n").decode(),
        }


class UniversalAgentTests(unittest.TestCase):
    def test_source_package_is_pinned_and_scoped(self):
        package = source_package(FakeClient(), order())
        self.assertEqual(package["protocol"], "hybrid.agent-stdio.v1")
        self.assertEqual(package["sources"][0], {
            "path": "src/example.py", "expected_sha": BLOB, "content": "value = 1\n",
        })
        self.assertEqual(package["output_contract"]["expected_base_sha"], COMMIT)

    def test_rejects_incomplete_scope(self):
        broken = order()
        broken["scope"]["complete"] = False
        with self.assertRaises(ValueError):
            source_package(FakeClient(), broken)

    def test_rejects_unsafe_path_before_any_write(self):
        broken = order()
        broken["scope"]["paths"] = ["../secrets"]
        with self.assertRaises(ValueError):
            source_package(FakeClient(), broken)

    def test_json_adapter_works_without_provider_sdk(self):
        command = [
            sys.executable, "-c",
            "import sys,json; data=json.load(sys.stdin); print(json.dumps("
            "{'schema_version':1,'repo':data['work_order']['repo'],"
            "'base':data['work_order']['base'],'expected_base_sha':"
            "data['work_order']['base_sha'],'title':'fix: fixture',"
            "'changes':[{'path':data['sources'][0]['path'],"
            "'expected_sha':data['sources'][0]['expected_sha'],"
            "'content':'value = 2\\n'}]}))",
        ]
        result = invoke_agent(command, source_package(FakeClient(), order()))
        self.assertEqual(result["changes"][0]["content"], "value = 2\n")

    def test_does_not_pass_git_token_to_child(self):
        with patch.dict(os.environ, {"GH_TOKEN": "SECRET_TOKEN"}, clear=False):
            result = invoke_agent(
                [sys.executable, "-c",
                 "import os,json; print(json.dumps({'token':os.environ.get('GH_TOKEN')}))"],
                {},
            )
        self.assertIsNone(result["token"])

    def test_refuses_credential_injection(self):
        with self.assertRaises(ValueError):
            invoke_agent([sys.executable, "-c", "print('{}')"], {}, allow_env=["GH_TOKEN"])
        with self.assertRaises(ValueError):
            invoke_agent([sys.executable, "-c", "print('{}')"], {}, allow_env=["AWS_SECRET_ACCESS_KEY"])

    def test_failed_agent_never_submits(self):
        with self.assertRaises(GitHubError):
            invoke_agent([sys.executable, "-c", "raise SystemExit(2)"], {})

    def test_preview_is_default_and_never_applies(self):
        with patch("hybrid_engine.universal.prepare", return_value=order()), \\
             patch("hybrid_engine.universal.source_package", return_value={}), \\
             patch("hybrid_engine.universal.invoke_agent", return_value={"schema_version": 1}), \\
             patch("hybrid_engine.universal.submit", return_value={"status": "PREVIEW"}) as submit:
            result = run_universal(object(), "acme/demo", "HYBRID DEBUG", ["src/example.py"], ["agent"])
        self.assertEqual(result["verification"], "NOT_RUN_PREVIEW")
        self.assertFalse(submit.call_args.kwargs["apply"])

    def test_apply_only_proposes_draft_pr(self):
        with patch("hybrid_engine.universal.prepare", return_value=order()), \\
             patch("hybrid_engine.universal.source_package", return_value={}), \\
             patch("hybrid_engine.universal.invoke_agent", return_value={"schema_version": 1}), \\
             patch("hybrid_engine.universal.submit",
                   return_value={"status": "DRAFT_PR_CREATED", "pr_number": 27}) as submit:
            result = run_universal(object(), "acme/demo", "HYBRID DEBUG",
                                   ["src/example.py"], ["agent"], apply=True)
        self.assertTrue(submit.call_args.kwargs["apply"])
        self.assertEqual(result["verification"], "PENDING_INDEPENDENT_CI")
        self.assertEqual(result["pr_number"], 27)


if __name__ == "__main__":
    unittest.main()
