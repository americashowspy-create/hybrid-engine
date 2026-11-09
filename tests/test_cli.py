import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from hybrid_engine.cli import main


class CliTests(unittest.TestCase):
    def call(self, argv):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(argv)
        return status, json.loads(output.getvalue())

    def test_init_run_status(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(self.call(["init", "--target", temp])[0], 0)
            rc, result = self.call(["run", "--target", temp, "--intent", "HYBRID AUDIT"])
            self.assertEqual(rc, 0)
            self.assertEqual(result["tests_status"], "NOT_RUN")
            self.assertTrue(Path(result["report"]).exists())
            self.assertTrue(Path(result["plan"]).exists())
            rc, state = self.call(["status", "--target", temp])
            self.assertEqual(rc, 0)
            self.assertEqual(state["flow"], "audit")

    def test_inspect_does_not_write_state(self):
        with tempfile.TemporaryDirectory() as temp:
            rc, scan = self.call(["inspect", "--target", temp])
            self.assertEqual(rc, 0)
            self.assertEqual(scan["findings"], [])
            self.assertFalse((Path(temp) / ".hybrid").exists())


if __name__ == "__main__":
    unittest.main()
