"""Bounded source structure: Python AST and a conservative JS import subset."""
from __future__ import annotations

import ast
import posixpath
import re
from pathlib import Path

from .source_io import read_source

MAX_NODES = 50000
MAX_SOURCE_BYTES = 128 * 1024
MAX_EDGES = 2000
SUFFIXES = {'.py', '.js', '.jsx', '.ts', '.tsx'}
# Token alternatives consume comments/templates as units so their text is never an import.
JS_TOKENS = re.compile(r'/\*[\s\S]*?\*/|//[^\n]*|`(?:\\[\s\S]|[^`\\])*`|'
                       r'"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|'
                       r'[A-Za-z_$][\w$]*|[^\s]', re.MULTILINE)


def _js_imports(text: str):
    tokens = []
    line = 1
    offset = 0
    for match in JS_TOKENS.finditer(text):
        line += text.count('\n', offset, match.start())
        value = match.group()
        if not value.startswith(('//', '/*', '`')):
            tokens.append((value, line))
        line += value.count('\n')
        offset = match.end()
    for i, (value, number) in enumerate(tokens):
        if value not in {'import', 'export'}:
            continue
        # Excludes member names, dynamic imports and import.meta.
        if i and tokens[i - 1][0] in {'.', '?.'}:
            continue
        following = tokens[i + 1:i + 24]
        if not following or following[0][0] in {'(', '.'}:
            continue
        if value == 'import' and following[0][0].startswith(('"', "'")):
            yield following[0][0][1:-1], number
            continue
        for j, (token, _) in enumerate(following[:-1]):
            if token == ';':
                break
            if token == 'from' and following[j + 1][0].startswith(('"', "'")):
                yield following[j + 1][0][1:-1], number
                break


