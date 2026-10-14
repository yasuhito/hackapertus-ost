"""Offline fictional controls; real inputs are checked by --prepare-only.

No historical fixture/gold/output is opened by this test module.
"""
import copy
import json
from pathlib import Path
import socket
import sys
import time

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import public_validation_continue as p
sys.path.insert(0, str(p.ROOT / 'track_2a/dev/format'))
import run_comparison as r
from test_comparison import item, response


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('network or credential access forbidden')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(r.legacy.c, 'read_key', forbidden)


def manifest():
    return {'strategy': 'C', 'models': [r.MODELS[1]],
            'role_models': {'parent': r.MODELS[1], 'child': r.MODELS[0]},
            'request_limit': p.CAP, 'token_budget': p.BUDGET,
            'frozen': [item()]}


def measured(q=.8, a=.8, b=.8, hit=.8):
    return {'Q': q, 'F1A': a, 'F1B': b, 'HitA': hit,
            'valid': 60, 'fallback': 0, 'usage_known': True}


def test_scoring_and_candidate_gates():
    baseline = [measured() for _ in range(5)]
    assert p.quality(baseline)['gain'] == 0
    assert p.quality(baseline, [measured(.83) for _ in range(5)])['strict_supplement']
    with pytest.raises(ValueError, match='GAIN_FAILED'):
        p.quality(baseline, [measured(.81) for _ in range(5)])
    with pytest.raises(ValueError, match='F1_FAILED'):
        p.quality(baseline, [measured(.85, a=.59) for _ in range(5)])
    with pytest.raises(ValueError, match='EVIDENCE_FAILED'):
        p.quality(baseline, [measured(.85, hit=.79) for _ in range(5)])
    noisy = [measured(.7 + i * .05) for i in range(5)]
    assert p.quality(noisy)['noise'] > .02
    with pytest.raises(ValueError, match='GAIN_FAILED'):
        p.quality(noisy, [measured(.83) for _ in range(5)])


@pytest.mark.parametrize('key,value', [('usage_known', False), ('fallback', 2), ('valid', 58)])
def test_baseline_must_be_measured_valid(key, value):
    values = [measured() for _ in range(5)]
    values[0][key] = value
    with pytest.raises(ValueError, match='VALIDITY_OR_USAGE'):
        p.quality(values)


def test_no_quality_requirement_imposed_on_baseline():
    assert p.quality([measured(.1, .1, .1) for _ in range(5)])['baseline_Q'] == .1


@pytest.mark.parametrize('fence', p.FENCES)
def test_existing_stop_or_orphan_fatal(tmp_path, fence):
    m = manifest()
    tmp_path.chmod(0o700)
    r.initialize(tmp_path, m)
    (tmp_path / fence).write_text('{}')
    with pytest.raises(r.Stop, match='UNCERTAIN_FENCE'):
        r.Ledger(tmp_path, m, lambda _: pytest.fail('transport selected'))


def test_explicit_300_post_cap_and_reservation(tmp_path):
    assert p.BUDGET == p.CAP * r.RESERVE == 78_720_000
    m = manifest()
    tmp_path.chmod(0o700)
    r.initialize(tmp_path, m)
    class Mock:
        def request(self, *args):
            return response(r.MODELS[1], content='fictional')
    ledger = r.Ledger(tmp_path, m, lambda _: Mock())
    for n in range(300):
        ledger.post(r.MODELS[1], 0, 'parent', n, {'model': r.MODELS[1]})
    with pytest.raises(r.Stop, match='HARD_BUDGET_STOP'):
        ledger.post(r.MODELS[1], 0, 'parent', 300, {'model': r.MODELS[1]})
    assert ledger.state['requests'] == 300
    assert ledger.state['tokens'] == 30000  # actual usage, not reservation twice
    assert not ledger.fence.exists()


