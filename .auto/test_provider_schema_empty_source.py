"""Fiction-only offline tests. No credentials, sockets, saved responses or task data."""
import copy
import json
from pathlib import Path
import socket
import subprocess
import sys
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import provider_schema_empty_source as b
from test_provider_schema_probe import FakeTransport, response


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*a, **k):
        raise AssertionError('NETWORK_OR_CREDENTIAL_READ')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    r = b.old.root_runner()
    monkeypatch.setattr(r.legacy.c, 'read_key', forbidden)
    monkeypatch.setattr(b.old, 'root_runner', lambda: r)


def schema(frame):
    return frame['payload']['tools'][0]['function']['parameters']


def fake_protocol():
    return dict(frames=b.frames(), origin=b.old.root_runner().legacy.c.BASE)


def test_first_empty_source_contract_and_numeric_gap():
    r = b.old.root_runner()
    assert r.candidates([''], True) == []
    control, candidate = map(schema, b.frames()[:2])
    for label in (0, 1, 2):
        value = dict(label=label, candidate_ids=[])
        assert b.old.validate(control, value)
        assert b.old.validate(candidate, value) == (label == 1)
        assert b.assembler_accepts(value) == (label == 1)
    value = b.old.strict('{"label":1.0,"candidate_ids":[]}')
    assert type(value['label']) is float
    assert b.old.validate(control, value) and b.old.validate(candidate, value)
    assert not b.assembler_accepts(value)
    measured = b.score(b.frames()[1], response(value))
    assert measured['assembler_violations'] == 1 and measured['native_schema_violations'] == 0
    for value in (True, False):
        args = dict(label=value, candidate_ids=[])
        assert not b.old.validate(control, args) and not b.old.validate(candidate, args)
        assert not b.assembler_accepts(args)


def test_matrix_native_subset_and_assembler_preservation_not_global_equality():
    control, candidate = map(schema, b.frames()[:2])
    cases = [None, False, [], 1, 'x', {}]
    for label in (0, 1, 2, -1, 3, True, False, 0.0, 1.0, 2.0, .5, '1', '', None, {}, []):
        for ids in ([], ['unknown'], [''], [None], [True], [0], ['unknown'] * 6,
                    None, False, 0, '', {}):
            value = dict(label=label, candidate_ids=ids)
            cases.extend((value, dict(value, extra=1), dict(label=label), dict(candidate_ids=ids)))
    script = """import { Compile } from '/home/yasuhito/.pi/agent/install/releases/1.1.0/node_modules/typebox/build/compile/index.mjs';
let input='';for await(const chunk of process.stdin)input+=chunk;
const {schemas,cases}=JSON.parse(input);console.log(JSON.stringify(schemas.map(s=>{const c=Compile(s);return cases.map(v=>c.Check(v))})));"""
    result = subprocess.run(['node', '--input-type=module', '-e', script],
        input=b.old.encode(dict(schemas=[control, candidate], cases=cases)),
        capture_output=True, timeout=30, check=True)
    baseline, native = json.loads(result.stdout)
    accepted = [b.assembler_accepts(v) for v in cases]
    assert any(accepted)
    assert all(not n or c for n, c in zip(native, baseline))
    assert all(not a or n for a, n in zip(accepted, native))
    assert any(n and not a for n, a in zip(native, accepted))  # Disclosed float gap.
    for value, n in zip(cases, native):
        if type(value) is dict and type(value.get('label')) is int:
            assert n == b.assembler_accepts(value)


