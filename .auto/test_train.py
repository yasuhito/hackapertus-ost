"""Offline TRAIN protocol controls. Fictional records plus saved TRAIN-only parity."""
import copy
from datetime import datetime, timedelta
import io
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tarfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import train_run as t
import train_results as results
import usage
sys.path.insert(0, str(t.ROOT / 'track_2a/dev/format'))
import run_comparison as runner
import test_comparison as fixtures


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('network or credentials forbidden')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(runner.legacy.c, 'read_key', forbidden)


def test_selection_order_parity_and_validation():
    m = {'frozen': [{'case': {'id': str(i)}, 'pages': ['opaque'], 'messages': ['unchanged']} for i in range(54)]}
    baseline = copy.deepcopy(m)
    selected = runner.select_cases(m, ['17', '2', '50'])
    assert selected['selected_case_ids'] == ['2', '17', '50']
    assert selected['selected_case_count'] == 3
    assert selected['frozen'] == [baseline['frozen'][i] for i in (2, 17, 50)]
    for bad in ([], ['2', '2'], ['unknown'], '2', [2], None, {}):
        with pytest.raises(runner.Stop):
            runner.select_cases(copy.deepcopy(baseline), bad)


def test_prepare_default_manifest_identical(monkeypatch):
    m = fixtures.manifest('A')
    m['sources'] = {}
    # prepare's selection must be absent, not merely all54 in a new field.
    monkeypatch.setattr(runner.legacy, 'prepare', lambda: copy.deepcopy(m))
    full = runner.prepare('A')
    assert len(full['frozen']) == 54
    assert 'selected_case_ids' not in full and 'selected_case_count' not in full


@pytest.mark.parametrize('count', [1, 2, 3, 36, 54])
def test_schedule_summary_counters(tmp_path, count):
    m = fixtures.manifest('A')
    m['frozen'] = m['frozen'][:count]
    job = tmp_path / 'job'
    runner.initialize(job, m)
    fake = fixtures.Fake()
    summary = runner.run(job, m, fake)
    assert len(fake.calls) == count * 2  # One valid A response for each of two models.
    assert summary['generation_requests'] == count * 2
    assert summary['actual_total_tokens'] == count * 200
    for model in runner.MODELS:
        assert summary['models'][model]['cases'] == count
    assert len((job / '70b-canonical.jsonl').read_text().splitlines()) == count


def window():
    return {'timezone': 'Asia/Tokyo', 'approved_candidates': ['v14', 'v15'], 'max_new_candidates': 2,
            'max_attempts_per_candidate': 3, 'retry_http_status': 504, 'retry_wait_seconds': 60,
            'baseline_version': 'v5', 'trials': t.TRIALS, 'approved': True, 'stop_on_execution_error': True,
            'started_at': '2026-10-14T14:14:17+09:00', 'candidate_start_before': '2026-10-14T15:44:17+09:00',
            'soft_finish_by': '2026-10-14T16:14:17+09:00'}


def test_window_boundaries():
    w = window()
    start = datetime.fromisoformat(w['started_at'])
    cutoff = datetime.fromisoformat(w['candidate_start_before'])
    for v in t.VERSIONS:
        t.validate_window(v, w, start)
        t.validate_window(v, w, cutoff - timedelta(microseconds=1))
        for bad in (start - timedelta(seconds=1), cutoff, cutoff + timedelta(minutes=29), start.replace(tzinfo=None)):
            with pytest.raises(ValueError):
                t.validate_window(v, w, bad)
    for key, value in [('approved', False), ('retry_http_status', 500), ('retry_wait_seconds', 0),
                       ('max_attempts_per_candidate', 4), ('trials', {'cases': 54, 'repeats': 5, 'configs': 1}),
                       ('max_new_candidates', True)]:
        with pytest.raises(ValueError):
            t.validate_window('v14', {**w, key: value}, start)


@pytest.fixture
def history(tmp_path, monkeypatch):
    monkeypatch.setattr(t, 'OUT', tmp_path)
    control = tmp_path / 'control.json'
    control.write_text('{}')
    monkeypatch.setattr(t, 'CONTROL', control)
    return tmp_path


