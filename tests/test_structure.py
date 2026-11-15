"""Source-only graph evidence, malformed syntax and bounded structural analysis."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hybrid_engine.structure import analyze_structure
from hybrid_engine.assessment import assess_project
from hybrid_engine.advisor import advise


class StructureTests(unittest.TestCase):
    def test_python_cycle_detected_and_advised_with_existing_flow(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'a.py').write_text('import b\n')
            (root / 'b.py').write_text('from a import function\n')
            report = assess_project(root)
            cycle = next(f for f in report['findings'] if f['rule'] == 'LOCAL_IMPORT_CYCLE')
            self.assertEqual(cycle['related_paths'], ['b.py'])
            self.assertEqual(cycle['metrics']['component_files'], 2)
            self.assertEqual(cycle['confidence'], 'suspected')
            order = next(o for o in advise(report)['work_orders'] if o['finding_id'] == cycle['id'])
            self.assertEqual(order['workflow']['flow'], 'review')
            self.assertIn('confirm runtime relevance', order['strategy'])
            self.assertEqual(order['evidence']['metrics'], cycle['metrics'])

    def test_relative_package_imports_resolve(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'pkg').mkdir()
            (root / 'pkg' / '__init__.py').write_text('')
            (root / 'pkg' / 'a.py').write_text('from . import b\n')
            (root / 'pkg' / 'b.py').write_text('from .a import function\n')
            result = analyze_structure(root, ['pkg/a.py', 'pkg/b.py', 'pkg/__init__.py'])
            self.assertTrue(any(i['rule'] == 'LOCAL_IMPORT_CYCLE' for i in result['issues']))

    def test_no_execution_and_acyclic_chain(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'a.py').write_text('import b\nraise RuntimeError("must not execute")')
            (root / 'b.py').write_text('value = 1')
            result = analyze_structure(root, ['a.py', 'b.py'])
            self.assertEqual(len(result['edges']), 1)
            self.assertEqual(result['issues'], [])

    def test_js_comments_strings_templates_and_dynamic_imports_excluded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'a.ts').write_text('''
/* import b from './b'; */
const text = "import b from './b'";
const template = `
import b from './b';
`;
import('./b');
''')
            (root / 'b.ts').write_text("import a from './a';")
            result = analyze_structure(root, ['a.ts', 'b.ts'])
            self.assertEqual(result['edges'], [{'source': 'b.ts', 'target': 'a.ts', 'line': 1}])

    def test_js_cycle_and_typescript_js_output_reference(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'a.ts').write_text("import {b} from './b.js';")
            (root / 'b.ts').write_text("export {a} from './a';")
            result = analyze_structure(root, ['a.ts', 'b.ts'])
            self.assertEqual(len(result['edges']), 2)
            self.assertEqual(result['issues'][0]['rule'], 'LOCAL_IMPORT_CYCLE')
            self.assertTrue(all(f['method'] == 'js_lexical_subset' for f in result['files']))

    def test_many_imports_are_review_evidence_not_bad_architecture(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for n in range(10):
                (root / f'm{n}.py').write_text('value=1')
            (root / 'app.py').write_text('\n'.join(f'import m{n}' for n in range(10)))
            result = assess_project(root)
            finding = next(f for f in result['findings'] if f['rule'] == 'HIGH_LOCAL_FAN_OUT')
            self.assertEqual(finding['metrics']['local_dependencies'], 10)
            order = next(o for o in advise(result)['work_orders'] if o['finding_id'] == finding['id'])
            self.assertIn('intentional composition root', order['strategy'])

    def test_control_flow_counts_without_claiming_business_responsibilities(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'app.py').write_text('\n'.join(
                f'def f{n}(x):\n' + '    if x: pass\n' * 6 for n in range(5)))
            result = analyze_structure(root, ['app.py'])
            self.assertEqual(result['issues'][0]['metrics'], {'definitions': 5, 'branch_points': 30})

    def test_invalid_python_and_node_budget_report_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'broken.py').write_text('def invalid(')
            self.assertEqual(assess_project(root)['status'], 'INCOMPLETE')
            (root / 'broken.py').write_text('x=1')
            with patch('hybrid_engine.structure.MAX_NODES', 1):
                result = assess_project(root)
            self.assertEqual(result['status'], 'INCOMPLETE')
            self.assertEqual(result['structure']['incomplete'][0]['reason'], 'parse_or_node_limit')
            self.assertEqual(advise(result)['status'], 'BLOCKED')

    def test_bounded_size_edges_and_determinism(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'a.py').write_text('import b\n')
            (root / 'b.py').write_text('import a\n')
            result = analyze_structure(root, ['a.py', 'b.py'])
            self.assertEqual(result, analyze_structure(root, ['b.py', 'a.py']))
            with patch('hybrid_engine.structure.MAX_EDGES', 1):
                limited = analyze_structure(root, ['a.py', 'b.py'])
            self.assertTrue(limited['incomplete'])
            self.assertEqual(len(limited['edges']), 1)
            with patch('hybrid_engine.structure.MAX_SOURCE_BYTES', 1):
                self.assertEqual(len(analyze_structure(root, ['a.py', 'b.py'])['incomplete']), 2)

    def test_generated_markers_exclude_design_heuristics_but_preserve_security(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            text = '// @generated\n' + 'export const value = 1;\n' * 510 + 'eval(input);\n'
            (root / 'first.ts').write_text(text)
            (root / 'second.ts').write_text(text)
            report = assess_project(root)
            rules = {f['rule'] for f in report['findings']}
            self.assertIn('JS_EVAL', rules)
            self.assertNotIn('LARGE_SOURCE_FILE', rules)
            self.assertNotIn('EXACT_DUPLICATE_SOURCE', rules)
            self.assertNotIn('NO_TESTS_DETECTED', rules)
            self.assertEqual(report['structure']['generated_files_excluded'], ['first.ts', 'second.ts'])

    def test_package_initializer_relative_import_does_not_create_implicit_self_cycle(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'pkg').mkdir()
            (root / 'pkg' / '__init__.py').write_text('from . import child\n')
            (root / 'pkg' / 'child.py').write_text('value=1')
            result = analyze_structure(root, ['pkg/__init__.py', 'pkg/child.py'])
            self.assertEqual(result['edges'], [{'source': 'pkg/__init__.py', 'target': 'pkg/child.py', 'line': 1}])
            self.assertEqual(result['issues'], [])

    def test_python_package_precedes_same_named_module(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'pkg').mkdir()
            (root / 'pkg' / '__init__.py').write_text('value=1')
            (root / 'pkg.py').write_text('value=2')
            (root / 'caller.py').write_text('import pkg')
            result = analyze_structure(root, ['pkg/__init__.py', 'pkg.py', 'caller.py'])
            self.assertEqual(result['edges'], [{'source': 'caller.py', 'target': 'pkg/__init__.py', 'line': 1}])

    def test_ambiguous_js_and_typescript_targets_are_not_guessed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'caller.ts').write_text("import {x} from './module.js';")
            (root / 'module.js').write_text('export const x=1')
            (root / 'module.ts').write_text('export const x=2')
            result = analyze_structure(root, ['caller.ts', 'module.js', 'module.ts'])
            self.assertEqual(result['edges'], [])
            self.assertEqual(result['unresolved_imports'][0]['reason'], 'ambiguous_local_target')

    def test_relative_import_beyond_known_package_is_not_a_local_edge(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'a.py').write_text('from . import b')
            (root / 'b.py').write_text('value=1')
            result = analyze_structure(root, ['a.py', 'b.py'])
            self.assertEqual(result['edges'], [])
            self.assertEqual(result['unresolved_imports'][0]['reason'], 'relative_import_without_known_package')

    def test_src_layout_and_bundler_alias_limitations_remain_explicit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'src').mkdir()
            (root / 'src' / 'a.py').write_text('import b')
            (root / 'src' / 'b.py').write_text('value=1')
            (root / 'a.ts').write_text("import {b} from '@/b';")
            (root / 'b.ts').write_text('export const b=1')
            result = analyze_structure(root, ['src/a.py', 'src/b.py', 'a.ts', 'b.ts'])
            self.assertEqual(result['edges'], [])
            self.assertTrue(any('src layouts and aliases' in limit for limit in result['limitations']))
