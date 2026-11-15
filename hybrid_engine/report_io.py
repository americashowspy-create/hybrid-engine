"""Strict bounded JSON and normalized metadata shared by offline report consumers."""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from .source_io import read_source

MAX_REPORT_BYTES = 8 * 1024 * 1024

def load_json_report(path: Path) -> dict:
    path = path.expanduser().absolute()
    return parse_json_bytes(read_source(path.parent, path.name, MAX_REPORT_BYTES))


def parse_json_bytes(raw: bytes) -> dict:
    if len(raw) > MAX_REPORT_BYTES:
        raise ValueError("JSON byte limit exceeded")
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON keys are not accepted')
            result[key] = value
        return result

    try:
        text = raw.decode('utf-8')
        depth = 0
        quoted = escaped = False
        for character in text:
            if quoted:
                if escaped:
                    escaped = False
                elif character == '\\':
                    escaped = True
                elif character == '"':
                    quoted = False
            elif character == '"':
                quoted = True
            elif character in '[{':
                depth += 1
                if depth > 64:
                    raise ValueError('Assessment JSON nesting exceeds 64 levels')
            elif character in ']}':
                depth -= 1
        return json.loads(text, object_pairs_hook=unique_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Non-finite JSON')))
    except (UnicodeError, RecursionError) as exc:
        raise ValueError('Invalid assessment JSON encoding or nesting') from exc


def relative_path(value) -> str:
    if (not isinstance(value, str) or not value or len(value) > 1024
            or any(ord(c) < 32 or ord(c) == 127 for c in value)
            or '\\' in value or ':' in value):
        raise ValueError('Invalid finding path')
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or '..' in parsed.parts or parsed.as_posix() != value:
        raise ValueError('Finding path must be normalized and relative')
    return value


