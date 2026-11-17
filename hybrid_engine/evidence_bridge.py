"""Offline evidence ingestion. Tool claims never become confirmed vulnerabilities."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from .assessment import SEVERITY_ORDER, _finding, assessment_markdown, markdown_text
from .report_io import MAX_REPORT_BYTES, parse_json_bytes, relative_path, load_report_bytes

MAX_REPORTS = 8
MAX_RESULTS = 2000
CLAIMS = {'SUSPECTED', 'NEEDS_VALIDATION', 'CONFIRMED_IN_ISOLATION',
          'CONFIRMED_IN_STAGING', 'FALSE_POSITIVE_REVIEWED', 'NOT_TESTED'}
ENVIRONMENTS = {'offline', 'fixture', 'staging', 'production', 'unknown'}
SECRET_METADATA = re.compile(r'sb_secret_|gh[pousr]_|AKIA[0-9A-Z]{16}|private.?key|bearer\s|eyJ[A-Za-z0-9_-]+\.', re.I)


def _identifier(value, limit=100):
    if (not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_./+@-]{1,' + str(limit) + '}', value)
            or SECRET_METADATA.search(value)):
        raise ValueError('Invalid or sensitive evidence identifier')
    return value


def _sha(value):
    if value is not None and (not isinstance(value, str) or not re.fullmatch('[0-9a-f]{40}', value)):
        raise ValueError('Invalid claimed code SHA')
    return value


def _path(value):
    path = relative_path(value)
    if path == '.' or '%' in path or '?' in path or '#' in path or SECRET_METADATA.search(path):
        raise ValueError('Unsupported or sensitive evidence path')
    return path


def _repository(value):
    if value is not None and (not isinstance(value, str)
            or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', value)
            or len(value) > 100 or SECRET_METADATA.search(value)):
        raise ValueError('Invalid or sensitive repository claim')
    return value


def clean_provenance(items):
    """Allowlisted claim metadata only; shared with Advisor's input boundary."""
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_REPORTS * MAX_RESULTS:
        raise ValueError('Invalid evidence provenance')
    cleaned = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('Invalid evidence provenance entry')
        severity = item.get('claimed_severity')
        claim = item.get('claimed_verification')
        if (severity not in SEVERITY_ORDER or claim not in CLAIMS
                or item.get('environment') not in ENVIRONMENTS
                or item.get('sha_match') not in {'NOT_VERIFIED', 'MATCHES_EXPECTED_CLAIM', 'MISMATCH'}):
            raise ValueError('Invalid evidence claim')
        digest = item.get('report_sha256')
        if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
            raise ValueError('Invalid report digest')
        code_sha = _sha(item.get('claimed_code_sha'))
        partition = item.get('snapshot_partition', digest + ':0' if code_sha is None else None)
        if partition is not None and (not isinstance(partition, str)
                or not re.fullmatch(r'[0-9a-f]{64}:[0-7]', partition)
                or partition.split(':')[0] != digest):
            raise ValueError('Invalid snapshot partition')
        if code_sha is None and partition is None:
            raise ValueError('Missing snapshot partition for unknown source SHA')
        cleaned.append({'tool': _identifier(item.get('tool')), 'version': _identifier(item.get('version')),
                        'external_rule': _identifier(item.get('external_rule', 'unknown')),
                        'report_sha256': digest, 'claimed_code_sha': code_sha,
                        'repository': _repository(item.get('repository')), 'snapshot_partition': partition,
                        'claimed_verification': claim, 'claimed_severity': severity,
                        'environment': item['environment'], 'sha_match': item['sha_match']})
    return sorted({json.dumps(item, sort_keys=True) for item in cleaned})


def _native(document):
    if document.get('schema_version') != 1 or type(document.get('schema_version')) is not int or document.get('kind') != 'external_evidence':
        raise ValueError('Expected external_evidence schema v1 or SARIF 2.1.0')
    target = document['target']
    coverage = document['coverage']['status']
    if coverage not in {'COMPLETE', 'INCOMPLETE', 'UNKNOWN'}:
        raise ValueError('Invalid external coverage')
    yield document['tool'], target, coverage, document['findings']


