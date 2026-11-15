"""Bounded source reads; reject special files and symlinked path components."""
from __future__ import annotations

import os
import stat
from pathlib import Path

MAX_RELATIVE_PATH_CHARS = 1024


def read_source(root: Path, relative: str, limit: int) -> bytes:
    """Open beneath a trusted root with descriptor-relative, no-follow reads.

    Directory descriptors prevent symlink replacement between inventory and read.
    Nonblocking open prevents a substituted FIFO from hanging the scanner.
    """
    parts = Path(relative).parts
    if not parts or Path(relative).is_absolute() or any(p in (".", "..") for p in parts):
        raise ValueError("Expected a relative source file")
    directory = open_directory(root, '/'.join(parts[:-1]))
    try:
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=directory)
        with os.fdopen(descriptor, "rb") as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > limit:
                raise OSError("Source is not a bounded regular file")
            data = stream.read(limit + 1)
            if len(data) > limit:
                raise OSError("Source grew beyond the byte limit")
            return data
    finally:
        os.close(directory)


def open_directory(root: Path, relative: str = '') -> int:
    """Return an owned directory descriptor without following child symlinks."""
    parts = Path(relative).parts
    if Path(relative).is_absolute() or any(part == '..' for part in parts):
        raise ValueError('Expected relative directory')
    if not hasattr(os, 'O_NOFOLLOW') or os.open not in os.supports_dir_fd:
        raise OSError('Safe descriptor-relative reads are unavailable on this platform')
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


class SourceReader:
    """Per-assessment bounded byte cache. Never persists source or exposes values."""

    def __init__(self, root: Path, max_cache_bytes: int = 8 * 1024 * 1024):
        self.root = root
        self.max_cache_bytes = max_cache_bytes
        self._cache = {}
        self.cached_bytes = 0
        self.physical_read_attempts = 0
        self.cache_hits = 0

    def __call__(self, root: Path, relative: str, limit: int) -> bytes:
        if root != self.root:
            raise ValueError('Source cache belongs to a different root')
        if relative in self._cache:
            self.cache_hits += 1
            data = self._cache[relative]
            if len(data) > limit:
                raise OSError('Cached source exceeds consumer byte limit')
            return data
        self.physical_read_attempts += 1
        data = read_source(root, relative, limit)
        if self.cached_bytes + len(data) <= self.max_cache_bytes:
            self._cache[relative] = data
            self.cached_bytes += len(data)
        return data

    def metrics(self) -> dict:
        return {'physical_read_attempts': self.physical_read_attempts, 'cache_hits': self.cache_hits,
                'cached_bytes': self.cached_bytes, 'cache_byte_limit': self.max_cache_bytes}