def failed(version='v14', attempt=1, status='STOP504', http=504, ended=100):
    record = {'candidate': version, 'attempt': attempt, 'candidate_sha256': 'candidate', 'status': status,
              'ended_at': ended, 'protocol_sha256': t.old.digest(t.CONTROL.read_bytes())}
    t.exclusive(t.attempt_path(version, attempt), record)
    t.exclusive(t.OUT / t.job_name(version, attempt, 2) / 'STOP.json', {'status': 'STOP', 'http_status': http})
    return record


def test_retry_whole_new_batch_wait_and_fences(history):
    assert t.validate_history('v14', 1, 'candidate', 100) == 0
    failed()
    assert t.validate_history('v14', 2, 'candidate', 100) == 60
    assert t.validate_history('v14', 2, 'candidate', 159) == 1
    assert t.validate_history('v14', 2, 'candidate', 160) == 0
    failed(attempt=2, ended=170)
    assert t.validate_history('v14', 3, 'candidate', 200) == 30
    with pytest.raises(ValueError):
        t.validate_history('v14', 4, 'candidate', 1000)
    with pytest.raises(ValueError):
        t.validate_history('v14', 3, 'different', 1000)
    assert (history / 'prompt-C-v14-a1-r2/STOP.json').exists()
    (history / 'prompt-C-v14-a3-r5-inflight.json').write_text('{}')
    with pytest.raises(ValueError, match='PREEXISTING'):
        t.validate_history('v14', 3, 'candidate', 1000)


@pytest.mark.parametrize('status,http', [('OTHER_STOP', 504), ('STOP504', 500), ('completed', 504), ('inflight', 504)])
def test_no_non504_or_quality_retry(history, status, http):
    failed(status=status, http=http)
    with pytest.raises(ValueError):
        t.validate_history('v14', 2, 'candidate', 200)


def test_no_retry_completed_five_or_skipping_attempt(history):
    failed()
    for i in range(1, 6):
        t.exclusive(history / t.job_name('v14', 1, i) / 'summary.json', {'status': 'completed'})
    with pytest.raises(ValueError):
        t.validate_history('v14', 2, 'candidate', 200)
    with pytest.raises((OSError, ValueError)):
        t.validate_history('v14', 3, 'candidate', 200)


@pytest.mark.parametrize('status', ['OTHER_STOP', 'STOP504', 'inflight', 'grading'])
def test_v15_blocked_after_fatal_or_exhaustion(history, status):
    failed(status=status)
    with pytest.raises(ValueError, match='V14'):
        t.validate_history('v15', 1, 'candidate', 200)


def test_v15_after_completed_quality_batch(history):
    failed(status='completed')
    for i in range(1, 6):
        t.exclusive(history / t.job_name('v14', 1, i) / 'summary.json', {'status': 'completed'})
    assert t.validate_history('v15', 1, 'candidate', 200) == 0


def test_metadata_fresh_scope_and_independence(tmp_path, monkeypatch):
    monkeypatch.setattr(t, 'PROMPTS', tmp_path)
    (tmp_path / 'v0-system.txt').write_text('old')
    monkeypatch.setattr(t.old, 'prior_prompt_hash', lambda version: 'oldhash')
    candidate = b'independent'
    meta = {'version': 'v14', 'proposed_trials': t.TRIALS, 'approved_trials': t.TRIALS,
            'inference_approved': True, 'approval_scope': {'candidate': 'v14', **t.TRIALS},
            'baseline_prompt_sha256': t.V5, 'candidate_prompt_sha256': t.old.digest(candidate)}
    t.validate_metadata('v14', meta, candidate)
    for key, value in [('version', 'v13'), ('inference_approved', False), ('approved_trials', {'cases': 54}),
                       ('approval_scope', {'candidate': 'v13', **t.TRIALS}), ('baseline_prompt_sha256', 'wrong')]:
        with pytest.raises(ValueError):
            t.validate_metadata('v14', {**meta, key: value}, candidate)
    (tmp_path / 'v15-system.txt').write_bytes(candidate)
    with pytest.raises(ValueError, match='DUPLICATE'):
        t.validate_metadata('v14', meta, candidate)


def test_literal_gate_not_strict_replacement():
    r = {'gain': .025, 'noise': .017, 'repeats': [{'F1_A': .6, 'F1_B': .75, 'valid': 36, 'fallback': 0, 'safe': True, 'Hit_A': .5}] * 5}
    assert all(results.gates(r).values())
    assert not r['gain'] >= r['noise'] + .02
    assert not results.gates({**r, 'gain': .017})['literal_gain']
    assert not results.gates({**r, 'repeats': [{**r['repeats'][0], 'fallback': 1}] * 5})['canonical_validity']


