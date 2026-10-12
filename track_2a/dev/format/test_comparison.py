import copy
import json
from pathlib import Path
import socket
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import run_comparison as r


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*a, **k):
        raise AssertionError('real network forbidden')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(r.legacy.c, 'read_key', forbidden)


def item():
    case = {'id': 'fake', 'claim': {'text': 'Original.'}, 'reference': {'text': 'Original.'}}
    pages, messages = r.legacy.engine().context(case, Path('.'))
    ids = [c['span_id'] for c in r.candidates(pages, True)]
    return {'case': case, 'pages': pages, 'messages': messages, 'messages_sha256': r.legacy.digest(r.legacy.encode(messages)), 'candidate_ids': ids, 'schema_sha256': r.legacy.digest(r.legacy.encode(r.schemas(ids)))}


def manifest(strategy='A'):
    return {'strategy': strategy, 'request_limit': r.LIMITS[strategy], 'token_budget': r.TOKEN_BUDGET, 'frozen': [item() for _ in range(54)]}


def response(model, *, content=None, calls=None):
    return {'id': 'fake', 'model': model, 'choices': [{'finish_reason': 'tool_calls' if calls else 'stop', 'message': {'role': 'assistant', 'content': content, **({'tool_calls': calls} if calls else {})}}], 'usage': {'prompt_tokens': 80, 'completion_tokens': 20, 'total_tokens': 100}}


def tool(name, args):
    return {'id': name + '-1', 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(args)}}


def test_real_sdk_child_then_parent_submit():
    x = item()
    calls = []
    def post(role, number, payload):
        calls.append((role, number, payload))
        name = payload['tool_choice']['function']['name']
        return response(r.MODELS[0], calls=[tool(name, {} if name == 'subagent' else {'label': 0, 'candidate_ids': x['candidate_ids']})])
    args, diagnostics, sdk = r.run_b(x, r.MODELS[0], post, seconds=30, isolation_guard=True)
    assert args == {'label': 0, 'candidate_ids': x['candidate_ids']}
    assert sdk['counts'] == {'parent': 2, 'child': 1}
    assert [c[0] for c in calls] == ['parent', 'child', 'parent']
    assert not diagnostics
    assert all(set(t['function']['name'] for t in p['tools']) <= {'submit', 'subagent'} for _, _, p in calls)
    label_schema = calls[0][2]['tools'][0]['function']['parameters']['properties']['label']
    assert label_schema['type'] == 'integer' and label_schema['enum'] == [0, 1, 2]
    assert sum(e['type'] == 'agent_settled' for e in sdk['events']) == 2
    assert not any(e['type'].startswith('auto_') for e in sdk['events'])
    for name in ('before_provider_request', 'after_provider_response', 'provider_stream_event'):
        assert sum(e['type'] == name for e in sdk['events']) == 3
    assert all('untrusted data' in p['messages'][0]['content'] for _, _, p in calls)


@pytest.mark.parametrize('bad', ['duplicate', 'label'])
def test_sdk_invalid_args_error_then_one_repair(bad):
    x = item()
    calls = []
    def post(role, number, payload):
        calls.append((role, number, payload))
        name = payload['tool_choice']['function']['name']
        args = {} if name == 'subagent' else {'label': 0, 'candidate_ids': x['candidate_ids']}
        if role == 'parent' and number == 1:
            args = {'label': '0', 'candidate_ids': x['candidate_ids']} if bad == 'label' else {'label': 0, 'candidate_ids': x['candidate_ids'] * 2}
        return response(r.MODELS[0], calls=[tool(name, args)])
    args, diagnostics, sdk = r.run_b(x, r.MODELS[0], post, seconds=30)
    assert args and sdk['counts'] == {'parent': 3, 'child': 1}
    assert any(m['role'] == 'tool' and ('error' in m['content'].lower() or 'validation' in m['content'].lower()) for m in calls[-1][2]['messages'])


def test_sdk_text_is_never_scraped():
    x = item()
    calls = []
    def post(role, number, payload):
        calls.append(1)
        return response(r.MODELS[0], content=json.dumps({'label': 0, 'candidate_ids': x['candidate_ids']}))
    args, _, sdk = r.run_b(x, r.MODELS[0], post, seconds=30)
    assert args is None and len(calls) == 1 and sdk['counts']['child'] == 0


