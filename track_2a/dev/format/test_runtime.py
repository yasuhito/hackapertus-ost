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


@pytest.fixture
def booklet_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv('LLM_MODEL', r.MODELS[0])
    engine = r.legacy.engine()
    monkeypatch.setattr(engine, 'pdf_pages', lambda _: (
        '', '3 Erste Vorlage Alpha In Kürze 4 Im Detail 6',
        '4 Erste Vorlage: Alpha Die Vorlage senkt Steuern.', '5 Frage.',
        '6 Erste Vorlage: Alpha Im Detail Steuern sinken ab 2027.'))
    translations = []
    original = engine.claim_pages
    def claim_pages(*args, **kwargs):
        translations.append(args[-1])
        return original(*args, **kwargs)
    monkeypatch.setattr(engine, 'claim_pages', claim_pages)
    case = {'id': 'booklet', 'booklet': {'path': 'fake.pdf', 'language': 'de'},
            'claim': {'text': 'Les impôts baissent.', 'language': 'fr'}, 'vote': 'Alpha'}
    source = tmp_path / 'input.jsonl'
    output = tmp_path / 'out/predictions.jsonl'
    return case, source, output, translations


def test_runtime_claim_translation_payload_metrics_and_resume(booklet_runtime, monkeypatch):
    case, source, output, translations = booklet_runtime
    monkeypatch.setenv('CONTEXT_SELECTION', 'claim_pages')
    monkeypatch.setenv('CLAIM_SPANS', '2')
    source.write_text(json.dumps(case) + '\n')
    calls = []
    class Fake:
        def request(self, method, path, payload):
            calls.append(payload)
            assert (method, path) == ('POST', '/v1/chat/completions')
            if len(calls) == 1:
                assert payload == {'model': r.MODELS[0], 'messages': [
                    {'role': 'system', 'content': 'Translate the user text into German. Output only the translation, nothing else.'},
                    {'role': 'user', 'content': case['claim']['text']}],
                    'temperature': 0, 'max_tokens': 256, 'stream': False}
                assert translations == []
                runtime.time.sleep(0.01)
                return response(r.MODELS[0], content='Die Steuern sinken.')
            assert translations == ['Die Steuern sinken.']
            return response(r.MODELS[0], content='{"label":1,"evidence":[]}')
    def factory(model):
        assert model == r.MODELS[0]
        return Fake()
    runtime.execute(source, output, 'A', factory)
    assert len(calls) == 2
    row = json.loads(output.read_text())
    assert row['metrics']['input_tokens'] == 160
    assert row['metrics']['output_tokens'] == 40
    assert row['metrics']['inference_time_ms'] >= 10
    job = output.parent / 'tmp/format-runtime'
    attempts = [json.loads(line) for line in (job / 'translations.jsonl').read_text().splitlines()]
    assert attempts == [{'case_id': 'booklet', 'target': 'de', 'ok': True,
                         'usage': {'prompt_tokens': 80, 'completion_tokens': 20, 'total_tokens': 100},
                         'finish_reason': 'stop', 'error_type': None}]
    manifest = json.loads((job / 'manifest.json').read_text())
    assert manifest['context_selection'] == 'claim_pages' and manifest['claim_spans'] == 2
    original = output.read_bytes()
    runtime.execute(source, output, 'A', lambda _: pytest.fail('resume called client'))
    assert output.read_bytes() == original
    assert len((job / 'translations.jsonl').read_text().splitlines()) == 1
    for variable, value in [('CONTEXT_SELECTION', 'full'), ('CLAIM_SPANS', '3')]:
        with monkeypatch.context() as patch:
            patch.setenv(variable, value)
            with pytest.raises(r.Stop, match='MANIFEST_CHANGED'):
                runtime.execute(source, output, 'A', lambda _: pytest.fail('changed selection called client'))


@pytest.mark.parametrize('failure', ['stop', 'garbage', 'bad-content', 'bad-finish', 'bad-usage'])
def test_runtime_translation_failure_is_nonfatal(booklet_runtime, monkeypatch, failure):
    case, source, output, translations = booklet_runtime
    monkeypatch.setenv('CONTEXT_SELECTION', 'claim_pages')
    source.write_text(json.dumps(case) + '\n')
    calls = []
    class Fake:
        def request(self, method, path, payload):
            calls.append(payload)
            if len(calls) == 1:
                if failure == 'stop':
                    raise r.Stop('SECRET RESPONSE BODY')
                if failure == 'garbage':
                    return None
                result = response(r.MODELS[0], content='Steuern sinken.')
                if failure == 'bad-content':
                    result['choices'][0]['message']['content'] = '   '
                elif failure == 'bad-finish':
                    result['choices'][0]['finish_reason'] = 'tool_calls'
                else:
                    result['usage'] = None
                return result
            return response(r.MODELS[0], content='{"label":1,"evidence":[]}')
    runtime.execute(source, output, 'A', lambda _: Fake())
    assert len(calls) == 2 and translations == [None]
    assert json.loads(output.read_text())['label'] == 1
    log = output.parent / 'tmp/format-runtime/translations.jsonl'
    attempt = json.loads(log.read_text())
    assert attempt['ok'] is False and attempt['error_type']
    assert 'SECRET' not in log.read_text()
    expected_tokens = 160 if failure in ('bad-content', 'bad-finish') else 80
    assert json.loads(output.read_text())['metrics']['input_tokens'] == expected_tokens
    original = output.read_bytes()
    runtime.execute(source, output, 'A', lambda _: pytest.fail('failed translation retried'))
    assert output.read_bytes() == original


@pytest.mark.parametrize('kind', ['same-language', 'reference', 'default', 'full'])
def test_runtime_skips_unneeded_translation(booklet_runtime, monkeypatch, kind):
    case, source, output, translations = booklet_runtime
    monkeypatch.setenv('CONTEXT_SELECTION', 'claim_pages')
    if kind == 'same-language':
        case['claim']['language'] = 'de'
    elif kind == 'reference':
        case.pop('booklet')
        case['reference'] = {'text': 'Steuern sinken.', 'language': 'de'}
    elif kind == 'default':
        monkeypatch.delenv('CONTEXT_SELECTION')
    else:
        monkeypatch.setenv('CONTEXT_SELECTION', 'full')
    source.write_text(json.dumps(case) + '\n')
    calls = []
    class Fake:
        def request(self, method, path, payload):
            calls.append(payload)
            assert payload['messages'][0]['content'].endswith(r.legacy.PROTOCOL_REMINDER)
            return response(r.MODELS[0], content='{"label":1,"evidence":[]}')
    runtime.execute(source, output, 'A', lambda _: Fake())
    assert len(calls) == 1
    assert not (output.parent / 'tmp/format-runtime/translations.jsonl').exists()