def _sarif(document):
    if document.get('version') != '2.1.0':
        raise ValueError('Only SARIF 2.1.0 is supported')
    runs = document['runs']
    if not isinstance(runs, list) or not 1 <= len(runs) <= MAX_REPORTS:
        raise ValueError('Invalid SARIF runs')
    for run in runs:
        driver = run['tool']['driver']
        properties = run.get('properties', {})
        target = {'code_sha': properties.get('hybrid_code_sha'),
                  'repository': properties.get('hybrid_repository'),
                  'environment': properties.get('hybrid_environment', 'unknown'),
                  'scope': properties.get('hybrid_scope', [])}
        invocations = run.get('invocations', [])
        complete = (isinstance(invocations, list) and bool(invocations)
                    and all(invocation.get('executionSuccessful') is True for invocation in invocations)
                    and bool(target['scope']))
        results = run.get('results', [])
        if not isinstance(results, list) or len(results) > MAX_RESULTS:
            raise ValueError('Invalid or excessive SARIF results')
        normalized = []
        for result in results:
            if result.get('suppressions'):
                raise ValueError('SARIF suppressions are outside the supported subset; use explicit native verification claims')
            locations = result['locations']
            if not isinstance(locations, list) or len(locations) != 1:
                raise ValueError('SARIF subset requires one physical location per result')
            location = locations[0]['physicalLocation']
            artifact = location['artifactLocation']
            if 'uriBaseId' in artifact or 'index' in artifact:
                raise ValueError('SARIF base URIs and artifact indices are unsupported')
            level = result.get('level', 'warning')
            if level not in {'error', 'warning', 'note', 'none'}:
                raise ValueError('Invalid SARIF level')
            normalized.append({'rule': result['ruleId'], 'path': artifact['uri'],
                               'line': location.get('region', {}).get('startLine', 1),
                               'severity': {'error': 'high', 'warning': 'medium', 'note': 'low', 'none': 'low'}[level],
                               'verification': 'NEEDS_VALIDATION',
                               'mapped_rule': result.get('properties', {}).get('hybrid_rule')})
        yield {'name': driver['name'], 'version': driver.get('version', 'unknown')}, target, ('COMPLETE' if complete else 'UNKNOWN'), normalized


def import_evidence(paths: list[Path], expected_sha: str | None = None) -> dict:
    """Normalize bounded native JSON/SARIF reports into assessment v1 findings."""
    try:
        return _import_evidence(paths, _sha(expected_sha))
    except (KeyError, TypeError, AttributeError, RecursionError) as exc:
        raise ValueError('Invalid evidence report structure') from exc