def test_exact_twelve_fixed_paired_frames():
    frames = b.frames(); r = b.old.root_runner()
    assert len(frames) == 12 and len({f['payload_sha256'] for f in frames}) == 12
    assert [f['model'] for f in frames] == [m for m in r.MODELS for _ in range(6)]
    assert [f['requested'] for f in frames[::2]] == [dict(label=l, candidate_ids=[]) for _ in range(2) for l in (1, 0, 2)]
    assert [f['arm'] for f in frames] == list(b.ARMS) * 6
    for control, candidate in zip(frames[::2], frames[1::2]):
        a, c = copy.deepcopy(control['payload']), copy.deepcopy(candidate['payload'])
        base = a['tools'][0]['function']['parameters']
        assert base == r.schemas([], True)[0]['function']['parameters']
        expected = copy.deepcopy(base)
        expected['properties']['label']['enum'] = [1]
        expected['properties']['candidate_ids']['maxItems'] = 0
        del expected['properties']['candidate_ids']['items']['enum']
        assert c['tools'][0]['function']['parameters'] == expected
        c['tools'][0]['function']['parameters'] = base
        assert a == c and a['messages'][0]['content'] == b.SYSTEM
        assert a['tools'][0]['function']['description'] == b.DESCRIPTION
        assert b.old.strict(a['messages'][1]['content']) == dict(source_spans=[], requested_arguments=control['requested'])
        assert (a['temperature'], a['max_tokens'], a['stream']) == (0, 256, False)
        assert a['tool_choice'] == dict(type='function', function=dict(name='submit'))
    assert max(len(b.old.encode(f['payload']['messages'])) + len(b.old.encode(f['payload']['tools'])) + 128 for f in frames) <= b.RESERVE - 256
    assert 11 * 1256 + b.RESERVE < b.BUDGET
    with pytest.raises(ValueError, match='EMPTY_SOURCE_ONLY'):
        b.specialize_empty(schema(frames[0]), ['unknown'])


def neutral_candidate(index, value):
    # Synthetic offline behavior, not a provider prediction or expected live result.
    if index % 2:
        value = response(dict(label=1, candidate_ids=[]), model=value['model'])
    return 200, json.dumps(value)


def test_complete_fake_twelve_exact_expected_counts_not_live_baseline(tmp_path, capsys):
    p = fake_protocol(); job = tmp_path / 'job'; fake = FakeTransport(p['frames'], neutral_candidate)
    b.run(p, job, fake)
    result = b.check(p, job)
    assert len(fake.calls) == result['requests'] == len(result['observations']) == 12
    assert {k: result[k] for k in (b.METRIC, 'control_assembler_violations', 'assembler_violations',
        'native_schema_violations', 'proposal_mismatches')} == {
        b.METRIC: 0, 'control_assembler_violations': 4, 'assembler_violations': 4,
        'native_schema_violations': 0, 'proposal_mismatches': 4}
    assert result['total_tokens'] == 1200
    for key, side in result['per_model_arm'].items():
        assert side['requests'] == 3 and side['total_tokens'] == 300
        assert side['prompt_tokens'] == 240 and side['completion_tokens'] == 60
        assert side['assembler_violations'] == (2 if key.endswith('/old_native') else 0)
        assert side['request_wall_seconds'] > 0
    b.print_result(result)
    assert 'METRIC requests=12' in capsys.readouterr().out
    with pytest.raises(FileExistsError):
        b.run(p, job, fake)


def test_proposal_copy_is_not_quality_and_nonzero_complete_is_pass(tmp_path):
    p = fake_protocol(); job = tmp_path / 'job'
    b.run(p, job, FakeTransport(p['frames']))
    result = b.check(p, job)
    assert result[b.METRIC] == result['control_assembler_violations'] == 4
    assert result['assembler_violations'] == 8 and result['native_schema_violations'] == 4
    assert result['proposal_mismatches'] == 0


@pytest.mark.parametrize('bad', ['malformed', 'duplicate', 'nonfinite', 'float', 'bool', 'missing',
    'extra', 'ids', 'nonlist', 'null', 'array', 'object_args', 'missing_call', 'multiple',
    'wrong_name', 'wrong_type', 'choices', 'truncated', 'prose'])
