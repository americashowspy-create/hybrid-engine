"""Static, bounded package manager and workspace metadata; never installs anything."""
from __future__ import annotations

import fnmatch
import posixpath
import re
from pathlib import Path

from .source_io import read_source
from .report_io import parse_json_bytes

LOCK_MANAGERS = {'package-lock.json': 'npm', 'npm-shrinkwrap.json': 'npm',
                 'pnpm-lock.yaml': 'pnpm', 'yarn.lock': 'yarn', 'bun.lock': 'bun', 'bun.lockb': 'bun'}
MAX_MANIFESTS = 100
MAX_MANIFEST_BYTES = 64 * 1024


def analyze_packages(root: Path, files: list[str], *, reader=None) -> dict:
    reader = reader or read_source
    known = set(files)
    manifests = sorted(p for p in files if posixpath.basename(p) == 'package.json')
    packages = {}
    incomplete = []
    if len(manifests) > MAX_MANIFESTS:
        incomplete.append({'path': '.', 'reason': 'manifest_budget'})
    for path in manifests[:MAX_MANIFESTS]:
        try:
            data = parse_json_bytes(reader(root, path, MAX_MANIFEST_BYTES))
            if not isinstance(data, dict):
                raise ValueError('Manifest must be an object')
            directory = posixpath.dirname(path)
            declaration = data.get('packageManager')
            manager = None
            if declaration is not None:
                if not isinstance(declaration, str) or not re.fullmatch(r'(npm|pnpm|yarn|bun)@[^\s]{1,100}', declaration):
                    raise ValueError('Unsupported package manager declaration')
                manager = declaration.split('@')[0]
            workspace = data.get('workspaces', [])
            if isinstance(workspace, dict):
                workspace = workspace.get('packages', [])
            if not isinstance(workspace, list):
                raise ValueError('Invalid workspace list')
            # pnpm's common YAML subset; no YAML object construction or interpolation.
            yaml_path = posixpath.join(directory, 'pnpm-workspace.yaml')
            if yaml_path in known:
                text = reader(root, yaml_path, MAX_MANIFEST_BYTES).decode('utf-8')
                active = False
                for line in text.splitlines():
                    if re.fullmatch(r'packages:\s*(?:#.*)?', line):
                        active = True
                    elif line.lstrip().startswith('packages:'):
                        raise ValueError('Unsupported pnpm inline workspace declaration')
                    elif active and line.strip() and not line.startswith((' ', '\t', '#')):
                        active = False
                    elif active and line.strip() and not line.lstrip().startswith('#'):
                        match = re.fullmatch(r'\s+-\s+[\'\"]?([a-zA-Z0-9_./*?!-]+)[\'\"]?\s*(?:#.*)?', line)
                        if not match:
                            raise ValueError('Unsupported pnpm workspace YAML')
                        workspace.append(match.group(1))
            if len(workspace) > 100 or any(not isinstance(p, str) or len(p) > 256
                    or p.startswith(('/', '!')) or '..' in p.split('/') or '\\' in p
                    for p in workspace):
                raise ValueError('Unsupported workspace pattern')
            locks = sorted(name for name in LOCK_MANAGERS if posixpath.join(directory, name) in known)
            packages[path] = {'path': path, 'directory': directory, 'declared_manager': manager,
                              'lockfiles': locks, 'workspace_patterns': sorted(set(workspace))}
        except (OSError, UnicodeError, ValueError, RecursionError):
            incomplete.append({'path': path, 'reason': 'invalid_or_unsupported_manifest'})
    issues = []
    for path, package in packages.items():
        directory = package['directory']
        owners = []
        for other, owner in packages.items():
            if other == path or not owner['workspace_patterns']:
                continue
            prefix = owner['directory'] + '/' if owner['directory'] else ''
            if directory.startswith(prefix):
                relative = directory[len(prefix):]
                if any(fnmatch.fnmatchcase(relative, pattern.rstrip('/')) for pattern in owner['workspace_patterns']):
                    owners.append(owner)
        owner = max(owners, key=lambda p: len(p['directory'])) if owners else None
        package['workspace_owner'] = owner['path'] if owner else None
        effective_manager = package['declared_manager'] or (owner['declared_manager'] if owner else None)
        lock_source = package if package['lockfiles'] else owner or package
        locks = lock_source['lockfiles']
        managers = {LOCK_MANAGERS[name] for name in locks}
        package['effective_manager'] = effective_manager or (next(iter(managers)) if len(managers) == 1 else None)
        package['lockfile_source'] = lock_source['path'] if locks else None
        if not locks:
            # Owner reports the missing workspace-wide lock; avoid duplicate child warnings.
            if not owner:
                issues.append({'rule': 'MISSING_JS_LOCKFILE', 'path': path, 'related_paths': []})
        elif len(managers) > 1:
            if lock_source is package:
                issues.append({'rule': 'CONFLICTING_JS_LOCKFILES', 'path': path,
                               'related_paths': [posixpath.join(lock_source['directory'], lock) for lock in locks]})
        elif effective_manager and effective_manager not in managers:
            issues.append({'rule': 'PACKAGE_MANAGER_LOCK_MISMATCH', 'path': path,
                           'related_paths': [posixpath.join(lock_source['directory'], lock) for lock in locks]})
    return {'packages': [packages[p] for p in sorted(packages)], 'issues': issues,
            'incomplete': incomplete, 'limits': {'manifests': MAX_MANIFESTS, 'manifest_bytes': MAX_MANIFEST_BYTES},
            'limitations': ['Lock presence is metadata only; freshness and content are not validated.',
                            'Only package.json workspaces and the common pnpm packages-list YAML subset are supported.',
                            'Workspace exclusions, YAML anchors, custom managers and lockfile policies require manual review.']}