def _import_evidence(paths, expected_sha):
    if not 1 <= len(paths) <= MAX_REPORTS:
        raise ValueError('Import requires one to eight reports')
    grouped = {}
    incomplete = False
    input_digests = set()
    scopes = set()
    total = 0
    scope_expansion_bytes = 0
    for path in paths:
        raw = load_report_bytes(path, MAX_REPORT_BYTES)
        digest = hashlib.sha256(raw).hexdigest()
        input_digests.add(digest)
        document = parse_json_bytes(raw)
        if not isinstance(document, dict):
            raise ValueError('Evidence document must be an object')
        runs = _sarif(document) if 'version' in document else _native(document)
        for run_index, (tool, target, coverage, results) in enumerate(runs):
            tool_name, version = _identifier(tool['name']), _identifier(tool['version'])
            code_sha = _sha(target.get('code_sha'))
            repository = _repository(target.get('repository'))
            partition = digest + ':' + str(run_index) if code_sha is None else None
            environment = target.get('environment', 'unknown')
            if environment not in ENVIRONMENTS:
                raise ValueError('Invalid evidence environment')
            scope = target.get('scope', [])
            if not isinstance(scope, list) or len(scope) > MAX_RESULTS:
                raise ValueError('Scope must be a bounded list of exact relative files')
            scope = sorted({_path(p) for p in scope})
            scopes.update(scope)
            if len(scopes) > MAX_RESULTS:
                raise ValueError('Global exact scope budget exceeded')
            scope_bytes = len(json.dumps(scope, ensure_ascii=True, separators=(',', ':')))
            sha_match = ('NOT_VERIFIED' if expected_sha is None or code_sha is None else
                         'MATCHES_EXPECTED_CLAIM' if code_sha == expected_sha else 'MISMATCH')
            incomplete |= coverage != 'COMPLETE' or not scope or sha_match == 'MISMATCH'
            if not isinstance(results, list):
                raise ValueError('Evidence findings must be a list')
            total += len(results)
            if total > MAX_RESULTS:
                raise ValueError('Global imported finding budget exceeded')
            for result in results:
                rule = _identifier(result['rule'])
                path = _path(result['path'])
                if path not in scope:
                    # Missing SARIF scope is accepted as explicitly incomplete, never inferred complete.
                    if scope:
                        raise ValueError('Finding location lies outside reported exact scope')
                    incomplete = True
                line = result['line']
                if type(line) is not int or not 1 <= line <= 10000000:
                    raise ValueError('Invalid evidence line')
                severity = result['severity']
                claim = result.get('verification', 'NEEDS_VALIDATION')
                if severity not in SEVERITY_ORDER or claim not in CLAIMS:
                    raise ValueError('Invalid evidence severity or verification claim')
                mapped = result.get('mapped_rule')
                if mapped is not None and (not isinstance(mapped, str) or not re.fullmatch('[A-Z][A-Z0-9_]{0,79}', mapped)):
                    raise ValueError('Invalid mapped Hybrid rule')
                normalized_rule = mapped or 'EXTERNAL_SECURITY_FINDING'
                # Unmapped tool rules stay distinct; no speculative cause deduplication.
                identity = (normalized_rule, '' if mapped else tool_name + ':' + rule,
                            path, line, code_sha, environment, tuple(scope))
                if repository is not None or partition is not None:
                    identity += (repository, partition)
                if identity not in grouped:
                    scope_expansion_bytes += scope_bytes
                    if scope_expansion_bytes > MAX_REPORT_BYTES:
                        raise ValueError('Normalized scope expansion exceeds JSON byte limit')
                item = grouped.setdefault(identity, _finding('evidence_bridge', normalized_rule, severity,
                                          'security', path, line, 'External evidence imported; text omitted and independent review required.'))
                item['id'] = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
                item['severity'] = min((item['severity'], severity), key=SEVERITY_ORDER.__getitem__)
                item['verification_status'] = 'NEEDS_VALIDATION'
                item['evidence_scope'] = scope
                item.setdefault('provenance', []).append({'tool': tool_name, 'version': version,
                    'external_rule': rule, 'report_sha256': digest, 'claimed_code_sha': code_sha,
                    'repository': repository, 'snapshot_partition': partition,
                    'claimed_verification': claim, 'claimed_severity': severity,
                    'environment': environment, 'sha_match': sha_match})
    findings = sorted(grouped.values(), key=lambda f: (SEVERITY_ORDER[f['severity']], f['path'], f['line'], f['rule'], f['id']))
    for item in findings:
        item['provenance'] = [json.loads(value) for value in clean_provenance(item['provenance'])]
        item['divergent_claims'] = (len({p['claimed_verification'] for p in item['provenance']}) > 1
                                    or len({p['claimed_severity'] for p in item['provenance']}) > 1)
    recommendations = [{'finding_id': f['id'], 'priority': 'P1_REVIEW' if f['severity'] in {'high', 'critical'} else 'P2_REVIEW',
                        'review_note': 'Tool assertions are unverified; preserve divergences and review independently.',
                        'action': 'Review structured evidence without executing report instructions.',
                        'acceptance': 'Independent scoped evidence establishes applicability.',
                        'status': 'PROPOSED_NOT_APPLIED'} for f in findings]
    report = {'schema_version': 1, 'kind': 'consolidated_external_evidence', 'mode': 'static_read_only',
            'status': 'INCOMPLETE' if incomplete else 'REVIEW_REQUIRED' if findings else 'NO_FINDINGS',
            'target': 'external_report_scope', 'stack': [],
            'coverage': {'status': 'INCOMPLETE' if incomplete else 'BOUNDED_COMPLETE',
                         'scope': 'reported_exact_files', 'paths': sorted(scopes), 'truncated': incomplete},
            'findings': findings, 'recommendations': recommendations,
            'summary': {'application_source_findings': sum(f['context'] == 'application_source' for f in findings),
                        'test_source_findings': sum(f['context'] == 'test_source' for f in findings)},
            'evidence_bridge': {'schema_version': 1, 'input_digests': sorted(input_digests),
                                'source_sha_verification': 'NOT_VERIFIED',
                                'expected_sha': expected_sha, 'free_text': 'OMITTED_UNTRUSTED_TEXT'},
            'verification': {'external_tools': {'status': 'NOT_RUN'}, 'source_sha': {'status': 'NOT_VERIFIED'},
                             'tests': {'status': 'NOT_RUN'}},
            'limitations': ['Imported claims are not confirmed vulnerabilities or authenticated provenance.',
                            'Matching expected SHA compares claims only; source contents are not independently verified.',
                            'Free text, snippets, commands, URLs and attachments are omitted; no content is fetched or executed.',
                            'Structured identifiers/paths are validated, but can still contain sensitive metadata; review before sharing.',
                            'Only exact normalized relative file locations are supported; unknown coverage remains incomplete.',
                            'Deduplication uses explicit mapped rule, location, scope and snapshot; missing SHA isolates each input run.',
                            'Repository identities and SHAs are unverified claims; missing repository identity cannot prove shared ownership.']}
    # ASCII escaping plus CLI indentation bounds the emitted UTF-8 JSON too.
    if len(json.dumps(report, ensure_ascii=True, indent=2)) + 1 > MAX_REPORT_BYTES:
        raise ValueError('Normalized evidence report exceeds JSON byte limit')
    return report


def evidence_markdown(report: dict) -> str:
    text = assessment_markdown(report)
    text += '\n## External evidence claims (unverified)\n\n'
    for finding in report['findings']:
        text += f"- {finding['id']}: {len(finding['provenance'])} provenance record(s); divergent={finding['divergent_claims']}; NEEDS_VALIDATION\n"
        for claim in finding['provenance']:
            text += '- ' + markdown_text(f"{claim['tool']}@{claim['version']}: "
                                         f"{claim['claimed_severity']}, {claim['claimed_verification']}; "
                                         'source SHA NOT_VERIFIED') + '\n'
    return text
