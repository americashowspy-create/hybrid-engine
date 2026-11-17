"""Evidence-backed read deduplication with bounded per-assessment memory."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hybrid_engine.source_io import SourceReader
from hybrid_engine.assessment import assess_project


class SourceCacheTests(unittest.TestCase):
    def test_single_physical_read_across_four_source_consumers(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'app.py').write_text('x=1\n')
            report = assess_project(root)
            self.assertEqual(report['processing']['physical_read_attempts'], 1)
            self.assertEqual(report['processing']['cache_hits'], 3)
            self.assertEqual(report['processing']['cached_bytes'], 4)

    def test_consumer_limits_preserved_and_root_cannot_change(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'app.py').write_bytes(b'x' * 20)
            reader = SourceReader(root)
            self.assertEqual(reader(root, 'app.py', 20), b'x' * 20)
            with self.assertRaises(OSError):
                reader(root, 'app.py', 19)
            with self.assertRaises(ValueError):
                reader(root / 'other', 'app.py', 100)

    def test_memory_limit_no_persistence_and_no_failed_read_caching(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'app.py').write_bytes(b'a' * 10)
            reader = SourceReader(root, max_cache_bytes=5)
            reader(root, 'app.py', 20)
            reader(root, 'app.py', 20)
            self.assertEqual(reader.cached_bytes, 0)
            self.assertEqual(reader.physical_read_attempts, 2)
            with self.assertRaises(OSError):
                reader(root, 'missing.py', 20)
            (root / 'missing.py').write_text('okay')
            self.assertEqual(reader(root, 'missing.py', 20), b'okay')
            self.assertEqual(sorted(p.name for p in root.iterdir()), ['app.py', 'missing.py'])

    def test_report_identical_with_cache_disabled_except_processing_metrics(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'app.py').write_text('x=1')
            cached = assess_project(root)
            with patch('hybrid_engine.assessment.SourceReader', side_effect=lambda path: SourceReader(path, 0)):
                uncached = assess_project(root)
            self.assertGreater(uncached.pop('processing')['physical_read_attempts'], cached.pop('processing')['physical_read_attempts'])
            self.assertEqual(cached, uncached)
