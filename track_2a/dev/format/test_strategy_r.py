"""Input-only routed submit strategy, with no inference or credentials."""
import json

import pytest

import run_comparison as r
import runtime
from test_comparison import offline, item, response, tool
from test_feedback import booklet_item


def r_manifest():
    return {'strategy': 'R', 'models': [r.MODELS[1]], 'request_limit': r.LIMITS['R'],
            'token_budget': r.TOKEN_BUDGET, 'frozen': [booklet_item(), item()]}


def test_r_routed_submit_and_nominal_summary(tmp_path):
    m = r_manifest()
    calls = []
    class Fake:
        def __init__(self, model):
            self.model = model
        def request(self, method, path, payload):
            index = len(calls)
            x = m['frozen'][index]
            expected = r.MODELS[1 - index]
            assert self.model == payload['model'] == expected
            assert [t['function']['name'] for t in payload['tools']] == ['submit']
            assert payload['tool_choice'] == {'type': 'function', 'function': {'name': 'submit'}}
            r.enforce_tools(payload, x['candidate_ids'], 'parent', strategy='R')
            calls.append(payload)
            return response(expected, calls=[tool('submit', {'label': 0, 'candidate_ids': x['candidate_ids']})])
    r.initialize(tmp_path, m)
    summary = r.run_locked(tmp_path, m, Fake)
    assert len(calls) == summary['generation_requests'] == 2
    assert list(summary['models']) == [r.MODELS[1]]
    assert summary['models'][r.MODELS[1]]['prompt_tokens'] == 160
    assert summary['models'][r.MODELS[1]]['completion_tokens'] == 40
    assert summary['calls_by_actual_model'] == dict.fromkeys(r.MODELS, 1)
    assert (tmp_path / '70b-canonical.jsonl').exists()
    assert not list(tmp_path.glob('8b-*'))
    for index, expected in enumerate(reversed(r.MODELS)):
        name = r.legacy.result_name(r.MODELS[1], index)
        case = r.legacy.load(tmp_path / name.replace('.json', '-case.json'))
        attempt = r.legacy.load(tmp_path / name.replace('.json', '-parent-0.json'))
        assert case['model'] == attempt['model'] == r.MODELS[1]
        assert case['request_model'] == attempt['request_model'] == expected
        assert case['sdk']['counts'] == {'parent': 1, 'child': 0}
        assert not case['diagnostics'] and case['output_valid']
        assert not any(e.get('toolName') == 'subagent' or e['type'].startswith('package_child')
                       for e in case['sdk']['events'])


@pytest.mark.parametrize('index', [0, 1])
@pytest.mark.parametrize('role', ['parent', 'child'])
def test_r_wrong_model_or_child_refused_before_fence(tmp_path, index, role):
    m = r_manifest()
    r.initialize(tmp_path, m)
    ledger = r.Ledger(tmp_path, m, lambda _: pytest.fail('client selected'))
    expected = r.MODELS[1 - index]
    wrong = r.MODELS[index]
    assert r.fixed_role_model('R', r.MODELS[1], 'parent', m['frozen'][index]['case']) == expected
    with pytest.raises(r.Stop, match='ROLE_MODEL_REFUSED'):
        ledger.post(expected, index, role, 0, {'model': wrong if role == 'parent' else expected})
    assert ledger.state['requests'] == 0 and not ledger.fence.exists()


@pytest.mark.parametrize('changes', [
    {'models': r.MODELS}, {'models': []}, {'models': [r.MODELS[0]]},
    {'models': None}, {'role_models': {}}, {'model': r.MODELS[0]},
])
def test_r_invalid_manifest_refused(changes):
    m = r_manifest()
    m.update(changes)
    with pytest.raises(r.Stop, match='ROLE_MODEL_REFUSED'):
        r.validate_role_models(m)


def test_r_prepare_limits_and_schema():
    m = r.prepare('R')
    assert m['models'] == [r.MODELS[1]] and 'role_models' not in m
    assert m['request_limit'] == r.LIMITS['S']
    assert m['parent_completion_limit'] == 3 and m['child_completion_limit'] == 0
    for x in m['frozen']:
        schema = r.schemas(x['candidate_ids'], strategy='R')
        assert schema == r.schemas(x['candidate_ids'], strategy='S')
        assert x['schema_sha256'] == r.legacy.digest(r.legacy.encode(schema))


def test_runtime_r_routes_with_nominal_owner_and_replay(tmp_path, monkeypatch):
    monkeypatch.setenv('LLM_MODEL', r.MODELS[0])
    cases = [booklet_item()['case'], item()['case']]
    cases[0]['id'] = 'booklet'
    source = tmp_path / 'input.jsonl'
    source.write_text(''.join(json.dumps(case) + '\n' for case in cases))
    engine = r.legacy.engine()
    original = engine.context
    monkeypatch.setattr(engine, 'context', lambda case, base: (booklet_item()['pages'], booklet_item()['messages'])
                        if 'booklet' in case else original(case, base))
    monkeypatch.setattr(r.legacy, 'engine', lambda: engine)
    output = tmp_path / 'out/predictions.jsonl'
    calls = []
    class Fake:
        def __init__(self, model):
            self.model = model
        def request(self, method, path, payload):
            assert self.model == payload['model'] == r.MODELS[1 - len(calls)]
            assert [t['function']['name'] for t in payload['tools']] == ['submit']
            calls.append(payload)
            return response(self.model, calls=[tool('submit', {'label': 1, 'candidate_ids': []})])
    runtime.execute(source, output, 'R', Fake)
    assert len(calls) == 2
    assert [json.loads(line)['label'] for line in output.read_text().splitlines()] == [1, 1]
    job = output.parent / 'tmp/format-runtime'
    assert r.legacy.load(job / 'manifest.json')['models'] == [r.MODELS[1]]
    assert r.legacy.load(job / 'state.json')['requests'] == 2
    for index, expected in enumerate(reversed(r.MODELS)):
        record = r.legacy.load(job / r.legacy.result_name(r.MODELS[1], index).replace('.json', '-case.json'))
        assert record['model'] == r.MODELS[1] and record['request_model'] == expected
        assert record['sdk']['counts'] == {'parent': 1, 'child': 0}
        assert record['prediction']['metrics']['input_tokens'] == 80
    runtime.execute(source, output, 'R', lambda _: pytest.fail('replay call'))
