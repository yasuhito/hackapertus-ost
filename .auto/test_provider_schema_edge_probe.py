"""Fiction-only offline proof and exclusive-driver tests; no API or credentials."""
import copy
import itertools
import json
from pathlib import Path
import socket
import subprocess
import sys
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import provider_schema_edge_probe as b
from test_provider_schema_probe import FakeTransport, response


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*_a, **_k):
        raise AssertionError('NETWORK_OR_CREDENTIAL_READ')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    runner = b.old.root_runner()
    monkeypatch.setattr(runner.legacy.c, 'read_key', forbidden)
    monkeypatch.setattr(b.old, 'root_runner', lambda: runner)


def fake_protocol():
    return dict(frames=b.frames(), origin=b.old.root_runner().legacy.c.BASE)


def test_complete_wrong_outcomes_recount_and_immutability(tmp_path):
    p = fake_protocol()
    def mutate(index, value):
        if index in (1, 6, 11):
            value = response({'label': 0}, model=value['model'])
        return 200, json.dumps(value)
    fake = FakeTransport(p['frames'], mutate)
    job = tmp_path / 'job'
    b.run(p, job, fake)
    result = b.check(p, job)
    assert len(fake.calls) == 12 and result[b.METRIC] == 3
    assert result['missing_field'] == 3 and result['total_tokens'] == 1200
    assert all(side['requests'] == 3 for side in result['per_model_arm'].values())
    assert result['request_wall_seconds'] > 0 and result['phase_wall_seconds'] > 0
    with pytest.raises(FileExistsError):
        b.run(p, job, fake)
    capture = job / '00-capture.json'
    capture.write_bytes(capture.read_bytes() + b' ')
    with pytest.raises(ValueError, match='CAPTURE_CHANGED'):
        b.check(p, job)


@pytest.mark.parametrize('failure', ['http', 'timeout', 'unknown', 'over_input', 'over_output', 'identity', 'storage'])
def test_fail_closed_no_resume(tmp_path, monkeypatch, failure):
    p = fake_protocol()
    def mutate(index, value):
        if failure == 'http':
            return 500, '{}'
        if failure == 'timeout':
            raise TimeoutError()
        if failure == 'unknown':
            value.pop('usage')
        if failure == 'over_input':
            value['usage'] = dict(prompt_tokens=1001, completion_tokens=20, total_tokens=1021)
        if failure == 'over_output':
            value['usage'] = dict(prompt_tokens=80, completion_tokens=257, total_tokens=337)
        if failure == 'identity':
            value['model'] = 'unknown'
        return 200, json.dumps(value)
    if failure == 'storage':
        monkeypatch.setattr(b.old, 'score', Mock(side_effect=OSError('storage uncertain')))
    fake = FakeTransport(p['frames'], mutate)
    job = tmp_path / 'job'
    with pytest.raises((ValueError, TimeoutError, OSError)):
        b.run(p, job, fake)
    assert len(fake.calls) == 1 and (job / 'inflight.json').exists() and (job / 'STOP.json').exists()
    with pytest.raises(FileExistsError):
        b.run(p, job, fake)
    with pytest.raises(ValueError, match='TERMINAL_OR_INFLIGHT'):
        b.check(p, job)


def test_conservative_reservation_before_send(tmp_path, monkeypatch):
    p = fake_protocol(); fake = FakeTransport(p['frames'])
    monkeypatch.setattr(b, 'BUDGET', 4095)
    with pytest.raises(ValueError, match='TOKEN_RESERVATION_REFUSED'):
        b.run(p, tmp_path / 'job', fake)
    assert not fake.calls


def test_atomic_replace_and_immutable_save(tmp_path):
    path = tmp_path / 'context.json'
    b.save(path, {'old': True})
    b.save(path, {'new': True}, replace=True)
    assert b.old.load(path) == {'new': True} and path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        b.save(path, {})
    assert not list(tmp_path.glob('.pending-*'))



def test_fixed_real_ids_and_paired_payloads():
    frames = b.frames(); r = b.old.root_runner()
    spans = r.candidates(b.pages(), False); ids = [s['span_id'] for s in spans]
    import re
    assert len(set(ids)) == 6 and all(len(x) == 36 and re.fullmatch(r'p\d{4}-o\d{7}-e\d{7}-[a-f0-9]{12}', x) for x in ids)
    assert b.frames() == frames
    assert [f['model'] for f in frames] == [m for m in r.MODELS for _ in range(6)]
    assert [f['requested'] for f in frames[:6:2]] == [dict(label=1, candidate_ids=ids[:2]), dict(label=0, candidate_ids=ids[:5]), dict(label=2, candidate_ids=ids[-5:])]
    for i in range(0, 12, 2):
        simple, complete = frames[i:i+2]
        assert (simple['arm'], complete['arm']) == ('simple', 'complete_branch')
        user = b.old.strict(simple['payload']['messages'][1]['content'])
        assert user == dict(source_spans=spans, requested_arguments=simple['requested'])
        a, c = copy.deepcopy(simple['payload']), copy.deepcopy(complete['payload'])
        common = a['tools'][0]['function']['parameters']
        assert common == r.schemas(ids, child=True)[0]['function']['parameters']
        branches = c['tools'][0]['function']['parameters'].pop('anyOf')
        assert a == c
        for branch, labels in zip(branches, ([1], [0, 2])):
            want = copy.deepcopy(common); want['properties']['label']['enum'] = labels
            if labels == [0, 2]:
                want['properties']['candidate_ids']['minItems'] = 1
            assert branch == want
        assert b.old.validate(common, simple['requested'])
        assert b.old.validate(complete['payload']['tools'][0]['function']['parameters'], complete['requested'])
    assert max(len(b.old.encode(f['payload']['messages'])) + len(b.old.encode(f['payload']['tools'])) + 128 for f in frames) == 2824 <= b.RESERVE - 256
    assert 12 * 1256 < b.BUDGET and 11 * 1256 + b.RESERVE < b.BUDGET


