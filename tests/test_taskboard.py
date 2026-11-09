import unittest
from hybrid_engine.taskboard import (
    TASK_MARKER, EVENT_MARKER, start_task, note_task, task_status, list_tasks,
    _encode,
)
from hybrid_engine.github_adapter import GitHubError

SHA = "a" * 40


class FakeGithub:
    def __init__(self):
        self.calls = []
        self.events = []
        self.issues_enabled = True
        self.issue = {
            "number": 7, "title": "[Hybrid] Audit the service",
            "html_url": "https://github.com/acme/demo/issues/7",
            "body": _encode(TASK_MARKER, {
                "schema_version": 1, "repo": "acme/demo", "goal": "audite o serviço",
                "flow": "audit", "steps": ["inventory"], "state": "planned",
            }),
        }

    def request(self, method, path, data=None, *, allow_404=False):
        self.calls.append((method, path, data))
        if method == "GET":
            if path == "/repos/acme/demo":
                return {"has_issues": self.issues_enabled}
            if path.startswith("/repos/acme/demo/issues/7/comments"):
                return self.events[:]
            if path == "/repos/acme/demo/issues/7":
                return self.issue
            if "/issues?state=all" in path:
                return [self.issue, {"pull_request": {}, "body": "", "number": 8}]
            if "/pulls/3" in path:
                return {"head": {"sha": SHA}, "state": "open", "merged": False}
            if "check-runs" in path:
                return {"total_count": 1, "check_runs": [
                    {"name": "test", "status": "completed", "conclusion": "success", "head_sha": SHA}
                ]}
            if path.endswith("/status"):
                return {"statuses": []}
            raise AssertionError(path)
        if method == "POST" and path == "/repos/acme/demo/issues":
            return self.issue
        if method == "POST" and path == "/repos/acme/demo/issues/7/comments":
            self.events.append({
                "body": data["body"], "user": {"login": "automation"},
                "created_at": "2026-11-09T12:00:00Z",
            })
            return {"html_url": "https://github.com/acme/demo/issues/7#issuecomment-4"}
        raise AssertionError((method, path))


class TaskboardTests(unittest.TestCase):
    def test_task_start_preview_does_not_write(self):
        client = FakeGithub()
        result = start_task(client, "acme/demo", "audite o sistema")
        self.assertEqual(result["status"], "PREVIEW")
        self.assertTrue(all(call[0] == "GET" for call in client.calls))

    def test_task_create_requires_apply(self):
        client = FakeGithub()
        result = start_task(client, "acme/demo", "audite o sistema", apply=True)
        self.assertEqual(result["status"], "CREATED")
        self.assertEqual(result["issue_number"], 7)
        self.assertEqual(client.calls[-1][0], "POST")

    def test_disabled_issues(self):
        client = FakeGithub()
        client.issues_enabled = False
        with self.assertRaises(GitHubError):
            start_task(client, "acme/demo", "revise o sistema", apply=True)
        self.assertTrue(all(call[0] == "GET" for call in client.calls))

    def test_rejects_sensitive_goal(self):
        client = FakeGithub()
        with self.assertRaises(ValueError):
            start_task(client, "acme/demo", "token sb_secret_abcdefghijklmnop", apply=True)
        self.assertEqual(client.calls, [])

    def test_status_ignores_unrelated_comments(self):
        client = FakeGithub()
        client.events = [
            {"body": "a random comment"},
            {"body": _encode(EVENT_MARKER, {
                "schema_version": 1, "repo": "another/repo",
                "issue_number": 7, "state": "completed_reported",
            })},
        ]
        result = task_status(client, "acme/demo", 7)
        self.assertEqual(result["state"], "planned")
        self.assertEqual(result["event_count"], 0)

    def test_status_retrieves_latest_note(self):
        client = FakeGithub()
        note_task(client, "acme/demo", 7, "in_progress", "Root cause investigated", apply=True)
        result = task_status(client, "acme/demo", 7)
        self.assertEqual(result["state"], "in_progress")
        self.assertEqual(result["event_count"], 1)
        self.assertEqual(result["latest_event"]["author"], "automation")

    def test_note_preview_does_not_write(self):
        client = FakeGithub()
        result = note_task(client, "acme/demo", 7, "blocked", "Missing access")
        self.assertEqual(result["status"], "PREVIEW")
        self.assertTrue(all(call[0] == "GET" for call in client.calls))

    def test_review_ready_requires_real_pr(self):
        client = FakeGithub()
        with self.assertRaises(ValueError):
            note_task(client, "acme/demo", 7, "review_ready", "Review PR")
        result = note_task(client, "acme/demo", 7, "review_ready", "Review PR", pr_number=3, apply=True)
        self.assertEqual(result["pr_verification"]["ci"], "PASSED")
        state = task_status(client, "acme/demo", 7)
        self.assertEqual(state["state"], "review_ready")
        self.assertEqual(state["pr_verification"]["head_sha"], SHA)

    def test_completed_is_only_reported_not_verified(self):
        client = FakeGithub()
        result = note_task(client, "acme/demo", 7, "completed_reported",
                           "Human reviewed final report", apply=True)
        self.assertEqual(result["state"], "completed_reported")
        state = task_status(client, "acme/demo", 7)
        self.assertEqual(state["state"], "completed_reported")
        self.assertIn("self-reported", state["status_source"])
        with self.assertRaises(ValueError):
            note_task(client, "acme/demo", 7, "in_progress", "Reopen it")

    def test_list_filters_other_issues_and_pr(self):
        result = list_tasks(FakeGithub(), "acme/demo")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["tasks"][0]["number"], 7)

    def test_issue_validation(self):
        client = FakeGithub()
        client.issue["body"] = "plain discussion"
        with self.assertRaises(ValueError):
            task_status(client, "acme/demo", 7)


if __name__ == "__main__":
    unittest.main()
