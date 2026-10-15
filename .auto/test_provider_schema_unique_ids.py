"""Offline real guarded Transport with scripted HTTPS, never real credentials."""
import copy
from pathlib import Path
import socket
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import provider_schema_unique_ids as b


class Clock:
    now = 0
    def __init__(self):
        self.waits = []
    def __call__(self):
        return self.now
    def sleep(self, seconds):
        self.waits.append(seconds)
        self.now += seconds


@pytest.fixture
def harness(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError('REAL_NETWORK_OR_CREDENTIAL')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    root = b.old.root_runner()
    monkeypatch.setattr(root.legacy.c, 'read_key', lambda path: 'dummy')
    monkeypatch.setattr(b.old, 'root_runner', lambda: root)
    p = b.protocol()
    script, posts, clients = [], [], []
    clock = Clock()
    job = tmp_path/'job'

    class HTTP:
        def __init__(self, *args, **kwargs):
            assert kwargs['timeout'] == 45
            clients.append(self)
        def set_debuglevel(self, level):
            assert level == 0
        def request(self, method, path, body, headers):
            assert method == 'POST' and headers['Authorization'] == 'Bearer dummy'
            n = len(posts)+1
            state = b.old.load(job/'budget.json')
            assert state['physical_posts'] == n
            assert state['charged_tokens'] <= 32768
            attempts = sorted(job.glob('*-attempt'))
            request = b.old.load(attempts[-1]/'request.json')
            assert request['identity']['physical_post'] == n
            assert request['identity']['payload_sha256'] == b.old.sha(body)
            assert request['identity']['charged_before'] + 4096 == state['charged_tokens']
            self.payload = b.old.strict(body)
            posts.append(body)
        def getresponse(self):
            action = script.pop(0) if script else 200
            if isinstance(action, BaseException):
                raise action
            self.status = action if type(action) is int else 200
            self.action = action
            return self
        def read(self, maximum):
            assert maximum == 2_000_001
            if callable(self.action):
                return self.action(self.payload)
            if self.status != 200:
                return b'{"error":{"message":"fictional 500 schema failure"}}'
            return answer(self.payload)
        def close(self):
            pass
    monkeypatch.setattr(b.old.http.client, 'HTTPSConnection', HTTP)
    def run(actions=()):
        script.extend(actions)
        b.run(p, job, clock=clock, sleep=clock.sleep)
    return p, job, script, posts, clients, clock, run


def answer(payload, *, model=None, usage=True):
    result = dict(model=model or payload['model'], choices=[dict(finish_reason='tool_calls',
        message=dict(content=None, tool_calls=[dict(type='function', function=dict(
            name='submit', arguments='{"label":1,"candidate_ids":[]}'))]))])
    if usage:
        result['usage'] = dict(prompt_tokens=10, completion_tokens=2, total_tokens=12)
    return b.old.encode(result)


def test_real_transport_500_500_200_immutable_and_unknown(harness):
    p, job, script, posts, clients, clock, run = harness
    run([500, 500, 200])
    assert len(posts) == len(clients) == 14
    assert posts[0] == posts[1] == posts[2]
    assert clock.waits == [2, 4]
    failed = [job/f'00-{n}-attempt'/'capture.json' for n in (1, 2)]
    before = [x.read_bytes() for x in failed]
    assert all(b.old.load(x)['status'] == 500 for x in failed)
    result = b.check(p, job)
    assert result['logical_count'] == 12 and result['physical_posts'] == 14
    assert result['retry_count'] == result['unknown_usage_count'] == 2
    assert result['known_success_tokens'] == 144
    assert result['reserved_budget_charge'] == 8192 and result['charged_tokens'] == 8336
    assert result['full_usage_known'] is False and result['full_total_tokens'] is None
    assert result['financial_cost'] is None
    assert result['unique_assembler_violations'] == result['control_assembler_violations'] == 0
    assert [x.read_bytes() for x in failed] == before
    with pytest.raises(FileExistsError):
        run()
    assert len(posts) == 14
    with pytest.raises(FileExistsError):
        b.save(failed[0], {})


def test_fifth_attempt_can_succeed_with_all_failures_preserved(harness):
    p, job, _, posts, clients, clock, run = harness
    run([500, 500, 500, 500, 200])
    assert len(posts) == len(clients) == 16
    assert all(body == posts[0] for body in posts[:5])
    assert clock.waits == [2, 4, 8, 16]
    result = b.check(p, job)
    assert result['logical_count'] == 12 and result['physical_posts'] == 16
    assert result['retry_count'] == result['unknown_usage_count'] == 4
    assert result['reserved_budget_charge'] == 16384
    assert result['charged_tokens'] == 16528
    assert result['full_total_tokens'] is None
    for number in range(1, 5):
        assert b.old.load(job/f'00-{number}-attempt'/'capture.json')['status'] == 500
    assert b.old.load(job/'00-5-attempt'/'capture.json')['status'] == 200


def test_five_attempt_policy_and_physical_cap():
    assert b.POLICY['max_attempts'] == 5
    assert b.POLICY['delays'] == [2, 4, 8, 16]
    assert b.POLICY['max_physical_posts'] == b.POLICY['logical_requests'] * 5 == 60
    b.preflight(dict(physical_posts=59, charged_tokens=0), 0, 0)
    with pytest.raises(ValueError, match='POST_CAP'):
        b.preflight(dict(physical_posts=60, charged_tokens=0), 0, 0)


def test_thirteen_posts_complete_read_only_check(harness, monkeypatch):
    p, job, _, posts, _, clock, run = harness
    run([500, 200])
    before = {str(x): x.read_bytes() for x in job.rglob('*') if x.is_file()}
    monkeypatch.setattr(b.old.Transport, 'request', lambda *a: pytest.fail('CHECK_POST'))
    result = b.check(p, job)
    assert result['physical_posts'] == 13 and result['logical_count'] == 12
    assert sum(x['logical_count'] for x in result['per_model_arm'].values()) == 12
    assert sum(x['physical_posts'] for x in result['per_model_arm'].values()) == 13
    assert before == {str(x): x.read_bytes() for x in job.rglob('*') if x.is_file()}


@pytest.mark.parametrize('actions,count,waits', [([500]*5, 5, [2,4,8,16]),
    ([500,400], 2, [2]), ([400],1,[]), ([401],1,[]), ([429],1,[]),
    ([502],1,[]), ([503],1,[]), ([TimeoutError()],1,[]), ([OSError()],1,[]),
    ([lambda p: b'invalid'],1,[]), ([lambda p: answer(p, model='wrong')],1,[]),
    ([lambda p: answer(p, usage=False)],1,[]),
    ([lambda p: b.old.encode(dict(model=p['model'], error={}))],1,[])])
def test_terminal_errors_never_continue(harness, actions, count, waits):
    p, job, _, posts, _, clock, run = harness
    with pytest.raises((ValueError, TimeoutError, OSError)):
        run(actions)
    assert len(posts) == count and clock.waits == waits
    assert (job/'STOP.json').exists() and (job/'inflight.json').exists()
    assert not (job/'completed.json').exists()
    assert len(list(job.glob('*-attempt/capture.json'))) == count
    state = b.old.load(job/'budget.json')
    assert state['charged_tokens'] == 4096*count
    assert state['unknown_usage_count'] == count
    with pytest.raises(ValueError, match='TERMINAL'):
        b.check(p, job)


def test_budget_prevents_next_retry_before_sleep_or_post(harness):
    p, job, _, posts, _, clock, run = harness
    # Two pairs of failures then success consume 16408; next pair consumes 8192;
    # further reservations eventually hit the unchanged 32768 budget.
    with pytest.raises(ValueError, match='TOKEN_RESERVATION'):
        run([500,500,200]*5)
    state = b.old.load(job/'budget.json')
    assert state['charged_tokens'] <= 32768
    assert len(posts) == 10
    assert clock.waits == [2,4,2,4,2,4]


@pytest.mark.parametrize('elapsed', [59, 60, 899, 900])
def test_deadline_slack_prevents_wait_and_retry(harness, elapsed):
    p, job, _, posts, _, clock, run = harness
    def slow(payload):
        clock.now = elapsed
        return b'500 raw not JSON'
    # Callable sets HTTP 200; replace with scripted response reader retaining 500.
    import unittest.mock
    original = b.old.http.client.HTTPSConnection.read
    def read(self, maximum):
        if self.status == 500:
            return slow(self.payload)
        return original(self, maximum)
    with unittest.mock.patch.object(b.old.http.client.HTTPSConnection, 'read', read):
        with pytest.raises(ValueError, match='WALL_LIMIT|WAIT_DEADLINE'):
            run([500])
    assert len(posts) == 1 and not clock.waits
    assert b.old.load(job/'00-1-attempt'/'capture.json')['raw'] == '500 raw not JSON'


@pytest.mark.parametrize('target', ['request.json','capture.json','result.json','budget.json'])
def test_write_failure_stops_without_retry(harness, monkeypatch, target):
    p, job, _, posts, _, clock, run = harness
    original = b.save
    def fail(path, value, **kw):
        if path.name == target:
            raise OSError('fictional disk failure')
        return original(path, value, **kw)
    monkeypatch.setattr(b, 'save', fail)
    with pytest.raises(OSError):
        run([500,200])
    assert len(posts) <= 1 and not clock.waits
    assert (job/'STOP.json').exists()


@pytest.mark.parametrize('target', ['00-1-attempt/capture.json','00-1-attempt/request.json',
                                  '00-1-attempt/result.json','budget.json'])
def test_capture_and_accounting_tamper(harness, target):
    p, job, _, posts, _, clock, run = harness
    run([500,200])
    b.save(job/target, {}, replace=True)
    with pytest.raises((ValueError, KeyError)):
        b.check(p, job)


@pytest.mark.parametrize('field', ['retry_policy','policy_sha256','frames','call_seconds'])
def test_policy_and_logical_shape_fail_before_job(harness, field):
    p, job, _, posts, _, _, _ = harness
    bad = copy.deepcopy(p)
    bad[field] = {} if field == 'retry_policy' else 'changed'
    with pytest.raises(ValueError):
        b.run(bad, job)
    assert not job.exists() and not posts


def test_atomic_replace_existing_budget_and_context(tmp_path):
    for name in ('budget.json','context.json'):
        path = tmp_path/name
        b.save(path, {'old': True})
        b.save(path, {'new': True}, replace=True)
        assert b.old.load(path) == {'new': True}
    assert not list(tmp_path.glob('.pending-*'))


def test_source_change_and_context_fail(harness, monkeypatch):
    p, job, _, posts, _, _, run = harness
    control = job.parent/'control.json'
    b.save(control, p)
    monkeypatch.setattr(b, 'CONTROL', control)
    monkeypatch.setattr(b, 'protocol', lambda: dict(p, sources={}))
    with pytest.raises(ValueError, match='SOURCE_CHANGED'):
        b.verify()
    monkeypatch.setattr(b, 'verify', lambda: p)
    monkeypatch.setattr(b, 'JOB', job)
    run()
    b.save(job/'baseline-report.json', {})
    context = job.parent/'context.json'
    b.save(context, {'mode':'provider_schema_empty'})
    monkeypatch.setattr(b.old, 'CONTEXT', context)
    monkeypatch.setattr(sys, 'argv', ['unique','--check','--report-phase','baseline'])
    with pytest.raises(ValueError, match='CONTEXT_CHANGED'):
        b.main()
    assert len(posts) == 12


def test_numeric_float_guard_unchanged(harness):
    p, *_ = harness
    f = p['frames'][1]
    response = b.old.strict(answer(f['payload']))
    response['choices'][0]['message']['tool_calls'][0]['function']['arguments'] = '{"label":1.0,"candidate_ids":[]}'
    result = b.score(f, response)
    assert result['native_schema_violations'] == 0 and result['assembler_violations'] == 1


@pytest.mark.parametrize('posts,charged,logical,phase,wait,reason', [
    (60,0,0,0,0,'POST_CAP'), (2**32,0,0,0,2,'POST_CAP'),
    (0,32768-4095,0,0,0,'TOKEN_RESERVATION'),
    (0,32768-4095,0,0,2,'TOKEN_RESERVATION'),
    (0,0,58,0,2,'WAIT_DEADLINE'), (0,0,0,896,4,'WAIT_DEADLINE'),
    (0,0,60,0,0,'WALL_LIMIT'), (0,0,0,900,0,'WALL_LIMIT')])
def test_hard_preflight_caps(posts, charged, logical, phase, wait, reason):
    with pytest.raises(ValueError, match=reason):
        b.preflight(dict(physical_posts=posts, charged_tokens=charged), logical, phase, wait)


def test_one_timer_covers_all_attempts_and_waits(harness, monkeypatch):
    p, job, _, posts, _, clock, run = harness
    timers, handlers = [], []
    def set_timer(which, seconds, interval=0):
        timers.append((seconds, interval))
        return (0, 0)
    def set_handler(which, handler):
        handlers.append(handler)
        return 'prior_handler'
    monkeypatch.setattr(b.signal, 'setitimer', set_timer)
    monkeypatch.setattr(b.signal, 'signal', set_handler)
    with pytest.raises(ValueError, match='HTTP_TERMINAL'):
        run([500,500,500,500,500])
    assert timers == [(60,0),(0,0)]
    assert handlers == [b.old.deadline, 'prior_handler']
    assert len(posts) == 5 and clock.waits == [2,4,8,16]


def test_delays_count_in_total_logical_deadline(harness, monkeypatch):
    p, job, _, posts, _, clock, run = harness
    original = b.old.http.client.HTTPSConnection.read
    def slow(self, maximum):
        clock.now += 28
        return original(self, maximum)
    monkeypatch.setattr(b.old.http.client.HTTPSConnection, 'read', slow)
    with pytest.raises(ValueError, match='WAIT_DEADLINE'):
        run([500,500,200])
    assert len(posts) == 2 and clock.waits == [2]
    assert clock.now == 58


def test_additive_dispatch_preserves_prior_bytes():
    measure = (b.ROOT/'.auto/measure.sh').read_text()
    start = measure.index('  --provider-schema-unique-prepare)')
    end = measure.index('  --provider-schema-branch-closure-prepare)')
    assert measure[:start]+measure[end:] == (b.ROOT/'.auto/protocol-archive/provider-unique-pre-measure.sh').read_text()
    checks = (b.ROOT/'.auto/checks.sh').read_text()
    start = checks.index("elif mode == 'provider_schema_unique_ids':")
    end = checks.index("elif mode == 'provider_schema_branch_closure':")
    assert checks[:start]+checks[end:] == (b.ROOT/'.auto/protocol-archive/provider-unique-pre-checks.sh').read_text()


def test_offline_cli_lifecycle_replaces_context_and_never_resumes(harness, monkeypatch):
    p, job, script, posts, clients, clock, run = harness
    control, context = job.parent/'control.json', job.parent/'context.json'
    monkeypatch.setattr(b, 'CONTROL', control)
    monkeypatch.setattr(b, 'JOB', job)
    monkeypatch.setattr(b.old, 'CONTEXT', context)
    b.save(context, {'old_context': True})
    original = b.run
    monkeypatch.setattr(b, 'run', lambda p,j: original(p,j,clock=clock,sleep=clock.sleep))
    monkeypatch.setattr(sys, 'argv', ['retry','--prepare'])
    b.main()
    assert not posts and not job.exists()
    monkeypatch.setattr(sys, 'argv', ['unique','--baseline'])
    script.extend([500,200])
    b.main()
    assert len(posts) == 13
    assert b.old.load(context) == b.context('baseline')
    monkeypatch.setattr(sys, 'argv', ['unique','--check','--report-phase','baseline'])
    b.main()
    assert len(posts) == 13
    monkeypatch.setattr(sys, 'argv', ['unique','--baseline'])
    with pytest.raises(FileExistsError):
        b.main()
    assert len(posts) == 13
    monkeypatch.setattr(sys, 'argv', ['retry','--prepare'])
    with pytest.raises(ValueError, match='JOB_ALREADY_EXISTS'):
        b.main()


def proposed_answer(payload, *, repair_unique=False):
    """Scripted model behavior in tests ONLY, never used by live scoring."""
    proposal = b.old.strict(payload['messages'][1]['content'])['requested_arguments']
    if repair_unique and payload['tools'][0]['function']['parameters']['properties']['candidate_ids'].get('uniqueItems'):
        proposal['candidate_ids'] = list(dict.fromkeys(proposal['candidate_ids']))
    response = b.old.strict(answer(payload))
    response['choices'][0]['message']['tool_calls'][0]['function']['arguments'] = b.old.encode(proposal).decode()
    return b.old.encode(response)


def test_actual_source_red_duplicate_contract():
    r = b.old.root_runner()
    ids = [s['span_id'] for s in r.candidates(b.PAGES, False)]
    control, unique = b.schemas(ids)
    for label in (0, 1, 2):
        duplicate = dict(label=label, candidate_ids=[ids[0], ids[0]])
        assert b.old.validate(control, duplicate) is True
        assert b.old.validate(unique, duplicate) is False
        with pytest.raises(ValueError, match='DUPLICATE_ID'):
            r.submission.assemble_tool(duplicate, {'id':'fictional-unique'}, b.PAGES,
                {'input_tokens':0, 'output_tokens':0, 'inference_time_ms':0})
    assert b.assembler_accepts(dict(label=0, candidate_ids=[ids[0]]))
    assert b.old.validate(unique, dict(label=1, candidate_ids=ids))
    assert b.assembler_accepts(dict(label=1, candidate_ids=ids))


def test_independent_typebox_subset_and_actual_assembler_typed_matrix():
    import itertools
    import subprocess
    ids = [s['span_id'] for s in b.old.root_runner().candidates(b.PAGES, False)]
    control, unique = b.schemas(ids)
    arrays = [list(xs) for size in range(7) for xs in itertools.product(ids, repeat=size)]
    arrays += [[None], [False], [0], [1.0], ['unknown-id'], ids+['unknown-id'], None, {}, 'x']
    labels = [0, 1, 2, True, False, 1.0, 0.0, 2.0, 3, '1', None]
    values = [dict(label=label, candidate_ids=xs) for label in labels for xs in arrays]
    values += [{}, None, [], {'label':1}, {'candidate_ids':[]}, dict(label=1, candidate_ids=[], extra=True)]
    rows = [dict(schema=schema, value=value) for value in values for schema in (control, unique)]
    result = subprocess.run(['node', str(b.ROOT/'.auto/provider_schema_validator.mjs')],
        input=b.old.encode(rows), capture_output=True, check=True, timeout=30)
    native = b.old.strict(result.stdout)
    for value, base_ok, candidate_ok in zip(values, native[::2], native[1::2]):
        assert not candidate_ok or base_ok
        if b.assembler_accepts(value):
            assert base_ok and candidate_ok, value
        if isinstance(value, dict) and type(value.get('label')) is int:
            xs = value.get('candidate_ids')
            if type(xs) is list and all(type(x) is str for x in xs) and len(set(xs)) < len(xs):
                assert not b.assembler_accepts(value) and not candidate_ok
    # TypeBox numerical equality is not lexical JSON/Python integer equality.
    assert b.old.validate(unique, dict(label=1.0, candidate_ids=[]))
    assert not b.assembler_accepts(dict(label=1.0, candidate_ids=[]))


def test_frames_fixed_only_three_metadata_additions():
    frames = b.frames()
    assert len(frames) == 12
    ids = [s['span_id'] for s in b.old.root_runner().candidates(b.PAGES, False)]
    assert all(len(x) == 36 for x in ids)
    for n, (control, unique) in enumerate(zip(frames[::2], frames[1::2])):
        assert control['model'] == unique['model'] == b.old.root_runner().MODELS[n//3]
        assert control['arm'] == 'control' and unique['arm'] == 'unique'
        assert control['requested'] == unique['requested'] == (
            dict(label=0, candidate_ids=[ids[0],ids[0]]),
            dict(label=2, candidate_ids=[ids[1],ids[1]]),
            dict(label=1, candidate_ids=ids))[n%3]
        assert control['payload']['messages'][0] == dict(role='system', content=b.empty.SYSTEM)
        assert b.old.strict(control['payload']['messages'][1]['content'])['source_spans'] == b.old.root_runner().candidates(b.PAGES, False)
        changed = copy.deepcopy(unique['payload'])
        schema = changed['tools'][0]['function']['parameters']
        for node in [schema]+schema['anyOf']:
            assert node['additionalProperties'] is False
            assert set(node['required']) == {'label', 'candidate_ids'}
            assert node['properties']['candidate_ids']['items']['enum'] == ids
            assert node['properties']['candidate_ids'].pop('uniqueItems') is True
        assert changed == control['payload']
        assert set(changed) == {'model','messages','temperature','max_tokens','stream','tools','tool_choice'}


@pytest.mark.parametrize('repair,expected', [(False,4),(True,0)])
def test_paired_reports_actual_failure_counts_shared_cost_and_no_inference(harness, monkeypatch, repair, expected):
    p, job, script, posts, clients, clock, run = harness
    frozen_sources = copy.deepcopy(p['sources'])
    frozen_frames = copy.deepcopy(p['frames'])
    run([lambda payload: proposed_answer(payload, repair_unique=repair)]*12)
    baseline = b.publish(p, job, 'baseline')
    assert baseline['result'][b.METRIC] == 4
    assert baseline['result']['unique_assembler_violations'] == expected
    before = {str(x): x.read_bytes() for x in job.rglob('*') if x.is_file()}
    def forbidden(*a, **kw):
        pytest.fail('REPORT_HTTP_OR_CREDENTIAL')
    monkeypatch.setattr(b.old.Transport, 'request', forbidden)
    monkeypatch.setattr(b.old.root_runner().legacy.c, 'read_key', forbidden)
    monkeypatch.setattr(b, 'run', forbidden)
    candidate = b.publish(p, job, 'candidate')
    assert candidate['result'][b.METRIC] == expected
    assert baseline['result']['new_api_calls'] == 12 and candidate['result']['new_api_calls'] == 0
    assert set(candidate['result']) == set(baseline['result'])
    assert candidate['result']['shared_known_usage'] == baseline['result']['shared_known_usage'] == 144
    assert len(candidate['result']['observations']) == len(baseline['result']['observations']) == 12
    for k in baseline['result']:
        if k not in (b.METRIC, 'new_api_calls'):
            assert baseline['result'][k] == candidate['result'][k]
    assert b.validate_report(p, job, 'candidate') == candidate
    assert b.validate_report(p, job, 'baseline') == baseline
    assert all(Path(name).read_bytes() == data for name,data in before.items())
    assert len(posts) == 12
    assert p['sources'] == frozen_sources and p['frames'] == frozen_frames
    assert b.protocol()['sources'] == frozen_sources
    for phase in ('baseline','candidate'):
        with pytest.raises(FileExistsError):
            b.publish(p, job, phase)


def test_candidate_requires_completed_baseline_and_rejects_tampering(harness):
    p, job, script, posts, clients, clock, run = harness
    with pytest.raises(FileNotFoundError):
        b.publish(p, job, 'candidate')
    assert not job.exists() and not posts
    run()
    with pytest.raises(FileNotFoundError):
        b.publish(p, job, 'candidate')
    assert not (job/'candidate-report-marker').exists()
    baseline = b.publish(p, job, 'baseline')
    baseline['result'][b.METRIC] = 42
    b.save(job/'baseline-report.json', baseline, replace=True)
    with pytest.raises(ValueError, match='REPORT_CHANGED'):
        b.publish(p, job, 'candidate')
    assert not (job/'candidate-report-marker').exists()


def test_cli_candidate_zero_new_http_and_phase_bound_context(harness, monkeypatch):
    p, job, script, posts, clients, clock, run = harness
    control, context = job.parent/'control.json', job.parent/'context.json'
    monkeypatch.setattr(b, 'CONTROL', control)
    monkeypatch.setattr(b, 'JOB', job)
    monkeypatch.setattr(b.old, 'CONTEXT', context)
    b.save(control,p)
    script.extend([lambda payload: proposed_answer(payload, repair_unique=True)]*12)
    original = b.run
    monkeypatch.setattr(b, 'run', lambda p,j: original(p,j,clock=clock,sleep=clock.sleep))
    monkeypatch.setattr(sys, 'argv', ['unique','--baseline'])
    b.main()
    assert b.old.load(context)['report_phase'] == 'baseline'
    def forbidden(*a, **kw):
        pytest.fail('READONLY_HTTP_OR_KEY')
    monkeypatch.setattr(b.old.Transport, 'request', forbidden)
    monkeypatch.setattr(b.old.root_runner().legacy.c, 'read_key', forbidden)
    monkeypatch.setattr(sys, 'argv', ['unique','--candidate'])
    b.main()
    assert len(posts) == 12
    assert b.old.load(context) == b.context('candidate')
    monkeypatch.setattr(sys, 'argv', ['unique','--check','--report-phase','candidate'])
    b.main()
    monkeypatch.setattr(sys, 'argv', ['unique','--check','--report-phase','baseline'])
    with pytest.raises(ValueError, match='CONTEXT_CHANGED'):
        b.main()
    monkeypatch.setattr(sys, 'argv', ['unique','--candidate'])
    with pytest.raises(FileExistsError):
        b.main()
    assert len(posts) == 12
