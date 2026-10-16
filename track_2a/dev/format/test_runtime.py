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
                return response(r.MODELS[0], calls=[tool(name, {'mode': 'source_only'} if name == 'subagent' else {'label': 0, 'candidate_ids': [source['span_id']]})])
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


@pytest.mark.parametrize('filename', ['package-child.mjs', 'safe-submit-child.ts', 'dependencies.mjs', 'entry.ts', 'package.json', 'package-lock.json'])
def test_runtime_child_dependency_mutation_refuses_resume_before_calls(tmp_path, monkeypatch, filename):
    import shutil
    code = tmp_path / 'code'
    code.mkdir()
    for path in r.HERE.iterdir():
        if path.is_file() and path.suffix in ('.py', '.ts', '.mjs', '.json'):
            shutil.copyfile(path, code / path.name)
    monkeypatch.setattr(r, 'HERE', code)
    monkeypatch.setenv('LLM_MODEL', r.MODELS[0])
    source = tmp_path / 'input.jsonl'
    source.write_text(json.dumps({'id': 'dependency-identity', 'reference': {'text': 'Original.'}, 'claim': {'text': 'Original.'}}) + '\n')
    calls = []
    class Fake:
        def request(self, method, path, payload):
            calls.append(1)
            return response(r.MODELS[0], content='{"label":1,"evidence":[]}')
    target = tmp_path / 'out/predictions.jsonl'
    runtime.execute(source, target, 'A', lambda _: Fake())
    assert calls == [1]
    original = target.read_bytes()
    changed = code / filename
    changed.write_bytes(changed.read_bytes() + b'\n')
    with pytest.raises(r.Stop, match='MANIFEST_CHANGED'):
        runtime.execute(source, target, 'A', lambda _: pytest.fail('client after changed dependency'))
    assert calls == [1] and target.read_bytes() == original


def test_final_image_includes_dependency_lock_for_runtime_fingerprint():
    import shlex
    final = (r.REPO / 'Dockerfile.agent').read_text().split('FROM ')[-1]
    copied = [shlex.split(line) for line in final.splitlines() if line.startswith('COPY ')]
    assert any('track_2a/dev/format/package-lock.json' in parts[1:-1]
               and parts[-1] == '/app/track_2a/dev/format/' for parts in copied)


def test_cpu_build_installs_node_shared_library_and_targets_amd64():
    dockerfile = (r.REPO / 'Dockerfile.agent').read_text()
    final = dockerfile.split('FROM ')[-1]
    assert 'libatomic1' in final
    assert 'COPY --from=pi /usr/local/LICENSE /usr/share/doc/node/LICENSE' in final
    assert '--platform=linux/amd64' not in dockerfile
    assert 'docker build --platform linux/amd64 -f $(DOCKERFILE)' in (r.REPO / 'Makefile').read_text()


def test_runtime_scales_limits_to_120_cases(tmp_path, monkeypatch):
    monkeypatch.setenv('LLM_MODEL', r.MODELS[0])
    source = tmp_path / 'input.jsonl'
    source.write_text(''.join(json.dumps({'id': str(i), 'reference': {'text': 'Original.'}, 'claim': {'text': 'Original.'}}) + '\n' for i in range(120)))
    class Fake:
        def request(self, method, path, payload):
            return response(r.MODELS[0], content='{"label":1,"evidence":[]}')
    output = tmp_path / 'out/predictions.jsonl'
    runtime.execute(source, output, 'A', lambda _: Fake())
    manifest = json.loads((output.parent / 'tmp/format-runtime/manifest.json').read_text())
    assert len(manifest['frozen']) == 120
    assert manifest['request_limit'] == 600
    assert manifest['token_budget'] == 600 * 262400
    assert len(output.read_text().splitlines()) == 120