def test_single_failure_per_response_and_raw_representation(tmp_path, bad):
    p = fake_protocol(); f = p['frames'][1]
    value = response(dict(label=1, candidate_ids=[]), model=f['model'])
    call = value['choices'][0]['message']['tool_calls'][0]
    raw_cases = {'malformed': '{', 'duplicate': '{"label":1,"label":1,"candidate_ids":[]}',
        'nonfinite': '{"label":NaN,"candidate_ids":[]}',
        'float': '{"label":1.0,"candidate_ids":[]}', 'bool': '{"label":true,"candidate_ids":[]}',
        'missing': '{"label":1}', 'extra': '{"label":1,"candidate_ids":[],"extra":0}',
        'ids': '{"label":1,"candidate_ids":["unknown"]}',
        'nonlist': '{"label":1,"candidate_ids":null}', 'null': 'null', 'array': '[]'}
    if bad in raw_cases:
        call['function']['arguments'] = raw_cases[bad]
    elif bad == 'object_args':
        call['function']['arguments'] = dict(label=1, candidate_ids=[])
    elif bad == 'missing_call':
        value['choices'][0]['message']['tool_calls'] = []
    elif bad == 'multiple':
        value['choices'][0]['message']['tool_calls'] *= 2
    elif bad == 'wrong_name':
        call['function']['name'] = 'other'
    elif bad == 'wrong_type':
        call['type'] = 'other'
    elif bad == 'choices':
        value['choices'] *= 2
    elif bad == 'truncated':
        value['choices'][0]['finish_reason'] = 'length'
    elif bad == 'prose':
        value['choices'][0]['message']['content'] = 'fictional prose'
    s = b.score(f, value)
    assert s['assembler_violations'] == 1
    assert s['native_schema_violations'] == (0 if bad == 'float' else 1)
    def mutate(index, original):
        return (200, json.dumps(value)) if index == 1 else neutral_candidate(index, original)
    job = tmp_path / 'job'
    b.run(p, job, FakeTransport(p['frames'], mutate))
    assert b.check(p, job)[b.METRIC] == 1
    if bad == 'float':
        captured = b.old.load(job / '01-capture.json')
        assert '1.0' in captured['raw']
        args = b.old.strict(b.old.strict(captured['raw'])['choices'][0]['message']['tool_calls'][0]['function']['arguments'])
        assert type(args['label']) is float


@pytest.mark.parametrize('failure', ['http400', 'http500', 'redirect', 'timeout', 'unknown_usage',
    'float_usage', 'over_input', 'over_output', 'inconsistent', 'identity', 'api_error', 'raw_json'])
def test_terminal_failure_no_retry_partial_scores_or_new_identity(tmp_path, failure):
    p = fake_protocol()
    def mutate(index, value):
        if failure.startswith('http'):
            return int(failure[4:]), '{"error":"fictional"}'
        if failure == 'redirect':
            return 302, '{}'
        if failure == 'timeout':
            raise TimeoutError()
        if failure == 'unknown_usage':
            value.pop('usage')
        if failure == 'float_usage':
            value['usage']['prompt_tokens'] = 80.0
        if failure == 'over_input':
            value['usage'] = dict(prompt_tokens=1001, completion_tokens=20, total_tokens=1021)
        if failure == 'over_output':
            value['usage'] = dict(prompt_tokens=80, completion_tokens=257, total_tokens=337)
        if failure == 'inconsistent':
            value['usage']['total_tokens'] += 1
        if failure == 'identity':
            value['model'] = 'wrong'
        if failure == 'api_error':
            value['error'] = dict(message='fictional')
        if failure == 'raw_json':
            return 200, '{'
        return 200, json.dumps(value)
    fake = FakeTransport(p['frames'], mutate); job = tmp_path / 'job'
    with pytest.raises((ValueError, TimeoutError)):
        b.run(p, job, fake)
    assert len(fake.calls) == 1 and (job / 'STOP.json').exists() and (job / 'inflight.json').exists()
    assert b.old.load(job / 'STOP.json')['primary'] is None
    assert not (job / 'completed.json').exists()
    if failure != 'timeout':
        assert (job / '00-capture.json').exists()
    with pytest.raises(FileExistsError):
        b.run(p, job, fake)
    with pytest.raises(ValueError, match='TERMINAL_OR_INFLIGHT'):
        b.check(p, job)


@pytest.mark.parametrize('failure', ['reservation', 'budget', 'phase'])
def test_limits_are_fatal(tmp_path, monkeypatch, failure):
    p = fake_protocol(); fake = FakeTransport(p['frames'])
    if failure == 'reservation':
        monkeypatch.setattr(b, 'BUDGET', 4095)
    elif failure == 'budget':
        monkeypatch.setattr(b, 'RESERVE', 1)
        monkeypatch.setattr(b, 'BUDGET', 99)
    else:
        monkeypatch.setattr(b, 'PHASE_SECONDS', 60)
    with pytest.raises(ValueError):
        b.run(p, tmp_path / 'job', fake)
    assert len(fake.calls) == (1 if failure == 'budget' else 0)
    if failure == 'budget':
        assert b.old.load(tmp_path / 'job/00-usage.json')['total_tokens'] == 100


