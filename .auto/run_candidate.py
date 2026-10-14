#!/usr/bin/env python3
"""Scoped v11..v13 or exact HTTP504 fresh-job retries. Offline by default."""
import argparse
import ast
import hashlib
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/cscs'
PYTHON = '/tmp/hackapertus-ost-contract/.venv/bin/python'
ENV = dict(os.environ, PI_PACKAGE_ROOT='/home/yasuhito/.pi/agent/install/releases/1.1.0/node_modules/@earendil-works/pi-coding-agent', PI_SUBAGENTS_ROOT='/home/yasuhito/.pi/agent/npm/node_modules/@tintinweb/pi-subagents', PYTHONDONTWRITEBYTECODE='1')
PROMPTS = ROOT / 'evals/c-system-prompt/prompts'
FUTURE = ('v11', 'v12', 'v13')
RETRIES = {
    'v12-retry1': ('v12', 11, 4, '4f6a19abaf8cda671db005b96f86d4b1c9302d5cb5f8511268b63754b0ba5cce'),
    'v13-retry1': ('v13', 12, 1, '6ff3d080bbd65076685b0d0a6f2f8500fd9d339d22769c56729bab6209998f28'),
}
SELECTABLE = FUTURE + tuple(RETRIES)
TRIALS = {'cases': 54, 'repeats': 5, 'configs': 1}
WINDOW = ROOT / '.auto/window.json'
ARTIFACT_SUFFIXES = ('.json', '-system.txt', '-added.txt', '.patch', '-overlap.json')


def require_future(version):
    if version not in SELECTABLE:
        raise SystemExit('REFUSED: only v11..v13 or exact approved v12-retry1/v13-retry1; no archived execution')


def validate_window(version, window, now):
    """Pure validation for synthetic tests; runtime callers use the actual UTC clock."""
    require_future(version)
    segment = tuple(RETRIES) if version in RETRIES else FUTURE
    expected = {'timezone': 'Asia/Tokyo',
                'approved_candidates': list(segment), 'max_new_candidates': len(segment),
                'baseline_version': 'v5', 'trials': TRIALS,
                'approved': True, 'stop_on_execution_error': True}
    if (not isinstance(window, dict)
            or json.dumps({k: window.get(k) for k in expected}, sort_keys=True)
            != json.dumps(expected, sort_keys=True)):
        raise SystemExit('REFUSED: missing or invalid segment window/scope')
    try:
        start, cutoff, finish = (datetime.fromisoformat(window[k]) for k in
                                ('started_at', 'candidate_start_before', 'soft_finish_by'))
        tokyo = ZoneInfo('Asia/Tokyo')
        if (not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None
                or any(t.utcoffset() is None or t.utcoffset() != t.astimezone(tokyo).utcoffset()
                       for t in (start, cutoff, finish))
                or cutoff.astimezone(timezone.utc) - start.astimezone(timezone.utc) != timedelta(minutes=90)
                or finish.astimezone(timezone.utc) - start.astimezone(timezone.utc) != timedelta(minutes=120)
                or not start <= now < cutoff):
            raise ValueError('unknown clock or outside candidate start window')
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise SystemExit('REFUSED: invalid clock/window or candidate start cutoff reached') from exc


def check_window(version):
    try:
        window = json.loads(WINDOW.read_text())
        now = datetime.now(timezone.utc)
    except (OSError, ValueError, OverflowError) as exc:
        raise SystemExit('REFUSED: unavailable window or UTC clock') from exc
    validate_window(version, window, now)


def prior_prompt_hash(version):
    """Rollback may remove eval artifacts; never trust metadata without SYSTEM bytes."""
    location = PROMPTS
    if not all((location / (version + suffix)).is_file() for suffix in ('.json', '-system.txt')):
        location = OUT / 'candidate-archive' / version
    try:
        meta = json.loads((location / f'{version}.json').read_text())
        actual = digest((location / f'{version}-system.txt').read_bytes())
    except (OSError, ValueError) as exc:
        raise SystemExit('PREVIOUS_PROMPT_ARTIFACTS_MISSING_OR_INVALID') from exc
    assert meta['version'] == version, 'PREVIOUS_METADATA_VERSION_CHANGED'
    assert actual == meta['candidate_prompt_sha256'], 'PREVIOUS_PROMPT_HASH_CHANGED'
    return actual


