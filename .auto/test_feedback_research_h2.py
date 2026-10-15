"""Fictional offline feedback research tests: no gold or historical response bodies."""
import copy
import json
from pathlib import Path
import socket
import sys
import time
import pytest
sys.path.insert(0, str(Path(__file__).parent))
import feedback_research_h2 as p
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

def measured(fallback=1, **updates):
    return {'Q': .805, 'F1A': .7, 'F1B': .916, 'HitA': .30, 'valid': 60-fallback,
            'fallback': fallback, 'usage_known': True, **updates}


def test_nonzero_fallback_primary_not_classification_gain():
    p.quality([measured() for _ in range(5)])
    p.quality([measured(0) for _ in range(5)])
    with pytest.raises(ValueError, match='PRIMARY_NOT_IMPROVED'):
        p.quality([measured(2)] * 5)


@pytest.mark.parametrize('key,value,reason', [('Q', .802, 'Q_FAILED'), ('F1A', .599, 'F1_FAILED'),
    ('F1B', .749, 'F1_FAILED'), ('HitA', .299, 'EVIDENCE_FAILED'),
    ('usage_known', False, 'VALIDITY_OR_USAGE'), ('valid', 60, 'VALIDITY_OR_USAGE')])
def test_fixed_safeguards(key, value, reason):
    values = [measured() for _ in range(5)]
    # F1 is per-repeat; Q/Hit are means.
    for v in values:
        v[key] = value
    with pytest.raises(ValueError, match=reason):
        p.quality(values)


def test_per_repeat_f1_not_just_mean():
    values = [measured() for _ in range(5)]
    values[0]['F1A'] = .599
    with pytest.raises(ValueError, match='F1_FAILED'):
        p.quality(values)


def test_no_prefix_metrics(capsys):
    for count in (0, 1, 4):
        with pytest.raises(ValueError, match='FIVE_ACTUAL_RESULTS'):
            p.print_metrics([measured()] * count, 1, False)
        with pytest.raises(ValueError, match='FIVE_ACTUAL_CANDIDATES'):
            p.quality([measured()] * count)
    assert not capsys.readouterr().out


def test_format_counts_from_decoder_not_label(tmp_path, monkeypatch):
    job = full_fake_job(tmp_path, monkeypatch, fallback=True)
    stats = p.completed_result(job)
    assert stats['valid'] == 59 and stats['fallback'] == 1
    assert len(p.rows(job / '70b-canonical.jsonl')) == 60
    # Fallback neutral is retained as a legal ordinary output.
    assert p.rows(job / '70b-canonical.jsonl')[0]['label'] == 1
    assert stats['requests'] == 60 and stats['tokens'] == 6000


def test_reference_import_exclusive_and_checks_bound(tmp_path, monkeypatch):
    control = tmp_path / 'protocol.json'; control.write_text('{}')
    marker = tmp_path / 'reference.json'
    (tmp_path / '.auto').mkdir()
    monkeypatch.setattr(p, 'ROOT', tmp_path)
    monkeypatch.setattr(p, 'CONTROL', control)
    monkeypatch.setattr(p, 'REFERENCE', marker)
    c = {'reference': {'results': [measured()] * 5}}
    monkeypatch.setattr(p, 'verify', lambda: c)
    monkeypatch.setattr(p, 'print_metrics', lambda *args: None)
    p.import_reference(time.time())
    p.check_reference(c)
    p.check()
    for key in ('mode','candidate','round','phase','protocol_sha256'):
        ctx = p.context('reference'); ctx[key] = 'tampered'
        (tmp_path / '.auto/check-context.json').write_bytes(p.encode(ctx))
        with pytest.raises(ValueError, match='CONTEXT_BINDING'):
            p.check()
    with pytest.raises(FileExistsError):
        p.import_reference(time.time())


def test_fresh_approval_no_live_replay(monkeypatch):
    for approved in (None, time.time()-181, time.time()+10):
        with pytest.raises(ValueError, match='CURRENT_BOUNDED_OPERATOR'):
            p.execute(approved)

def test_official_macro_all_three_labels_and_neutral_fallback():
    # Evaluator dependencies live in its pinned interpreter, not contract venv.
    code = """
import importlib.util, socket, sys
def forbidden(*a, **k): raise AssertionError('network forbidden')
socket.socket.connect = forbidden
socket.create_connection = forbidden
spec = importlib.util.spec_from_file_location('official', sys.argv[1])
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)
assert e.macro_f1([(0,0),(1,1),(2,2)])[0] == 1
assert e.label_of({'label':1,'label_name':'neutral'})[0] == 1
assert abs(e.macro_f1([(0,0),(1,1),(2,1)])[0] - 5/9) < 1e-12
assert e.macro_f1([(1,1)])[0] == 1
"""
    p.subprocess.run([p.SCORER_PYTHON, '-B', '-Werror::ResourceWarning', '-c', code,
                      str(p.OFFICIAL / 'evaluate.py')], check=True, capture_output=True)


