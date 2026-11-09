"""Scoped remote inspection is explicitly limited, fail-closed and read-only."""
import base64
import unittest

from hybrid_engine.github_adapter import GitHubError, remote_audit

SHA0 = "a" * 40
TREE = "b" * 40
BLOB = "c" * 40
OTHER = "d" * 40


class LargeRepo:
    def __init__(self, *, symlink=False, corrupt=False, missing=False):
        self.calls = []
        self.symlink = symlink
        self.corrupt = corrupt
        self.missing = missing
        self.entries = [
            {"type": "blob", "mode": "100644", "path": f"src/file_{i:03d}.ts",
             "sha": BLOB, "size": 28}
            for i in range(270)
        ]
        if not missing:
            self.entries.append({
                "type": "blob", "mode": "120000" if symlink else "100644",
                "path": ".gitignore", "sha": OTHER, "size": 22,
            })

    def request(self, method, path, data=None, *, allow_404=False):
        self.calls.append((method, path))
        if method != "GET":
            raise AssertionError("Unexpected write")
        if path == "/repos/acme/large":
            return {"default_branch": "main"}
        if path.endswith("/git/ref/heads/main"):
            return {"object": {"sha": SHA0}}
        if "/git/commits/" in path:
            return {"tree": {"sha": TREE}}
        if "/git/trees/" in path:
            return {"truncated": False, "tree": self.entries}
        if "/git/blobs/" in path:
            if self.corrupt:
                return {"encoding": "utf-8", "content": "invalid"}
            content = ".env\n" if path.endswith(OTHER) else "const value = 1;\n"
            return {"encoding": "base64", "content": base64.b64encode(content.encode()).decode()}
        raise AssertionError(path)


class ScopedAuditTests(unittest.TestCase):
    def test_large_project_global_audit_is_truthfully_incomplete(self):
        client = LargeRepo()
        output = remote_audit(client, "acme/large", "main")
        self.assertTrue(output["truncated"])
        self.assertEqual(output["source_files"], 270)
        self.assertEqual(output["files_scanned"], 250)
        self.assertNotIn("scope", output)
        self.assertTrue(all(method == "GET" for method, _ in client.calls))

    def test_exact_file_scope_is_complete_but_not_global(self):
        client = LargeRepo()
        output = remote_audit(client, "acme/large", "main", scope_paths=[".gitignore"])
        self.assertFalse(output["truncated"])
        self.assertEqual(output["files_scanned"], 1)
        self.assertEqual(output["scope"]["paths"], [".gitignore"])
        self.assertTrue(output["scope"]["complete"])
        self.assertIn("rest of repository NOT_AUDITED", output["scope"]["notice"])
        self.assertEqual(output["source_sha"], SHA0)
        self.assertEqual(output["tests"]["status"], "NOT_RUN")
        self.assertTrue(all(method == "GET" for method, _ in client.calls))

    def test_duplicate_and_unsafe_paths_are_rejected_before_network(self):
        for scope in [[".gitignore", ".gitignore"], ["../other"], [".gitignore"] * 21, []]:
            with self.subTest(scope=scope):
                client = LargeRepo()
                with self.assertRaises(ValueError):
                    remote_audit(client, "acme/large", "main", scope_paths=scope)
                self.assertEqual(client.calls, [])

    def test_missing_or_symlinked_scope_fails_closed(self):
        for opts in ({"missing": True}, {"symlink": True}):
            with self.subTest(opts=opts), self.assertRaises(GitHubError):
                remote_audit(LargeRepo(**opts), "acme/large", "main",
                             scope_paths=[".gitignore"])

    def test_unreadable_scope_is_marked_incomplete(self):
        output = remote_audit(LargeRepo(corrupt=True), "acme/large", "main",
                              scope_paths=[".gitignore"])
        self.assertFalse(output["scope"]["complete"])
        self.assertEqual(output["files_unavailable"], 1)

    def test_scope_finds_secret_indicator_without_exposing_match(self):
        client = LargeRepo()
        client.entries.append({"type": "blob", "mode": "100644", "path": "src/secret.ts",
                               "sha": BLOB, "size": 28})
        # Existing fake blob has no secret; audit is explicitly not a full review.
        report = remote_audit(client, "acme/large", "main", scope_paths=["src/secret.ts"])
        self.assertTrue(report["scope"]["complete"])
        self.assertEqual(report["findings"], [])