@pytest.mark.parametrize('target', ['capture', 'request', 'usage', 'completed', 'inflight', 'stop', 'arity', 'protocol'])
def test_capture_set_recount_and_tamper_refused(tmp_path, target):
    p = fake_protocol(); job = tmp_path / 'job'
    b.run(p, job, FakeTransport(p['frames'], neutral_candidate))
    if target in ('capture', 'request'):
        path = job / ('00-' + target + '.json'); path.write_bytes(path.read_bytes() + b' ')
        if target == 'request':  # Semantic tamper, request digest also enforced.
            value = b.old.load(path); value['arm'] = 'wrong'; path.write_bytes(b.old.encode(value))
    elif target == 'usage':
        (job / '00-usage.json').write_text('{}')
    elif target == 'completed':
        (job / 'completed.json').write_text('{"capture_sha256":[],"wall_seconds":0}')
    elif target in ('inflight', 'stop'):
        b.save(job / ('STOP.json' if target == 'stop' else 'inflight.json'), {})
    elif target == 'arity':
        (job / '11-capture.json').unlink()
    else:
        (job / 'protocol.json').write_text('{}')
    with pytest.raises(ValueError):
        b.check(p, job)


@pytest.mark.parametrize('target', ['source', 'frame', 'reservation', 'actual_source'])
def test_current_fresh_pins_tamper_refused(tmp_path, monkeypatch, target):
    frozen = b.protocol()
    if target == 'source':
        frozen['sources'][str(b.ROOT / 'track_2a/src/source_spans.py')] = '0' * 64
    elif target == 'frame':
        frozen['frames'][0]['payload']['temperature'] = 1
    elif target == 'reservation':
        frozen['reservation'] = 1256
    else:
        source = tmp_path / 'source.py'; source.write_text('original')
        monkeypatch.setattr(b, 'SOURCES', b.SOURCES + [source])
        frozen = b.protocol(); source.write_text('mutated')
    control = tmp_path / 'control.json'; b.save(control, frozen)
    monkeypatch.setattr(b, 'CONTROL', control)
    with pytest.raises(ValueError, match='PROTOCOL_OR_SOURCE_CHANGED'):
        b.verify()


def test_full_fake_prepare_execute_check_report_is_exclusive(tmp_path, monkeypatch, capsys):
    control, job, context = [tmp_path / x for x in ('control.json', 'job', 'context.json')]
    monkeypatch.setattr(b, 'CONTROL', control); monkeypatch.setattr(b, 'JOB', job)
    monkeypatch.setattr(b.old, 'CONTEXT', context)
    b.save(context, dict(previous=True))
    monkeypatch.setattr(b.old, 'Transport', Mock(side_effect=AssertionError('OFFLINE_PREPARE')))
    monkeypatch.setattr(sys, 'argv', ['probe', '--prepare']); b.main()
    assert len(b.verify()['frames']) == 12 and not job.exists()
    with pytest.raises(FileExistsError):
        b.main()
    fake = FakeTransport(b.frames())
    monkeypatch.setattr(b.old, 'Transport', lambda p: fake)
    monkeypatch.setattr(sys, 'argv', ['probe', '--execute']); b.main()
    assert len(fake.calls) == 12 and b.old.load(context) == b.context()
    assert b.old.load(job / 'report.json')['result'][b.METRIC] == 4  # Nonzero is reportable PASS.
    monkeypatch.setattr(sys, 'argv', ['probe', '--check']); b.main()
    assert len(fake.calls) == 12
    monkeypatch.setattr(sys, 'argv', ['probe', '--execute'])
    with pytest.raises(FileExistsError):
        b.main()
    assert len(fake.calls) == 12
    (job / 'report.json').write_text('{}')
    monkeypatch.setattr(sys, 'argv', ['probe', '--check'])
    with pytest.raises(ValueError, match='CONTEXT_CHANGED'):
        b.main()


def test_correct_atomic_replace_immutable_and_symlink_refusal(tmp_path):
    path = tmp_path / 'context.json'
    b.save(path, dict(old=True)); b.save(path, dict(new=True), replace=True)
    assert b.old.load(path) == dict(new=True) and path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        b.save(path, {})
    assert not list(tmp_path.glob('.pending-*'))
    link = tmp_path / 'link'; link.symlink_to(path)
    with pytest.raises(ValueError, match='SYMLINK_REFUSED'):
        b.save(link, {}, replace=True)


