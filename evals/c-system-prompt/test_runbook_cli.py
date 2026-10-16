"""Offline unit tests for source-only batch and aggregate analysis helpers."""
import copy
import json
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent))
import run_batch as runner
import analyze_runs as analysis

REPO = Path(__file__).resolve().parents[2]


def test_prompt_constants_match_the_real_module():
    import importlib.util
    text = (REPO / 'track_2a/src/predict.py').read_text()
    constants = runner.prompt_constants(text)
    sys.path.insert(0, str(REPO / 'track_2a/src'))
    spec = importlib.util.spec_from_file_location('predict_real', REPO / 'track_2a/src/predict.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert constants['SYSTEM'] == module.SYSTEM


@pytest.mark.parametrize('text', ["SYSTEM = __import__('os').system('false')", 'SYSTEM = open("x").read()', 'SYSTEM = "ok"\nSYSTEM *= 2'])
def test_no_prompt_execution(text):
    with pytest.raises(ValueError):
        runner.prompt_constants(text)


@pytest.mark.parametrize('suffix', ['', *runner.SUFFIXES])
def test_whole_batch_refuses_existing_paths(tmp_path, suffix):
    jobs = [tmp_path / 'r1', tmp_path / 'r5']
    occupied = jobs[1] if not suffix else Path(str(jobs[1]) + '-' + suffix)
    occupied.write_text('protected')
    with pytest.raises(ValueError, match='PREEXISTING'):
        runner.refuse_existing(jobs)
    assert occupied.read_text() == 'protected'
    assert not jobs[0].exists()


@pytest.mark.parametrize('name', ['r4.', 'r4 ', 'parent./r4'])
def test_runner_ambiguous_paths(tmp_path, name):
    with pytest.raises(ValueError, match='AMBIGUOUS'):
        runner.write_target(tmp_path / name)
    assert not list(tmp_path.iterdir())


def test_stable_path_and_exact_dotted_read_input(tmp_path):
    assert runner.write_target(tmp_path / 'x/../r5') == tmp_path / 'r5'
    dotted = tmp_path / 'r4.'
    dotted.mkdir()
    Path(str(dotted) + '-end.txt').write_text('42')
    assert analysis.command_time(dotted) == {'command_start': None, 'command_end': 42., 'command_seconds': None}
    assert dotted.exists() and not (tmp_path / 'r4').exists()


def test_noise_formula_and_single_repeat_null():
    got = analysis.noise([1., 2., 3.])
    assert got['mean'] == 2. and got['runSD'] == 1.
    assert got['detectable_width'] == pytest.approx(2 * np.sqrt(2) / np.sqrt(3))
    assert analysis.noise([1.])['detectable_width'] is None


def test_paired_bootstrap_same_groups_all_repeats():
    c = np.zeros((3, 5, 2, 3, 3))
    for i in range(3):
        c[i, :, :, i, i] = 1
    assert analysis.q(analysis.f1(c.sum(axis=(0, 1)))) == pytest.approx(1.)
    got = analysis.paired(c, c, 1, 50)
    assert got == {'pooled_delta95': [0., 0.], 'mean_repeat_delta95': [0., 0.]}


def test_tracked_fixture_fixed_groups():
    rows, split = analysis.fixture(REPO)
    parts = list(analysis.sides('split', rows, split))
    assert [len(ids) for _, ids, _ in parts] == [36, 18]
    assert set(parts[0][1]).isdisjoint(parts[1][1])


def manifest():
    return {'strategy': 'C', 'role_models': {'parent': analysis.MODEL, 'child': 'swiss-ai/Apertus-v1.5-8B'}, 'request_limit': 270,
            'sources': {'track_2a/src/predict.py': 'v0', 'track_2a/dev/format/run_comparison.py': 'old'},
            'frozen': [{'case': {'id': str(i), 'booklet': {'path': '/workspace/booklets/a.pdf'}},
                        'pages': ['same'], 'candidate_ids': ['same'], 'schema_sha256': 'same',
                        'messages': [{'role': 'system', 'content': 'v0'}, {'role': 'user', 'content': 'source'}],
                        'messages_sha256': 'old'} for i in range(54)]}


def test_audit_cli_allowance_explicit_and_caps_fixed(tmp_path):
    jobs = [tmp_path / 'base', tmp_path / 'candidate']
    base = manifest()
    candidate = copy.deepcopy(base)
    candidate['sources']['track_2a/dev/format/run_comparison.py'] = 'new'
    for job, m in zip(jobs, [base, candidate]):
        job.mkdir()
        (job / 'manifest.json').write_text(json.dumps(m))
    with pytest.raises(ValueError, match='NON_PROMPT'):
        analysis.audit(jobs, False)
    assert analysis.audit(jobs, True)['differences'][1]['changed_source_hashes'] == ['track_2a/dev/format/run_comparison.py']
    candidate['request_limit'] = 271
    (jobs[1] / 'manifest.json').write_text(json.dumps(candidate))
    with pytest.raises(ValueError, match='MODEL_CAP_POLICY'):
        analysis.audit(jobs, True)


def test_repeat_count_arm_independence_and_nonlinear_f1():
    c = np.zeros((1, 2, 2, 3, 3))
    c[0, 0, :, 0, 0] = 1
    c[0, 1, :, 0, 1] = 1
    pooled = float(analysis.q(analysis.f1(c.sum(axis=(0, 1)))))
    mean = float(analysis.q(analysis.f1(c.sum(axis=0))).mean())
    assert pooled != pytest.approx(mean)
    # Repeating each observed contribution cannot change either estimand.
    got = analysis.paired(c, np.repeat(c, 3, axis=1), 7, 30)
    assert got['pooled_delta95'] == pytest.approx([0., 0.])
    assert got['mean_repeat_delta95'] == pytest.approx([0., 0.])


@pytest.mark.parametrize('kind', ['uncertain', 'not_completed', 'unknown_usage', 'missing_cases'])
def test_score_refuses_incomplete_unknown_jobs(tmp_path, kind):
    job = tmp_path / 'job'
    job.mkdir()
    state = {'tokens': 100, 'reserved_tokens': 0, 'blocked': False, 'cases': {}}
    summary = {'status': 'completed', 'actual_total_tokens': 100}
    if kind == 'uncertain':
        (job / 'inflight.json').write_text('protected')
    if kind == 'not_completed':
        summary['status'] = 'starting'
    if kind == 'unknown_usage':
        state['reserved_tokens'] = 100
    (job / 'summary.json').write_text(json.dumps(summary))
    (job / 'state.json').write_text(json.dumps(state))
    rows, split = analysis.fixture(REPO)
    with pytest.raises(ValueError):
        analysis.score([job], tmp_path / 'dest', 'full', rows, split, tmp_path / 'official', Path(sys.executable), 10)
    if kind == 'uncertain':
        assert (job / 'inflight.json').read_text() == 'protected'


def test_full_compare_cannot_be_adoption_gate(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'argv', ['analyze_runs.py', 'compare', '--repo', str(REPO),
        '--official-repo', str(tmp_path), '--python', sys.executable,
        '--jobs', str(tmp_path / 'base'), '--candidate-jobs', str(tmp_path / 'candidate'),
        '--part', 'full', '--destination', str(tmp_path / 'out')])
    with pytest.raises(SystemExit) as error:
        analysis.main()
    assert error.value.code == 2
    assert not (tmp_path / 'out').exists()


def test_venv_executable_is_not_dereferenced(monkeypatch, tmp_path):
    executable = tmp_path / 'venv/bin/python'
    executable.parent.mkdir(parents=True)
    executable.symlink_to(sys.executable)
    seen = []
    def capture_score(jobs, dest, part, byid, split, official, python, samples):
        seen.append(python)
        return {}, {}
    fixture_rows, _ = analysis.fixture(REPO)
    original_load = analysis.load
    monkeypatch.setattr(analysis, 'load', lambda p: {'frozen': [
        {'case': r['input']} for r in fixture_rows.values()]} if p.name == 'manifest.json' else original_load(p))
    monkeypatch.setattr(analysis, 'audit', lambda *args: {})
    monkeypatch.setattr(analysis, 'score', capture_score)
    monkeypatch.setattr(sys, 'argv', ['analyze_runs.py', 'score', '--repo', str(REPO),
        '--official-repo', str(tmp_path), '--python', str(executable), '--jobs', str(tmp_path / 'base'),
        '--destination', str(REPO / 'output/unused-venv-test')])
    monkeypatch.setattr(Path, 'mkdir', lambda *args, **kwargs: None)
    monkeypatch.setattr(analysis, 'dump', lambda *args: None)
    analysis.main()
    assert seen == [executable.absolute()]
    assert seen[0] != executable.resolve()


@pytest.mark.parametrize('kind', ['canonical', 'manifest', 'case_names'])
def test_ledger_binds_manifest_case_set_and_canonical(tmp_path, kind):
    import hashlib
    def digest(record):
        return hashlib.sha256(json.dumps(record, ensure_ascii=False,
            sort_keys=True, allow_nan=False).encode()).hexdigest()
    job = tmp_path / 'job'
    job.mkdir()
    manifest_data = {'fixed': 'original'}
    preds, hashes = [], {}
    for index in range(54):
        pred = {'id': f'id-{index}', 'label': 1, 'label_name': 'neutral'}
        record = {'case_id': pred['id'], 'prediction': pred}
        name = f'70b-{index:02}-case.json'
        (job / name).write_text(json.dumps(record))
        hashes[name] = digest(record)
        preds.append(pred)
    state = {'version': 'format-1', 'tokens': 0, 'requests': 0, 'reserved_tokens': 0,
             'blocked': False, 'manifest_sha256': digest(manifest_data), 'cases': hashes, 'attempts': {}}
    if kind == 'canonical':
        preds[0] = {**preds[0], 'label': 0, 'label_name': 'entailment'}
    elif kind == 'manifest':
        manifest_data['fixed'] = 'replaced'
    else:
        state['cases']['70b-99-case.json'] = state['cases'].pop('70b-00-case.json')
    (job / 'manifest.json').write_text(json.dumps(manifest_data))
    (job / 'summary.json').write_text(json.dumps({'status': 'completed', 'actual_total_tokens': 0}))
    (job / 'state.json').write_text(json.dumps(state))
    (job / '70b-canonical.jsonl').write_text(''.join(json.dumps(p) + '\n' for p in preds))
    byid = {f'id-{i}': {} for i in range(54)}
    error = {'canonical': 'CANONICAL_RECORD_MISMATCH', 'manifest': 'MANIFEST_LEDGER_MISMATCH',
             'case_names': 'MISSING_COMPLETED_CASES'}[kind]
    with pytest.raises(ValueError, match=error):
        analysis.score([job], tmp_path / 'dest', 'full', byid, {}, tmp_path, Path(sys.executable), 10)
