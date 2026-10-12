"""Offline submitted JSONL E2E, including actual Pi sessions."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import runtime
import run_comparison as r
from test_comparison import offline, response, tool


def test_runtime_a_b_share_assembler(tmp_path, monkeypatch):
    monkeypatch.setenv('LLM_MODEL', r.MODELS[0])
    input_path = tmp_path / 'input.jsonl'
    cases = [
        {'id': 'entails', 'reference': {'text': 'Original.'}, 'claim': {'text': 'Original.'}},
        {'id': 'fallback', 'reference': {'text': 'Other.'}, 'claim': {'text': 'Original.'}},
    ]
    input_path.write_text(''.join(json.dumps(x) + '\n' for x in cases))
    results = {}
    for strategy in ('A', 'B'):
        calls = []
        class Fake:
            def request(self, method, path, payload):
                calls.append(payload)
                user = next(m for m in payload['messages'] if m['role'] == 'user')
                source = json.loads(user['content'])['source_spans'][0]
                if source['text'] == 'Other.':
                    return response(r.MODELS[0], content='not a submission')
                if strategy == 'A':
                    return response(r.MODELS[0], content=json.dumps({'label': 'entailment', 'evidence': [source['span_id']]}))
                name = payload['tool_choice']['function']['name']
                return response(r.MODELS[0], calls=[tool(name, {} if name == 'subagent' else {'label': 0, 'candidate_ids': [source['span_id']]})])
        output = tmp_path / strategy / 'predictions.jsonl'
        runtime.execute(input_path, output, strategy, lambda model: Fake())
        rows = [json.loads(line) for line in output.read_text().splitlines()]
        assert len(rows) == 2 and all(set(row) == {'id', 'label', 'label_name', 'evidence', 'metrics'} for row in rows)
        results[strategy] = [{k: v for k, v in row.items() if k != 'metrics'} for row in rows]
        evaluations = [json.loads(line) for line in output.with_suffix('.jsonl.evaluation.jsonl').read_text().splitlines()]
        assert evaluations[1]['error'] == 'NO_ACCEPTED_SUBMIT' and evaluations[1]['label'] == 1
        from score import score
        scored = score([{'id': 'fallback', 'label': 1, 'task': 'beginner'}], [evaluations[1]])
        assert scored['invalid_or_missing'] == 1 and scored['macro_f1']['overall']['value'] == 0
        count = len(calls)
        runtime.execute(input_path, output, strategy, lambda model: Fake())
        assert len(calls) == count
        assert rows[0]['metrics']['input_tokens'] == (80 if strategy == 'A' else 240)
    assert results['A'] == results['B']


def test_empty_runtime_no_calls(tmp_path, monkeypatch):
    monkeypatch.setenv('LLM_MODEL', r.MODELS[0])
    source = tmp_path / 'empty.jsonl'
    source.write_text('')
    output = tmp_path / 'out/predictions.jsonl'
    runtime.execute(source, output, 'B', lambda _: pytest.fail('remote call'))
    assert output.read_bytes() == b''


def test_runtime_requires_injected_endpoint(monkeypatch):
    monkeypatch.delenv('BASE_URL', raising=False)
    monkeypatch.delenv('API_KEY', raising=False)
    with pytest.raises(r.Stop, match='INJECTED'):
        r.Transport(r.MODELS[0], submitted=True)


@pytest.mark.parametrize('variable,value,allowed', [
    ('LLM_MODEL', 'swiss-ai/apertus-v1.5-8b', r.MODELS[0]),
    ('LLM_NAME', 'SWISS-AI/APERTUS-V1.5-70B', r.MODELS[1]),
])
def test_runtime_model_casefold_and_same_protocol_reminder(tmp_path, monkeypatch, variable, value, allowed):
    monkeypatch.delenv('LLM_MODEL', raising=False)
    monkeypatch.delenv('LLM_NAME', raising=False)
    monkeypatch.setenv(variable, value)
    source = tmp_path / 'input.jsonl'
    source.write_text(json.dumps({'id': 'same-protocol', 'reference': {'text': 'Original.'}, 'claim': {'text': 'Original.'}}) + '\n')
    selected = []
    class Fake:
        def request(self, method, path, payload):
            assert payload['model'] == allowed
            assert payload['messages'][0]['content'].endswith('\n\n' + r.legacy.PROTOCOL_REMINDER)
            return response(allowed, content='{"label":1,"evidence":[]}')
    def client(model):
        selected.append(model)
        return Fake()
    runtime.execute(source, tmp_path / 'out/predictions.jsonl', 'A', client)
    assert selected == [allowed]


def test_runtime_does_not_normalize_unknown_or_thinking_models(tmp_path, monkeypatch):
    source = tmp_path / 'empty.jsonl'
    source.write_text('')
    monkeypatch.setenv('LLM_MODEL', 'swiss-ai/apertus-v1.5-8b-thinking')
    with pytest.raises(r.Stop, match='MODEL_REFUSED'):
        runtime.execute(source, tmp_path / 'out/predictions.jsonl', 'B', lambda _: pytest.fail('remote'))
