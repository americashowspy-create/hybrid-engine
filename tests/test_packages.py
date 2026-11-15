"""Static npm/pnpm/Yarn/Bun and workspace metadata; no dependency execution."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hybrid_engine.assessment import assess_project
from hybrid_engine.advisor import advise
from hybrid_engine.packages import analyze_packages


class PackageTests(unittest.TestCase):
    def put(self, root, path, content):
        destination = root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(content) if isinstance(content, dict) else content)

    def test_each_supported_manager_and_lock(self):
        for manager, lock in [('npm','package-lock.json'), ('npm','npm-shrinkwrap.json'),
                              ('pnpm','pnpm-lock.yaml'), ('yarn','yarn.lock'),
                              ('bun','bun.lock'), ('bun','bun.lockb')]:
            with self.subTest(manager=manager, lock=lock), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.put(root, 'package.json', {'packageManager': manager + '@1.0.0'})
                self.put(root, lock, '')
                result = assess_project(root)
                self.assertEqual(result['packages']['packages'][0]['effective_manager'], manager)
                self.assertFalse(result['packages']['issues'])

    def test_root_workspace_lock_inherited_and_independent_package_warns(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.put(root, 'package.json', {'workspaces': ['packages/*'], 'packageManager': 'yarn@4.0'})
            self.put(root, 'yarn.lock', '')
            self.put(root, 'packages/app/package.json', {})
            self.put(root, 'tools/standalone/package.json', {})
            result = assess_project(root)
            missing = [f['path'] for f in result['findings'] if f['rule'] == 'MISSING_JS_LOCKFILE']
            self.assertEqual(missing, ['tools/standalone/package.json'])
            child = next(p for p in result['packages']['packages'] if p['path'] == 'packages/app/package.json')
            self.assertEqual(child['workspace_owner'], 'package.json')
            self.assertEqual(child['lockfile_source'], 'package.json')

    def test_pnpm_yaml_workspace(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.put(root, 'package.json', {'packageManager': 'pnpm@9'})
            self.put(root, 'pnpm-workspace.yaml', "packages:\n  - 'apps/*'\n")
            self.put(root, 'pnpm-lock.yaml', '')
            self.put(root, 'apps/web/package.json', {})
            result = assess_project(root)
            self.assertFalse(result['packages']['issues'])
            self.assertFalse(result['packages']['incomplete'])
            self.assertEqual(result['packages']['packages'][0]['workspace_owner'], 'package.json')

    def test_conflicting_locks_and_declared_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.put(root, 'package.json', {'packageManager': 'pnpm@9'})
            self.put(root, 'yarn.lock', '')
            result = assess_project(root)
            self.assertIn('PACKAGE_MANAGER_LOCK_MISMATCH', {f['rule'] for f in result['findings']})
            self.assertEqual(advise(result)['status'], 'REVIEW_REQUIRED')
            self.put(root, 'package-lock.json', '{}')
            result = assess_project(root)
            self.assertIn('CONFLICTING_JS_LOCKFILES', {f['rule'] for f in result['findings']})

    def test_invalid_unsupported_and_budget_mark_incomplete(self):
        for data in ('[]', '{', {'workspaces': ['../external']}, {'packageManager': 'unknown@1'}):
            with self.subTest(data=data), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.put(root, 'package.json', data)
                self.assertEqual(assess_project(root)['status'], 'INCOMPLETE')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.put(root, 'package.json', {})
            with patch('hybrid_engine.packages.MAX_MANIFESTS', 0):
                self.assertTrue(analyze_packages(root, ['package.json'])['incomplete'])

    def test_workspace_missing_root_lock_reports_once(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.put(root, 'package.json', {'workspaces': {'packages': ['apps/*']}})
            self.put(root, 'apps/a/package.json', {})
            self.put(root, 'apps/b/package.json', {})
            result = assess_project(root)
            self.assertEqual([f['path'] for f in result['findings'] if f['rule'] == 'MISSING_JS_LOCKFILE'], ['package.json'])

    def test_inline_yaml_workspace_and_duplicate_json_keys_fail_honestly(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.put(root, 'package.json', {})
            self.put(root, 'pnpm-workspace.yaml', 'packages: [apps/*]')
            self.assertEqual(assess_project(root)['status'], 'INCOMPLETE')
            (root / 'pnpm-workspace.yaml').unlink()
            self.put(root, 'package.json', '{"workspaces":[],"workspaces":["apps/*"]}')
            self.assertEqual(assess_project(root)['status'], 'INCOMPLETE')