def test_baseline_no_inference_grader_or_test_record_reads(monkeypatch):
    monkeypatch.setattr(t, 'verify_protocol', lambda **kwargs: None)
    original = Path.read_text
    opened = []
    def read(path, *args, **kwargs):
        text = str(path)
        assert '/test-' not in text and not text.endswith('70b-canonical.jsonl')
        opened.append(text)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_text', read)
    monkeypatch.setattr(results, 'import_module', lambda *a: pytest.fail('baseline imported grader'))
    saved, predictions, records, attributed = results.reference()
    assert saved['Q_mean'] == t.BASE_Q
    assert len(predictions) == len(records) == len(attributed) == 5
    assert all(len(x) == 36 for x in predictions)
    # Assert every individual response opened belongs to a selected TRAIN index.
    ids = set(t.train_split()[0])
    for repeat in range(1, 6):
        m = t.load(t.OUT / f'prompt-C-v5-r{repeat}/manifest.json')
        for path in opened:
            if f'/prompt-C-v5-r{repeat}/70b-' in path:
                index = int(Path(path).name.split('-')[1])
                assert m['frozen'][index]['case']['id'] in ids


def test_saved_train_usage_role_and_digest_tampering(tmp_path):
    ids = t.train_split()[0]
    job = t.OUT / 'prompt-C-v5-r1'
    manifest = t.load(job / 'manifest.json')
    state = t.load(job / 'state.json')
    selected = {i for i, item in enumerate(manifest['frozen']) if item['case']['id'] in ids}
    for category in ('cases', 'attempts'):
        for name in state[category]:
            if int(name.split('-')[1]) in selected:
                shutil.copyfile(job / name, tmp_path / name)
    (tmp_path / 'state.json').write_text(json.dumps(state))
    results.selected_records(tmp_path, manifest, ids)
    name = next(n for n in state['attempts'] if int(n.split('-')[1]) in selected)
    record = t.load(tmp_path / name)
    for key, bad in [('role', 'third'), ('source_sha256', 'wrong'), ('usage_known', False), ('request_model', 'wrong')]:
        changed = {**record, key: bad}
        (tmp_path / name).write_text(json.dumps(changed))
        state['attempts'][name] = usage.digest(changed)
        (tmp_path / 'state.json').write_text(json.dumps(state))
        with pytest.raises(ValueError):
            results.selected_records(tmp_path, manifest, ids)


def test_paired_bootstrap_identical_and_reproducible():
    ids = ['fiction-A', 'fiction-B']
    pred = {id: {'label': 0} for id in ids}
    gold = {id: {'label': 0} for id in ids}
    args = ([pred] * 5, [pred] * 5, gold, ids, [ids], lambda p: (p['label'], None))
    assert results.paired_interval(*args) == [0., 0.]
    assert results.paired_interval(*args) == [0., 0.]


