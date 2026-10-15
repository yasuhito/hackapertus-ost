"""Current-root offline replay. Archived diagnostics remain historical controls."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import diagnose_format_failures as d


def test_all_19_cached_failures_preserve_rejection_and_source_contract():
    r = d.runner()
    baseline = d.load(d.OUT / 'summary.json')['failures']
    by_trace = {row['trace']: row for row in baseline}
    assert len(by_trace) == 19
    replayed = 0
    direct_codes = []
    sdk_codes = []
    for jobname in d.JOBS:
        job = d.ROOT / 'output/cscs' / jobname
        # Consume frozen source-only inputs programmatically; never print/write them.
        manifest = d.load(job / 'manifest.json')
        for index, frozen in enumerate(manifest['frozen']):
            historical = by_trace.get(d.trace(jobname, index))
            if historical is None:
                continue
            item = {k: frozen[k] for k in ('case', 'pages', 'messages', 'candidate_ids')}
            assert not any(k in item['case'] for k in ('gold', 'expected', 'label'))
            records = {}
            for role in ('parent', 'child'):
                for path in job.glob(f'70b-{index:02d}-{role}-*.json'):
                    record = d.load(path)
                    records[(role, record['number'])] = record
            expected = []
            for record in sorted(records.values(), key=lambda rr: rr['started_unix_ms']):
                for call in record['response']['choices'][0]['message'].get('tool_calls', []):
                    if call['function']['name'] != 'submit':
                        continue
                    probe = d.direct_probe(r, call['function']['arguments'], item)
                    assert probe['code'] in ('SUPPORTING_SPAN_REQUIRED', 'DUPLICATE_ID')
                    expected.append(probe['code'])
            used = []
            feedback_seen = []
            def cached(role, number, payload):
                record = records[(role, number)]
                assert payload['model'] == record.get('request_model', record['model'])
                assert payload['max_tokens'] == 256
                r.enforce_tools(payload, item['candidate_ids'], role)
                used.append((role, number))
                for message in payload['messages']:
                    if message['role'] != 'tool':
                        continue
                    try:
                        result = json.loads(message['content'])
                    except json.JSONDecodeError:
                        continue  # DUPLICATE_ID keeps the existing schema-marker gate.
                    if result.get('error') == 'SUPPORTING_SPAN_REQUIRED':
                        assert result == {'ok': False, 'error': 'SUPPORTING_SPAN_REQUIRED',
                                          'message': r.SUPPORTING_SPAN_MESSAGE}
                        feedback_seen.append(role)
                return record['response']
            with d.offline(r):
                accepted, diagnostics, sdk = r.run_b(item, r.MODELS[1], cached, seconds=45,
                                                     isolation_guard=True, strategy=manifest['strategy'])
            assert accepted is None
            assert diagnostics == expected
            assert sdk['counts'] == historical['counts'] == {'parent': 3, 'child': 2}
            assert len(used) == len(records) == 5
            assert 'parent' in feedback_seen
            direct_codes.extend(expected)
            sdk_codes.extend(diagnostics)
            replayed += 1
    assert replayed == 19
    assert sdk_codes == direct_codes
    assert direct_codes.count('SUPPORTING_SPAN_REQUIRED') == 72
    assert direct_codes.count('DUPLICATE_ID') == 4
