"""Offline checks for the bundle runner's separate escalation phase."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


spec = importlib.util.spec_from_file_location('bundle_runner', Path(__file__).parents[1] / 'eval/run_bundle.py')
bundle_runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle_runner)


def test_bundle_escalation_merges_only_valid_booklet_retries(tmp_path, monkeypatch):
    job = tmp_path / 'job'
    job.mkdir()
    rows = [{'id': name, 'label': 1} for name in ('recover', 'fail', 'reference')]
    (job / '70b-canonical.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows))
    for index, row in enumerate(rows):
        (job / f'70b-{index:02d}-case.json').write_text(json.dumps({
            'case_id': row['id'], 'error': 'NO_ACCEPTED_SUBMIT', 'output_valid': False, 'case_wall_ms': 100}))
    manifest = {'frozen': [{'case': {'id': row['id'], ('reference' if row['id'] == 'reference' else 'booklet'): {}}} for row in rows]}

    def prepare(core, bundle, **kwargs):
        assert kwargs == {'strategy': 'R', 'selection': 'vote_pages', 'case_ids': {'recover', 'fail'}}
        return {'frozen': [1, 2]}, []

    def run(core, transport, second_job, second_manifest):
        assert second_job == tmp_path / 'job-escalation'
        second_job.mkdir()
        physical = second_job / 'physical'
        physical.mkdir()
        (physical / '1-result.json').write_text(json.dumps({'usage_known': True, 'usage': {'total_tokens': 200}, 'http_status': 200}))
        for index, name in enumerate(('recover', 'fail')):
            (second_job / f'70b-{index:02d}-case.json').write_text(json.dumps({
                'case_id': name, 'output_valid': name == 'recover', 'prediction': {'id': name, 'label': 2}}))
        return {'wall_seconds': 2, 'generation_requests': 2}

    monkeypatch.setattr(bundle_runner, 'prepare', prepare)
    monkeypatch.setattr(bundle_runner, 'run', run)
    escalation = bundle_runner.escalate(None, SimpleNamespace(), job, tmp_path, manifest, '70b')
    assert bundle_runner.load_jsonl(escalation['predictions']) == [
        {'id': 'recover', 'label': 2}, {'id': 'fail', 'label': 1}, {'id': 'reference', 'label': 1}]
    assert escalation['escalated_cases'] == 2 and escalation['escalation_recovered'] == 1
    (job / 'manifest.json').write_text('{}')
    (job / 'physical').mkdir()
    (job / 'physical/0-result.json').write_text(json.dumps({'usage_known': True, 'usage': {'total_tokens': 100}, 'http_status': 200}))
    official = {'official_report': {'tasks': {'A': {'macro_f1': 0}, 'B': {'macro_f1': 0}}}, 'classification_objective': {'value': 0}}
    summary = {'wall_seconds': 1, 'models': {'70b': {'diagnostic_counts': {}}}}
    metrics = bundle_runner.metrics(job, summary, official, [], escalation=escalation)
    assert metrics['known_tokens'] == 300 and metrics['physical_requests'] == 2
    assert metrics['fallbacks'] == 4  # Three original failures plus one failed retry.
    assert metrics['wall_seconds'] == 3 and metrics['escalation_recovered'] == 1


def test_bundle_recheck_uses_accepted_context_and_merges_only_cited_contradictions(tmp_path, monkeypatch):
    import run_comparison as core
    job = tmp_path / 'job'
    job.mkdir()
    names = ('flip', 'empty', 'neutral', 'invalid', 'escalated', 'reference', 'fallback', 'entails')
    rows = [{'id': name, 'label': 0 if name == 'entails' else 1} for name in names]
    frozen = []
    for index, row in enumerate(rows):
        frozen.append({'case': {'id': row['id'], 'reference' if row['id'] == 'reference' else 'booklet': {}},
                       'pages': [], 'messages': [{'role': 'system', 'content': 'original'}, {'role': 'user', 'content': row['id']}],
                       'candidate_ids': ['span'], 'schema_sha256': 'schema'})
        (job / f'70b-{index:02d}-case.json').write_text(json.dumps({
            'case_id': row['id'], 'output_valid': row['id'] not in ('fallback', 'escalated'), 'prediction': row}))
    (job / '70b-canonical.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows))
    escalation_job = tmp_path / 'job-escalation'
    escalation_job.mkdir()
    full = {**frozen[4], 'messages': [{'role': 'system', 'content': 'full'}, {'role': 'user', 'content': 'escalated context'}]}
    (escalation_job / 'manifest.json').write_text(json.dumps({'frozen': [full]}))
    canonical = job / 'canonical-escalated.jsonl'
    canonical.write_text((job / '70b-canonical.jsonl').read_text())
    escalation = {'job': escalation_job, 'cases': [{'case_id': 'escalated', 'output_valid': True, 'prediction': rows[4]}],
                  'predictions': canonical}
    manifest = {'strategy': 'R', 'frozen': frozen}

    def run(core, transport, second_job, second_manifest):
        assert second_job == tmp_path / 'job-recheck'
        second_job.mkdir()
        items = second_manifest['frozen']
        assert [item['case']['id'] for item in items] == list(names[:5])
        assert items[4]['messages'][1]['content'] == 'escalated context'
        assert items[4]['messages'][0]['content'].startswith('full\n\nContradiction check.')
        assert items[0]['messages'][0]['content'].startswith('original\n\nContradiction check.')
        assert items[0]['messages_sha256'] == core.legacy.digest(core.legacy.encode(items[0]['messages']))
        for index, item in enumerate(items):
            name = item['case']['id']
            prediction = {'id': name, 'label': 1 if name == 'neutral' else 2,
                          'evidence': [] if name == 'empty' else [{'span_id': 'span'}]}
            (second_job / f'70b-{index:02d}-case.json').write_text(json.dumps({
                'case_id': name, 'output_valid': name != 'invalid', 'prediction': prediction}))
        physical = second_job / 'physical'
        physical.mkdir()
        (physical / '0-result.json').write_text(json.dumps({'usage_known': True, 'usage': {'total_tokens': 200}, 'http_status': 200}))
        return {'generation_requests': 5, 'wall_seconds': 2}

    monkeypatch.setattr(bundle_runner, 'run', run)
    checked = bundle_runner.recheck(core, SimpleNamespace(), job, manifest, '70b', escalation)
    assert checked['rechecked_cases'] == 5 and checked['recheck_flipped'] == 2
    merged = bundle_runner.load_jsonl(checked['predictions'])
    assert [row['label'] for row in merged] == [2, 1, 1, 1, 2, 1, 1, 0]
    assert frozen[0]['messages'][0]['content'] == 'original'
    for index in range(len(rows)):
        path = job / f'70b-{index:02d}-case.json'
        case = json.loads(path.read_text())
        case['case_wall_ms'] = 100
        path.write_text(json.dumps(case))
    (job / 'manifest.json').write_text('{}')
    (job / 'physical').mkdir()
    official = {'official_report': {'tasks': {'A': {'macro_f1': 0}, 'B': {'macro_f1': 0}}}, 'classification_objective': {'value': 0}}
    summary = {'models': {'70b': {'diagnostic_counts': {}}}}
    metrics = bundle_runner.metrics(job, summary, official, [], recheck=checked)
    assert metrics['known_tokens'] == 200 and metrics['physical_requests'] == 1
    assert metrics['rechecked_cases'] == 5 and metrics['recheck_flipped'] == 2