def test_context_binding(tmp_path, monkeypatch):
    control = tmp_path / 'protocol.json'
    control.write_text('{}')
    monkeypatch.setattr(p, 'CONTROL', control)
    context = {'mode': 'public_continue_baseline', 'candidate': '', 'phase': 'v5',
               'protocol_sha256': p.sha(control.read_bytes())}
    p.check_binding(context, 'v5')
    for key in context:
        wrong = {**context, key: 'wrong'}
        with pytest.raises(ValueError, match='BINDING_FAILED'):
            p.check_binding(wrong, 'v5')


def test_workspace_input_only_and_route(tmp_path):
    p.bundle_manifest()
    for variant in p.VARIANTS:
        workspace = tmp_path / variant
        workspace.mkdir()
        hashes = p.copy_workspace(workspace, variant)
        assert 'public-inputs.json' in hashes
        assert not any('fixtures/' in path or Path(path).name in
                       ('expected.jsonl', 'source.jsonl', 'source-metadata.jsonl') for path in hashes)
        assert len(p.load(workspace / 'public-inputs.json')) == 60
        assert all(Path(c['booklet']['path']).is_relative_to(workspace) for c in
                   p.load(workspace / 'public-inputs.json') if 'booklet' in c)


def test_guard_before_base_or_credentials(monkeypatch):
    called = []
    class Base:
        def request(self, *args):
            called.append(args)
    monkeypatch.setattr(p.time, 'monotonic', lambda: 10)
    guard = p.guarded_transport(r, 11, Base)()
    guard.request('POST', '/', {'content': 'x' * 183485})
    assert len(called) == 1
    with pytest.raises(r.Stop, match='PAYLOAD_BYTE_LIMIT'):
        guard.request('POST', '/', {'content': 'x' * p.BYTE_CAP})
    monkeypatch.setattr(p.time, 'monotonic', lambda: 11)
    with pytest.raises(r.Stop, match='BATCH_DEADLINE_STOP'):
        guard.request('POST', '/', {})
    assert len(called) == 1


def test_no_metric_for_incomplete_batch(capsys):
    with pytest.raises(ValueError, match='FIVE_ACTUAL_RESULTS'):
        p.print_metrics([measured()] * 4, {}, 1)
    assert 'METRIC' not in capsys.readouterr().out


def test_live_requires_current_approval(monkeypatch):
    monkeypatch.setattr(p, 'verify', lambda: {})
    for approved in (None, time.time() - 181, time.time() + 10):
        with pytest.raises(ValueError, match='CURRENT_BOUNDED_OPERATOR'):
            p.execute('v5', approved)


def test_exclusive_refuses_overwrite(tmp_path):
    path = tmp_path / 'test.json'
    p.exclusive(path, {'first': True})
    with pytest.raises(FileExistsError):
        p.exclusive(path, {'first': False})
    assert p.load(path) == {'first': True}


def full_fake_job(tmp_path, monkeypatch, fallback=False):
    monkeypatch.setattr(p, 'CONTROL', tmp_path / 'no-protocol')
    m = manifest()
    m['frozen'] = []
    for index in range(60):
        x = item()
        x['case']['id'] = f'fictional-{index}'
        m['frozen'].append(x)
    job = tmp_path / 'job'
    r.initialize(job, m)
    def fake_sdk(x, model, post, **kwargs):
        post('parent', 0, {'model': model})
        return (None if fallback and x['case']['id'] == 'fictional-0' else {'label': 1, 'candidate_ids': []}), ['NO_ACCEPTED_SUBMIT'] if fallback else [], {}
    monkeypatch.setattr(r, 'run_b', fake_sdk)
    class Mock:
        def request(self, *args):
            return response(r.MODELS[1], content='fictional')
    r.run(job, m, lambda model: Mock())
    monkeypatch.setattr(p, 'module', lambda *args: r)
    return job


