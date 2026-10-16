"""New transient protocol only; fictional HTTP, real Root logical ledger."""
import json
from pathlib import Path
import sys
import time

import pytest
sys.path.insert(0, str(Path(__file__).parent))
from test_fragment_review import candidate, offline, r, response, candidate_manifest
def post(ledger,role='reviewer',number=0):
    payload={'model':r.fixed_role_model('C',r.MODELS[1],role),'messages':[],
             'temperature':0,'max_tokens':256,'stream':False}
    return ledger.post(r.MODELS[1],0,role,number,payload,deadline=400)
import role_review_transport as t


def setup(tmp_path, monkeypatch, statuses, body=b'capacity overloaded', mutate=None, observed=None):
    job = tmp_path / 'fictional'; manifest = candidate_manifest()
    r.initialize(job, manifest)
    now = [100.]; posts = []; sleeps = []
    monkeypatch.setattr(time, 'monotonic', lambda: now[0])
    monkeypatch.setattr(time, 'sleep', lambda seconds: (sleeps.append(seconds), now.__setitem__(0, now[0] + seconds)))
    monkeypatch.setenv('BASE_URL', 'http://fictional.invalid/v1')
    monkeypatch.setenv('API_KEY', 'fictional-secret')
    class Connection:
        def __init__(self, *args, **kwargs):
            assert 0 < kwargs['timeout'] <= 45
            if observed is not None:
                import signal
                observed.append((kwargs['timeout'], signal.getitimer(signal.ITIMER_REAL)[0]))
        def set_debuglevel(self, value): assert value == 0
        def request(self, method, path, body, headers):
            assert (job / 'physical/inflight.json').exists()
            posts.append(json.loads(body))
        def getresponse(self):
            value = statuses[min(len(posts)-1, len(statuses)-1)]
            if isinstance(value, BaseException): raise value
            class Response:
                status = value
                def read(self, bound):
                    if self.status != 200:
                        assert 65536 <= bound <= 65536 + len(b'Bearer fictional-secret')
                        return body[:bound]
                    data = response(posts[-1]['model'], content='fictional')
                    if mutate: mutate(data)
                    return json.dumps(data).encode()
            return Response()
        def close(self): pass
    Base = t.experimental_transport(r, 1000, Connection)
    side = t.PhysicalLedger(r, job, 1000)
    ledger = r.Ledger(job, manifest, lambda model: side.client(model, lambda model: Base(model, submitted=True)))
    return job, side, ledger, posts, sleeps


@pytest.mark.parametrize('status', [408,425,429,500,502,503,504,599,409])
def test_transient_fifth_success_and_authoritative_unknown_reserves(candidate, tmp_path, monkeypatch, status):
    job, side, ledger, posts, sleeps = setup(tmp_path, monkeypatch, [status]*4+[200])
    post(ledger)
    stats = t.verify(r, job)
    assert len(posts) == 5 and sleeps == [2,4,8,16]
    assert ledger.state['requests'] == 1 and ledger.state['tokens'] == 100
    assert stats['charged_tokens'] == 4*t.RESERVE+100
    assert stats['known_successful_tokens'] == 100 and stats['full_total_tokens'] is None
    assert stats['physical_reviewer_calls'] == 5


@pytest.mark.parametrize('status,body', [(400,b'unsupported schema capacity overloaded'),(500,b'unsupported grammar'),(400,b'invalid input'),
    (401,b'capacity overload'),(403,b'rate limit'),(422,b'grammar'),(404,b'not found')])
def test_permanent_no_retry(candidate, tmp_path, monkeypatch, status, body):
    job, side, ledger, posts, sleeps = setup(tmp_path, monkeypatch, [status], body)
    with pytest.raises(r.Stop): post(ledger)
    assert len(posts) == 1 and not sleeps and side.charged == t.RESERVE
    assert (job/'inflight.json').exists() and (job/'physical/inflight.json').exists()


