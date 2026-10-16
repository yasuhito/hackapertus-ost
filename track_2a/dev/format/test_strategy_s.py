"""Single-model native submit strategy, with no inference or credentials."""
import copy
import json

import pytest

import run_comparison as r
import runtime
from test_comparison import offline, item, manifest, response, tool
from test_feedback import booklet_item, MESSAGE


def s_manifest(model):
    value = manifest('S')
    value['models'] = [model]
    return value


@pytest.mark.parametrize('model', r.MODELS)
def test_s_single_parent_submit_assembled(model):
    x = item()
    calls = []
    expected = {'label': 0, 'candidate_ids': x['candidate_ids']}
    def post(role, number, payload):
        calls.append((role, number, copy.deepcopy(payload)))
        assert role == 'parent' and number == 0
        assert payload['model'] == model
        assert [t['function']['name'] for t in payload['tools']] == ['submit']
        assert payload['tool_choice'] == {'type': 'function', 'function': {'name': 'submit'}}
        r.enforce_tools(payload, x['candidate_ids'], role, strategy='S')
        # Physical transport infers child from the submit-only declaration.
        r.enforce_tools(payload, x['candidate_ids'], 'child')
        return response(model, calls=[tool('submit', expected)])
    args, diagnostics, sdk = r.run_b(x, model, post, strategy='S', isolation_guard=True, seconds=30)
    assert args == expected and not diagnostics
    assert len(calls) == 1 and sdk['counts'] == {'parent': 1, 'child': 0}
    assert all(e['role'] == 'parent' for e in sdk['events'])
    assert not any(e.get('toolName') == 'subagent' or e['type'].startswith('package_child') for e in sdk['events'])
    assembled = r.submission.assemble_tool(args, x['case'], x['pages'], {'input_tokens': 80, 'output_tokens': 20, 'inference_time_ms': 1})
    assert assembled['label'] == 0 and assembled['evidence']


@pytest.mark.parametrize('model', r.MODELS)
@pytest.mark.parametrize('label', [0, 2])
def test_s_supporting_span_feedback_repairs(model, label):
    x = booklet_item()
    calls = []
    def post(role, number, payload):
        calls.append((role, number))
        assert role == 'parent'
        assert [t['function']['name'] for t in payload['tools']] == ['submit']
        assert payload['tool_choice']['function']['name'] == 'submit'
        feedback = {'ok': False, 'error': 'SUPPORTING_SPAN_REQUIRED', 'message': MESSAGE}
        seen = any(m['role'] == 'tool' and json.loads(m['content']) == feedback for m in payload['messages'])
        assert seen == (number == 1)
        return response(model, calls=[tool('submit', {'label': label, 'candidate_ids': x['candidate_ids'] if seen else []})])
    args, diagnostics, sdk = r.run_b(x, model, post, strategy='S', isolation_guard=True, seconds=30)
    assert args == {'label': label, 'candidate_ids': x['candidate_ids']}
    assert diagnostics == ['SUPPORTING_SPAN_REQUIRED']
    assert calls == [('parent', 0), ('parent', 1)]
    assert sdk['counts'] == {'parent': 2, 'child': 0}


@pytest.mark.parametrize('model', r.MODELS)
def test_s_child_payload_refused_before_fence(tmp_path, model):
    m = s_manifest(model)
    r.initialize(tmp_path, m)
    ledger = r.Ledger(tmp_path, m, lambda _: pytest.fail('client selected'))
    assert r.fixed_role_model('S', model, 'parent') == model
    with pytest.raises(r.Stop, match='ROLE_MODEL_REFUSED'):
        ledger.post(model, 0, 'child', 0, {'model': model})
    assert ledger.state['requests'] == 0 and not ledger.fence.exists()


@pytest.mark.parametrize('changes', [
    {'models': r.MODELS}, {'models': []}, {'models': ['unknown']},
    {'role_models': {}}, {'models': None},
    {'models': [r.MODELS[0]], 'model': r.MODELS[1]},
])
def test_s_invalid_manifest_refused(changes):
    m = s_manifest(r.MODELS[1])
    m.update(changes)
    with pytest.raises(r.Stop, match='ROLE_MODEL_REFUSED'):
        r.validate_role_models(m)


def test_s_prepare_limits_and_schema():
    m = r.prepare('S')
    assert m['request_limit'] == 180
    assert m['parent_completion_limit'] == 3 and m['child_completion_limit'] == 0
    assert 'role_models' not in m
    for x in m['frozen']:
        schema = r.schemas(x['candidate_ids'], strategy='S')
        assert schema == r.schemas(x['candidate_ids'], child=True)
        assert x['schema_sha256'] == r.legacy.digest(r.legacy.encode(schema))


@pytest.mark.parametrize('selected', [None, r.MODELS[0], r.MODELS[1]])
def test_runtime_s_model_counts_and_replay(tmp_path, monkeypatch, selected):
    monkeypatch.delenv('LLM_MODEL', raising=False)
    monkeypatch.delenv('LLM_NAME', raising=False)
    if selected:
        monkeypatch.setenv('LLM_MODEL', selected)
    model = selected or r.MODELS[1]
    source = tmp_path / 'input.jsonl'
    source.write_text(json.dumps(item()['case']) + '\n')
    output = tmp_path / 'out/predictions.jsonl'
    calls = []
    class Fake:
        def request(self, method, path, payload):
            calls.append(payload)
            assert payload['model'] == model
            assert [t['function']['name'] for t in payload['tools']] == ['submit']
            return response(model, calls=[tool('submit', {'label': 1, 'candidate_ids': []})])
    runtime.execute(source, output, 'S', lambda target: Fake() if target == model else pytest.fail('wrong model'))
    assert len(calls) == 1
    assert json.loads(output.read_text())['label'] == 1
    job = output.parent / 'tmp/format-runtime'
    assert r.legacy.load(job / 'manifest.json')['models'] == [model]
    assert r.legacy.load(job / 'state.json')['requests'] == 1
    runtime.execute(source, output, 'S', lambda _: pytest.fail('replay call'))