def test_completed_result_and_metrics(tmp_path, monkeypatch, capsys):
    job = full_fake_job(tmp_path, monkeypatch)
    stats = p.completed_result(job)
    assert stats['requests'] == 60 and stats['input_tokens'] == 4800
    assert stats['output_tokens'] == 1200 and stats['parent_calls'] == 60
    results = [{**stats, **measured()} for _ in range(5)]
    p.print_metrics(results, p.quality(results), 2)
    metrics = dict(line.removeprefix('METRIC ').split('=') for line in capsys.readouterr().out.splitlines())
    assert float(metrics['public_Q_gain_v5']) == 0
    assert int(metrics['public_total_requests']) == 300
    assert int(metrics['public_usage_known']) == 1


@pytest.mark.parametrize('change', ['count', 'id', 'usage', 'flag', 'fallback'])
def test_complete_integrity_refuses_mutation(tmp_path, monkeypatch, change):
    job = full_fake_job(tmp_path, monkeypatch)
    if change in ('count', 'id'):
        values = p.rows(job / '70b-canonical.jsonl')
        if change == 'count':
            values.pop()
        else:
            values[0]['id'] = 'other'
        (job / '70b-canonical.jsonl').write_bytes(b'\n'.join(p.encode(x) for x in values))
    else:
        state = p.load(job / 'state.json')
        name = next(iter(state['cases'] if change == 'fallback' else state['attempts']))
        record = p.load(job / name)
        if change == 'usage':
            record['usage']['prompt_tokens'] = '80'
        elif change == 'flag':
            record['safe'] = False
        else:
            record['output_valid'] = False
        (job / name).write_bytes(p.encode(record))
        group = 'cases' if change == 'fallback' else 'attempts'
        state[group][name] = r.legacy.digest(r.legacy.encode(record))
        (job / 'state.json').write_bytes(p.encode(state))
    with pytest.raises((ValueError, r.Stop)):
        p.completed_result(job)


def test_504_stop_no_retry_and_unknown_usage(tmp_path, monkeypatch):
    m = manifest()
    r.initialize(tmp_path, m)
    calls = []
    class Mock:
        def request(self, *args):
            calls.append(1)
            exc = r.Stop('HTTP_FAILURE_NO_RETRY')
            exc.http_status = 504
            raise exc
    def fake_sdk(x, model, post, **kwargs):
        post('parent', 0, {'model': model})
    monkeypatch.setattr(r, 'run_b', fake_sdk)
    with pytest.raises(r.Stop):
        r.run(tmp_path, m, lambda model: Mock())
    assert p.load(tmp_path / 'STOP.json')['http_status'] == 504
    assert (tmp_path / 'inflight.json').exists()
    state = p.load(tmp_path / 'state.json')
    assert state['reserved_tokens'] == r.RESERVE and state['tokens'] == 0
    with pytest.raises(r.Stop, match='UNCERTAIN_FENCE'):
        r.run(tmp_path, m, lambda model: Mock())
    assert calls == [1]


def test_grade_actual_schema_and_exclusive(tmp_path, monkeypatch):
    monkeypatch.setattr(p, 'OUT', tmp_path)
    monkeypatch.setattr(p, 'completed_result', lambda job: {'valid': 60})
    commands = []
    def grade(command, **kwargs):
        commands.append(command)
        pth = Path(command[command.index('--output') + 1])
        q = (.30 * .7 + .28 * .8) / .58
        pth.write_bytes(p.encode({'official_report': {'tasks': {'A': {'macro_f1': .7}, 'B': {'macro_f1': .8}}},
                                 'classification_objective': {'value': q},
                                 'primary_evidence_objective': {'value': .9}}))
        return type('Result', (), {'returncode': 0})()
    monkeypatch.setattr(p.subprocess, 'run', grade)
    job = tmp_path / 'fictional-job'
    result = p.grade_job(job)
    assert result['F1A'] == .7 and result['HitA'] == .9
    assert str(p.BUNDLE / 'expected.jsonl') in commands[0]
    with pytest.raises(ValueError, match='GRADER_REPLAY'):
        p.grade_job(job)


