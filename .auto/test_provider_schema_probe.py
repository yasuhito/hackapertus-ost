"""Fiction only: no credential reads or network. TypeBox is the independent oracle."""
import copy
import json
from pathlib import Path
import socket
import sys
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import provider_schema_probe as p


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*_a, **_k):
        raise AssertionError('NETWORK_OR_CREDENTIAL_READ')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    r = p.root_runner()
    monkeypatch.setattr(r.legacy.c, 'read_key', forbidden)
    monkeypatch.setattr(p, 'root_runner', lambda: r)


def response(args=None, **changes):
    if args is None:
        args = {'label': 0, 'candidate_ids': ['toy-a']}
    value = {'choices': [{'finish_reason': 'tool_calls', 'message': {'tool_calls': [
        {'type': 'function', 'function': {'name': 'submit', 'arguments': json.dumps(args)}}]}}],
        'usage': {'prompt_tokens': 80, 'completion_tokens': 20, 'total_tokens': 100}}
    value.update(changes)
    return value


class FakeTransport:
    def __init__(self, frames, mutate=None):
        self.frames, self.mutate, self.calls = frames, mutate, []

    def request(self, payload):
        index = len(self.calls)
        assert payload == self.frames[index]['payload']
        self.calls.append(copy.deepcopy(payload))
        value = response(self.frames[index]['requested'], model=payload['model'])
        if self.mutate:
            return self.mutate(index, value)
        return 200, json.dumps(value)


def fake_protocol():
    return dict(frames=p.frames(), origin=p.root_runner().legacy.c.BASE)


@pytest.mark.parametrize('change', [{'model': 'wrong'}, {'error': {'message': 'fictional'}}])
def test_response_identity_or_error_refused(change):
    frame = p.frames()[0]
    raw = response(model=frame['model'])
    raw.update(change)
    with pytest.raises(ValueError, match='RESPONSE_IDENTITY_OR_API_ERROR'):
        p.checked_response(frame, json.dumps(raw))


def test_frozen_arity_order_messages_and_exact_h2_schema():
    frames = p.frames()
    assert len(frames) == 12
    assert [f['model'] for f in frames] == [m for m in p.root_runner().MODELS for _ in range(6)]
    for i in range(0, 12, 2):
        simple, conditional = frames[i:i+2]
        assert simple['arm'] == 'simple' and conditional['arm'] == 'conditional'
        assert simple['payload']['messages'] == conditional['payload']['messages']
        a, b = copy.deepcopy(simple['payload']), copy.deepcopy(conditional['payload'])
        schema = b['tools'][0]['function']['parameters']
        assert schema.pop('anyOf') == [{'properties': {'label': {'enum': [1]}}},
                                        {'properties': {'candidate_ids': {'minItems': 1}}}]
        assert a == b
        assert a['tools'][0]['function']['parameters'] == p.root_runner().schemas(['toy-a', 'toy-b'], True)[0]['function']['parameters']
        assert p.score(simple, response(simple['requested']))['violation'] == 0
        assert p.score(conditional, response(conditional['requested']))['violation'] == 0
    assert [f['requested'] for f in frames[::2]][:3] == [
        {'label': 0, 'candidate_ids': ['toy-a']}, {'label': 1, 'candidate_ids': []},
        {'label': 2, 'candidate_ids': ['toy-b']}]


@pytest.mark.parametrize('args', [None, {}, {'label': 0}, {'candidate_ids': ['toy-a']},
    {'label': True, 'candidate_ids': []}, {'label': 3, 'candidate_ids': []},
    {'label': 0, 'candidate_ids': ['other']}, {'label': 0, 'candidate_ids': [], 'extra': 1},
    {'label': 0, 'candidate_ids': ['toy-a'] * 6}, [], 'text'])
@pytest.mark.parametrize('arm', [0, 1])
def test_independent_full_schema(args, arm):
    raw = response()
    raw['choices'][0]['message']['tool_calls'][0]['function']['arguments'] = json.dumps(args)
    assert p.score(p.frames()[arm], raw)['violation'] == 1