def analyze_structure(root: Path, candidates: list[str], *, reader=None) -> dict:
    """No imports executed. Graph nodes are only successfully analyzed local files."""
    reader = reader or read_source
    paths = {p for p in candidates if Path(p).suffix in SUFFIXES}
    records = {}
    pending = []
    issues = []
    incomplete = []
    nodes_used = 0
    for path in sorted(paths):
        try:
            text = reader(root, path, MAX_SOURCE_BYTES).decode('utf-8')
            if '\x00' in text:
                raise ValueError('Binary source')
        except (OSError, UnicodeError, ValueError):
            incomplete.append({'path': path, 'reason': 'unreadable_or_size_limit'})
            continue
        # Generated sources still receive security scanning, but not design advice.
        if (path.endswith('database.types.ts') and 'export type Database =' in text
                and '__InternalSupabase' in text):
            continue
        local_imports = []
        branches = definitions = 0
        if path.endswith('.py'):
            try:
                tree = ast.parse(text)
                for node in ast.walk(tree):
                    nodes_used += 1
                    if nodes_used > MAX_NODES:
                        raise ValueError('node_budget')
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        definitions += 1
                    if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try,
                                         ast.IfExp, ast.Match, ast.comprehension)):
                        branches += 1
                    if isinstance(node, ast.Import):
                        local_imports.extend((alias.name, node.lineno) for alias in node.names)
                    elif isinstance(node, ast.ImportFrom):
                        prefix = node.module or ''
                        base = posixpath.dirname(path).split('/') if '/' in path else []
                        if node.level:
                            if node.level - 1 > len(base):
                                continue
                            base = base[:len(base) - node.level + 1]
                            prefix = '.'.join(base + ([prefix] if prefix else []))
                        for alias in node.names:
                            local_imports.append((prefix + '.' + alias.name if prefix else alias.name, node.lineno))
                        local_imports.append((prefix, node.lineno))
                kind = 'python_ast'
            except (SyntaxError, ValueError, RecursionError, MemoryError):
                incomplete.append({'path': path, 'reason': 'parse_or_node_limit'})
                if nodes_used > MAX_NODES:
                    break
                continue
            for module, line in local_imports:
                base = module.replace('.', '/')
                target = next((p for p in (base + '.py', base + '/__init__.py') if p in paths), None)
                if target:
                    pending.append((path, target, line))
        else:
            kind = 'js_lexical_subset'
            for module, line in _js_imports(text):
                if not module.startswith('.') or '\\' in module:
                    continue
                base = posixpath.normpath(posixpath.join(posixpath.dirname(path), module))
                if base.startswith('../'):
                    continue
                # TypeScript may reference a .js output path while source is .ts.
                possibilities = [base] + [base + s for s in ('.ts', '.tsx', '.js', '.jsx')]
                possibilities += [base + '/index' + s for s in ('.ts', '.tsx', '.js', '.jsx')]
                if base.endswith('.js'):
                    possibilities += [base[:-3] + '.ts', base[:-3] + '.tsx']
                target = next((p for p in possibilities if p in paths), None)
                if target:
                    pending.append((path, target, line))
        records[path] = {'path': path, 'method': kind, 'definitions': definitions,
                         'branch_points': branches, 'local_dependencies': 0, 'local_dependents': 0}
        if len(pending) > MAX_EDGES:
            incomplete.append({'path': path, 'reason': 'edge_budget'})
            break
    edges = sorted(set(edge for edge in pending if edge[0] in records and edge[1] in records))[:MAX_EDGES]
    graph = {path: set() for path in records}
    reverse = {path: set() for path in records}
    for source, target, _ in edges:
        graph[source].add(target)
        reverse[target].add(source)
    for path, record in records.items():
        record['local_dependencies'] = len(graph[path])
        record['local_dependents'] = len(reverse[path])
        if record['branch_points'] >= 30 and record['definitions'] >= 5:
            issues.append({'rule': 'CONCENTRATED_CONTROL_FLOW', 'path': path, 'line': 1,
                           'related_paths': [], 'metrics': {k: record[k] for k in ('definitions', 'branch_points')}})
        if record['local_dependencies'] >= 10:
            issues.append({'rule': 'HIGH_LOCAL_FAN_OUT', 'path': path, 'line': 1,
                           'related_paths': sorted(graph[path])[:20],
                           'metrics': {'local_dependencies': len(graph[path])}})
    # SCCs computed iteratively: bounded graph, no recursion on deep import chains.
    visited = set()
    order = []
    for start in sorted(graph):
        stack = [(start, False)]
        while stack:
            node, exiting = stack.pop()
            if exiting:
                order.append(node)
            elif node not in visited:
                visited.add(node)
                stack.append((node, True))
                stack.extend((child, False) for child in sorted(graph[node], reverse=True) if child not in visited)
    assigned = set()
    for start in reversed(order):
        if start in assigned:
            continue
        component = []
        stack = [start]
        assigned.add(start)
        while stack:
            node = stack.pop()
            component.append(node)
            for child in sorted(reverse[node], reverse=True):
                if child not in assigned:
                    assigned.add(child)
                    stack.append(child)
        component.sort()
        if len(component) > 1 or start in graph[start]:
            location = component[0]
            line = min(n for source, target, n in edges if source == location and target in component)
            issues.append({'rule': 'LOCAL_IMPORT_CYCLE', 'path': location, 'line': line,
                           'related_paths': component[1:21],
                           'metrics': {'component_files': len(component)}})
    return {'files': [records[p] for p in sorted(records)],
            'edges': [{'source': a, 'target': b, 'line': n} for a, b, n in edges],
            'issues': issues, 'incomplete': incomplete, 'ast_nodes_examined': nodes_used,
            'limits': {'source_bytes': MAX_SOURCE_BYTES, 'ast_nodes': MAX_NODES, 'edges': MAX_EDGES},
            'limitations': ['Local static imports only; no runtime, aliases, tsconfig paths or dependency execution.',
                            'Python AST resolves source-root modules; src layouts and ambiguous package roots may be unresolved.',
                            'JS/TS uses a lexical subset, not a full parser; dynamic imports and require are not resolved.',
                            'Counts and cycles are review evidence, not proof of poor design or runtime failure.']}