def test_independent_typebox_equivalence_edge_domains():
    frames = b.frames(); schema = frames[1]['payload']['tools'][0]['function']['parameters']
    ids = schema['properties']['candidate_ids']['items']['enum']
    previous = copy.deepcopy(schema)
    previous['anyOf'] = [{'properties': {'label': {'enum': [1]}}}, {'properties': {'candidate_ids': {'minItems': 1}}}]
    arrays = [list(x) for n in range(7) for x in itertools.permutations(ids, n)]
    arrays += [[x] * n for x in ids for n in range(7)]
    for n in range(1, 7):
        for i in range(n):
            for bad in ('wrong', '', None, True, 0, {}, []):
                a = ids[:n]; a[i] = bad; arrays.append(a)
    arrays += [None, False, 0, 'wrong', {}]
    cases, expected = [None, False, 0, [], {}], [False] * 5
    for label in (None, False, True, -1, 0, 1, 2, 3, .5, 1.0, '1', {}, []):
        for a in arrays:
            valid = (type(label) in (int, float) and label in (0, 1, 2)
                     and type(a) is list and len(a) <= 5
                     and all(type(x) is str and x in ids for x in a)
                     and (label == 1 or len(a) > 0))
            for value, ok in ((dict(label=label, candidate_ids=a), valid),
                              (dict(label=label, candidate_ids=a, extra=1), False),
                              (dict(label=label), False), (dict(candidate_ids=a), False)):
                cases.append(value); expected.append(ok)
    script = """import { Compile } from '/home/yasuhito/.pi/agent/install/releases/1.1.0/node_modules/typebox/build/compile/index.mjs';
let input=''; for await (const chunk of process.stdin) input+=chunk;
const {schemas,cases}=JSON.parse(input); console.log(JSON.stringify(schemas.map(s=>{const v=Compile(s);return cases.map(c=>v.Check(c))})));"""
    result = subprocess.run(['node', '--input-type=module', '-e', script],
        input=b.old.encode(dict(schemas=[previous, schema], cases=cases)), capture_output=True, timeout=60, check=True)
    assert json.loads(result.stdout) == [expected, expected]


@pytest.mark.parametrize('failure', ['api_error', 'inconsistent'])
def test_additional_fatal_usage_identity(tmp_path, failure):
    p = fake_protocol()
    def mutate(index, value):
        if failure == 'api_error':
            value['error'] = {'message': 'fictional'}
        else:
            value['usage']['total_tokens'] += 1
        return 200, json.dumps(value)
    fake = FakeTransport(p['frames'], mutate); job = tmp_path / 'job'
    with pytest.raises(ValueError):
        b.run(p, job, fake)
    assert len(fake.calls) == 1 and (job / 'inflight.json').exists()
    with pytest.raises(FileExistsError):
        b.run(p, job, fake)


def test_unmasked_copy_errors_per_arm_usage_and_metric(tmp_path, capsys):
    p = fake_protocol(); job = tmp_path / 'job'
    def mutate(i, value):
        if i == 0:
            value = response({'label': 0}, model=value['model'])
        elif i == 1:
            value = response({'label': 1, 'candidate_ids': []}, model=value['model'])
        return 200, json.dumps(value)
    b.run(p, job, FakeTransport(p['frames'], mutate))
    result = b.check(p, job)
    assert result[b.METRIC] == 1 and 'schema_contract_violations' not in result
    assert result['all_exact_copy_mismatches'] == 2 and result['exact_copy_mismatch'] == 1
    for side in result['per_model_arm'].values():
        assert side['requests'] == 3 and side['total_tokens'] == 300
        assert side['prompt_tokens'] == 240 and side['completion_tokens'] == 60
        assert side['request_wall_seconds'] > 0
    b.print_result(result)
    output = capsys.readouterr().out
    assert 'METRIC edge_schema_contract_violations=1' in output
    assert 'METRIC requests=12' in output