@pytest.mark.parametrize('error,retry', [(TimeoutError(),True),(ConnectionResetError(),True),(OSError(104,'fictional'),True),(OSError('unknown'),False)])
def test_network_classification_not_confirmed_capacity(candidate,tmp_path,monkeypatch,error,retry):
    job, side, ledger, posts, sleeps = setup(tmp_path,monkeypatch,[error,200])
    if retry:
        post(ledger)
        assert t.verify(r,job)['unknown_failed_count'] == 1
    else:
        with pytest.raises(r.Stop): post(ledger)
    result = r.legacy.load(job/'physical/0001-result.json')
    assert result['http_status'] is None and result['usage'] is None and result['unknown_charge'] == t.RESERVE
    assert result['error_classification'] == ('transient_network' if retry else 'uncertain_transport')
    assert result['exception_kind'] == type(error).__name__


def test_error_excerpt_redaction_and_bound(candidate,tmp_path,monkeypatch):
    body=b'Bearer fictional-secret overloaded '+b'x'*70000
    job, side, ledger, posts, sleeps = setup(tmp_path,monkeypatch,[500,200],body)
    post(ledger)
    data=(job/'physical/0001-result.json').read_text()
    assert 'fictional-secret' not in data and 'Bearer' not in data
    assert len(json.loads(data)['error_excerpt'].encode()) <= 65536
    t.verify(r,job)


@pytest.mark.parametrize('guard', ['exhausted','deadline','physical','budget','storage','invalid_usage','invalid_model','absolute'])
def test_all_guards_preserve_fences_no_success_retry(candidate,tmp_path,monkeypatch,guard):
    mutate = (lambda v:v.pop('usage')) if guard=='invalid_usage' else (lambda v:v.update(model='wrong')) if guard=='invalid_model' else None
    job, side, ledger, posts, sleeps = setup(tmp_path,monkeypatch,[500]*6 if guard=='exhausted' else [200],mutate=mutate)
    if guard=='deadline': side.deadline=100
    if guard=='physical': side.records=[None]*300
    if guard=='budget': side.charged=t.BUDGET-t.RESERVE+1
    if guard=='absolute': monkeypatch.setattr(time,'time',lambda:t.ABSOLUTE_STOP)
    if guard=='storage':
        original=r.legacy.exclusive
        def exclusive(path,value):
            if path.name.endswith('-result.json'): raise OSError('fictional storage uncertainty')
            return original(path,value)
        monkeypatch.setattr(r.legacy,'exclusive',exclusive)
    with pytest.raises((r.Stop,OSError)): post(ledger)
    assert len(posts)==(5 if guard=='exhausted' else 1 if guard in ('storage','invalid_usage','invalid_model') else 0)
    assert (job/'inflight.json').exists()
    with pytest.raises(r.Stop,match='UNCERTAIN_FENCE'): r.Ledger(job,ledger.manifest,None)


def test_wait_cannot_cross_logical_sixty_seconds(candidate,tmp_path,monkeypatch):
    job, side, ledger, posts, sleeps = setup(tmp_path,monkeypatch,[500]*6)
    original=time.sleep
    def slow(seconds): original(seconds+15)
    monkeypatch.setattr(time,'sleep',slow)
    with pytest.raises(r.Stop,match='DEADLINE'): post(ledger)
    assert len(posts) < 5 and (job/'physical/inflight.json').exists()


def test_verifier_rejects_classification_tamper(candidate,tmp_path,monkeypatch):
    job, side, ledger, posts, sleeps = setup(tmp_path,monkeypatch,[429,200])
    post(ledger)
    path=job/'physical/0001-result.json'; value=json.loads(path.read_bytes())
    value['error_classification']='explicit_capacity';path.write_text(json.dumps(value))
    with pytest.raises(ValueError,match='UNKNOWN_CHANGED'):t.verify(r,job)