def test_archived_old76_and_edge_bytes_unchanged_additive_dispatch():
    proof = b.old.load(b.ROOT / '.auto/protocol-archive/provider-empty-immutable-sha256.json')
    prior = b.old.load(b.ROOT / '.auto/protocol-archive/provider-edge-immutable-sha256.json')
    assert len(prior) == 76 and all(proof[k] == v for k, v in prior.items())
    for path, digest in proof.items():
        assert b.old.sha(Path(path).read_bytes()) == digest
    current = (b.ROOT / '.auto/measure.sh').read_text()
    start = current.index('  --provider-schema-empty-prepare)')
    end = current.index('  --provider-schema-branch-closure-prepare)')
    assert current[:start] + current[end:] == (b.ROOT / '.auto/protocol-archive/provider-empty-pre-measure.sh').read_text()
    current = (b.ROOT / '.auto/checks.sh').read_text()
    start = current.index("elif mode == 'provider_schema_empty':")
    end = current.index("elif mode == 'provider_schema_branch_closure':")
    assert current[:start] + current[end:] == (b.ROOT / '.auto/protocol-archive/provider-empty-pre-checks.sh').read_text()


def test_fresh_pinset_contains_runtime_root_and_current_sources():
    p = b.protocol()
    assert p['mode'] == 'provider_schema_empty' and p['metric'] == b.METRIC
    assert (p['reservation'], p['budget'], p['input_usage_cap'], p['output_usage_cap']) == (4096, 32768, 1000, 256)
    for name in ('predict.py', 'source_spans.py', 'submission.py'):
        assert str(b.ROOT / 'track_2a/src' / name) in p['sources']
    for name in ('provider_schema_empty_source.py', 'test_provider_schema_empty_source.py',
        'provider-schema-empty-source-plan.md', 'provider_schema_probe.py', 'provider_schema_probe_recovery.py',
        'provider_schema_validator.mjs', 'measure.sh', 'checks.sh'):
        assert str(b.ROOT / '.auto' / name) in p['sources']
    for name in ('package.json', 'package-lock.json', 'runtime.py', 'run_comparison.py'):
        assert str(b.ROOT / 'track_2a/dev/format' / name) in p['sources']
    assert str(b.old.TYPEBOX / 'compile/index.mjs') in p['sources']
    assert 'reference' not in p


def test_numeric_representation_diagnostic_is_not_python_bool_equality():
    f = b.frames()[1]
    for label in (1.0, True):
        s = b.score(f, response(dict(label=label, candidate_ids=[])))
        assert s['assembler_violations'] == s['proposal_mismatches'] == 1


def test_post_completion_scoring_failure_is_terminal_not_zero(tmp_path, monkeypatch):
    control, job = tmp_path / 'control.json', tmp_path / 'job'
    monkeypatch.setattr(b, 'CONTROL', control); monkeypatch.setattr(b, 'JOB', job)
    b.save(control, b.protocol())
    fake = FakeTransport(b.frames(), neutral_candidate)
    monkeypatch.setattr(b.old, 'Transport', lambda p: fake)
    monkeypatch.setattr(b, 'score', Mock(side_effect=OSError('fictional storage failure')))
    monkeypatch.setattr(sys, 'argv', ['probe', '--execute'])
    with pytest.raises(OSError):
        b.main()
    assert len(fake.calls) == 12 and (job / 'STOP.json').exists()
    assert not (job / 'report.json').exists()
    with pytest.raises(FileExistsError):
        b.main()


def test_numeric_control_pin_changes_are_not_python_equal(tmp_path, monkeypatch):
    frozen = b.protocol()
    frozen['frames'][0]['requested']['label'] = 1.0
    control = tmp_path / 'control.json'; b.save(control, frozen)
    monkeypatch.setattr(b, 'CONTROL', control)
    with pytest.raises(ValueError, match='PROTOCOL_OR_SOURCE_CHANGED'):
        b.verify()


def test_numeric_usage_artifact_changes_are_not_python_equal(tmp_path):
    p = fake_protocol(); job = tmp_path / 'job'
    b.run(p, job, FakeTransport(p['frames'], neutral_candidate))
    path = job / '00-usage.json'; value = b.old.load(path)
    value['prompt_tokens'] = 80.0
    path.write_bytes(b.old.encode(value))
    with pytest.raises(ValueError, match='USAGE_CHANGED'):
        b.check(p, job)
