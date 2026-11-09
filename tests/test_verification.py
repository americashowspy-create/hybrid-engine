"""PR-check evaluation must fail closed and bind evidence to the PR head."""
import unittest
from hybrid_engine.verification import verify_pr
from hybrid_engine.github_adapter import GitHubError

SHA = "a" * 40
SHA_OTHER = "b" * 40


class FakeGitHub:
    def __init__(self, checks=None, contexts=None, merged=False, total=None):
        self.checks = [] if checks is None else checks
        self.contexts = [] if contexts is None else contexts
        self.merged = merged
        self.total = len(self.checks) if total is None else total
        self.urls = []

    def request(self, method, path, data=None, *, allow_404=False):
        self.urls.append((method, path))
        if "/pulls/12" in path:
            return {
                "head": {"sha": SHA}, "merged": self.merged,
                "state": "closed" if self.merged else "open",
                "merge_commit_sha": SHA_OTHER if self.merged else None,
                "html_url": "https://github.com/acme/demo/pull/12",
            }
        if "check-runs" in path:
            return {"total_count": self.total, "check_runs": self.checks}
        if "/status" in path:
            return {"statuses": self.contexts}
        raise AssertionError(path)


def check(conclusion="success", status="completed", sha=SHA):
    return {
        "name": "test", "head_sha": sha, "status": status,
        "conclusion": conclusion, "html_url": "https://github.com/acme/demo/actions/runs/3",
    }


class PullVerificationTests(unittest.TestCase):
    def test_no_checks_is_not_passed(self):
        result = verify_pr(FakeGitHub(), "acme/demo", 12)
        self.assertEqual(result["ci"], "NOT_RUN")
        self.assertEqual(result["check_count"], 0)

    def test_successful_checks(self):
        fake = FakeGitHub(checks=[check()],
                          contexts=[{"context": "lint", "state": "success"}])
        result = verify_pr(fake, "acme/demo", 12)
        self.assertEqual(result["ci"], "PASSED")
        self.assertEqual(result["check_count"], 2)
        self.assertTrue(all(method == "GET" for method, _ in fake.urls))
        self.assertTrue(all(SHA in path or "/pulls/" in path for _, path in fake.urls))

    def test_pending_takes_precedence_over_success(self):
        self.assertEqual(verify_pr(FakeGitHub(checks=[check(), check(None, "in_progress")]),
                                   "acme/demo", 12)["ci"], "PENDING")

    def test_failed_takes_precedence_over_pending(self):
        result = verify_pr(FakeGitHub(checks=[check(None, "in_progress"), check("failure")]),
                           "acme/demo", 12)
        self.assertEqual(result["ci"], "FAILED")

    def test_non_success_is_not_accepted(self):
        self.assertEqual(verify_pr(FakeGitHub(checks=[check("neutral")]),
                                   "acme/demo", 12)["ci"], "INCONCLUSIVE")

    def test_truncated_checks_cannot_pass(self):
        self.assertEqual(verify_pr(FakeGitHub(checks=[check()], total=101),
                                   "acme/demo", 12)["ci"], "INCOMPLETE")

    def test_other_sha_not_counted(self):
        self.assertEqual(verify_pr(FakeGitHub(checks=[check(sha=SHA_OTHER)]),
                                   "acme/demo", 12)["ci"], "NOT_RUN")

    def test_merged_is_reported_separately(self):
        result = verify_pr(FakeGitHub(checks=[check()], merged=True), "acme/demo", 12)
        self.assertTrue(result["merged"])
        self.assertEqual(result["merge_commit_sha"], SHA_OTHER)
        self.assertEqual(result["ci"], "PASSED")

    def test_bad_pr_number(self):
        with self.assertRaises(ValueError):
            verify_pr(FakeGitHub(), "acme/demo", 0)


if __name__ == "__main__":
    unittest.main()