def test_later_physical_packet_byte_guard(candidate,tmp_path,monkeypatch):
    job, side, ledger, posts, sleeps = setup(tmp_path,monkeypatch,[200])
    post(ledger,'parent',0)
    payload={'model':r.MODELS[1], 'messages':[{'role':'user','content':'x'*240000}],
             'temperature':0,'max_tokens':256,'stream':False}
    with pytest.raises(r.Stop,match='PAYLOAD_BYTE_LIMIT'):
        ledger.post(r.MODELS[1],0,'parent',1,payload,deadline=400)
    assert len(posts)==1 and side.charged==100 and (job/'inflight.json').exists()


def test_known_200_body_timeout_fences_without_resending(candidate,tmp_path,monkeypatch):
    job=tmp_path/'fictional';manifest=candidate_manifest();r.initialize(job,manifest)
    monkeypatch.setenv('BASE_URL','http://fictional.invalid/v1');monkeypatch.setenv('API_KEY','fictional-secret')
    monkeypatch.setattr(time,'sleep',lambda _:None)
    calls=[]
    class Connection:
        def __init__(self,*args,**kwargs):pass
        def set_debuglevel(self,_):pass
        def request(self,*args,**kwargs):calls.append(1)
        def getresponse(self):
            class Response:
                status=200
                def read(self,*args):
                    if len(calls)==1:raise TimeoutError('never log this message')
                    return json.dumps(response(r.MODELS[0],content='fictional')).encode()
            return Response()
        def close(self):pass
    Base=t.experimental_transport(r,time.monotonic()+60,Connection)
    side=t.PhysicalLedger(r,job,time.monotonic()+60)
    ledger=r.Ledger(job,manifest,lambda model:side.client(model,lambda model:Base(model,submitted=True)))
    with pytest.raises(r.Stop):
        ledger.post(r.MODELS[1],0,'reviewer',0,{'model':r.MODELS[0], 'messages':[],
            'temperature':0,'max_tokens':256,'stream':False},deadline=time.monotonic()+60)
    assert calls == [1] and side.charged == t.RESERVE
    assert (job/'inflight.json').exists() and (job/'physical/inflight.json').exists()
    record = json.loads((job/'physical/0001-result.json').read_bytes())
    assert record['http_status'] == 200 and record['error_classification'] == 'permanent'
    assert record['usage'] is None and record['unknown_charge'] == t.RESERVE
    assert 'never log this message' not in (job/'physical/0001-result.json').read_text()


@pytest.mark.parametrize('repeated', [False, True])
def test_secret_crossing_excerpt_boundary_is_fully_redacted(candidate,tmp_path,monkeypatch,repeated):
    key = b'fictional-secret'
    prefix = key * (65536 // len(key)) if repeated else b'x' * (65536-4)
    body = key*5000 if repeated else prefix + key + b' overloaded ' + key*3
    job, side, ledger, posts, sleeps = setup(tmp_path,monkeypatch,[500,200],body)
    post(ledger)
    record = json.loads((job/'physical/0001-result.json').read_bytes())
    excerpt = record['error_excerpt']
    assert excerpt and record['raw_body_unavailable'] is False
    assert key.decode() not in excerpt and 'fict' not in excerpt
    assert len(excerpt.encode()) <= t.BODY_CAP
    t.verify(r,job)


def test_in_progress_socket_and_alarm_are_clamped_to_absolute_stop(candidate,tmp_path,monkeypatch):
    observed = []
    job, side, ledger, posts, sleeps = setup(tmp_path,monkeypatch,[200],observed=observed)
    monkeypatch.setattr(time,'time',lambda:t.ABSOLUTE_STOP-3)
    post(ledger)
    assert len(posts) == 1 and len(observed) == 1
    socket_timeout, alarm_timeout = observed[0]
    assert 0 < socket_timeout <= 3 and 0 < alarm_timeout <= 3
