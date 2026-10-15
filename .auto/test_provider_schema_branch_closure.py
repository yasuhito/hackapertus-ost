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
import provider_schema_branch_closure as b
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


def test_only_conditional_schema_changes_and_preflight():
    old, new = b.old.frames(), b.frames()
    assert len(new) == 12 and b.RESERVE * 12 == 21600 < b.BUDGET
    sizes = []
    for before, after in zip(old, new):
        a, c = copy.deepcopy(before), copy.deepcopy(after)
        a.pop('payload_sha256'); c.pop('payload_sha256')
        if before['arm'] == 'simple':
            assert b.old.encode(before) == b.old.encode(after)
        else:
            original = a['payload']['tools'][0]['function'].pop('parameters')
            changed = c['payload']['tools'][0]['function'].pop('parameters')
            common = copy.deepcopy(original); del common['anyOf']
            root = copy.deepcopy(changed); branches = root.pop('anyOf')
            assert root == common
            for branch, labels in zip(branches, ([1], [0, 2])):
                want = copy.deepcopy(common)
                want['properties']['label']['enum'] = labels
                if labels == [0, 2]:
                    want['properties']['candidate_ids']['minItems'] = 1
                assert branch == want
            assert a == c
        payload = after['payload']
        assert after['payload_sha256'] == b.old.sha(b.old.encode(payload))
        sizes.append(len(b.old.encode(payload['messages'])) + len(b.old.encode(payload['tools'])) + 128)
    assert max(sizes) == 1358 <= b.RESERVE - 256


def test_exhaustive_finite_domains_independent_typebox_equivalence():
    # All binary known-ID arrays of lengths 0..6, duplicates and multi-IDs included;
    # insert each invalid ID/value at every position in each valid base array.
    arrays = [list(x) for n in range(7) for x in itertools.product(['toy-a', 'toy-b'], repeat=n)]
    invalid = ['other', 'toy-ａ', '', None, True, 0, {}, []]
    for n in range(1, 7):
        for position in range(n):
            for bad in invalid:
                value = ['toy-a'] * n; value[position] = bad; arrays.append(value)
    ids_domain = arrays + [None, False, 0, 1.5, 'toy-a', {}]
    labels = [None, False, True, -1, 0, 1, 2, 3, 0.5, 1.0, '0', '1', '', [], {}]
    cases = [None, False, 0, 'text', [], {}]
    expected = [False] * len(cases)
    for label in labels:
        for ids in ids_domain:
            valid = (type(label) in (int, float) and label in (0, 1, 2)
                     and type(ids) is list and len(ids) <= 5
                     and all(type(x) is str and x in ('toy-a', 'toy-b') for x in ids)
                     and (label == 1 or len(ids) >= 1))
            base = dict(label=label, candidate_ids=ids)
            for value, answer in ((base, valid), ({**base, 'extra': 0}, False),
                                  ({'label': label}, False), ({'candidate_ids': ids}, False)):
                cases.append(value); expected.append(answer)
    schemas = [b.old.frames()[1]['payload']['tools'][0]['function']['parameters'],
               b.frames()[1]['payload']['tools'][0]['function']['parameters']]
    script = """import { Compile } from '/home/yasuhito/.pi/agent/install/releases/1.1.0/node_modules/typebox/build/compile/index.mjs';
let input=''; for await (const chunk of process.stdin) input+=chunk;
const {schemas,cases}=JSON.parse(input); const validators=schemas.map(s=>Compile(s));
console.log(JSON.stringify(validators.map(v=>cases.map(c=>v.Check(c)))));"""
    run = subprocess.run(['node', '--input-type=module', '-e', script],
                         input=b.old.encode(dict(schemas=schemas, cases=cases)), capture_output=True,
                         timeout=60, check=True)
    old, new = json.loads(run.stdout)
    assert old == expected and new == expected
    assert b.old.validate(schemas[1], {'label': 1, 'candidate_ids': ['toy-a', 'toy-b']})
    # Unicode lookalike is an expected enum mismatch, not a new encoding rule.
    assert not b.old.validate(schemas[1], {'label': 1, 'candidate_ids': ['toy-ａ']})


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
    result = b.old.check(p, job)
    assert len(fake.calls) == 12 and result['schema_contract_violations'] == 3
    assert result['missing_field'] == 3 and result['total_tokens'] == 1200
    assert all(side['requests'] == 3 for side in result['per_model_arm'].values())
    assert result['request_wall_seconds'] > 0 and result['phase_wall_seconds'] > 0
    with pytest.raises(FileExistsError):
        b.run(p, job, fake)
    capture = job / '00-capture.json'
    capture.write_bytes(capture.read_bytes() + b' ')
    with pytest.raises(ValueError, match='CAPTURE_CHANGED'):
        b.old.check(p, job)


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
        b.old.check(p, job)


def test_conservative_reservation_before_send(tmp_path, monkeypatch):
    p = fake_protocol(); fake = FakeTransport(p['frames'])
    monkeypatch.setattr(b, 'BUDGET', 1799)
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


