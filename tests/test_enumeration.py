"""Bounded enumeration under large, deep, hostile and changing filesystems."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hybrid_engine.enumeration import enumerate_tree
from hybrid_engine.audit import scan, SKIP_DIRS
from hybrid_engine.db_guard import scan_database
from hybrid_engine.assessment import assess_project


class EnumerationTests(unittest.TestCase):
    def test_thousands_ineligible_files_stop_before_any_read(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for n in range(2001):
                (root / f'{n:04}.txt').touch()
            with patch('hybrid_engine.enumeration.MAX_ENTRIES', 1000):
                for scanner in (scan, scan_database, assess_project):
                    result = scanner(root)
                    coverage = result.get('enumeration', result.get('coverage', {}).get('enumeration'))
                    self.assertEqual(coverage['entries_examined'], 1000)
                    self.assertEqual(coverage['reasons'], ['entry_budget'])
                    self.assertEqual(coverage['discarded_entries'], 1000)
                    self.assertIsNone(coverage['unexamined_entries'])
                    self.assertTrue(result.get('truncated', result.get('coverage', {}).get('truncated')))

    def test_thousands_directories_directory_budget(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for n in range(2000):
                (root / f'd{n:04}').mkdir()
            with patch('hybrid_engine.enumeration.MAX_DIRECTORIES', 50):
                result = enumerate_tree(root, SKIP_DIRS)
            self.assertEqual(result.directories_examined, 50)
            self.assertEqual(result.entries_examined, 2000)
            self.assertEqual(result.reasons, ['directory_budget'])

    def test_deep_tree_uses_no_recursion_and_reports_depth(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            child = root
            for n in range(100):
                child /= 'd'
                child.mkdir()
            result = enumerate_tree(root, SKIP_DIRS)
            self.assertEqual(result.reasons, ['depth_budget'])
            self.assertEqual(result.directories_examined, 65)

    def test_ignored_directory_never_opened(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'node_modules').mkdir()
            for n in range(100):
                (root / 'node_modules' / str(n)).touch()
            result = enumerate_tree(root, SKIP_DIRS)
            self.assertEqual(result.ignored_directories, 1)
            self.assertEqual(result.directories_examined, 1)
            self.assertEqual(result.entries_examined, 1)
            self.assertFalse(result.truncated)

    def test_symlink_and_fifo_are_distinct_exclusions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'outside').symlink_to('/tmp')
            os.mkfifo(root / 'special.py')
            result = enumerate_tree(root, SKIP_DIRS)
            self.assertEqual(result.symlinks_excluded, 1)
            self.assertEqual(result.special_files_excluded, 1)
            self.assertEqual(result.files, [])
            self.assertEqual(assess_project(root)['status'], 'INCOMPLETE')

    def test_enumeration_permission_error(self):
        with tempfile.TemporaryDirectory() as temp, patch(
                'hybrid_engine.enumeration.os.scandir', side_effect=PermissionError):
            result = enumerate_tree(Path(temp), SKIP_DIRS)
            self.assertEqual(result.errors, 1)
            self.assertFalse(result.truncated)
            self.assertIsNone(result.coverage()['unexamined_entries'])

    def test_removed_file_after_inventory_marks_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / 'app.py'
            path.write_text('x=1')
            tree = enumerate_tree(root, SKIP_DIRS)
            path.unlink()
            for scanner in (scan, scan_database):
                result = scanner(root, enumeration=tree)
                self.assertEqual(result['files_skipped'], 1)

    def test_deterministic_with_budget_exhaustion_in_later_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ('b', 'a'):
                (root / name).mkdir()
            (root / 'a' / 'good.py').write_text('x=1')
            for n in range(20):
                (root / 'b' / f'{n}.py').touch()
            with patch('hybrid_engine.enumeration.MAX_ENTRIES', 10):
                first = enumerate_tree(root, SKIP_DIRS)
                self.assertEqual(first, enumerate_tree(root, SKIP_DIRS))
            self.assertEqual(first.files, ['a/good.py'])
            self.assertEqual(first.reasons, ['entry_budget'])

    def test_exact_budget_is_conservatively_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'one.py').touch()
            with patch('hybrid_engine.enumeration.MAX_ENTRIES', 1):
                self.assertTrue(enumerate_tree(root, SKIP_DIRS).truncated)
            with patch('hybrid_engine.enumeration.MAX_ENTRIES', 2):
                self.assertFalse(enumerate_tree(root, SKIP_DIRS).truncated)

    def test_assessment_enumerates_only_once(self):
        import hybrid_engine.assessment as module
        with tempfile.TemporaryDirectory() as temp, patch.object(
                module, 'enumerate_tree', wraps=enumerate_tree) as wrapped:
            assess_project(Path(temp))
            self.assertEqual(wrapped.call_count, 1)

    def test_regular_file_replaced_by_symlink_is_a_read_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'app.py'
            source.write_text('value=1')
            target = root / 'target.txt'
            target.write_text('external content')
            tree = enumerate_tree(root, SKIP_DIRS)
            source.unlink()
            source.symlink_to(target)
            for scanner in (scan, scan_database):
                result = scanner(root, enumeration=tree)
                self.assertEqual(result['files_skipped'], 1)
            from hybrid_engine.assessment import _inventory
            self.assertEqual(_inventory(root, tree)[1], 1)

    @unittest.skipUnless(os.name == 'posix', 'POSIX non-UTF8 filename fixture')
    def test_non_utf8_filename_is_incomplete_instead_of_raising(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            filename = os.fsencode(temp) + b'/bad_\xff.js'
            with open(filename, 'wb') as stream:
                stream.write(b'eval(input);')
            result = assess_project(root)
            self.assertEqual(result['status'], 'INCOMPLETE')
            self.assertGreater(result['coverage']['enumeration']['errors'], 0)

    def test_paths_beyond_report_contract_do_not_break_advisor_round_trip(self):
        from hybrid_engine.advisor import advise
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            parent = root
            for _ in range(9):
                parent /= 'd' * 120
                parent.mkdir()
            (parent / 'source.js').write_text('eval(input);')
            report = assess_project(root)
            self.assertEqual(report['status'], 'INCOMPLETE')
            self.assertEqual(advise(report)['status'], 'BLOCKED')
