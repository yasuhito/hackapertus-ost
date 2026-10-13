"""Fictional, offline usage fixtures. No model imports or inference."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import usage


class Usage(unittest.TestCase):
    def fixture(self, job, repair=True):
        manifest = {'strategy': 'C', 'role_models': usage.MODELS,
                    'parent_completion_limit': 3, 'child_completion_limit': 2,
                    'frozen': [{'case': {'id': 'fictional-train'}}, {'case': {'id': 'fictional-test'}}]}
        state = {'version': 'format-1', 'manifest_sha256': usage.digest(manifest),
                 'blocked': False, 'reserved_tokens': 0, 'attempts': {}, 'cases': {},
                 'tokens': 0, 'requests': 0}
        records = {}
        for index in range(2):
            for role, count in [('parent', 3 if repair else 2), ('child', 2 if repair else 1)]:
                for number in range(count):
                    name = f'fictional-{index}-{role}-{number}.json'
                    record = {'role': role, 'case_index': index, 'number': number,
                              'request_model': usage.MODELS[role], 'usage_known': True,
                              'usage_valid': True, 'safe': True, 'generation_requests': 1,
                              'usage': {'prompt_tokens': 10, 'completion_tokens': 2, 'total_tokens': 12},
                              'response': {'opaque': 'fictional non-ASCII café'}}
                    records[name] = record
                    state['tokens'] += 12
                    state['requests'] += 1
        summary = {'actual_total_tokens': state['tokens'], 'generation_requests': state['requests']}
        split = {'train': ['fictional-train'], 'test': ['fictional-test']}
        self.save(job, manifest, state, records)
        return manifest, state, records, summary, split

    def save(self, job, manifest, state, records):
        for name, record in records.items():
            (job / name).write_text(json.dumps(record))
            state['attempts'][name] = usage.digest(record)
        (job / 'manifest.json').write_text(json.dumps(manifest))
        (job / 'state.json').write_text(json.dumps(state))

    def test_legacy_serialization(self):
        import hashlib
        self.assertEqual(usage.digest({'b': 1, 'a': 'café'}),
                         hashlib.sha256('{"a": "café", "b": 1}'.encode()).hexdigest())
        with self.assertRaises(ValueError):
            usage.digest({'x': float('nan')})

    def test_repair_is_subset_not_third_role(self):
        with tempfile.TemporaryDirectory() as directory:
            job = Path(directory)
            _, _, _, summary, split = self.fixture(job)
            result = usage.job_usage(job, split, summary)
            totals = result['totals']
            self.assertEqual(totals['parent']['total_tokens'], 72)
            self.assertEqual(totals['child']['total_tokens'], 48)
            self.assertEqual(totals['repair_window']['total_tokens'], 48)
            self.assertEqual(totals['repair_window']['calls'], 4)
            self.assertEqual(totals['parent']['total_tokens'] + totals['child']['total_tokens'], summary['actual_total_tokens'])
            self.assertEqual(result['splits']['train']['parent']['total_tokens'], 36)
            self.assertEqual(result['splits']['test']['child']['total_tokens'], 24)
            self.fixture(job, repair=False)
            self.assertEqual(usage.job_usage(job, split, {'actual_total_tokens': 72, 'generation_requests': 6})['totals']['repair_window'], dict.fromkeys(usage.FIELDS, 0))

    def test_tampered_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            job = Path(directory)
            _, _, records, summary, split = self.fixture(job)
            name = next(iter(records))
            records[name]['usage']['prompt_tokens'] = 999
            (job / name).write_text(json.dumps(records[name]))
            with self.assertRaisesRegex(ValueError, 'RECORD_CHANGED'):
                usage.job_usage(job, split, summary)

    def test_invalid_metadata_and_usage_fail_closed(self):
        changes = [('role', 'other'), ('number', 3), ('number', -1), ('number', True),
                   ('case_index', 2), ('case_index', True), ('usage_known', False),
                   ('usage_valid', False), ('safe', False), ('request_model', usage.MODELS['child']),
                   ('generation_requests', True), ('usage', None),
                   ('usage', {'prompt_tokens': True, 'completion_tokens': 2, 'total_tokens': 3}),
                   ('usage', {'prompt_tokens': -1, 'completion_tokens': 2, 'total_tokens': 1}),
                   ('usage', {'prompt_tokens': 10.0, 'completion_tokens': 2, 'total_tokens': 12}),
                   ('usage', {'prompt_tokens': 10, 'completion_tokens': 2, 'total_tokens': 13}),
                   ('usage', {'completion_tokens': 2, 'total_tokens': 12})]
        for key, value in changes:
            with self.subTest(key=key, value=value), tempfile.TemporaryDirectory() as directory:
                job = Path(directory)
                manifest, state, records, summary, split = self.fixture(job)
                records[next(iter(records))][key] = value
                self.save(job, manifest, state, records)
                with self.assertRaises(ValueError):
                    usage.job_usage(job, split, summary)

    def test_child_cap_and_duplicate_slot(self):
        for duplicate in (False, True):
            with tempfile.TemporaryDirectory() as directory:
                job = Path(directory)
                manifest, state, records, summary, split = self.fixture(job)
                name = 'fictional-0-child-0.json'
                if duplicate:
                    records['duplicate.json'] = copy.deepcopy(records[name])
                else:
                    records[name]['number'] = 2
                self.save(job, manifest, state, records)
                with self.assertRaisesRegex(ValueError, 'DUPLICATE_SLOT|REQUEST_NUMBER'):
                    usage.job_usage(job, split, summary)

    def test_reconcile_state_and_summary(self):
        for target, key in [('state', 'tokens'), ('state', 'requests'),
                            ('summary', 'actual_total_tokens'), ('summary', 'generation_requests')]:
            with self.subTest(target=target, key=key), tempfile.TemporaryDirectory() as directory:
                job = Path(directory)
                manifest, state, records, summary, split = self.fixture(job)
                (state if target == 'state' else summary)[key] += 1
                self.save(job, manifest, state, records)
                with self.assertRaisesRegex(ValueError, 'LEDGER_MISMATCH'):
                    usage.job_usage(job, split, summary)


if __name__ == '__main__':
    unittest.main()
