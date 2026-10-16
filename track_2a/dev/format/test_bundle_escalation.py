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