@pytest.mark.parametrize('raw', ['{"label":0,"label":1,"candidate_ids":[]}',
                                  '{"label":NaN,"candidate_ids":[]}', '{"label":0,'])
def test_strict_argument_json(raw):
    r = response()
    r['choices'][0]['message']['tool_calls'][0]['function']['arguments'] = raw
    assert p.score(p.frames()[0], r)['violation'] == 1


@pytest.mark.parametrize('mutate', [lambda r: r.update(choices=[]),
    lambda r: r['choices'].append(copy.deepcopy(r['choices'][0])),
    lambda r: r['choices'][0]['message'].update(tool_calls=[]),
    lambda r: r['choices'][0]['message']['tool_calls'].append(copy.deepcopy(r['choices'][0]['message']['tool_calls'][0])),
    lambda r: r['choices'][0]['message']['tool_calls'][0]['function'].update(name='other'),
    lambda r: r['choices'][0]['message'].pop('tool_calls')])
def test_envelope_arity(mutate):
    r = response(); mutate(r)
    assert p.score(p.frames()[0], r)['violation'] == 1


def test_missing_truncation_and_copy_are_separate():
    f = p.frames()[0]
    assert p.score(f, response({'label': 0}))['missing_field'] == 1
    r = response(); r['choices'][0]['finish_reason'] = 'length'
    assert p.score(f, r)['truncation'] == 1 and p.score(f, r)['violation'] == 1
    result = p.score(f, response({'label': 2, 'candidate_ids': ['toy-b']}))
    assert result['violation'] == 0 and result['exact_copy_mismatch'] == 1
    r = response(); r['choices'][0]['finish_reason'] = 'function_call'
    assert p.score(f, r)['violation'] == 0
    # Simple and conditional genuinely differ only on empty IDs with non-1 label.
    r = response({'label': 0, 'candidate_ids': []})
    assert p.score(p.frames()[0], r)['violation'] == 0
    assert p.score(p.frames()[1], r)['violation'] == 1


@pytest.mark.parametrize('u', [{}, {'prompt_tokens': 1, 'completion_tokens': 1},
    {'prompt_tokens': True, 'completion_tokens': 1, 'total_tokens': 2},
    {'prompt_tokens': -1, 'completion_tokens': 1, 'total_tokens': 0},
    {'prompt_tokens': 1, 'completion_tokens': 257, 'total_tokens': 258},
    {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 3},
    {'prompt_tokens': 1001, 'completion_tokens': 1, 'total_tokens': 1002}])
def test_unknown_inconsistent_usage_fatal(u):
    with pytest.raises(ValueError):
        p.score(p.frames()[0], response(usage=u))


def test_complete_nonzero_primary_checks_and_arm_stats(tmp_path):
    protocol = fake_protocol()
    def mutate(index, r):
        if index in (1, 6):
            r = response({'label': 0}, model=r['model'])
        return 200, json.dumps(r)
    fake = FakeTransport(protocol['frames'], mutate)
    job = tmp_path / 'job'
    p.run(protocol, job, fake)
    result = p.check(protocol, job)
    assert len(fake.calls) == 12 and result['schema_contract_violations'] == 2
    assert result['missing_field'] == 2 and result['total_tokens'] == 1200
    assert result['prompt_tokens'] == 960 and result['completion_tokens'] == 240
    assert len(result['per_model_arm']) == 4
    assert all(v['requests'] == 3 for v in result['per_model_arm'].values())
    assert sorted(v['violations'] for v in result['per_model_arm'].values()) == [0, 0, 1, 1]
    assert all((x.stat().st_mode & 0o777) == 0o600 for x in job.iterdir())
    with pytest.raises(FileExistsError):
        p.run(protocol, job, fake)
    path = job / '00-capture.json'
    path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(ValueError, match='CAPTURE_CHANGED'):
        p.check(protocol, job)