def test_real_offline_cli_prepare36_saved_v5_parity(tmp_path):
    """No new candidates or approval writes. Only v5 source assembly with selected inputs."""
    archive = subprocess.check_output(['git', 'archive', 'HEAD', 'track_2a/src', 'track_2a/dev/cscs', 'track_2a/dev/format'], cwd=t.ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(tmp_path, filter='data')
    (tmp_path / t.RUNNER).write_bytes((t.ROOT / t.RUNNER).read_bytes())
    (tmp_path / 'booklets').mkdir()
    (tmp_path / 'output/cscs/tmp').mkdir(parents=True)
    historical = t.load(t.OUT / 'prompt-C-v5-r5-provenance.json')['pdf_mapping']
    mapping = {}
    for original, local in t.load(t.OUT / 'preparation-provenance.json')['pdf_mapping'].items():
        saved = historical[original]
        target = tmp_path / 'booklets' / Path(saved).name
        shutil.copyfile(t.ROOT / local, target)
        mapping[saved] = str(target)
    ids = t.train_split()[0]
    (tmp_path / 'ids.json').write_text(json.dumps(ids))
    env = t.old.workspace_env(tmp_path, False)
    for key in list(env):
        if any(x in key.upper() for x in ('KEY', 'TOKEN', 'SECRET', 'AUTH', 'PASSWORD', 'BASE_URL')):
            env.pop(key)
    command = [t.old.PYTHON, '-B', t.RUNNER, '--prepare-only', '--strategy', 'C', '--case-ids-file', 'ids.json']
    result = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['prepared_cases'] == 36
    export = "import runpy,json; m=runpy.run_path('track_2a/dev/format/run_comparison.py'); m['legacy'].c.protect(); open('snapshot.json','w').write(json.dumps(m['prepare']('C',json.load(open('ids.json')))))"
    subprocess.run([t.old.PYTHON, '-B', '-c', export], cwd=tmp_path, env=env, check=True, capture_output=True, text=True)
    m = t.load(tmp_path / 'snapshot.json')
    t.audit(m, t.load(t.OUT / 'prompt-C-v5-r5/manifest.json'), mapping,
            t.old.digest((t.ROOT / t.RUNNER).read_bytes()), (t.PROMPTS / 'v5-system.txt').read_text())
    assert len(m['frozen']) == 36
    assert not list((tmp_path / 'output/cscs').glob('format-*'))


def test_first_post_shim_gates_actual_clock_not_later_calls(tmp_path, monkeypatch):
    path = tmp_path / 'runner.py'
    path.write_text('''class Stop(Exception): pass
class Transport:
    def request(self,*args,**kwargs): print('fictional confirmed request')
def main():
    Transport().request()
    Transport().request()
''')
    wpath = tmp_path / 'window.json'
    monkeypatch.setattr(t, 'WINDOW', wpath)
    monkeypatch.setattr(t, 'RUNNER', str(path))
    now = datetime.now().astimezone()
    def attempt(start, cutoff, retry_after=0):
        wpath.write_text(json.dumps({'started_at': start.isoformat(), 'candidate_start_before': cutoff.isoformat()}))
        return subprocess.run(t.guarded_command(tmp_path / 'fake-job', True, retry_after), capture_output=True, text=True)
    result = attempt(now - timedelta(seconds=10), now + timedelta(seconds=10))
    assert result.returncode == 0 and result.stdout.count('fictional confirmed request') == 2
    for start, cutoff, retry_after in [(now - timedelta(seconds=20), now - timedelta(seconds=1), 0),
                                       (now + timedelta(seconds=10), now + timedelta(seconds=20), 0),
                                       (now - timedelta(seconds=10), now + timedelta(seconds=10), now.timestamp() + 60)]:
        result = attempt(start, cutoff, retry_after)
        assert result.returncode != 0 and 'fictional confirmed request' not in result.stdout
    assert '-c' not in t.guarded_command(tmp_path / 'fake-job', False)


def test_train_scoring_uses_only_train_references_and_quality_failure_is_check_only(tmp_path, monkeypatch):
    # Entirely fictional candidate scoring. No grading of the real saved baseline.
    monkeypatch.setattr(results, 'OUT', tmp_path)
    control = tmp_path / 'control.json'
    control.write_text('{}')
    monkeypatch.setattr(t, 'CONTROL', control)
    ids = [f'fiction-{i}-{task}' for i in range(18) for task in ('A', 'B')]
    monkeypatch.setattr(t, 'train_split', lambda: (ids, [ids[i:i + 2] for i in range(0, 36, 2)]))
    predictions = {id: {'id': id, 'label': 0, 'metrics': {'input_tokens': 1, 'output_tokens': 1}} for id in ids}
    records = {id: {'prediction': predictions[id], 'output_valid': True, 'error': None, 'case_wall_ms': 3, 'api_wait_ms': 2} for id in ids}
    saved = {'Q_mean': t.BASE_Q, 'Q_temporal_detectable_difference': 0,
             'repeats': [{'Q': t.BASE_Q, 'F1_A': .8, 'F1_B': .85, 'Hit_A': .5}] * 5}
    monkeypatch.setattr(results, 'reference', lambda: (saved, [predictions] * 5, [records] * 5, []))
    ops = [{'repeat': i, 'usage': {g: {**dict.fromkeys(usage.FIELDS, 0), 'API_wait_seconds': 0} for g in usage.GROUPS},
            'command_seconds': 1, 'API_wait_seconds': .1} for i in range(1, 6)]
    monkeypatch.setattr(results, 'completed', lambda *args, **kwargs: ([predictions] * 5, [records] * 5, ops))
    ref = tmp_path / 'hillclimb-v5-analysis'
    ref.mkdir()
    for suffix in ('expected', 'cases'):
        (ref / f'train-{suffix}.jsonl').write_text(''.join(json.dumps({'id': id, 'label': 0}) + '\n' for id in ids))
    evaluator = tmp_path / 'evaluate.py'
    evaluator.write_text('fictional scorer')
    monkeypatch.setattr(results, 'OFFICIAL', tmp_path)
    class Grader:
        calls = 0
        @staticmethod
        def grade(repo, python, preds, expected, cases):
            Grader.calls += 1
            for path in (preds, expected, cases):
                assert set(results.by_id(path, ids)) == set(ids)
                assert 'train-grade-' in str(path.parent) and 'workspace' not in str(path)
            return {'official_commit': results.COMMIT, 'official_evaluate_sha256': t.old.digest(evaluator.read_bytes()),
                    'official_report': {'tasks': {'A': {'macro_f1': .6}, 'B': {'macro_f1': .75}}},
                    'primary_evidence_objective': {'value': .5}, 'safe_passes': {'A': True, 'B': True}}
    class Official:
        @staticmethod
        def label_of(pred): return pred['label'], None
    monkeypatch.setattr(results, 'import_module', lambda name, path: Grader if name == 'train_grader' else Official)
    result = results.compute('v14', 1, True)
    assert Grader.calls == 5
    assert not result['gates']['literal_gain']
    results.report(result)  # Measurement reports quality failure without execution failure.
    with pytest.raises(ValueError, match='CHECKS_FAILED'):
        results.report(result, check=True)
    assert results.compute('v14', 1, False) == result
    assert Grader.calls == 5  # --check is read-only, no grading.


def test_control_source_runtime_and_head_checkpoint(tmp_path, monkeypatch):
    prompt = (t.PROMPTS / 'v5-system.txt').read_text()
    monkeypatch.setattr(t, 'ROOT', tmp_path)
    prompts = tmp_path / 'prompts'
    prompts.mkdir()
    monkeypatch.setattr(t, 'PROMPTS', prompts)
    (prompts / 'v5-system.txt').write_text(prompt)
    predict = tmp_path / 'track_2a/src/predict.py'
    predict.parent.mkdir(parents=True)
    predict.write_text('SYSTEM = ' + repr(prompt) + '\n')
    runner_path = tmp_path / t.RUNNER
    runner_path.parent.mkdir(parents=True)
    runner_path.write_text('frozen selection protocol')
    control = tmp_path / 'control.json'
    monkeypatch.setattr(t, 'CONTROL', control)
    monkeypatch.setattr(t, 'train_split', lambda: (['fiction'], []))
    monkeypatch.setattr(t, 'protocol_paths', lambda: [predict, runner_path])
    monkeypatch.setattr(t, 'candidate_payload', lambda version: {})
    monkeypatch.setattr(t.old, 'verify_candidate_artifacts', lambda *args: None)
    monkeypatch.setattr(t, 'runtime_fingerprint', lambda: {'fictional-runtime': 'sha'})
    control.write_text(json.dumps({'version': 'train36x5-1', 'case_ids': ['fiction'],
                                  'runner_sha256': t.old.digest(runner_path.read_bytes()),
                                  'files': t.hashes([predict, runner_path]), 'runtime': {'fictional-runtime': 'sha'}}))
    t.verify_protocol()
    def git_show(command, **kwargs):
        return (tmp_path / command[-1].removeprefix('HEAD:')).read_bytes()
    monkeypatch.setattr(t.subprocess, 'check_output', git_show)
    t.verify_protocol(checkpoint=True)
    monkeypatch.setattr(t.subprocess, 'check_output', lambda *args, **kwargs: b'old source')
    with pytest.raises(ValueError, match='HEAD_CHECKPOINT'):
        t.verify_protocol(checkpoint=True)
    monkeypatch.setattr(t, 'runtime_fingerprint', lambda: {'fictional-runtime': 'changed'})
    with pytest.raises(ValueError, match='RUNTIME_CHANGED'):
        t.verify_protocol()
    monkeypatch.setattr(t, 'runtime_fingerprint', lambda: {'fictional-runtime': 'sha'})
    runner_path.write_text('changed source')
    with pytest.raises(ValueError, match='PROTOCOL_CHANGED'):
        t.verify_protocol()


def test_audit_refuses_non_system_input_protocol_changes():
    baseline = t.load(t.OUT / 'prompt-C-v5-r5/manifest.json')
    ids = set(t.train_split()[0])
    manifest = copy.deepcopy(baseline)
    manifest['frozen'] = [x for x in manifest['frozen'] if x['case']['id'] in ids]
    manifest['selected_case_ids'] = [x['case']['id'] for x in manifest['frozen']]
    manifest['selected_case_count'] = 36
    key = next(k for k in manifest['sources'] if k.endswith(t.RUNNER))
    manifest['sources'][key] = 'approved-new-runner'
    mapping = {x['case']['booklet']['path']: x['case']['booklet']['path'] for x in manifest['frozen'] if 'booklet' in x['case']}
    prompt = (t.PROMPTS / 'v5-system.txt').read_text()
    def audit(m): t.audit(m, baseline, mapping, 'approved-new-runner', prompt)
    audit(manifest)
    for key in ('pages', 'candidate_ids', 'schema_sha256', 'messages_sha256'):
        changed = copy.deepcopy(manifest)
        changed['frozen'][0][key] = 'changed'
        with pytest.raises(ValueError): audit(changed)
    changed = copy.deepcopy(manifest)
    changed['frozen'][0]['messages'][1]['content'] += 'changed'
    with pytest.raises(ValueError): audit(changed)
    for key in ('request_limit', 'token_budget', 'role_models'):
        changed = copy.deepcopy(manifest)
        changed[key] = 'changed'
        with pytest.raises(ValueError): audit(changed)


def test_orchestrator_fresh_entire_retry_no_prefix_reuse(history, monkeypatch):
    clock = [100.]
    monkeypatch.setattr(t.time, 'time', lambda: clock[0])
    sleeps = []
    def sleep(seconds):
        sleeps.append(seconds)
        clock[0] += seconds
    monkeypatch.setattr(t.time, 'sleep', sleep)
    monkeypatch.setattr(t, 'check_window', lambda version: None)
    monkeypatch.setattr(t, 'verify_protocol', lambda **kwargs: {'runner_sha256': 'frozen-runner'})
    monkeypatch.setattr(t, 'candidate_payload', lambda version: {version + '.json': json.dumps({'candidate_prompt_sha256': 'candidate'}).encode()})
    manifest = {'sources': {}}
    def prepare(version, execute):
        workspaces = []
        for repeat in range(1, 6):
            workspace = history / f'workspace-{int(clock[0])}-{repeat}'
            workspace.mkdir()
            workspaces.append((workspace, {}, manifest, {}, {}))
        return workspaces
    monkeypatch.setattr(t, 'prepare', prepare)
    monkeypatch.setattr(t, 'guarded_command', lambda job, first, retry_after: ['fictional-run', str(job)])
    calls = []
    def process(command, **kwargs):
        if command[0] != 'fictional-run':
            return subprocess.CompletedProcess(command, 0)  # Fictional grading completes.
        job = Path(command[1])
        calls.append(job.name)
        if job.name == 'prompt-C-v14-a1-r2':
            t.exclusive(job / 'STOP.json', {'status': 'STOP', 'http_status': 504})
            t.exclusive(job / 'inflight.json', {'unknown_request_usage': True})
            return subprocess.CompletedProcess(command, 1)
        t.exclusive(job / 'manifest.json', manifest)
        t.exclusive(job / 'summary.json', {'status': 'completed'})
        return subprocess.CompletedProcess(command, 0)
    monkeypatch.setattr(t.subprocess, 'run', process)
    with pytest.raises(SystemExit, match='EXECUTION_STOP'):
        t.execute('v14', 1)
    original_stop = (history / 'prompt-C-v14-a1-r2/STOP.json').read_bytes()
    assert t.load(t.attempt_path('v14', 1))['status'] == 'STOP504'
    t.execute('v14', 2)
    assert sleeps == [60.]
    assert calls == ['prompt-C-v14-a1-r1', 'prompt-C-v14-a1-r2'] + [f'prompt-C-v14-a2-r{i}' for i in range(1, 6)]
    assert t.load(t.attempt_path('v14', 2))['status'] == 'completed'
    assert (history / 'prompt-C-v14-a1-r2/STOP.json').read_bytes() == original_stop
    assert (history / 'prompt-C-v14-a1-r2/inflight.json').exists()
    with pytest.raises(ValueError, match='STOP504'):
        t.execute('v14', 3)