def test_original_and_recovery_pins_and_reference():
    original, actual = b.reference()
    assert actual['schema_contract_violations'] == 3
    assert [actual['per_model_arm'][m+'/'+a]['violations'] for m in original['models']
            for a in ('simple', 'conditional')] == [0, 0, 0, 3]
    frozen = b.protocol()
    assert len(frozen['reference']['frame_sha256']) == 12
    assert len(frozen['reference']['artifacts']) == 27
    assert str(b.ROOT / 'track_2a/dev/format/run_comparison.py') in frozen['sources']


@pytest.mark.parametrize('target', ['new_source', 'reference_artifact', 'frame', 'reservation'])
def test_frozen_protocol_tamper_refused(tmp_path, monkeypatch, target):
    frozen = b.protocol()
    if target == 'new_source':
        frozen['sources'][str(b.ROOT / '.auto/provider_schema_branch_closure.py')] = '0'*64
    elif target == 'reference_artifact':
        frozen['reference']['artifacts'][next(iter(frozen['reference']['artifacts']))] = '0'*64
    elif target == 'frame':
        frozen['frames'][1]['payload']['temperature'] = 1
    else:
        frozen['reservation'] = 1256
    control = tmp_path / 'protocol.json'
    b.save(control, frozen); monkeypatch.setattr(b, 'CONTROL', control)
    with pytest.raises(ValueError, match='PROTOCOL_OR_SOURCE_CHANGED'):
        b.verify()


def test_historical_dispatcher_tamper_refused_before_scoring(tmp_path, monkeypatch):
    changed = tmp_path / 'archive.sh'; changed.write_text('not the pinned dispatcher')
    monkeypatch.setattr(b, 'ARCHIVES', {**b.ARCHIVES, next(iter(b.ARCHIVES)): changed})
    scorer = Mock(side_effect=AssertionError('SCORING_BEFORE_VERIFICATION'))
    monkeypatch.setattr(b.old, 'check', scorer)
    with pytest.raises(ValueError, match='RECOVERY_SOURCE_CHANGED'):
        b.reference()
    scorer.assert_not_called()


def test_metric_keys_match_recovery_and_zero_overhead(capsys, tmp_path):
    p = fake_protocol(); job = tmp_path / 'job'
    b.run(p, job, FakeTransport(p['frames']))
    result = b.old.check(p, job)
    b.recovery.print_report(dict(result=result, recovery_wall_seconds=0))
    output = capsys.readouterr().out
    metrics = dict(line.removeprefix('METRIC ').split('=', 1) for line in output.splitlines() if line.startswith('METRIC '))
    expected = set(result) - {'per_model_arm'} | {'requests', 'recovery_wall_seconds'}
    expected |= {f'model{model}_{arm}_{key}' for model in ('8b', '70b') for arm in ('simple', 'conditional')
                 for key in ('requests', 'violations', 'missing_field', 'truncation', 'exact_copy_mismatch')}
    assert set(metrics) == expected and metrics['recovery_wall_seconds'] == '0' and metrics['requests'] == '12'


def test_reference_unknown_or_wrong_primary_refused(monkeypatch):
    original_check = b.old.check
    def changed(protocol, job):
        result = original_check(protocol, job)
        result['schema_contract_violations'] = 0
        return result
    monkeypatch.setattr(b.old, 'check', changed)
    with pytest.raises(ValueError, match='REFERENCE_RESULT_CHANGED'):
        b.reference()
    monkeypatch.setattr(b.old, 'check', Mock(side_effect=ValueError('UNKNOWN_USAGE')))
    with pytest.raises(ValueError, match='UNKNOWN_USAGE'):
        b.reference()


def test_prepare_offline_only_immutable_control(tmp_path, monkeypatch):
    control, job = tmp_path / 'control.json', tmp_path / 'job'
    monkeypatch.setattr(b, 'CONTROL', control)
    monkeypatch.setattr(b, 'JOB', job)
    monkeypatch.setattr(b.old, 'Transport', Mock(side_effect=AssertionError('NO_TRANSPORT_DURING_PREPARE')))
    monkeypatch.setattr(sys, 'argv', ['probe', '--prepare'])
    b.main()
    assert b.verify() == b.old.load(control) and not job.exists()
    with pytest.raises(FileExistsError):
        b.main()


def test_main_full_mock_execute_check_atomic_context(tmp_path, monkeypatch, capsys):
    control, job, context = tmp_path / 'control.json', tmp_path / 'job', tmp_path / 'context.json'
    monkeypatch.setattr(b, 'CONTROL', control)
    monkeypatch.setattr(b, 'JOB', job)
    monkeypatch.setattr(b.old, 'CONTEXT', context)
    b.save(context, {'previous': True})
    b.save(control, b.protocol())
    frames = b.frames()
    def wrong(index, value):
        return 200, json.dumps(response({'label': 0}, model=value['model']))
    fake = FakeTransport(frames, wrong)
    monkeypatch.setattr(b.old, 'Transport', lambda _: fake)
    monkeypatch.setattr(sys, 'argv', ['probe', '--execute'])
    b.main()
    assert b.old.load(context) == b.context() and len(fake.calls) == 12
    monkeypatch.setattr(sys, 'argv', ['probe', '--check'])
    b.main()
    assert 'METRIC schema_contract_violations=12' in capsys.readouterr().out
    with pytest.raises(FileExistsError):
        monkeypatch.setattr(sys, 'argv', ['probe', '--execute'])
        b.main()
    assert len(fake.calls) == 12
