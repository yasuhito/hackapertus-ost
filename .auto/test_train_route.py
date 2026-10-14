"""Offline route checks with frozen prompts and synthetic cases only."""
import ast
import copy
from collections import Counter
from datetime import datetime, timedelta
import importlib.util
import json
from pathlib import Path
import socket
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import train_run as original
import train_route as route
sys.path.insert(0, str(original.ROOT / 'track_2a/dev/format'))
import test_comparison as fixtures


@pytest.fixture
def run(monkeypatch):
    monkeypatch.setenv('TRAIN_ROUND', 'v16')
    spec = importlib.util.spec_from_file_location('route_test_run', Path(__file__).with_name('train_run.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('network forbidden')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(fixtures.r.legacy.c, 'read_key', forbidden)


def bundle():
    return {k: (original.ROOT / p).read_bytes().decode() for k, p in route.SOURCE_ARTIFACTS.items()}


def engine():
    text = (original.ROOT / 'track_2a/src/predict.py').read_text()
    source = route.candidate_source(text, json.dumps(bundle(), ensure_ascii=False), original.old)
    ns = {'__name__': 'route_test', '__file__': str(original.ROOT / 'track_2a/src/predict.py')}
    sys.path.insert(0, str(original.ROOT / 'track_2a/src'))
    exec(compile(source, '<isolated route>', 'exec'), ns)
    return text, source, ns


def test_bundle_exact_and_rejections():
    expected = bundle()
    assert route.bundle(json.dumps(expected).encode(), original.ROOT, original.old.digest) == expected
    for task in expected:
        assert original.old.digest(expected[task].encode()) == route.SYSTEM_HASHES[task]
    for bad in ([], {'A': expected['A']}, {**expected, 'C': 'bad'}, {**expected, 'A': 1},
                {**expected, 'B': expected['B'] + '\n'}, {**expected, 'A': expected['B']}):
        with pytest.raises(ValueError):
            route.bundle(json.dumps(bad), original.ROOT, original.old.digest)
    with pytest.raises(ValueError):
        route.bundle('{"A":"x","A":"y","B":"z"}', original.ROOT, original.old.digest)


@pytest.mark.parametrize('task', ['A', 'B'])
def test_source_and_messages_parity(task):
    text, source, ns = engine()
    oldtree, newtree = ast.parse(text), ast.parse(source)
    # All original functions and guards are byte-for-byte AST-equivalent.
    functions = lambda tree: Counter(ast.dump(n) for n in tree.body if isinstance(n, ast.FunctionDef))
    assert functions(oldtree) <= functions(newtree)
    for guard in ('NEUTRAL_GUARD', 'FINAL_VERIFICATION', 'PARAPHRASE_GUARD'):
        assert ns[guard] == fixtures.r.legacy.engine().__dict__[guard]
    assert original.old.system(source) == json.dumps(bundle(), ensure_ascii=False)
    case = {'id': 'B-task-A-gold-999', 'claim': {'text': 'Task B. Task A. reference booklet gold label 0'},
            ('booklet' if task == 'A' else 'reference'): {'text': 'Source.'}}
    pages = ('Source.',)
    baseline = ns['_route_original_messages_for_pages'](case, pages)
    routed = ns['messages_for_pages'](case, pages)
    assert routed[1:] == baseline[1:]
    assert routed[0] == {**baseline[0], 'content': bundle()[task]}
    assert route.chosen_system(json.dumps(bundle()), case, routed) == bundle()[task]
    bad = copy.deepcopy(routed)
    payload = json.loads(bad[1]['content']); payload['task'] = 'B' if task == 'A' else 'A'
    bad[1]['content'] = json.dumps(payload)
    with pytest.raises(ValueError):
        route.chosen_system(json.dumps(bundle()), case, bad)
    for invalid in ({'claim': case['claim']}, {**case, 'booklet': {}, 'reference': {}}):
        with pytest.raises(ValueError):
            ns['messages_for_pages'](invalid, pages)
    for task_value in ('unknown', 'B' if task == 'A' else 'A'):
        bad = copy.deepcopy(baseline)
        payload = json.loads(bad[1]['content']); payload['task'] = task_value
        bad[1]['content'] = json.dumps(payload)
        ns['_route_original_messages_for_pages'] = lambda *args: copy.deepcopy(bad)
        with pytest.raises(ValueError):
            ns['messages_for_pages'](case, pages)


@pytest.mark.parametrize('task', ['A', 'B'])
def test_actual_sdk_mock_receives_chosen_system(task):
    _, _, ns = engine()
    x = fixtures.item()
    case = x['case']
    if task == 'A':
        case['booklet'] = case.pop('reference')
    x['messages'] = ns['messages_for_pages'](case, x['pages'])
    calls = []
    def post(role, number, payload):
        calls.append((role, payload))
        name = payload['tool_choice']['function']['name']
        args = {'mode': 'source_only'} if name == 'subagent' else {'label': 0, 'candidate_ids': x['candidate_ids']}
        return fixtures.response(fixtures.r.MODELS[1 if role == 'parent' else 0], calls=[fixtures.tool(name, args)])
    args, diagnostics, sdk = fixtures.r.run_b(x, fixtures.r.MODELS[1], post, seconds=30, isolation_guard=True, strategy='C')
    assert args and not diagnostics and sdk['counts'] == {'parent': 2, 'child': 1}
    assert [role for role, _ in calls] == ['parent', 'child', 'parent']
    # The child SDK prepends its existing agent identity. Compare against the
    # unchanged SDK path rather than assuming SYSTEM is the first byte.
    routed_calls = list(calls)
    calls.clear()
    x['messages'] = ns['_route_original_messages_for_pages'](case, x['pages'])
    x['messages'][0]['content'] = 'route-baseline-marker'
    fixtures.r.run_b(x, fixtures.r.MODELS[1], post, seconds=30, isolation_guard=True, strategy='C')
    for (role, actual), (saved_role, saved) in zip(routed_calls, calls):
        assert actual['model'] == fixtures.r.MODELS[1 if role == 'parent' else 0]
        system = actual['messages'][0]['content']
        assert role == saved_role and system.count(bundle()[task]) == 1
        assert system.replace(bundle()[task], 'route-baseline-marker') == saved['messages'][0]['content']
        assert json.dumps(bundle(), ensure_ascii=False) not in system


def window():
    return {'timezone': 'Asia/Tokyo', 'approved_candidates': ['v16'], 'max_new_candidates': 1,
            'max_attempts_per_candidate': 3, 'retry_http_status': 504, 'retry_wait_seconds': 60,
            'baseline_version': 'v5', 'trials': original.TRIALS, 'approved': True, 'stop_on_execution_error': True,
            'started_at': '2026-10-14T16:04:15+09:00', 'candidate_start_before': '2026-10-14T17:34:15+09:00',
            'soft_finish_by': '2026-10-14T18:04:15+09:00'}


def test_round_window_metadata_and_default(run):
    assert run.VERSIONS == ('v16',) and original.VERSIONS == ('v14', 'v15')
    assert run.CONTROL.name == 'train-route-protocol.json' and original.CONTROL.name == 'train-protocol.json'
    w = window(); start = datetime.fromisoformat(w['started_at']); cutoff = datetime.fromisoformat(w['candidate_start_before'])
    run.validate_window('v16', w, start)
    run.validate_window('v16', w, cutoff - timedelta(microseconds=1))
    for now in (start - timedelta(seconds=1), cutoff, start.replace(tzinfo=None)):
        with pytest.raises(ValueError):
            run.validate_window('v16', w, now)
    for key, value in [('max_new_candidates', 2), ('retry_http_status', 500), ('approved_candidates', ['v15']),
                       ('trials', {**run.TRIALS, 'cases': 54}), ('retry_wait_seconds', 0)]:
        with pytest.raises(ValueError):
            run.validate_window('v16', {**w, key: value}, start)
    raw = json.dumps(bundle()).encode()
    meta = {'version': 'v16', 'proposed_trials': run.TRIALS, 'approved_trials': run.TRIALS,
            'inference_approved': True, 'approval_scope': {'candidate': 'v16', **run.TRIALS},
            'baseline_prompt_sha256': run.V5, 'candidate_prompt_sha256': run.old.digest(raw),
            'SYSTEM_by_task_sha256': route.SYSTEM_HASHES, 'source_artifacts': route.SOURCE_ARTIFACTS}
    run.validate_metadata('v16', meta, raw)
    for key, value in [('version', 'v15'), ('approved_trials', {**run.TRIALS, 'cases': 54}),
                       ('SYSTEM_by_task_sha256', {}), ('source_artifacts', {}), ('retry_of_run', 'old')]:
        with pytest.raises(ValueError):
            run.validate_metadata('v16', {**meta, key: value}, raw)
    assert run.job_name('v16', 3, 5) == 'prompt-C-v16-a3-r5'
    for version in ('v14', 'v15'):
        with pytest.raises(ValueError):
            run.job_name(version, 1, 1)


def test_route_history_preserves_fences_and_only_retries_504(run, tmp_path, monkeypatch):
    monkeypatch.setattr(run, 'OUT', tmp_path)
    control = tmp_path / 'route-control.json'; control.write_text('{}')
    monkeypatch.setattr(run, 'CONTROL', control)
    assert run.validate_history('v16', 1, 'bundle', 100) == 0
    record = {'status': 'STOP504', 'candidate_sha256': 'bundle', 'attempt': 1, 'candidate': 'v16',
              'protocol_sha256': run.old.digest(control.read_bytes()), 'ended_at': 100}
    run.attempt_path('v16', 1).write_text(json.dumps(record))
    job = tmp_path / run.job_name('v16', 1, 1); job.mkdir()
    stop = job / 'STOP.json'; stop.write_text(json.dumps({'status': 'STOP', 'http_status': 504}))
    before = {str(p): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert run.validate_history('v16', 2, 'bundle', 159) == 1
    assert run.validate_history('v16', 2, 'bundle', 160) == 0
    assert before == {str(p): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    for status in ('completed', 'grading', 'OTHER_STOP'):
        run.attempt_path('v16', 1).write_text(json.dumps({**record, 'status': status}))
        with pytest.raises(ValueError):
            run.validate_history('v16', 2, 'bundle', 160)
    run.attempt_path('v16', 1).write_text(json.dumps(record))
    for status in (500, '504', True):
        stop.write_text(json.dumps({'status': 'STOP', 'http_status': status}))
        with pytest.raises(ValueError):
            run.validate_history('v16', 2, 'bundle', 160)


def test_route_check_context_selects_before_import_and_rejects_pending(tmp_path):
    import shutil
    import subprocess
    auto = tmp_path / '.auto'; auto.mkdir()
    shutil.copyfile(Path(__file__).with_name('checks.sh'), auto / 'checks.sh')
    (auto / 'train_run.py').write_text('''import os
assert os.environ['TRAIN_ROUND'] == 'v16'
from pathlib import Path
CONTROL = Path('.auto/control.json')
VERSIONS = ('v16',)
class old:
    @staticmethod
    def digest(raw): return 'pinned'
def verify_protocol(): pass
''')
    (auto / 'control.json').write_text('{}')
    (auto / 'train_results.py').write_text("import os; assert os.environ['TRAIN_ROUND'] == 'v16'\n")
    context = {'mode': 'train_baseline', 'round': 'v16', 'candidate': '', 'attempt': None, 'protocol_sha256': 'pinned'}
    def check(value):
        (auto / 'check-context.json').write_text(json.dumps(value))
        import os
        env = {k: v for k, v in os.environ.items() if k != 'TRAIN_ROUND'}
        return subprocess.run(['bash', str(auto / 'checks.sh')], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert check(context).returncode == 0
    assert check({**context, 'protocol_sha256': 'wrong'}).returncode != 0
    assert check({**context, 'round': 'v17'}).returncode != 0
    result = check({**context, 'mode': 'train_pending'})
    assert result.returncode != 0 and 'CHECK_SELECTOR_MISSING' in result.stderr


def test_route_freeze_is_exclusive_and_preserves_old_control(run, tmp_path, monkeypatch):
    monkeypatch.setattr(run, 'ROOT', tmp_path)
    monkeypatch.setattr(run, 'OUT', tmp_path)
    old_control = tmp_path / 'train-protocol.json'; old_control.write_bytes(b'historical immutable control\n')
    control = tmp_path / 'train-route-protocol.json'; monkeypatch.setattr(run, 'CONTROL', control)
    w = tmp_path / 'route-window.json'; w.write_text(json.dumps(window())); monkeypatch.setattr(run, 'WINDOW', w)
    runner = tmp_path / run.RUNNER; runner.parent.mkdir(parents=True); runner.write_text('unchanged runner')
    monkeypatch.setattr(run.old, 'preserve_candidate', lambda version: None)
    monkeypatch.setattr(run, 'train_split', lambda: (['fiction'], []))
    monkeypatch.setattr(run, 'protocol_paths', lambda: [w, runner])
    monkeypatch.setattr(run, 'runtime_fingerprint', lambda: {'frozen': 'runtime'})
    monkeypatch.setattr(run, 'route_fingerprint', lambda: {'wrapper_sha256': 'pinned', 'candidate_source_sha256': 'pinned'})
    run.freeze_protocol()
    saved = control.read_bytes()
    assert run.load(control)['version'] == 'train-route36x5-1'
    assert run.load(control)['routing']['wrapper_sha256'] == 'pinned'
    with pytest.raises(FileExistsError):
        run.freeze_protocol()
    assert control.read_bytes() == saved and old_control.read_bytes() == b'historical immutable control\n'
    (tmp_path / run.job_name('v16', 1, 1)).mkdir()
    with pytest.raises(ValueError, match='FREEZE_AFTER_TRIAL_REFUSED'):
        run.freeze_protocol()