def original_retry_artifacts(version):
    """Read-only original archive validation; never restore approval into a retry."""
    original, run, repeat, expected = RETRIES[version]
    archive = OUT / 'candidate-archive' / original
    meta = json.loads((archive / f'{original}.json').read_text())
    data = (archive / f'{original}-system.txt').read_bytes()
    assert meta['version'] == original, 'RETRY_ORIGINAL_METADATA_CHANGED'
    assert meta['candidate_prompt_sha256'] == digest(data) == expected, 'RETRY_ORIGINAL_HASH_CHANGED'
    stop = json.loads((OUT / f'prompt-C-{original}-r{repeat}/STOP.json').read_text())
    assert stop.get('status') == 'STOP' and type(stop.get('http_status')) is int and stop['http_status'] == 504, 'RETRY_REQUIRES_ORIGINAL_STOP_504'
    return meta, data


def refuse_duplicates(version, candidate_hash):
    require_future(version)
    if version in RETRIES:
        original, _, _, expected = RETRIES[version]
        original_retry_artifacts(version)
        assert candidate_hash == expected, 'RETRY_PROMPT_HASH_CHANGED'
        # Check all original candidates, including later ones, except the exact pair.
        previous_versions = [f'v{i}' for i in range(1, 14) if f'v{i}' != original]
    else:
        previous_versions = [f'v{i}' for i in range(1, int(version[1:]))]
    for previous in previous_versions:
        assert candidate_hash != prior_prompt_hash(previous), 'DUPLICATE_CANDIDATE'


def preserve_candidate(version):
    """Preserve exact offline inputs once; an identical archive is not a job fence."""
    payload = {version + suffix: (PROMPTS / (version + suffix)).read_bytes()
               for suffix in ARTIFACT_SUFFIXES}
    archive = OUT / 'candidate-archive' / version
    if archive.exists():
        assert {p.name for p in archive.iterdir()} == set(payload), 'CANDIDATE_ARCHIVE_CHANGED'
        assert all((archive / name).read_bytes() == data for name, data in payload.items()), 'CANDIDATE_ARCHIVE_CHANGED'
        return payload
    archive.mkdir(parents=True, exist_ok=False)
    for name, data in payload.items():
        with (archive / name).open('xb') as handle:
            handle.write(data)
    return payload


def verify_candidate_artifacts(version, payload):
    archive = OUT / 'candidate-archive' / version
    for name, data in payload.items():
        assert (PROMPTS / name).read_bytes() == data, 'CANDIDATE_ARTIFACT_CHANGED'
        assert (archive / name).read_bytes() == data, 'CANDIDATE_ARCHIVE_CHANGED'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def system(text):
    ns = {}
    for node in ast.parse(text).body:
        if (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in {'SYSTEM', 'NEUTRAL_GUARD', 'FINAL_VERIFICATION', 'PARAPHRASE_GUARD'} for t in node.targets)) or (isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and node.target.id == 'SYSTEM'):
            exec(compile(ast.Module(body=[node], type_ignores=[]), '<prompt constants>', 'exec'), ns)
    return ns['SYSTEM']


def candidate_source(text, candidate):
    """Override SYSTEM after frozen assembly, leaving all other source intact."""
    anchor = 'SYSTEM += "\\n\\n" + NEUTRAL_GUARD + "\\n\\n" + PARAPHRASE_GUARD'
    if text.count(anchor) == 1:
        return text.replace(anchor, anchor + '\nSYSTEM = ' + repr(candidate))
    # Also support source-only snapshots whose final SYSTEM is already literal.
    assignments = [node for node in ast.parse(text).body
                   if isinstance(node, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'SYSTEM' for t in node.targets)]
    node = assignments[-1]
    assert node.lineno == node.end_lineno and isinstance(node.value, ast.Constant), 'ADOPTED_SYSTEM_ASSIGNMENT_CHANGED'
    lines = text.splitlines(keepends=True)
    lines[node.lineno - 1] = 'SYSTEM = ' + repr(candidate) + '\n'
    return ''.join(lines)