@pytest.mark.parametrize('failure', [r.Stop('TRANSPORT_UNCERTAIN_NO_RETRY'), RuntimeError('secret body')])
def test_runtime_case_failure_continues_and_resumes(tmp_path, monkeypatch, failure):
    monkeypatch.setenv('LLM_MODEL', r.MODELS[0])
    source = tmp_path / 'input.jsonl'
    source.write_text(''.join(json.dumps({'id': str(i), 'reference': {'text': 'Original.'}, 'claim': {'text': 'Original.'}}) + '\n' for i in range(4)))
    calls = []
    class Fake:
        def request(self, method, path, payload):
            calls.append(payload)
            if len(calls) == 2:
                raise failure
            user = next(m for m in payload['messages'] if m['role'] == 'user')
            span = json.loads(user['content'])['source_spans'][0]['span_id']
            return response(r.MODELS[0], content=json.dumps({'label': 0, 'evidence': [span]}))
    output = tmp_path / 'out/predictions.jsonl'
    runtime.execute(source, output, 'A', lambda _: Fake())
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert [row['id'] for row in rows] == ['0', '1', '2', '3']
    assert [row['label'] for row in rows] == [0, 1, 0, 0]
    assert rows[1]['evidence'] == []
    assert rows[1]['metrics']['input_tokens'] == 0
    assert rows[1]['metrics']['inference_time_ms'] > 0
    assert rows[2]['metrics']['input_tokens'] == 80
    diagnostics = [json.loads(line) for line in output.with_suffix('.jsonl.diagnostics.jsonl').read_text().splitlines()]
    code = 'TRANSPORT_UNCERTAIN_NO_RETRY' if isinstance(failure, r.Stop) else 'CASE_FAILED'
    assert diagnostics[1] == {'id': '1', 'error': code, 'diagnostics': [code]}
    assert all(row['error'] is None for i, row in enumerate(diagnostics) if i != 1)
    job = output.parent / 'tmp/format-runtime'
    assert not (job / 'STOP.json').exists()
    assert not (job / 'inflight.json').exists()
    state = json.loads((job / 'state.json').read_text())
    assert state['reserved_tokens'] == 0 and state['blocked'] is False
    original = output.read_bytes()
    runtime.execute(source, output, 'A', lambda _: pytest.fail('saved cases must be skipped'))
    assert output.read_bytes() == original and len(calls) == 4
    output.write_bytes(b'changed\n')
    with pytest.raises(r.Stop, match='EXISTING_OUTPUT_CHANGED'):
        runtime.execute(source, output, 'A', lambda _: pytest.fail('saved cases must be skipped'))


def test_runtime_rejects_duplicate_ids(tmp_path, monkeypatch):
    monkeypatch.setenv('LLM_MODEL', r.MODELS[0])
    source = tmp_path / 'input.jsonl'
    case = {'id': 'duplicate', 'reference': {'text': 'Original.'}, 'claim': {'text': 'Original.'}}
    source.write_text((json.dumps(case) + '\n') * 2)
    with pytest.raises(r.Stop, match='INPUT_COUNT_OR_DUPLICATE_IDS'):
        runtime.execute(source, tmp_path / 'out/predictions.jsonl', 'A', lambda _: pytest.fail('remote call'))


def test_runtime_unknown_response_preserves_block_and_known_usage(tmp_path, monkeypatch):
    monkeypatch.setenv('LLM_MODEL', r.MODELS[0])
    source = tmp_path / 'input.jsonl'
    source.write_text(''.join(json.dumps({'id': str(i), 'reference': {'text': 'Original.'}, 'claim': {'text': 'Original.'}}) + '\n' for i in range(2)))
    calls = []
    class Fake:
        def request(self, method, path, payload):
            calls.append(payload)
            return response(r.MODELS[1] if len(calls) == 1 else r.MODELS[0], content='{"label":1,"evidence":[]}')
    output = tmp_path / 'out/predictions.jsonl'
    runtime.execute(source, output, 'A', lambda _: Fake())
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert len(rows) == 2 and len(calls) == 2
    assert rows[0]['metrics']['input_tokens'] == 80
    sidecar = [json.loads(line) for line in output.with_suffix('.jsonl.diagnostics.jsonl').read_text().splitlines()]
    assert sidecar[0]['error'] == 'UNKNOWN_MODEL_USAGE_OR_RESPONSE_ALL_STOP'
    assert sidecar[1]['error'] is None
    job = output.parent / 'tmp/format-runtime'
    state = json.loads((job / 'state.json').read_text())
    assert state['blocked'] is True and state['reserved_tokens'] == 0
    assert not (job / 'inflight.json').exists() and not (job / 'STOP.json').exists()