def test_metrics_historical_time_not_new_inference(capsys):
    rows = [{**measured(), **{k: 1 for k in ('case_wall_ms','requests','tokens','input_tokens',
             'output_tokens','parent_calls','child_calls','api_wait_ms')}} for _ in range(5)]
    p.print_metrics(rows, .25, True)
    output = capsys.readouterr().out
    assert 'METRIC format_fallbacks=5\n' in output
    assert 'reference_import_seconds=8.121229351032525' in output
    assert 'historical_reference=1' in output and 'usage_historical=1' in output
    assert 'candidate_command_wall_seconds' not in output
    assert 'historical_total_case_wall_seconds=2238.1406852069777' in output


def test_exclusive_candidate_phase_and_no_regrade(tmp_path, monkeypatch):
    monkeypatch.setattr(p, 'OUT', tmp_path)
    monkeypatch.setattr(p, 'CONTROL', tmp_path / 'control.json')
    p.CONTROL.write_text('{}')
    jobs = [{'name': p.job_name('v5', r)} for r in range(1,6)]
    monkeypatch.setattr(p, 'verify', lambda: {'jobs': jobs})
    monkeypatch.setattr(p, 'check_reference', lambda _: None)
    monkeypatch.setattr(p, 'grade_job', lambda _: pytest.fail('regrade selected'))
    p.phase_path('v5').write_text('{}')
    with pytest.raises(ValueError, match='PHASE_REPLAY_FATAL'):
        p.execute(time.time())


def test_partial_transport_failure_no_primary_or_success(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(p, 'OUT', tmp_path)
    monkeypatch.setattr(p, 'CONTROL', tmp_path / 'control.json')
    p.CONTROL.write_text('{}')
    workspace = tmp_path / 'workspace'; workspace.mkdir()
    jobs = [{'name': p.job_name('v5', r), 'workspace': str(workspace), 'manifest_sha256': 'fake'} for r in range(1,6)]
    monkeypatch.setattr(p, 'verify', lambda: {'jobs': jobs})
    monkeypatch.setattr(p, 'check_reference', lambda _: None)
    calls = []
    def fail(*args, **kwargs):
        calls.append(1)
        return type('Result', (), {'returncode': 1})()
    monkeypatch.setattr(p.subprocess, 'run', fail)
    monkeypatch.setattr(p, 'grade_job', lambda _: pytest.fail('prefix grading'))
    with pytest.raises(ValueError, match='WORKSPACE_RUN_STOP_NO_RETRY'):
        p.execute(time.time())
    assert len(calls) == 1
    captured = capsys.readouterr()
    assert 'METRIC' not in captured.out and 'unavailable' in captured.err
    assert p.load(tmp_path / 'public60-feedback-h2-STOP.json')['primary'] == 'unavailable'
    with pytest.raises(ValueError, match='PHASE_REPLAY_FATAL'):
        p.execute(time.time())


def test_exact_two_wire_insertions_and_frozen_h1():
    p.wire_source_binding()


def test_wire_no_wildcard_changes(tmp_path, monkeypatch):
    control = p.load(p.H1_CONTROL)
    for name in (p.RUNNER, p.WIRE_SDK):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((p.ROOT / name).read_bytes())
    monkeypatch.setattr(p, 'ROOT', tmp_path)
    p.wire_source_binding()
    path = tmp_path / p.RUNNER
    path.write_bytes(path.read_bytes() + b'\n# unapproved\n')
    with pytest.raises(ValueError, match='NON_WIRE_CHANGE'):
        p.wire_source_binding()


def test_candidate_metrics_include_historical_observations(capsys):
    values = [{**measured(), **{k: 1 for k in ('case_wall_ms','requests','tokens','input_tokens',
             'output_tokens','parent_calls','child_calls','api_wait_ms')}} for _ in range(5)]
    p.print_metrics(values, 12.5, False)
    text = capsys.readouterr().out
    assert 'candidate_command_wall_seconds=12.5' in text
    assert 'candidate_total_case_wall_seconds=0.005' in text
    assert 'reference_import_seconds=8.121229351032525' in text
    assert 'historical_total_case_wall_seconds=2238.1406852069777' in text
    assert 'historical_reference=0' in text and 'usage_historical=0' in text


def test_equivalence_exact_wire_delta_only(tmp_path):
    # Real frozen input contexts, never historical response bodies or gold.
    workroot = p.OUT / 'public60-feedback-h2-workspaces'
    prepared = list(workroot.glob('*/prepared.json'))
    if not prepared:
        pytest.skip('offline first workspace not yet prepared')
    workspace = prepared[0].parent
    m = p.load(prepared[0])
    reference = p.load(p.H1_CONTROL)['reference']['jobs'][0]
    p.equivalent_baseline(m, workspace, reference)
    for mutate in ('sdk', 'schema', 'messages', 'caps'):
        changed = copy.deepcopy(m)
        if mutate == 'sdk': changed['sources'][p.WIRE_SDK] = 'unapproved'
        elif mutate == 'schema': changed['frozen'][0]['schema_sha256'] = 'unapproved'
        elif mutate == 'messages': changed['frozen'][0]['messages'][0]['content'] += 'changed'
        else: changed['output_limit'] = 257
        with pytest.raises(ValueError):
            p.equivalent_baseline(changed, workspace, reference)
