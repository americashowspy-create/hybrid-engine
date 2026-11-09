"""Integration: real Hybrid Engine code against a private, in-memory GitHub fixture."""
import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from hybrid_engine.chat_package import export_chat_package, work_order_from_bundle
from hybrid_engine.agent_bridge import submit
from hybrid_engine.github_adapter import GitHubError

REPO="acme/demo"
BASE="a"*40
TREE="b"*40
NEW_BLOB="c"*40
NEW_TREE="d"*40
NEW_COMMIT="e"*40
TEXT="value = 1\n"
BYTES=TEXT.encode()
BLOB=hashlib.sha1(b"blob "+str(len(BYTES)).encode()+b"\x00"+BYTES).hexdigest()

class GitHubFixture:
    def __init__(self):
        self.sha=BASE
        self.blob=BLOB
        self.calls=[]
    def request(self,method,path,data=None,*,allow_404=False):
        self.calls.append((method,path,data))
        if method=="GET":
            if path=="/repos/acme/demo/git/ref/heads/main":
                return {"object":{"sha":self.sha}}
            if path=="/repos/acme/demo/git/commits/"+self.sha:
                return {"tree":{"sha":TREE}}
            if path=="/repos/acme/demo/git/trees/"+TREE+"?recursive=1":
                return {"truncated":False,"tree":[{"path":"src/demo.py","type":"blob",
                        "mode":"100644","sha":self.blob,"size":len(BYTES)}]}
            if path=="/repos/acme/demo/git/blobs/"+self.blob:
                return {"encoding":"base64","content":base64.b64encode(BYTES).decode()}
            if path=="/repos/acme/demo/contents/src/demo.py?ref="+self.sha:
                return {"type":"file","sha":self.blob,"encoding":"base64",
                        "content":base64.b64encode(BYTES).decode()}
            raise AssertionError("Unexpected simulated GET "+path)
        if method=="POST":
            suffix=path.removeprefix("/repos/acme/demo")
            if suffix=="/git/blobs": return {"sha":NEW_BLOB}
            if suffix=="/git/trees": return {"sha":NEW_TREE}
            if suffix=="/git/commits": return {"sha":NEW_COMMIT}
            if suffix=="/git/refs": return {"ref":data["ref"]}
            if suffix=="/pulls":
                assert data["draft"] is True
                return {"html_url":"https://github.com/acme/demo/pull/42","number":42}
            raise AssertionError("Unexpected simulated POST "+path)
        raise AssertionError("Unexpected method "+method)

def proposal(bundle):
    o=bundle["work_order"]
    src=bundle["sources"][0]
    return {"schema_version":1,"repo":o["repo"],"base":o["base"],
            "expected_base_sha":o["base_sha"],"title":"fix: correct demo value",
            "body":"Simulated reviewed patch, no production change",
            "changes":[{"path":src["path"],"expected_sha":src["expected_sha"],
                        "content":"value = 2\n"}]}

class ChatAutoRoundTrip(unittest.TestCase):
    def test_actual_pinned_export_preview_and_draft_pr(self):
        client=GitHubFixture()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"bundle.json"
            metadata=export_chat_package(client,REPO,"HYBRID DEBUG: correct value",
                                        ["src/demo.py"],path,ref="main")
            self.assertEqual(metadata["status"],"PACKAGE_EXPORTED")
            self.assertTrue(path.exists())
            bundle=json.loads(path.read_text())
            order=work_order_from_bundle(bundle)
            self.assertEqual(order["base_sha"],BASE)
            self.assertEqual(bundle["sources"][0]["expected_sha"],BLOB)
            self.assertTrue(order["audit"]["complete"])
            self.assertFalse(any(method=="POST" for method,_,_ in client.calls))
            dry=submit(client,order,proposal(bundle),apply=False)
            self.assertEqual(dry["status"],"PREVIEW")
            self.assertFalse(any(method=="POST" for method,_,_ in client.calls))
            draft=submit(client,order,proposal(bundle),apply=True)
            self.assertEqual(draft["status"],"DRAFT_PR_CREATED")
            self.assertEqual(draft["pr_number"],42)
            self.assertEqual(draft["production"],"UNCHANGED")
            posts=[(p,data) for m,p,data in client.calls if m=="POST"]
            self.assertEqual(len(posts),5)
            self.assertEqual(posts[-1][0],"/repos/acme/demo/pulls")
            self.assertTrue(posts[-1][1]["draft"])
            self.assertNotIn("refs/heads/main",[d.get("ref") for _,d in posts if isinstance(d,dict)])
    def test_stale_branch_is_rejected_before_git_write(self):
        client=GitHubFixture()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"bundle.json"
            export_chat_package(client,REPO,"HYBRID DEBUG: fix value",["src/demo.py"],path,ref="main")
            bundle=json.loads(path.read_text())
            client.sha="f"*40
            with self.assertRaises(GitHubError):
                submit(client,work_order_from_bundle(bundle),proposal(bundle),apply=True)
            self.assertFalse(any(m=="POST" for m,_,_ in client.calls))
    def test_tampered_git_blob_is_rejected_before_git_write(self):
        client=GitHubFixture()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"bundle.json"
            export_chat_package(client,REPO,"HYBRID DEBUG: fix value",["src/demo.py"],path,ref="main")
            bundle=json.loads(path.read_text())
            bundle["sources"][0]["content"]="value = 999\n"
            with self.assertRaisesRegex(ValueError,"audited Git blob SHA"):
                work_order_from_bundle(bundle)
            self.assertFalse(any(m=="POST" for m,_,_ in client.calls))
    def test_changed_file_blocks_commit(self):
        client=GitHubFixture()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"bundle.json"
            export_chat_package(client,REPO,"HYBRID DEBUG: fix value",["src/demo.py"],path,ref="main")
            bundle=json.loads(path.read_text())
            client.blob="f"*40
            with self.assertRaises(GitHubError):
                submit(client,work_order_from_bundle(bundle),proposal(bundle),apply=True)
            self.assertFalse(any(m=="POST" for m,_,_ in client.calls))

if __name__=="__main__":
    unittest.main()