class Fake:
    def __init__(self, bad=None):
        self.calls = []
        self.bad = bad
    def __call__(self, model):
        outer = self
        class Client:
            def request(self, method, path, payload):
                outer.calls.append(payload)
                if outer.bad == 'http':
                    raise r.Stop('HTTP_FAILURE')
                value = response(model, content=json.dumps({'label': 1, 'evidence': []}))
                if outer.bad == 'usage':
                    value['usage'] = None
                if outer.bad == 'model':
                    value['model'] = 'other'
                return value
        return Client()


def setup(tmp_path, strategy='A'):
    m = manifest(strategy)
    d = tmp_path / 'job'
    r.initialize(d, m)
    return d, m


def test_full_a_summary_resume_no_duplicates(tmp_path):
    d, m = setup(tmp_path)
    fake = Fake()
    summary = r.run(d, m, fake)
    assert len(fake.calls) == 108 and summary['actual_total_tokens'] == 10800
    r.run(d, m, fake)
    assert len(fake.calls) == 108
    assert len((d / '8b-predictions.jsonl').read_text().splitlines()) == 54
    assert all(set(json.loads(line)) == {'id', 'label', 'label_name', 'evidence', 'metrics'} for line in (d / '8b-canonical.jsonl').read_text().splitlines())


@pytest.mark.parametrize('bad', ['usage', 'model', 'http'])
def test_unsafe_fence_no_resume(tmp_path, bad):
    d, m = setup(tmp_path)
    fake = Fake(bad)
    with pytest.raises(r.Stop):
        r.run(d, m, fake)
    assert (d / 'inflight.json').exists() and len(fake.calls) == 1
    with pytest.raises(r.Stop):
        r.run(d, m, fake)
    assert len(fake.calls) == 1


def test_replay_confirmed_attempt_without_case_does_not_send(tmp_path):
    d, m = setup(tmp_path)
    fake = Fake()
    ledger = r.Ledger(d, m, fake)
    payload = {'model': r.MODELS[0], 'messages': m['frozen'][0]['messages'], 'temperature': 0, 'max_tokens': 256, 'stream': False}
    ledger.post(r.MODELS[0], 0, 'parent', 0, payload)
    r.run(d, m, fake)
    assert len(fake.calls) == 108


def test_storage_reservation_fence_before_post(tmp_path, monkeypatch):
    d, m = setup(tmp_path)
    fake = Fake()
    monkeypatch.setattr(r.legacy, 'state_write', lambda *a: (_ for _ in ()).throw(OSError('disk')))
    with pytest.raises(OSError):
        r.run(d, m, fake)
    assert (d / 'inflight.json').exists() and not fake.calls


@pytest.mark.parametrize('limit', ['requests', 'tokens'])
def test_hard_budget_before_next_post(tmp_path, limit):
    d, m = setup(tmp_path)
    m['request_limit'] = 1 if limit == 'requests' else 216
    m['token_budget'] = r.RESERVE + 99 if limit == 'tokens' else r.TOKEN_BUDGET
    # New job identity with the test bounds.
    d = tmp_path / 'bounded'
    r.initialize(d, m)
    fake = Fake()
    with pytest.raises(r.Stop):
        r.run(d, m, fake)
    assert len(fake.calls) == 1


def test_submitted_injected_url_for_every_call(monkeypatch):
    seen = []
    monkeypatch.setenv('BASE_URL', 'http://proxy.invalid:8123/injected/v1')
    monkeypatch.setenv('API_KEY', 'offline-synthetic')
    class Connection:
        def __init__(self, host, port, **kwargs):
            assert (host, port) == ('proxy.invalid', 8123)
        def set_debuglevel(self, value):
            assert value == 0
        def request(self, method, path, body, headers):
            seen.append(path)
        def getresponse(self):
            class Response:
                status = 200
                def read(self, limit):
                    return json.dumps(response(r.MODELS[0])).encode()
            return Response()
        def close(self):
            pass
    transport = r.Transport(r.MODELS[0], submitted=True, factory=Connection)
    for _ in range(3):
        transport.request('POST', '/v1/chat/completions', {'model': r.MODELS[0], 'temperature': 0, 'max_tokens': 256, 'stream': False, 'messages': []})
    assert seen == ['/injected/v1/chat/completions'] * 3
