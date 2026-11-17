"""Adversarial regressions for bounded offline assessment."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hybrid_engine.assessment import assess_project, assessment_markdown
from hybrid_engine.source_io import read_source


class AssessmentHardeningTests(unittest.TestCase):
    def test_fifo_does_not_block_or_claim_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            os.mkfifo(root / 'source.py')
            report = assess_project(root)
            self.assertEqual(report['status'], 'INCOMPLETE')
            with self.assertRaises(OSError):
                read_source(root, 'source.py', 100)

    def test_replaced_parent_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as outside:
            root = Path(temp)
            (Path(outside) / 'source.py').write_text('external')
            (root / 'parent').symlink_to(outside)
            with self.assertRaises(OSError):
                read_source(root, 'parent/source.py', 100)
            with self.assertRaises(ValueError):
                read_source(root, '../source.py', 100)

    def test_byte_limit_enforced_at_read(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'source.py').write_bytes(b'a' * 101)
            with self.assertRaises(OSError):
                read_source(root, 'source.py', 100)

    def test_directory_walk_error_marks_incomplete(self):
        with tempfile.TemporaryDirectory() as temp, patch(
                'hybrid_engine.enumeration.os.scandir', side_effect=PermissionError('unreadable directory')):
            result = assess_project(Path(temp))
            self.assertEqual(result['status'], 'INCOMPLETE')
            self.assertGreater(result['coverage']['inventory_files_skipped'], 0)

    def test_html_sink_is_a_lead_for_both_static_and_dynamic_html(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'static.tsx').write_text('<div dangerouslySetInnerHTML={{__html: "hello"}} />')
            (root / 'dynamic.tsx').write_text('<div dangerouslySetInnerHTML={{__html: props.value}} />')
            result = assess_project(root)
            sinks = [f for f in result['findings'] if f['rule'] == 'REACT_HTML_INJECTION']
            self.assertEqual(len(sinks), 2)
            self.assertTrue(all(f['confidence'] == 'suspected' for f in sinks))
            self.assertTrue(all('exploitability is not verified' in f['message'] for f in sinks))
            self.assertIn('Static trusted HTML may need no change', json.dumps(result))
            self.assertNotIn('props.value', json.dumps(result))

    def test_lockfile_directory_and_symlink_do_not_count(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'package.json').write_text('{}')
            (root / 'yarn.lock').mkdir()
            (root / 'package-lock.json').symlink_to(root / 'package.json')
            self.assertIn('MISSING_JS_LOCKFILE', {f['rule'] for f in assess_project(root)['findings']})

    def test_test_config_is_not_test_source_and_go_test_is(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'app.go').write_text('package main')
            (root / 'test_config.json').write_text('{}')
            self.assertIn('NO_TESTS_DETECTED', {f['rule'] for f in assess_project(root)['findings']})
            (root / 'app_test.go').write_text('package main')
            self.assertNotIn('NO_TESTS_DETECTED', {f['rule'] for f in assess_project(root)['findings']})

    def test_markdown_cannot_inject_html_links_or_headings_via_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / '<img src=x onerror=alert(1)>\n# [go](evil).tsx').write_text('eval(value);')
            rendered = assessment_markdown(assess_project(root))
            self.assertNotIn('<img', rendered)
            self.assertNotIn('[go](evil)', rendered)
            self.assertNotIn('\n# [go]', rendered)

    def test_general_finding_limit_marks_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'source.ts').write_text('eval(input);\n' * 10)
            with patch('hybrid_engine.audit.MAX_FINDINGS', 3):
                report = assess_project(root)
            self.assertEqual(report['status'], 'INCOMPLETE')
            self.assertTrue(report['coverage']['truncated'])
            self.assertEqual(len([f for f in report['findings'] if f['rule'] == 'JS_EVAL']), 3)

    def test_generated_dependency_directories_excluded_consistently(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ('vendor', 'target', '.cache'):
                (root / name).mkdir()
                (root / name / 'generated.ts').write_text('eval(input);')
            report = assess_project(root)
            self.assertEqual(report['findings'], [])
            self.assertEqual(report['coverage']['candidate_files'], 0)