def test_batch_deadline_stops_before_next_job(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(p, 'OUT', tmp_path)
    control = tmp_path / 'protocol'
    p.exclusive(control, {})
    monkeypatch.setattr(p, 'CONTROL', control)
    jobs = [{'variant': 'v5', 'name': p.job_name('v5', i),
             'workspace': str(tmp_path), 'manifest_sha256': 'fictional'} for i in range(1, 6)]
    monkeypatch.setattr(p, 'verify', lambda: {'jobs': jobs})
    times = iter([0, 0, p.BATCH_SECONDS])
    monkeypatch.setattr(p.time, 'monotonic', lambda: next(times))
    calls = []
    monkeypatch.setattr(p.subprocess, 'run', lambda *a, **kw: calls.append(a) or type('Result', (), {'returncode': 0})())
    monkeypatch.setattr(p, 'completed_result', lambda job: {})
    monkeypatch.setattr(p, 'grade_job', lambda job: pytest.fail('prefix graded'))
    with pytest.raises(ValueError, match='BATCH_DEADLINE_STOP'):
        p.execute('v5', time.time())
    assert len(calls) == 1
    assert p.load(tmp_path / 'public60b-v5-STOP.json')['quality'] == 'unknown'
    assert 'METRIC' not in capsys.readouterr().out


def test_isolated_run_workspace_mock_transport(tmp_path, monkeypatch):
    original = full_fake_job(tmp_path, monkeypatch)
    m = p.load(original / 'manifest.json')
    m['sources'] = {}
    cscs = tmp_path / 'cscs'
    workspace = cscs / 'public60b-workspaces' / 'fresh'
    (workspace / '.auto').mkdir(parents=True)
    monkeypatch.setattr(p, '__file__', str(workspace / '.auto/public_validation_continue.py'))
    monkeypatch.setattr(p, 'ROOT', workspace)
    p.exclusive(workspace / 'prepared.json', m)
    job = cscs / p.job_name('v5', 2)
    control = cscs / 'protocol.json'
    monkeypatch.setattr(p, 'CONTROL', control)
    p.exclusive(control, {'version': 'public60-continue-v16-1', 'byte_cap': p.BYTE_CAP,
                         'jobs': [{'name': job.name, 'workspace': str(workspace),
                                   'manifest_sha256': p.sha(p.encode(m)),
                                   'files': {'prepared.json': p.sha((workspace / 'prepared.json').read_bytes())}}]})
    p.exclusive(cscs / 'public60b-v5-phase.json',
                {'status': 'running', 'protocol_sha256': p.sha(control.read_bytes())})
    protected = []
    monkeypatch.setattr(r.legacy.c, 'protect', lambda: protected.append(1))
    class Mock:
        def __init__(self, model):
            self.model = model
        def request(self, *args):
            return response(self.model, content='fictional')
    monkeypatch.setattr(r, 'Transport', Mock)
    p.run_workspace(job, time.time() + 100, p.sha(p.encode(m)))
    assert protected == [1]
    assert p.completed_result(job)['requests'] == 60
    with pytest.raises(FileExistsError):
        p.run_workspace(job, time.time() + 100, p.sha(p.encode(m)))
    (workspace / 'prepared.json').write_text('{}')
    with pytest.raises(ValueError, match='WORKSPACE_CHANGED'):
        p.run_workspace(job, time.time() + 100, p.sha(p.encode(m)))


def test_legal_fallback_kept_exactly_and_candidate_only_gate(tmp_path, monkeypatch):
    job = full_fake_job(tmp_path, monkeypatch, fallback=True)
    before = (job / '70b-canonical.jsonl').read_bytes()
    stats = p.completed_result(job)
    assert stats['valid'] == 59 and stats['fallback'] == 1
    assert stats['valid'] + stats['fallback'] == 60
    assert (job / '70b-canonical.jsonl').read_bytes() == before
    baseline = [{**measured(), **stats} for _ in range(5)]
    assert p.quality(baseline)['gain'] == 0
    candidate = [{**measured(.9), **stats} for _ in range(5)]
    with pytest.raises(ValueError, match='CANDIDATE_FALLBACK_FAILED'):
        p.quality(baseline, candidate)


@pytest.mark.parametrize('change', ['source', 'request_model', 'schema', 'unknown', 'case', 'symlink', 'summary'])
def test_more_ledger_tamper_rejected(tmp_path, monkeypatch, change):
    job = full_fake_job(tmp_path, monkeypatch)
    if change == 'symlink':
        (job / 'extra').symlink_to(job / 'manifest.json')
    elif change == 'summary':
        (job / 'summary.json').write_text('{"status":"running"}')
    else:
        state = p.load(job / 'state.json')
        group = 'cases' if change == 'case' else 'attempts'
        name = next(iter(state[group]))
        record = p.load(job / name)
        key = {'source': 'source_sha256', 'request_model': 'request_model',
               'schema': 'assembler_schema_sha256', 'unknown': 'usage_known', 'case': 'case_id'}[change]
        record[key] = False if change == 'unknown' else 'changed'
        (job / name).write_bytes(p.encode(record))
        state[group][name] = r.legacy.digest(r.legacy.encode(record))
        (job / 'state.json').write_bytes(p.encode(state))
    with pytest.raises((ValueError, r.Stop)):
        p.completed_result(job)


@pytest.mark.parametrize('variant', p.VARIANTS)
def test_all_repeats_collected_before_all_grading_despite_fallback(tmp_path, monkeypatch, capsys, variant):
    monkeypatch.setattr(p, 'OUT', tmp_path)
    monkeypatch.setattr(p, 'ROOT', tmp_path)
    control = tmp_path / 'protocol'
    p.exclusive(control, {})
    monkeypatch.setattr(p, 'CONTROL', control)
    jobs = [{'variant': variant, 'name': p.job_name(variant, i), 'repeat': i,
             'workspace': str(tmp_path), 'manifest_sha256': 'fictional',
             'imported': variant == 'v5' and i == 1} for i in range(1, 6)]
    monkeypatch.setattr(p, 'verify', lambda: {'jobs': jobs})
    stats = {'valid': 59, 'fallback': 1, 'usage_known': True, 'requests': 187,
             'tokens': 1782477, 'input_tokens': 1780000, 'output_tokens': 2477,
             'parent_calls': 120, 'child_calls': 67, 'case_wall_ms': 1000,
             'api_wait_ms': 900, 'repairs': 1}
    score = {**measured(.9), **stats}
    monkeypatch.setattr(p, 'phase_complete', lambda _: {'results': [score.copy() for _ in range(5)]})
    monkeypatch.setattr(p, 'completed_result', lambda _: stats.copy())
    events = []
    def run(command, **kwargs):
        name = Path(command[command.index('--job') + 1]).name
        events.append(('run', name))
        (tmp_path / name).mkdir()
        return type('Result', (), {'returncode': 0})()
    def grade(job):
        events.append(('grade', job.name))
        (tmp_path / (job.name + '-official.json')).write_text('{}')
        return score.copy()
    monkeypatch.setattr(p.subprocess, 'run', run)
    monkeypatch.setattr(p, 'grade_job', grade)
    (tmp_path / '.auto').mkdir()
    if variant == 'v5':
        (tmp_path / 'public60-v5-r1').mkdir()
    p.execute(variant, time.time())
    new_count = 4 if variant == 'v5' else 5
    assert [e[0] for e in events] == ['run'] * new_count + ['grade'] * 5
    assert not any(e == ('run', 'public60-v5-r1') for e in events)
    phase = p.load(p.phase_path(variant))
    assert phase['accepted_total'] == 295 and phase['fallback_total'] == 5
    assert len(phase['results']) == 5
    metrics = dict(line.removeprefix('METRIC ').split('=') for line in capsys.readouterr().out.splitlines())
    assert int(metrics['public_total_requests']) == 5 * 187
    assert int(metrics['public_total_tokens']) == 5 * 1782477
    assert int(metrics['public_total_accepted']) == 295
    assert not (tmp_path / f'public60b-{variant}-STOP.json').exists()
    if variant == 'v16':
        with pytest.raises(ValueError, match='CANDIDATE_FALLBACK_FAILED'):
            p.quality([score] * 5, phase['results'])


def test_exclusive_nine_new_jobs_no_old_r1():
    names = [p.job_name(v, r) for v, r in p.new_scope()]
    assert len(names) == len(set(names)) == 9
    assert names == [f'public60b-v5-r{i}' for i in range(2, 6)] + [f'public60b-v16-r{i}' for i in range(1, 6)]
    assert p.job_name('v5', 1) == 'public60-v5-r1'


@pytest.mark.parametrize('fence', p.FENCES)
def test_complete_import_never_accepts_job_fence(tmp_path, monkeypatch, fence):
    job = full_fake_job(tmp_path, monkeypatch, fallback=True)
    (job / fence).write_text('{}')
    with pytest.raises(ValueError, match='STOP_OR_ORPHAN_FATAL'):
        p.completed_result(job, bind=False)


@pytest.fixture
def fictional_original(tmp_path, monkeypatch):
    monkeypatch.setattr(p, 'ROOT', tmp_path)
    monkeypatch.setattr(p, 'OUT', tmp_path)
    monkeypatch.setattr(p, 'CONTROL', tmp_path / 'new-control')
    monkeypatch.setattr(p, 'ORIGINAL_CONTROL', tmp_path / 'old-control')
    monkeypatch.setattr(p, 'CHECKPOINT', tmp_path / 'checkpoint')
    source = tmp_path / 'original-helper.py'
    source.write_text('original helper')
    manifest = {'fictional': True}
    workspace = tmp_path / 'old-workspace'
    workspace.mkdir()
    p.exclusive(workspace / 'prepared.json', manifest)
    job = tmp_path / 'public60-v5-r1'
    job.mkdir()
    p.exclusive(job / 'manifest.json', manifest)
    p.exclusive(tmp_path / 'public60-v5-STOP.json', {'status': 'STOP'})
    jobs = [{'name': f'public60-{v}-r{i}', 'variant': v, 'repeat': i,
             'workspace': str(workspace), 'files': {'prepared.json': p.sha((workspace / 'prepared.json').read_bytes())},
             'manifest_sha256': p.sha(p.encode(manifest))} for v in p.VARIANTS for i in range(1, 6)]
    original = {'version': 'public60-v16-1', 'runtime': {'sdk': 'pinned'},
                'files': {'original-helper.py': p.sha(source.read_bytes())}, 'jobs': jobs}
    p.exclusive(p.ORIGINAL_CONTROL, original)
    monkeypatch.setattr(p, 'ORIGINAL_SHA', p.sha(p.ORIGINAL_CONTROL.read_bytes()))
    snapshot = p.fingerprint([source, workspace / 'prepared.json', job / 'manifest.json',
                              tmp_path / 'public60-v5-STOP.json'], tmp_path)
    p.exclusive(p.CHECKPOINT, snapshot)
    monkeypatch.setattr(p, 'CHECKPOINT_SHA', p.sha(p.CHECKPOINT.read_bytes()))
    monkeypatch.setattr(p, 'runtime', lambda: {'sdk': 'pinned'})
    monkeypatch.setattr(p, 'audit', lambda *args: None)
    stats = {'valid': 59, 'fallback': 1, 'requests': 187, 'tokens': 1782477, 'usage_known': True}
    monkeypatch.setattr(p, 'completed_result', lambda job, bind: stats.copy())
    return source, workspace, job, stats


def test_only_explicit_first_completed_import_phase_stop_readonly(fictional_original):
    before = p.fingerprint([p.OUT / 'public60-v5-STOP.json'], p.ROOT)
    imported = p.verify_original()
    assert imported['first_repeat']['name'] == 'public60-v5-r1'
    assert imported['stats']['requests'] == 187
    assert before == p.fingerprint([p.OUT / 'public60-v5-STOP.json'], p.ROOT)


@pytest.mark.parametrize('change', ['source', 'canonical', 'sdk', 'protocol', 'checkpoint', 'workspace', 'symlink'])
def test_original_tamper_refused(fictional_original, monkeypatch, change):
    source, workspace, job, stats = fictional_original
    if change == 'source':
        source.write_text('changed')
    elif change == 'canonical':
        (job / 'manifest.json').write_text('{}')
    elif change == 'sdk':
        monkeypatch.setattr(p, 'runtime', lambda: {'sdk': 'changed'})
    elif change == 'protocol':
        p.ORIGINAL_CONTROL.write_text('{}')
    elif change == 'checkpoint':
        p.CHECKPOINT.write_text('{}')
    elif change == 'workspace':
        (workspace / 'prepared.json').write_text('{}')
    else:
        (workspace / 'prepared.json').unlink()
        (workspace / 'prepared.json').symlink_to(job / 'manifest.json')
    with pytest.raises(ValueError):
        p.verify_original()


@pytest.mark.parametrize('key,value', [('valid', 60), ('fallback', 0), ('requests', 186), ('tokens', 0), ('usage_known', False)])
def test_original_import_requires_exact_complete_known_first_repeat(fictional_original, key, value):
    stats = fictional_original[3]
    stats[key] = value
    with pytest.raises(ValueError, match='IMPORT_COMPLETE_USAGE_REQUIRED'):
        p.verify_original()


def test_phase_rejects_altered_result_metrics(tmp_path, monkeypatch):
    monkeypatch.setattr(p, 'OUT', tmp_path)
    monkeypatch.setattr(p, 'ROOT', tmp_path)
    control = tmp_path / 'control'
    p.exclusive(control, {})
    monkeypatch.setattr(p, 'CONTROL', control)
    score = measured()
    phase = {'status': 'completed', 'protocol_sha256': p.sha(control.read_bytes()),
             'results': [score] * 5, 'artifacts': {}, 'accepted_total': 300, 'fallback_total': 0}
    monkeypatch.setattr(p, 'official_result', lambda job: {**score, 'Q': .1})
    p.exclusive(p.phase_path('v5'), phase)
    p.exclusive(tmp_path / 'public60b-v5-analysis.json', phase)
    with pytest.raises(ValueError, match='PHASE_RESULTS_CHANGED'):
        p.phase_complete('v5')


def test_workspace_inventory_refuses_gold_or_unpinned_file(tmp_path):
    (tmp_path / 'input.json').write_text('[]')
    p.workspace_inventory(tmp_path, {'input.json': 'hash'})
    (tmp_path / 'expected.jsonl').write_text('fictional gold')
    with pytest.raises(ValueError, match='UNFROZEN_WORKSPACE_FILE'):
        p.workspace_inventory(tmp_path, {'input.json': 'hash'})


def test_normalized_baseline_contract_refuses_policy_change(tmp_path):
    old = tmp_path / 'old'
    new = tmp_path / 'new'
    for w in (old, new):
        w.mkdir()
        p.exclusive(w / 'public-inputs.json', [{'path': str(w / 'booklets/x.pdf')}])
    def manifest(w):
        return {'case_sha256': p.sha((w / 'public-inputs.json').read_bytes()),
                'temperature': 0, 'sources': {str(w / 'predict.py'): 'same'},
                'case': {'path': str(w / 'booklets/x.pdf')}}
    p.exclusive(old / 'prepared.json', manifest(old))
    first = {'workspace': str(old)}
    p.equivalent_baseline(manifest(new), new, first)
    changed = {**manifest(new), 'temperature': 1}
    with pytest.raises(ValueError, match='BASELINE_CONTRACT_NOT_EQUIVALENT'):
        p.equivalent_baseline(changed, new, first)
