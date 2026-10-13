"""Fixed heterogeneous C policy: offline transport and actual package contracts."""
import copy
import json

import pytest

import run_comparison as r
import runtime
from test_comparison import offline, item, manifest, response, tool


def c_manifest():
    value = manifest('C')
    value.update(models=[r.MODELS[1]], role_models={'parent': r.MODELS[1], 'child': r.MODELS[0]})
    return value


@pytest.mark.parametrize('strategy,owner,role', [
    ('C', r.MODELS[0], 'parent'), ('C', r.MODELS[0], 'child'),
    ('C', r.MODELS[1], 'other'), ('D', r.MODELS[1], 'parent'),
])
def test_fixed_policy_refuses(strategy, owner, role):
    with pytest.raises(r.Stop, match='ROLE_MODEL_REFUSED'):
        r.fixed_role_model(strategy, owner, role)


def test_c_freeze_same_source_and_only_parent_model():
    a, b, c = (r.prepare(s) for s in ('A', 'B', 'C'))
    assert c['models'] == [r.MODELS[1]] and c['request_limit'] == 270
    assert c['role_models'] == {'parent': r.MODELS[1], 'child': r.MODELS[0]}
    assert len(c['frozen']) == 54
    assert a['frozen'] == b['frozen'] == c['frozen']
    assert c['token_budget'] == 6_000_000 and c['request_token_reserve'] == 262400


@pytest.mark.parametrize('role,target', [('child', r.MODELS[1]), ('parent', r.MODELS[0]), ('child', 'unknown')])
def test_c_wrong_payload_before_fence_or_request(tmp_path, role, target):
    m = c_manifest()
    r.initialize(tmp_path, m)
    ledger = r.Ledger(tmp_path, m, lambda _: pytest.fail('client selected'))
    with pytest.raises(r.Stop, match='ROLE_MODEL_REFUSED'):
        ledger.post(r.MODELS[1], 0, role, 0, {'model': target})
    assert ledger.state['requests'] == 0 and not ledger.fence.exists()


def test_c_manifest_wrong_child_refused_before_client(tmp_path):
    m = c_manifest()
    m['role_models']['child'] = r.MODELS[1]
    r.initialize(tmp_path, m)
    with pytest.raises(r.Stop, match='ROLE_MODEL_REFUSED'):
        r.Ledger(tmp_path, m, lambda _: pytest.fail('client selected'))


def test_c_child_server_mismatch_preserves_fence(tmp_path):
    m = c_manifest()
    r.initialize(tmp_path, m)
    selected = []
    class Fake:
        def request(self, *args):
            return response(r.MODELS[1], content='wrong server')
    def factory(model):
        selected.append(model)
        return Fake()
    ledger = r.Ledger(tmp_path, m, factory)
    with pytest.raises(r.Stop, match='UNKNOWN_MODEL'):
        ledger.post(r.MODELS[1], 0, 'child', 0, {'model': r.MODELS[0]})
    assert selected == [r.MODELS[0]] and ledger.fence.exists()
    fence = r.legacy.load(ledger.fence)
    assert fence['model'] == r.MODELS[1] and fence['request_model'] == r.MODELS[0]
    assert ledger.state['blocked'] and ledger.state['reserved_tokens'] == r.RESERVE
    with pytest.raises(r.Stop, match='UNCERTAIN_FENCE'):
        r.Ledger(tmp_path, m, factory)


def synthetic_post(calls):
    def post(role, number, payload):
        calls.append((role, number, copy.deepcopy(payload)))
        name = payload['tool_choice']['function']['name']
        return response(payload['model'], calls=[tool(name, {'mode': 'source_only'} if name == 'subagent' else {'label': 1, 'candidate_ids': []})])
    return post


def test_real_c_sdk_role_models_scope_and_identical_source():
    calls = []
    x = item()
    args, diagnostics, sdk = r.run_b(x, r.MODELS[1], synthetic_post(calls), strategy='C', isolation_guard=True, seconds=30)
    assert args == {'label': 1, 'candidate_ids': []} and not diagnostics
    assert sdk['counts'] == {'parent': 2, 'child': 1}
    assert [p['model'] for _, _, p in calls] == [r.MODELS[1], r.MODELS[0], r.MODELS[1]]
    assert all(next(m['content'] for m in p['messages'] if m['role'] == 'user') == x['messages'][1]['content'] for _, _, p in calls)
    end = next(e for e in sdk['events'] if e['type'] == 'package_child_completed')
    assert end['model'] == r.MODELS[0] and end['tools'] == ['submit']
    events = [e for e in sdk['events'] if e['type'] == 'before_provider_request']
    assert [(e['role'], e['model']) for e in events] == [('parent', r.MODELS[1]), ('child', r.MODELS[0]), ('parent', r.MODELS[1])]


