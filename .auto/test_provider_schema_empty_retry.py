"""Offline real guarded Transport with scripted HTTPS, never real credentials."""
import copy
from pathlib import Path
import socket
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import provider_schema_empty_retry as b


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
    assert result[b.empty.METRIC] == result['control_assembler_violations'] == 0
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
    b.save(job/'report.json', {})
    context = job.parent/'context.json'
    b.save(context, {'mode':'provider_schema_empty'})
    monkeypatch.setattr(b.old, 'CONTEXT', context)
    monkeypatch.setattr(sys, 'argv', ['retry','--check'])
    with pytest.raises(ValueError, match='CONTEXT_CHANGED'):
        b.main()
    assert len(posts) == 12


def test_numeric_float_guard_unchanged(harness):
    p, *_ = harness
    f = p['frames'][1]
    response = b.old.strict(answer(f['payload']))
    response['choices'][0]['message']['tool_calls'][0]['function']['arguments'] = '{"label":1.0,"candidate_ids":[]}'
    result = b.empty.score(f, response)
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
    start = measure.index('  --provider-schema-empty-retry-prepare)')
    end = measure.index('  --provider-schema-branch-closure-prepare)')
    assert measure[:start]+measure[end:] == (b.ROOT/'.auto/protocol-archive/provider-empty-retry-pre-measure.sh').read_text()
    checks = (b.ROOT/'.auto/checks.sh').read_text()
    start = checks.index("elif mode == 'provider_schema_empty_retry':")
    end = checks.index("elif mode == 'provider_schema_branch_closure':")
    assert checks[:start]+checks[end:] == (b.ROOT/'.auto/protocol-archive/provider-empty-retry-pre-checks.sh').read_text()


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
    monkeypatch.setattr(sys, 'argv', ['retry','--execute'])
    script.extend([500,200])
    b.main()
    assert len(posts) == 13
    assert b.old.load(context) == b.context()
    monkeypatch.setattr(sys, 'argv', ['retry','--check'])
    b.main()
    assert len(posts) == 13
    monkeypatch.setattr(sys, 'argv', ['retry','--execute'])
    with pytest.raises(FileExistsError):
        b.main()
    assert len(posts) == 13
    monkeypatch.setattr(sys, 'argv', ['retry','--prepare'])
    with pytest.raises(ValueError, match='JOB_ALREADY_EXISTS'):
        b.main()