@pytest.mark.parametrize('target', ['source', 'frame', 'reservation', 'actual_source'])
def test_current_pins_tamper_refused(tmp_path, monkeypatch, target):
    frozen = b.protocol()
    if target == 'source':
        frozen['sources'][str(b.ROOT / 'track_2a/src/source_spans.py')] = '0'*64
    elif target == 'frame':
        frozen['frames'][0]['payload']['temperature'] = 1
    elif target == 'reservation':
        frozen['reservation'] = 1256
    elif target == 'actual_source':
        source = tmp_path / 'source.py'; source.write_text('original')
        monkeypatch.setattr(b, 'SOURCES', b.SOURCES + [source])
        frozen = b.protocol(); source.write_text('mutated')
    control = tmp_path / 'control.json'; b.save(control, frozen)
    monkeypatch.setattr(b, 'CONTROL', control)
    with pytest.raises(ValueError, match='PROTOCOL_OR_SOURCE_CHANGED'):
        b.verify()


def test_full_prepare_execute_check_fake_only(tmp_path, monkeypatch, capsys):
    control, job, context = [tmp_path / x for x in ('control.json', 'job', 'context.json')]
    monkeypatch.setattr(b, 'CONTROL', control); monkeypatch.setattr(b, 'JOB', job)
    monkeypatch.setattr(b.old, 'CONTEXT', context)
    b.save(context, {'previous': True})
    monkeypatch.setattr(b.old, 'Transport', Mock(side_effect=AssertionError('OFFLINE_PREPARE')))
    monkeypatch.setattr(sys, 'argv', ['probe', '--prepare']); b.main()
    assert len(b.verify()['frames']) == 12 and not job.exists()
    with pytest.raises(FileExistsError):
        b.main()
    fake = FakeTransport(b.frames()); monkeypatch.setattr(b.old, 'Transport', lambda _: fake)
    monkeypatch.setattr(sys, 'argv', ['probe', '--execute']); b.main()
    assert len(fake.calls) == 12 and b.old.load(context) == b.context()
    monkeypatch.setattr(sys, 'argv', ['probe', '--check']); b.main()
    assert len(fake.calls) == 12
    monkeypatch.setattr(sys, 'argv', ['probe', '--execute'])
    with pytest.raises(FileExistsError):
        b.main()
    assert len(fake.calls) == 12


def test_immutable_proof_and_additive_dispatchers():
    proof = b.old.load(b.ROOT / '.auto/protocol-archive/provider-edge-immutable-sha256.json')
    for path, digest in proof.items():
        assert b.old.sha(Path(path).read_bytes()) == digest, path
    current = (b.ROOT / '.auto/measure.sh').read_text()
    start = current.index('  --provider-schema-edge-prepare)')
    end = current.index('  --provider-schema-branch-closure-prepare)')
    assert current[:start] + current[end:] == (b.ROOT / '.auto/protocol-archive/provider-edge-pre-measure.sh').read_text()
    current = (b.ROOT / '.auto/checks.sh').read_text()
    start = current.index("if mode == 'provider_schema_edge':")
    end = current.index("elif mode == 'provider_schema_branch_closure':")
    assert current[:start] + 'if' + current[end+4:] == (b.ROOT / '.auto/protocol-archive/provider-edge-pre-checks.sh').read_text()


def test_max_five_requested_native_output_byte_bound():
    for frame in b.frames():
        requested = frame['requested']
        assert 0 < len(requested['candidate_ids']) <= 5
        assert len(b.old.encode(requested)) <= 256
        assert b.old.score(frame, response(requested))['violation'] == 0
        assert frame['payload']['max_tokens'] == 256
    # Byte bound for requested JSON is not a claim about actual model output.


def test_oversized_fiction_stops_before_freeze(tmp_path, monkeypatch):
    control = tmp_path / 'control.json'; monkeypatch.setattr(b, 'CONTROL', control)
    monkeypatch.setattr(b, 'JOB', tmp_path / 'job')
    monkeypatch.setattr(b, 'pages', lambda: ['Fictional ' + 'x' * 1100] * 6)
    monkeypatch.setattr(sys, 'argv', ['probe', '--prepare'])
    with pytest.raises(ValueError, match='INPUT_ESTIMATE_EXCEEDED'):
        b.main()
    assert not control.exists() and not b.JOB.exists()


def test_fresh_pinset_has_sourcepack_and_no_historical_references():
    p = b.protocol()
    assert p['metric'] == b.METRIC and p['reservation'] == 4096
    assert (p['input_usage_cap'], p['output_usage_cap']) == (1000, 256)
    assert 'reference' not in p
    for name in ('source_spans.py', 'predict.py', 'submission.py'):
        assert str(b.ROOT / 'track_2a/src' / name) in p['sources']
    for name in ('provider_schema_edge_probe.py', 'test_provider_schema_edge_probe.py',
                 'provider-schema-edge-probe-plan.md', 'provider_schema_probe.py',
                 'provider_schema_probe_recovery.py', 'provider_schema_validator.mjs',
                 'measure.sh', 'checks.sh'):
        assert str(b.ROOT / '.auto' / name) in p['sources']
    for name in ('package.json', 'package-lock.json', 'runtime.py'):
        assert str(b.ROOT / 'track_2a/dev/format' / name) in p['sources']
    assert str(b.old.TYPEBOX / 'compile/index.mjs') in p['sources']
    assert p['origin'].startswith('https://')
