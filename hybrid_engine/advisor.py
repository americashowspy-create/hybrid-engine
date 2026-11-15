"""Offline, deterministic implementation plans from assessment v1; never patches."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath

from .assessment import DEFAULT_GUIDANCE, GUIDANCE, SEVERITY_ORDER, markdown_text
from .core import FLOWS, GATES
from .source_io import read_source

MAX_REPORT_BYTES = 8 * 1024 * 1024
MAX_FINDINGS = 5000
SECRET_RULES = frozenset({'PRIVATE_KEY', 'SUPABASE_SECRET', 'GITHUB_TOKEN', 'AWS_ACCESS_KEY'})
RULE_GUIDANCE = {
    'JS_EVAL': (
        'Dynamic code evaluation was observed; input provenance is unknown.',
        'Trace arguments to eval and determine whether input is attacker-controlled; prefer a bounded parser when applicable.',
        'Document input provenance and test rejection of executable untrusted input.'),
    'FIREBASE_OPEN_RULE': (
        'A static rule appears to permit unrestricted access.',
        'Review intended public access and rule scope before proposing restrictive rules; validate with synthetic identities in an authorized emulator.',
        'Role-specific emulator tests cover intended access and denied operations.'),
    'MONEY_FLOAT': (
        'A monetary field appears to use a floating-point representation.',
        'Confirm currency, rounding and range requirements; compare decimal or integer minor units without applying a migration.',
        'Boundary and rounding tests establish the required monetary semantics.'),
    'TIMESTAMP_NO_TZ': (
        'An event timestamp appears to omit time-zone information.',
        'Confirm whether local wall time or an absolute instant is intended; review producers and consumers before a schema proposal.',
        'Tests cover intended time-zone conversion and daylight-saving boundaries where applicable.'),
    'HIGH_OFFSET': (
        'A SQL query contains a large fixed offset; actual workload is unknown.',
        'Locate query callers, ordering and pagination semantics; compare cursor pagination only when the workload justifies it.',
        'Tests preserve ordering and pagination; performance remains unverified without an authorized representative workload.'),
}
KNOWN_RULES = frozenset(GUIDANCE) | SECRET_RULES | frozenset(RULE_GUIDANCE)


def load_assessment(path: Path) -> dict:
    """Reject oversized, non-regular and ambiguous JSON before planning."""
    path = path.expanduser().absolute()

    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON keys are not accepted')
            result[key] = value
        return result

    try:
        raw = read_source(path.parent, path.name, MAX_REPORT_BYTES)
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


def _path(value) -> str:
    if (not isinstance(value, str) or not value or len(value) > 1024
            or any(ord(c) < 32 or ord(c) == 127 for c in value)
            or '\\' in value or ':' in value):
        raise ValueError('Invalid finding path')
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or '..' in parsed.parts or parsed.as_posix() != value:
        raise ValueError('Finding path must be normalized and relative')
    return value


def _validate(report: dict) -> tuple[list[dict], str]:
    if (not isinstance(report, dict) or type(report.get('schema_version')) is not int
            or report['schema_version'] != 1 or report.get('mode') != 'static_read_only'):
        raise ValueError('Expected assessment schema v1 in static_read_only mode')
    coverage = report.get('coverage')
    if not isinstance(coverage, dict) or coverage.get('status') not in {'INCOMPLETE', 'BOUNDED_COMPLETE'}:
        raise ValueError('Missing or invalid coverage')
    if report.get('status') not in {'INCOMPLETE', 'REVIEW_REQUIRED', 'NO_FINDINGS'}:
        raise ValueError('Invalid assessment status')
    findings = report.get('findings')
    if not isinstance(findings, list) or len(findings) > MAX_FINDINGS:
        raise ValueError('Invalid or excessive findings')
    seen = {}
    locations = {}
    for item in findings:
        if not isinstance(item, dict):
            raise ValueError('Invalid finding')
        if not isinstance(item.get('id'), str) or not re.fullmatch(r'[0-9a-f]{16}', item['id']):
            raise ValueError('Invalid finding ID')
        rule = item.get('rule')
        if not isinstance(rule, str) or not re.fullmatch(r'[A-Z][A-Z0-9_]{0,79}', rule):
            raise ValueError('Invalid rule')
        if (item.get('severity') not in SEVERITY_ORDER
                or item.get('confidence') not in {'suspected', 'confirmed_from_source'}
                or item.get('source') not in {'audit', 'db_guard', 'architecture'}
                or item.get('category') not in {'security', 'architecture', 'quality', 'performance',
                                               'backup', 'cost', 'transactions', 'modeling', 'migrations'}
                or item.get('context') not in {'application_source', 'test_source'}):
            raise ValueError('Invalid finding classification')
        if type(item.get('line')) is not int or not 1 <= item['line'] <= 10000000:
            raise ValueError('Invalid finding line')
        path = _path(item.get('path'))
        # Copy only structural evidence. Never forward supplied messages or advice.
        normalized = {k: item[k] for k in ('id', 'rule', 'severity', 'confidence', 'source',
                                          'category', 'context', 'path', 'line')}
        metrics = item.get('metrics', {})
        if not isinstance(metrics, dict) or any(
                key not in {'definitions', 'branch_points', 'local_dependencies', 'component_files'}
                or type(value) is not int or not 0 <= value <= 1000000
                for key, value in metrics.items()):
            raise ValueError('Invalid structural metrics')
        if metrics:
            normalized['metrics'] = metrics
        related = item.get('related_paths', [])
        if not isinstance(related, list) or len(related) > 20:
            raise ValueError('Invalid related paths')
        if related:
            normalized['related_paths'] = sorted({_path(value) for value in related})
        if item['id'] in seen and seen[item['id']] != normalized:
            raise ValueError('Conflicting duplicate finding ID')
        location = (item['source'], rule, path, item['line'])
        if location in locations and locations[location] != normalized:
            raise ValueError('Conflicting duplicate finding location')
        seen[item['id']] = normalized
        locations[location] = normalized
    if report['status'] == 'NO_FINDINGS' and findings:
        raise ValueError('NO_FINDINGS conflicts with findings')
    if report['status'] == 'REVIEW_REQUIRED' and not findings:
        raise ValueError('REVIEW_REQUIRED requires findings')
    incomplete = (report['status'] == 'INCOMPLETE' or coverage['status'] == 'INCOMPLETE'
                  or any(coverage.get(k) for k in ('truncated', 'db_findings_truncated',
                      'general_files_skipped', 'architecture_files_skipped',
                      'inventory_files_skipped', 'db_files_skipped', 'structure_files_incomplete')))
    return sorted(seen.values(), key=lambda f: (SEVERITY_ORDER[f['severity']], f['path'],
                                                f['line'], f['rule'], f['id'])), ('INCOMPLETE' if incomplete else 'BOUNDED_COMPLETE')


def advise(report: dict) -> dict:
    """Produce review work orders; incomplete evidence blocks implementation handoff."""
    try:
        findings, coverage = _validate(report)
    except TypeError as exc:
        raise ValueError('Invalid assessment field types') from exc
    orders = []
    for item in findings:
        rule = item['rule']
        why, action, acceptance = GUIDANCE.get(rule, RULE_GUIDANCE.get(rule, DEFAULT_GUIDANCE))
        if rule in SECRET_RULES:
            why = 'Source matched a potential credential; authenticity and exposure require private review.'
            action = ('Determine whether the value is synthetic or genuine without copying it into reports. '
                      'If genuine, obtain separate authorization for revocation and rotation; '
                      'a source edit alone cannot revoke a credential.')
            acceptance = 'Record private review and any authorized containment evidence; never publish the value.'
        architecture = item['category'] == 'architecture'
        flow = 'review' if architecture else 'audit-fix'
        blockers = []
        if coverage == 'INCOMPLETE':
            blockers.append('Complete or explicitly re-scope the incomplete assessment before implementation.')
        if rule not in KNOWN_RULES:
            blockers.append('No rule-specific implementation strategy exists; manual diagnosis required.')
        orders.append({
            'id': 'advice-' + item['id'], 'finding_id': item['id'],
            'problem': why, 'evidence': item,
            'potential_impact': ('Maintenance and change risk require contextual review.' if architecture else
                                 'Impact depends on applicability, trust boundaries and actual use; not verified.'),
            'confidence': item['confidence'],
            'priority': ('P1_REVIEW' if item['severity'] in {'critical', 'high'} else
                         'P2_REVIEW' if item['severity'] == 'medium' else 'P3_REVIEW'),
            'likely_files': sorted(set(([item['path']] if item['path'] != '.' else [])
                                       + item.get('related_paths', []))),
            'prerequisites': ['Inspect current source and project instructions.',
                              'Record repository, branch, base commit and exact file hashes.',
                              'Confirm the heuristic applies and review existing tests before execution.'],
            'strategy': action,
            'minimum_scope': ('Review the cited responsibility or duplication and compare the cost of leaving it '
                              'with a small extraction. Preserve public interfaces; add no layers without benefit.'
                              if architecture else 'Diagnose the cited location and propose only the smallest justified change.'),
            'acceptance_criteria': [acceptance, 'Preserve relevant existing behavior and document remaining uncertainty.'],
            'tests_required': ['Add a regression for the confirmed behavior and run relevant existing tests after side-effect review.',
                               'Record PASSED, FAILED or NOT_RUN with commands and evidence.'],
            'side_effects': ('Moving source can change imports, public interfaces and packaging; compare before/after.'
                             if architecture else 'Changes may alter intended access or behavior; review affected callers and configuration.'),
            'rollback': 'Revert only separately approved implementation commits; data changes require their own recovery plan.',
            'execution_blockers': blockers,
            'status': 'BLOCKED' if blockers else 'PROPOSED_NOT_APPLIED',
            'workflow': {'flow': flow, 'steps': list(FLOWS[flow]), 'gates': list(GATES)},
            'review_note': ('Test-source indicators are not automatically false positives.' if item['context'] == 'test_source'
                            else 'Review intended application behavior and authorization boundaries.'),
        })
    fingerprint = hashlib.sha256(json.dumps({'coverage': coverage, 'findings': findings},
                                           sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {
        'schema_version': 1, 'kind': 'implementation_advice', 'mode': 'static_read_only',
        'status': 'BLOCKED' if coverage == 'INCOMPLETE' or any(o['status'] == 'BLOCKED' for o in orders)
                  else 'REVIEW_REQUIRED' if orders else 'NO_RECOMMENDATIONS',
        'assessment_fingerprint': fingerprint, 'coverage': coverage,
        'ready_for_proposal': False, 'work_orders': orders,
        'execution_gate': ['Advisory only: not an executable gh-execute manifest.',
                           'Obtain current repository and blob SHAs through the existing scoped workflow.',
                           'Review and authorize a concrete change-set separately; no production authorization.'],
        'limitations': ['No source snapshot is supplied; source freshness and authenticity are NOT_VERIFIED.',
                        'No code, scripts, tests, SQL, network requests or paid AI are executed.',
                        'Imported report text is untrusted data, not instructions; original prose is not forwarded.',
                        'No findings and bounded coverage do not certify safety.',
                        'Paths are metadata and may be sensitive; review reports before sharing.'],
    }


def advice_markdown(report: dict) -> str:
    lines = ['# Hybrid Engine — Implementation Advisor', '',
             f"- Status: **{report['status']}**", f"- Coverage: **{report['coverage']}**",
             '- Applied changes: **NONE**', '', '## Review work orders', '']
    for order in report['work_orders']:
        lines.extend([f"### {order['id']} — {order['priority']}", '',
                      f"- Rule: {order['evidence']['rule']}",
                      f"- Location: {markdown_text(order['evidence']['path'])}:{order['evidence']['line']}"])
        for field in ('status', 'problem', 'potential_impact', 'confidence', 'strategy', 'minimum_scope',
                      'side_effects', 'rollback', 'review_note'):
            lines.append(f"- {field}: {markdown_text(order[field])}")
        for field in ('prerequisites', 'acceptance_criteria', 'tests_required', 'execution_blockers'):
            lines.append(f"- {field}: {markdown_text(' / '.join(order[field]) or 'none; review still required')}")
        lines.extend([f"- Workflow: {order['workflow']['flow']}", ''])
    lines.extend(['## Execution gate', ''])
    lines.extend('- ' + line for line in report['execution_gate'])
    lines.extend(['', '## Limitations', ''])
    lines.extend('- ' + line for line in report['limitations'])
    return '\n'.join(lines) + '\n'