def test_c_whole_case_metrics_and_confirmed_replay(tmp_path):
    m = c_manifest()
    r.initialize(tmp_path, m)
    selected = []
    class Fake:
        def request(self, method, path, payload):
            assert payload['model'] == selected[-1]
            return response(payload['model'], content='synthetic')
    def factory(model):
        selected.append(model)
        return Fake()
    ledger = r.Ledger(tmp_path, m, factory)
    for role, number in [('parent', 0), ('child', 0), ('parent', 1)]:
        ledger.post(r.MODELS[1], 0, role, number, {'model': r.fixed_role_model('C', r.MODELS[1], role)})
    metrics, wait = r.metrics_for(ledger, r.MODELS[1], 0, 120)
    assert metrics == {'input_tokens': 240, 'output_tokens': 60, 'inference_time_ms': 120}
    assert wait >= 0 and ledger.state['tokens'] == 300
    assert all(record['model'] == r.MODELS[1] for record in ledger.records.values())
    ledger = r.Ledger(tmp_path, m, lambda _: pytest.fail('replay call'))
    for role, number in [('parent', 0), ('child', 0), ('parent', 1)]:
        ledger.post(r.MODELS[1], 0, role, number, {'model': r.fixed_role_model('C', r.MODELS[1], role)})
    assert selected == [r.MODELS[1], r.MODELS[0], r.MODELS[1]]


@pytest.mark.parametrize('injected', [None, 'SWISS-AI/APERTUS-V1.5-70B'])
def test_runtime_c_two_cases_canonical_cost_and_replay(tmp_path, monkeypatch, injected):
    monkeypatch.delenv('LLM_MODEL', raising=False)
    monkeypatch.delenv('LLM_NAME', raising=False)
    if injected:
        monkeypatch.setenv('LLM_MODEL', injected)
    source = tmp_path / 'input.jsonl'
    source.write_text(''.join(json.dumps({**item()['case'], 'id': str(i)}) + '\n' for i in range(2)))
    target = tmp_path / 'out/predictions.jsonl'
    selected, calls = [], []
    post = synthetic_post(calls)
    class Fake:
        def __init__(self, model):
            self.model = model
        def request(self, method, path, payload):
            assert self.model == payload['model']
            return post('fake', 0, payload)
    def factory(model):
        selected.append(model)
        return Fake(model)
    runtime.execute(source, target, 'C', factory)
    rows = [json.loads(line) for line in target.read_text().splitlines()]
    assert len(rows) == 2 and len(calls) == 6
    assert selected.count(r.MODELS[0]) == 2 and selected.count(r.MODELS[1]) == 4
    assert all(set(row) == {'id', 'label', 'label_name', 'evidence', 'metrics'} for row in rows)
    assert all(row['metrics']['input_tokens'] == 240 and row['metrics']['output_tokens'] == 60 for row in rows)
    state = r.legacy.load(target.parent / 'tmp/format-runtime/state.json')
    assert state['requests'] == 6 and state['tokens'] == 600
    runtime.execute(source, target, 'C', lambda _: pytest.fail('replay call'))
    assert len(calls) == 6


def test_runtime_c_rejects_8b_parent_before_input_or_credentials(tmp_path, monkeypatch):
    monkeypatch.setenv('LLM_MODEL', r.MODELS[0])
    with pytest.raises(r.Stop, match='ROLE_MODEL_REFUSED'):
        runtime.execute(tmp_path / 'missing', tmp_path / 'out/predictions.jsonl', 'C', lambda _: pytest.fail('call'))


def test_old_b_attempt_without_actual_target_replays(tmp_path):
    m = manifest('B')
    r.initialize(tmp_path, m)
    class Fake:
        def request(self, method, path, payload):
            return response(payload['model'], content='synthetic')
    ledger = r.Ledger(tmp_path, m, lambda _: Fake())
    payload = {'model': r.MODELS[0]}
    ledger.post(r.MODELS[0], 0, 'child', 0, payload)
    name = next(iter(ledger.state['attempts']))
    record = r.legacy.load(tmp_path / name)
    record.pop('request_model')
    # Construct a valid pre-provenance ledger fixture, not a changed live job.
    (tmp_path / name).write_bytes(r.legacy.encode(record))
    ledger.state['attempts'][name] = r.legacy.digest(r.legacy.encode(record))
    r.legacy.state_write(tmp_path / 'state.json', ledger.state)
    replay = r.Ledger(tmp_path, m, lambda _: pytest.fail('old B replay call'))
    assert replay.post(r.MODELS[0], 0, 'child', 0, payload) == record['response']
    assert replay.state['requests'] == 1


@pytest.mark.parametrize('owner,child', [(r.MODELS[0], r.MODELS[0]), (r.MODELS[1], r.MODELS[1]), (r.MODELS[1], 'unknown')])
def test_sdk_refuses_unapproved_c_pair_before_bridge(owner, child):
    import os
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory(prefix='ost-pi-', dir='/tmp') as home:
        env = {'PATH': os.defpath, 'HOME': home, 'PI_CODING_AGENT_DIR': home, 'PI_OFFLINE': '1'}
        for name in ('PI_PACKAGE_ROOT', 'PI_SUBAGENTS_ROOT'):
            if name in os.environ:
                env[name] = os.environ[name]
        result = subprocess.run([r.shutil.which('node'), '--import', str(r.HERE / 'isolation-guard.mjs'), str(r.HERE / 'entry.ts')],
                                input=json.dumps({'strategy': 'C', 'model': owner, 'child_model': child}) + '\n',
                                text=True, capture_output=True, env=env, timeout=30)
        assert result.returncode == 1
        assert json.loads(result.stdout) == {'kind': 'fatal', 'error': 'SDK_FAILED'}