@pytest.mark.parametrize('failure', ['non200', 'timeout', 'usage', 'duplicate', 'storage'])
def test_terminal_failures_no_resume(tmp_path, monkeypatch, failure):
    protocol = fake_protocol()
    def mutate(index, r):
        if failure == 'timeout':
            raise TimeoutError()
        if failure == 'non200':
            return 400, '{}'
        if failure == 'usage':
            r.pop('usage')
        if failure == 'duplicate':
            return 200, '{"usage":{},"usage":{}}'
        return 200, json.dumps(r)
    if failure == 'storage':
        original = p.score
        def broken(*args):
            raise OSError('fsync uncertainty')
        monkeypatch.setattr(p, 'score', broken)
    fake = FakeTransport(protocol['frames'], mutate)
    job = tmp_path / 'job'
    with pytest.raises((ValueError, TimeoutError, OSError)):
        p.run(protocol, job, fake)
    assert len(fake.calls) == 1 and (job / 'STOP.json').exists() and (job / 'inflight.json').exists()
    with pytest.raises(FileExistsError):
        p.run(protocol, job, fake)
    assert len(fake.calls) == 1
    with pytest.raises(ValueError, match='TERMINAL'):
        p.check(protocol, job)


def test_payload_allowlist_before_credentials_or_network():
    t = p.Transport(fake_protocol())
    with pytest.raises(ValueError, match='PAYLOAD_REFUSED'):
        t.request({'model': 'unapproved'})


def test_source_change_refused(tmp_path, monkeypatch):
    control = tmp_path / 'control.json'
    monkeypatch.setattr(p, 'CONTROL', control)
    monkeypatch.setattr(p, 'protocol', lambda: {'sources': {'fiction': 'first'}})
    p.save(control, p.protocol())
    assert p.verify() == p.protocol()
    monkeypatch.setattr(p, 'protocol', lambda: {'sources': {'fiction': 'changed'}})
    with pytest.raises(ValueError, match='PROTOCOL_OR_SOURCE_CHANGED'):
        p.verify()


def test_http_guard_defaults_no_env_redirect_retry(monkeypatch):
    monkeypatch.setenv('API_KEY', 'not-used')
    monkeypatch.setenv('BASE_URL', 'https://not-used.invalid')
    made = []
    class Connection:
        def __init__(self, host, port, **kw):
            made.append(self); self.kw = kw; self.requests = []; self.closed = False
        def set_debuglevel(self, level):
            assert level == 0
        def request(self, method, target, **kw):
            self.requests.append((method, target, kw))
        def getresponse(self):
            return type('Reply', (), {'status': 302, 'read': lambda _, cap: b'{}'})()
        def close(self):
            self.closed = True
    monkeypatch.setattr(p.http.client, 'HTTPSConnection', Connection)
    t = p.Transport(fake_protocol())
    # Explicit synthetic credential at transport seam; no real read.
    t.read_key = Mock(return_value='fictional-key')
    payload = p.frames()[0]['payload']
    assert t.request(payload) == (302, '{}')
    assert made[0].closed and made[0].kw['timeout'] == 45 and len(made[0].requests) == 1
    assert made[0].requests[0][2]['headers']['Authorization'] == 'Bearer fictional-key'
    with pytest.raises(ValueError, match='PAYLOAD_REFUSED'):
        t.request(payload)
    assert len(made) == 1 and t.read_key.call_count == 1


def test_budget_refuses_before_send(tmp_path, monkeypatch):
    protocol = fake_protocol(); fake = FakeTransport(protocol['frames'])
    monkeypatch.setattr(p, 'BUDGET', p.RESERVE - 1)
    with pytest.raises(ValueError, match='TOKEN_RESERVATION'):
        p.run(protocol, tmp_path / 'job', fake)
    assert not fake.calls


def test_strict_outer_json():
    for raw in ('{"a":0,"a":1}', '{"a":NaN}', '{"a":Infinity}'):
        with pytest.raises(ValueError):
            p.strict(raw)
