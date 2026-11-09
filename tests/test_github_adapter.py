"""Offline and deterministic checks for GitHub read/write adapters."""
import base64
import unittest

from hybrid_engine.github_adapter import (
    GitHubError, MAX_CHANGE_BYTES, remote_audit, propose_changes,
    safe_repo_path, validate_changeset, validate_change_path, validate_ref,
)

SHA0 = "a" * 40
SHA1 = "b" * 40
SHA2 = "c" * 40
SHA3 = "d" * 40
BLOB = "e" * 40


class FakeGitHub:
    def __init__(self, *, exists=True, tree_truncated=False):
        self.calls = []
        self.exists = exists
        self.tree_truncated = tree_truncated
        self.contents = {
            "package.json": '{"scripts":{"test":"node test.js"}}',
            "app.ts": "const publicKey='sb_publishable_abcde123456';\n"
                      "const secret='sb_secret_abcdef123456789';\n",
        }

    def request(self, method, path, data=None, *, allow_404=False):
        self.calls.append((method, path, data))
        if method == "GET":
            if path == "/repos/acme/demo":
                return {"default_branch": "main"}
            if "/git/ref/heads/main" in path:
                return {"object": {"sha": SHA0}}
            if "/git/commits/" in path:
                return {"tree": {"sha": SHA1}}
            if "/git/trees/" in path:
                return {
                    "truncated": self.tree_truncated,
                    "tree": [
                        {"type": "blob", "mode": "100644", "path": path,
                         "sha": SHA2 if path == "package.json" else SHA3, "size": 100}
                        for path in self.contents
                    ] + [
                        {"type": "blob", "mode": "100755", "path": "src/app.ts", "sha": SHA3},
                        {"type": "blob", "mode": "120000", "path": "linked.ts", "sha": SHA3}
                    ],
                }
            if "/git/blobs/" in path:
                name = "package.json" if path.endswith(SHA2) else "app.ts"
                return {"encoding": "base64", "content": base64.b64encode(
                    self.contents[name].encode("utf-8")).decode("ascii")}
            if "/contents/" in path:
                return {"type": "file", "sha": BLOB} if self.exists else None
            raise AssertionError("Unexpected GET " + path)
        if method == "POST":
            if path.endswith("/git/blobs"):
                return {"sha": SHA2}
            if path.endswith("/git/trees"):
                return {"sha": SHA3}
            if path.endswith("/git/commits"):
                return {"sha": SHA2}
            if path.endswith("/git/refs"):
                return {"ref": data["ref"]}
            if path.endswith("/pulls"):
                return {"html_url": "https://github.com/acme/demo/pull/8", "number": 8}
            raise AssertionError("Unexpected POST " + path)
        raise AssertionError("Unexpected request")


def changeset(expected=BLOB):
    return {
        "schema_version": 1, "repo": "acme/demo", "base": "main",
        "title": "fix: repair example", "body": "Approved code patch",
        "changes": [{"path": "src/app.ts", "expected_sha": expected, "content": "const ok = true;\n"}],
    }


class InputValidationTests(unittest.TestCase):
    def test_paths(self):
        for path in ("../secrets", "/etc/passwd", "a/../../b", "a\\evil", "a//b", ".git/config", "bad\npath"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                safe_repo_path(path)

    def test_sensitive_paths(self):
        for path in (".github/workflows/ci.yml", ".github/CODEOWNERS", ".env", "src/.env.production",
                     "supabase/migrations/01.sql", "keys/server.pem"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_change_path(path)

    def test_reference(self):
        for ref in ("../main", "main..broken", "/root", "ref.lock", "bad\nref"):
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                validate_ref(ref)

    def test_missing_sha(self):
        document = changeset()
        del document["changes"][0]["expected_sha"]
        with self.assertRaises(ValueError):
            validate_changeset(document)

    def test_invalid_repo(self):
        document = changeset()
        document["repo"] = "https://github.com/other/repo"
        with self.assertRaises(ValueError):
            validate_changeset(document)

    def test_duplicate_path(self):
        document = changeset()
        document["changes"].append(document["changes"][0].copy())
        with self.assertRaises(ValueError):
            validate_changeset(document)

    def test_oversized_content(self):
        document = changeset()
        document["changes"][0]["content"] = "z" * (MAX_CHANGE_BYTES + 1)
        with self.assertRaises(ValueError):
            validate_changeset(document)

    def test_allows_new_file_explicit_null(self):
        document = changeset(expected=None)
        self.assertIsNone(validate_changeset(document)["changes"][0]["expected_sha"])


class AuditTests(unittest.TestCase):
    def test_remote_read_only_redacts_secret(self):
        fake = FakeGitHub()
        output = remote_audit(fake, "acme/demo", "main")
        self.assertEqual(output["mode"], "remote-read-only")
        self.assertEqual(output["source_sha"], SHA0)
        self.assertEqual(output["tests"]["status"], "NOT_RUN")
        self.assertIn("SUPABASE_SECRET", [f["rule"] for f in output["findings"]])
        self.assertNotIn("sb_secret_abcdef123456789", repr(output))
        self.assertTrue(all(method == "GET" for method, _, _ in fake.calls))
        self.assertEqual(output["files_scanned"], 3)

    def test_rejects_truncated_tree(self):
        with self.assertRaises(GitHubError):
            remote_audit(FakeGitHub(tree_truncated=True), "acme/demo", "main")


class ProposalTests(unittest.TestCase):
    def test_preview_is_read_only(self):
        fake = FakeGitHub()
        output = propose_changes(fake, changeset())
        self.assertEqual(output["status"], "PREVIEW")
        self.assertFalse(output["writes_performed"])
        self.assertTrue(all(method == "GET" for method, _, _ in fake.calls))

    def test_rejects_stale_sha_before_writes(self):
        fake = FakeGitHub()
        with self.assertRaises(GitHubError):
            propose_changes(fake, changeset(expected=SHA3), apply=True)
        self.assertTrue(all(method == "GET" for method, _, _ in fake.calls))

    def test_new_file_only_when_missing(self):
        fake = FakeGitHub(exists=True)
        with self.assertRaises(GitHubError):
            propose_changes(fake, changeset(expected=None), apply=True)
        self.assertTrue(all(method == "GET" for method, _, _ in fake.calls))

    def test_proposes_atomic_commit_draft_pr(self):
        fake = FakeGitHub()
        output = propose_changes(fake, changeset(), apply=True)
        self.assertEqual(output["status"], "DRAFT_PR_CREATED")
        self.assertEqual(output["pr_number"], 8)
        self.assertEqual(output["tests"], "NOT_RUN")
        posts = [(path, body) for method, path, body in fake.calls if method == "POST"]
        self.assertEqual(len(posts), 5)
        self.assertTrue(posts[-1][0].endswith("/pulls"))
        self.assertTrue(posts[-1][1]["draft"])
        self.assertTrue(posts[-2][0].endswith("/git/refs"))
        self.assertEqual(posts[-3][1]["parents"], [SHA0])
        self.assertEqual(posts[1][1]["tree"][0]["mode"], "100755")


if __name__ == "__main__":
    unittest.main()
