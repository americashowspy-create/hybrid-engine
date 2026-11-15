"""Resource-bounded, deterministic tree inventory shared by offline scanners."""
from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path

from .source_io import open_directory

MAX_ENTRIES = 20000
MAX_DIRECTORIES = 1000
MAX_DEPTH = 64


@dataclass
class Enumeration:
    files: list[str] = field(default_factory=list)
    entries_examined: int = 0
    directories_examined: int = 0
    ignored_directories: int = 0
    symlinks_excluded: int = 0
    special_files_excluded: int = 0
    errors: int = 0
    discarded_entries: int = 0
    reasons: list[str] = field(default_factory=list)

    @property
    def truncated(self) -> bool:
        return bool(self.reasons)

    def coverage(self) -> dict:
        return {name: value for name, value in vars(self).items() if name != 'files'} | {
            'truncated': self.truncated, 'regular_files_enumerated': len(self.files),
            'limits': {'entries': MAX_ENTRIES, 'directories': MAX_DIRECTORIES, 'depth': MAX_DEPTH},
            'unexamined_entries': None if self.truncated or self.errors else 0,
        }


def enumerate_tree(root: Path, skip_dirs: set | frozenset) -> Enumeration:
    """Do not sort an unbounded directory or count the tree after exhaustion.

    A directory that consumes the remaining budget is discarded in its entirety:
    partial directory iteration is not stable across filesystems. Exact-budget
    exhaustion is conservatively incomplete without requesting another entry.
    """
    result = Enumeration()
    pending = [('', 0)]
    while pending:
        if result.directories_examined >= MAX_DIRECTORIES:
            result.reasons.append('directory_budget')
            break
        relative, depth = pending.pop()
        if depth > MAX_DEPTH:
            if 'depth_budget' not in result.reasons:
                result.reasons.append('depth_budget')
            continue
        result.directories_examined += 1
        entries = []
        try:
            descriptor = open_directory(root, relative)
            try:
                with os.scandir(descriptor) as iterator:
                    for entry in iterator:
                        result.entries_examined += 1
                        entries.append(entry)
                        if result.entries_examined >= MAX_ENTRIES:
                            result.discarded_entries += len(entries)
                            result.reasons.append('entry_budget')
                            return result
                    # Classify before closing the fd: DirEntry.stat may need it.
                    children = []
                    for entry in sorted(entries, key=lambda e: e.name):
                        path = f'{relative}/{entry.name}' if relative else entry.name
                        try:
                            if entry.is_symlink():
                                result.symlinks_excluded += 1
                            elif entry.is_dir(follow_symlinks=False):
                                if entry.name in skip_dirs:
                                    result.ignored_directories += 1
                                else:
                                    children.append((path, depth + 1))
                            elif entry.is_file(follow_symlinks=False):
                                result.files.append(path)
                            else:
                                result.special_files_excluded += 1
                        except OSError:
                            result.errors += 1
                    pending.extend(reversed(children))
            finally:
                os.close(descriptor)
        except OSError:
            result.errors += 1
    return result
