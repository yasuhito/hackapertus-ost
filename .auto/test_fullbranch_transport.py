"""Fictional HTTP transport tests, through unmodified Root Ledger.post."""
import copy
import json
from pathlib import Path
import socket
import sys
import time
import pytest
sys.path.insert(0, str(Path(__file__).parent))
import fullbranch_transport as p
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'track_2a/dev/format'))
import run_comparison as r
from test_comparison import item, response


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*a, **k):
        raise AssertionError('network/real credentials forbidden')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(r.legacy.c, 'read_key', forbidden)
    monkeypatch.setenv('BASE_URL', 'http://fictional.invalid/v1')
    monkeypatch.setenv('API_KEY', 'fictional-secret-never-record')


def setup(tmp_path, monkeypatch, statuses, mutate=None):
    job = tmp_path / 'job'
    m = {'strategy': 'C', 'models': [r.MODELS[1]],
         'role_models': {'parent': r.MODELS[1], 'child': r.MODELS[0]},
         'request_limit': 300, 'token_budget': p.BUDGET, 'frozen': [item()]}
    r.initialize(job, m)
    posts, sleeps = [], []
    now = [100.0]
    monkeypatch.setattr(time, 'monotonic', lambda: now[0])
    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds
    monkeypatch.setattr(time, 'sleep', sleep)
    class Connection:
        def __init__(self, *args, **kwargs):
            assert kwargs['timeout'] == 45
        def set_debuglevel(self, value):
            assert value == 0
        def request(self, method, path, body, headers):
            assert method == 'POST' and path == '/v1/chat/completions'
            assert headers['Authorization'] == 'Bearer fictional-secret-never-record'
            assert (job / 'physical/inflight.json').exists()
            assert (job / 'inflight.json').exists()
            posts.append(json.loads(body))
        def getresponse(self):
            status_value = statuses[min(len(posts)-1, len(statuses)-1)]
            if isinstance(status_value, BaseException):
                raise status_value
            class HTTPResponse:
                status = status_value
                def read(self, *args):
                    assert self.status == 200, 'non200 bodies must not be read'
                    value = response(posts[-1]['model'], content='fictional')
                    if mutate:
                        mutate(value)
                    return json.dumps(value).encode()
            return HTTPResponse()
        def close(self):
            pass
    def base(model):
        return r.Transport(model, submitted=True, factory=Connection)
    side = p.PhysicalLedger(r, job, 1000)
    ledger = r.Ledger(job, m, lambda model: side.client(model, base))
    payload = {'model': r.MODELS[1], 'messages': [], 'temperature': 0,
               'max_tokens': 256, 'stream': False}
    return job, side, ledger, payload, posts, sleeps, now


def post(ledger, payload, number=0, role='parent'):
    return ledger.post(r.MODELS[1], 0, role, number, payload, deadline=400)


def test_four_500_then_200_one_logical_request(tmp_path, monkeypatch):
    job, side, ledger, payload, posts, sleeps, _ = setup(tmp_path, monkeypatch, [500]*4+[200])
    result = post(ledger, payload)
    assert result['usage']['total_tokens'] == 100
    assert sleeps == [2, 4, 8, 16] and len(posts) == 5
    assert ledger.state['requests'] == 1 and ledger.state['tokens'] == 100
    stats = p.verify(r, job)
    assert stats['physical_requests'] == 5 and stats['unknown_failed_count'] == 4
    assert stats['reserved_unknown_charge'] == 4*262400
    assert stats['charged_tokens'] == 4*262400+100
    assert stats['full_total_tokens'] is None and not stats['full_usage_known']
    assert not (job / 'physical/inflight.json').exists()
    assert 'fictional-secret' not in ''.join(x.read_text() for x in (job / 'physical').iterdir())
    assert len(ledger.state['attempts']) == 1


@pytest.mark.parametrize('statuses,count,waits', [([500]*5,5,[2,4,8,16]), ([500,400],2,[2]),
    ([429],1,[]), ([502],1,[]), ([503],1,[]), ([TimeoutError()],1,[])])
def test_only_500_retries_fatal_fences(tmp_path, monkeypatch, statuses, count, waits):
    job, side, ledger, payload, posts, sleeps, _ = setup(tmp_path, monkeypatch, statuses)
    with pytest.raises(r.Stop):
        post(ledger, payload)
    assert len(posts) == count and sleeps == waits
    assert (job / 'inflight.json').exists() and (job / 'physical/inflight.json').exists()
    assert ledger.state['requests'] == 1 and ledger.state['reserved_tokens'] == r.RESERVE
    assert side.charged == count*r.RESERVE
    with pytest.raises(r.Stop, match='UNCERTAIN_FENCE'):
        r.Ledger(job, ledger.manifest, lambda _: pytest.fail('resume'))