def refuse_batch(version):
    # Include every sidecar, including STOP/fences, before any request.
    for repeat in range(1, 6):
        if list(OUT.glob(f'prompt-C-{version}-r{repeat}*')):
            raise SystemExit('PREEXISTING_CANDIDATE_PATH: NO EXECUTION OR RESUME')
    if (OUT / f'hillclimb-{version}-analysis').exists():
        raise SystemExit('PREEXISTING_CANDIDATE_ANALYSIS: NO EXECUTION')


def validate_metadata(version, meta, execute):
    require_future(version)
    trials = TRIALS
    if (meta.get('version') != version
            or json.dumps(meta.get('proposed_trials'), sort_keys=True) != json.dumps(trials, sort_keys=True)):
        raise SystemExit('REFUSED: candidate version/proposed_trials must match 54 x 5 x 1')
    if version in RETRIES:
        original, run, _, expected = RETRIES[version]
        original_meta, original_data = original_retry_artifacts(version)
        assert meta.get('original_candidate_version') == original, 'RETRY_ORIGINAL_PAIR_CHANGED'
        assert type(meta.get('retry_of_run')) is int and meta['retry_of_run'] == run, 'RETRY_ORIGINAL_PAIR_CHANGED'
        assert meta.get('candidate_prompt_sha256') == expected, 'RETRY_PROMPT_HASH_CHANGED'
        assert (PROMPTS / f'{version}-system.txt').read_bytes() == original_data, 'RETRY_SYSTEM_BYTES_CHANGED'
        assert meta.get('baseline_prompt_sha256') == original_meta['baseline_prompt_sha256'], 'RETRY_BASELINE_CHANGED'
    if execute or version in RETRIES:
        # A candidate-specific machine-readable scope cannot inherit v3 permission.
        scope = {'candidate': version, 'cases': 54, 'repeats': 5, 'configs': 1}
        if (meta.get('inference_approved') is not True
                or json.dumps(meta.get('approved_trials'), sort_keys=True) != json.dumps(trials, sort_keys=True)
                or json.dumps(meta.get('approval_scope'), sort_keys=True) != json.dumps(scope, sort_keys=True)):
            raise SystemExit('REFUSED: explicit selected-candidate approval and fixed approved_trials/scope required')


def sources(m):
    return {k[k.index('track_2a/'):]: v for k, v in m['sources'].items()}


def audit(manifest, baseline, mapping):
    assert len(manifest['frozen']) == len(baseline['frozen']) == 54
    for key in baseline:
        if key not in {'sources', 'frozen'}:
            assert manifest[key] == baseline[key], 'PROTOCOL_CHANGED: ' + key
    bs, cs = sources(baseline), sources(manifest)
    assert bs.keys() == cs.keys()
    assert [k for k in bs if bs[k] != cs[k]] == ['track_2a/src/predict.py'], 'NON_PROMPT_SOURCE_CHANGE'
    for actual, old in zip(manifest['frozen'], baseline['frozen']):
        case = dict(old['case'])
        if 'booklet' in case:
            case['booklet'] = {**case['booklet'], 'path': mapping[case['booklet']['path']]}
        assert actual['case'] == case, 'CASE_CHANGED'
        assert actual['messages'][1:] == old['messages'][1:], 'MODEL_INPUT_CHANGED'
        assert actual['messages'][0]['content'].endswith('\n\n' + baseline['protocol_reminder'])
        for key in ('pages', 'candidate_ids', 'schema_sha256'):
            assert actual[key] == old[key], 'FROZEN_INPUT_CHANGED: ' + key