@pytest.mark.parametrize('mutate', [lambda v: v.pop('usage'), lambda v: v.update(model='changed'),
    lambda v: v['usage'].update(prompt_tokens_details={'cached_tokens': -1}),
    lambda v: v.update(choices=[]), lambda v: v.update(error='unsafe'),
    lambda v: v['choices'][0]['message'].update(tool_calls=[{}]),
    lambda v: v['usage'].update(total_tokens=True)])
def test_unknown_200_or_unsafe_never_retries(tmp_path, monkeypatch, mutate):
    job, side, ledger, payload, posts, sleeps, _ = setup(tmp_path, monkeypatch, [200], mutate)
    with pytest.raises(r.Stop):
        post(ledger, payload)
    assert len(posts) == 1 and not sleeps
    assert (job / 'physical/inflight.json').exists()


@pytest.mark.parametrize('guard', ['bytes', 'phase', 'wait_deadline', 'budget', 'cap', 'constructor', 'storage'])
def test_guards_before_every_post_or_wait(tmp_path, monkeypatch, guard):
    job, side, ledger, payload, posts, sleeps, now = setup(tmp_path, monkeypatch, [500,200])
    if guard == 'bytes':
        payload['messages'] = [{'role':'user','content':'x'*240000}]
    elif guard == 'phase':
        side.deadline = now[0]
    elif guard == 'wait_deadline':
        side.deadline = now[0]+1
    elif guard == 'budget':
        side.charged = p.BUDGET-p.RESERVE+1
    elif guard == 'cap':
        side.records = [None]*300
    elif guard == 'constructor':
        def failed(model):
            raise r.Stop('CONSTRUCTOR_FAILED')
        ledger.client_factory = lambda model: side.client(model, failed)
    else:
        original = r.legacy.exclusive
        def failed(path, value):
            if path.name.endswith('-before.json'):
                raise OSError('fictional disk failure')
            return original(path, value)
        monkeypatch.setattr(r.legacy, 'exclusive', failed)
    with pytest.raises((r.Stop, OSError)):
        post(ledger, payload)
    assert len(posts) == (1 if guard == 'wait_deadline' else 0)
    assert not sleeps
    if guard == 'constructor':
        assert side.charged == p.RESERVE
        assert r.legacy.load(job / 'physical/0001-result.json')['usage_known'] is False


def test_physical_300_not_1500_and_role_models(tmp_path, monkeypatch):
    job, side, ledger, payload, posts, sleeps, _ = setup(tmp_path, monkeypatch, [200])
    for n in range(300):
        role = 'parent' if n%2 == 0 else 'child'
        q = {**payload, 'model': r.MODELS[1] if role == 'parent' else r.MODELS[0]}
        post(ledger, q, n, role)
    with pytest.raises(r.Stop, match='HARD_BUDGET'):
        post(ledger, payload, 300)
    assert len(posts) == 300
    stats = p.verify(r, job)
    assert stats['physical_parent_calls'] == stats['physical_child_calls'] == 150
    assert stats['charged_tokens'] == 30000 and stats['full_total_tokens'] == 30000
    assert p.BUDGET == p.CAP*p.RESERVE == 78720000


@pytest.mark.parametrize('change', ['digest', 'extra', 'wait', 'charge', 'success'])
def test_side_bijection_or_digest_mutations_refused(tmp_path, monkeypatch, change):
    job, side, ledger, payload, posts, sleeps, _ = setup(tmp_path, monkeypatch, [500,200])
    post(ledger, payload)
    path = job / 'physical/0002-result.json'
    value = r.legacy.load(path)
    if change == 'digest':
        value['logical_payload_sha256'] = 'wrong'
    elif change == 'extra':
        (job / 'physical/extra.json').write_text('{}')
    elif change == 'wait':
        (job / 'physical/0001-wait.json').write_text('{"seconds": 3}')
    elif change == 'charge':
        value['charged_after'] += 1
    else:
        value['response']['model'] = 'wrong'
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        p.verify(r, job)

@pytest.mark.parametrize('guard', ['budget','cap'])
def test_next_attempt_or_wait_guard_after_unknown500(tmp_path,monkeypatch,guard):
    job,side,ledger,payload,posts,sleeps,_=setup(tmp_path,monkeypatch,[500,200])
    if guard=='budget':side.charged=p.BUDGET-p.RESERVE
    else:side.records=[None]*299
    with pytest.raises(r.Stop,match='PHYSICAL_BUDGET'):
        post(ledger,payload)
    assert len(posts)==1 and not sleeps
    assert (job/'physical/inflight.json').exists()


def test_malformed_return_never_retried(tmp_path,monkeypatch):
    job,side,ledger,payload,posts,sleeps,_=setup(tmp_path,monkeypatch,[200])
    class Bad:
        def __init__(self,model):pass
        def request(self,*args):return []
    ledger.client_factory=lambda model:side.client(model,Bad)
    with pytest.raises(r.Stop):post(ledger,payload)
    assert len(side.records)==1 and not sleeps
    assert side.records[0]['http_status']==200
    assert not side.records[0]['safe_success']