def workspace_env(workspace, execute):
    env = dict(ENV, TMPDIR=str(workspace / 'output/cscs/tmp'))
    if not execute:
        for key in ('API_KEY', 'BASE_URL', 'OPENAI_API_KEY'):
            env.pop(key, None)
    return env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, choices=tuple(f'v{i}' for i in range(1, 14)) + tuple(RETRIES))
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--prepare-only', action='store_true')
    modes.add_argument('--execute-approved', action='store_true', help='Only after human approval for this candidate, exactly 54 x 5 x 1')
    args = parser.parse_args()
    version = args.candidate
    require_future(version)
    if args.execute_approved:
        check_window(version)  # Before archive extraction or costly preflights.
    refuse_batch(version)
    if not all((PROMPTS / name).is_file() for name in (f'{version}.json', f'{version}-system.txt')):
        raise SystemExit('CANDIDATE_ARTIFACTS_MISSING: selected metadata/system required; no requests or jobs created')
    meta = json.loads((PROMPTS / f'{version}.json').read_text())
    validate_metadata(version, meta, args.execute_approved)
    candidate = (PROMPTS / f'{version}-system.txt').read_text()
    assert digest(candidate.encode()) == meta['candidate_prompt_sha256']
    assert digest((PROMPTS / 'v5-system.txt').read_bytes()) == meta['baseline_prompt_sha256']
    refuse_duplicates(version, meta['candidate_prompt_sha256'])
    payload = preserve_candidate(version)  # Offline, before any workspace or inference.
    original = (ROOT / 'track_2a/src/predict.py').read_bytes()
    archive = subprocess.check_output(['/usr/bin/git', 'archive', 'HEAD', 'track_2a/src', 'track_2a/dev/cscs', 'track_2a/dev/format'], cwd=ROOT)
    archive_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    baseline = json.loads((OUT / 'prompt-C-v5-r5/manifest.json').read_text())
    provenance = json.loads((OUT / 'preparation-provenance.json').read_text())
    historical_mapping = json.loads((OUT / 'prompt-C-v5-r5-provenance.json').read_text())['pdf_mapping']
    provenance['pdf_mapping'] = {historical_mapping[old]: local
                                 for old, local in provenance['pdf_mapping'].items()}
    pdfs = {x['case']['booklet']['path'] for x in baseline['frozen'] if 'booklet' in x['case']}
    assert len(pdfs) == 6 and pdfs == set(provenance['pdf_mapping'])
    workroot = OUT / 'workspaces'
    workroot.mkdir(parents=True, exist_ok=True)
    workspaces = []
    # Preflight the entire batch before execution, never create designated jobs offline.
    for repeat in range(1, 6):
        workspace = Path(tempfile.mkdtemp(prefix=f'{version}-r{repeat}-', dir=workroot))
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(workspace, filter='data')
        (workspace / 'booklets').mkdir()
        (workspace / 'output/cscs/tmp').mkdir(parents=True)
        mapping = {}
        for old, local in provenance['pdf_mapping'].items():
            source = ROOT / local
            assert source.resolve().is_relative_to(ROOT) and not source.is_symlink()
            target = workspace / 'booklets' / Path(old).name
            shutil.copyfile(source, target)
            assert digest(target.read_bytes()) == digest(source.read_bytes())
            mapping[old] = str(target)
        target = workspace / 'track_2a/src/predict.py'
        text = target.read_text()
        assert digest(system(text).encode()) == meta['baseline_prompt_sha256'], 'ARCHIVE_V5_CHANGED'
        anchor = 'SYSTEM += "\\n\\n" + NEUTRAL_GUARD + "\\n\\n" + PARAPHRASE_GUARD'
        assert text.count(anchor) == 1
        target.write_text(candidate_source(text, candidate))
        assert digest(system(target.read_text()).encode()) == meta['candidate_prompt_sha256']
        env = workspace_env(workspace, args.execute_approved)
        command = [PYTHON, '-B', 'track_2a/dev/format/run_comparison.py', '--prepare-only', '--strategy', 'C']
        result = subprocess.run(command, cwd=workspace, env=env, capture_output=True, text=True)
        (workspace / 'prepare.log').write_text(result.stdout + result.stderr)
        if result.returncode:
            raise SystemExit('PREPARE_FAILED: NO API REQUEST; SEE WORKSPACE prepare.log')
        # Existing prepare-only prints only a hash. Capture actual preparation separately,
        # using the unchanged runner's prepare(), without invoking main or Transport.
        export = "import runpy,json; m=runpy.run_path('track_2a/dev/format/run_comparison.py'); m['legacy'].c.protect(); open('prepared.json','w').write(json.dumps(m['prepare']('C')))"
        result = subprocess.run([PYTHON, '-B', '-c', export], cwd=workspace, env=env, capture_output=True, text=True)
        (workspace / 'audit.log').write_text(result.stdout + result.stderr)
        if result.returncode:
            raise SystemExit('PREPARED_ARTIFACT_FAILED: NO API REQUEST')
        manifest = json.loads((workspace / 'prepared.json').read_text())
        audit(manifest, baseline, mapping)
        assert all(x['messages'][0]['content'] == candidate + '\n\n' + baseline['protocol_reminder'] for x in manifest['frozen'])
        workspaces.append((workspace, env, manifest, mapping))
    assert (ROOT / 'track_2a/src/predict.py').read_bytes() == original
    if not args.execute_approved:
        print(f'Prepared {version}: 5 isolated workspaces, 54 cases each; hashes/inputs/pages/IDs/source audit passed; zero requests. No candidate jobs created.')
        return
    refuse_batch(version)
    for repeat, (workspace, env, prepared, mapping) in enumerate(workspaces, 1):
        # Revocation or artifact changes during preparation must stop before requests.
        current_meta = json.loads((PROMPTS / f'{version}.json').read_text())
        validate_metadata(version, current_meta, True)
        assert current_meta == meta, 'APPROVAL_OR_METADATA_CHANGED'
        assert digest((PROMPTS / f'{version}-system.txt').read_bytes()) == meta['candidate_prompt_sha256'], 'CANDIDATE_PROMPT_CHANGED'
        verify_candidate_artifacts(version, payload)
        for relative, expected_hash in sources(prepared).items():
            source = workspace / relative
            assert source.resolve().is_relative_to(workspace) and not source.is_symlink(), 'WORKSPACE_SOURCE_NONLOCAL'
            assert digest(source.read_bytes()) == expected_hash, 'WORKSPACE_SOURCE_CHANGED'
        refuse_duplicates(version, meta['candidate_prompt_sha256'])
        assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == archive_commit, 'SOURCE_PROVENANCE_CHANGED'
        assert subprocess.check_output(['/usr/bin/git', 'archive', 'HEAD', 'track_2a/src', 'track_2a/dev/cscs', 'track_2a/dev/format'], cwd=ROOT) == archive, 'SOURCE_ARCHIVE_CHANGED'
        job = OUT / f'prompt-C-{version}-r{repeat}'
        prefix = OUT / f'prompt-C-{version}-r{repeat}'
        # Refuse future batch paths too, while preserving completed repeats.
        for future in range(repeat, 6):
            assert not list(OUT.glob(f'prompt-C-{version}-r{future}*')), 'PREEXISTING_BATCH_PATH'
        if repeat == 1:
            check_window(version)  # Last gate before first request; never gate later repeats.
        with Path(str(prefix) + '-start.txt').open('x') as f:
            f.write(str(time.time()) + '\n')
        with Path(str(prefix) + '-run.log').open('x') as stdout, Path(str(prefix) + '-stderr.log').open('x') as stderr:
            result = subprocess.run([PYTHON, '-B', 'track_2a/dev/format/run_comparison.py', '--user-run', '--strategy', 'C', '--repeat', '1', '--job', str(job)], cwd=workspace, env=env, stdout=stdout, stderr=stderr)
        for suffix, value in (('end.txt', time.time()), ('exit-code.txt', result.returncode)):
            with Path(str(prefix) + '-' + suffix).open('x') as f:
                f.write(str(value) + '\n')
        assert (ROOT / 'track_2a/src/predict.py').read_bytes() == original
        if result.returncode:
            raise SystemExit('CANDIDATE_STOP: PRESERVE FENCES; NO RETRY OR NEXT REPEAT')
        assert json.loads((job / 'manifest.json').read_text()) == prepared
        assert json.loads((job / 'summary.json').read_text())['status'] == 'completed'
        Path(str(prefix) + '-provenance.json').write_text(json.dumps({'workspace': str(workspace), 'version': version, **({k: meta[k] for k in ('original_candidate_version', 'retry_of_run')} if version in RETRIES else {}), 'repeat': repeat, 'prompt_sha256': meta['candidate_prompt_sha256'], 'pdf_mapping': mapping, 'production_unchanged': True, 'archive_commit': archive_commit, 'only_source_change': 'track_2a/src/predict.py SYSTEM assignment'}, indent=2) + '\n')
        print(f'{version} repeat {repeat}: completed', flush=True)


if __name__ == '__main__':
    main()
