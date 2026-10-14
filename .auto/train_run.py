#!/usr/bin/env python3
"""Bounded TRAIN36x5 research only. No implicit approval or same-job resume."""
import argparse
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import time
from zoneinfo import ZoneInfo

import run_candidate as old

ROOT, OUT, PROMPTS = old.ROOT, old.OUT, old.PROMPTS
RUNNER = 'track_2a/dev/format/run_comparison.py'
CONTROL = OUT / 'train-protocol.json'
WINDOW = ROOT / '.auto/train-window.json'
VERSIONS = ('v14', 'v15')
TRIALS = {'cases': 36, 'repeats': 5, 'configs': 1}
V5 = '06c89db1756d54d04cc5f1650b855acda2e2986d4c0c84943d2e54866383313c'
SPLIT = '963cb7cfaab01cb8b178cf0ce1d5207e464ad0a81b5868370186aa161d0be3d9'
OLD_RUNNER = '3677a78904776ad90249e2141f6072573424fa685267f4c61ff9e7b504ac265a'
BASE_Q = .8275862068965517
LEGACY_NOISE = .017051043674621427
FENCES = ('STOP.json', 'inflight.json', 'state.pending')


def load(path):
    return json.loads(path.read_text())


def require(ok, message):
    if not ok:
        raise ValueError(message)


def exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as handle:
        json.dump(value, handle, sort_keys=True, indent=2, allow_nan=False)
        handle.write('\n')


def train_split():
    path = ROOT / 'evals/c-system-prompt/split.json'
    require(old.digest(path.read_bytes()) == SPLIT, 'SPLIT_CHANGED')
    split = load(path)
    ids = split['train']
    require(split['seed'] == 20261016 and len(ids) == len(set(ids)) == 36, 'TRAIN_SCOPE_CHANGED')
    groups = [g for g in split['groups'].values() if set(g) <= set(ids)]
    require(set(x for g in groups for x in g) == set(ids), 'TRAIN_GROUPS_CHANGED')
    return ids, groups


def validate_window(version, window, now):
    require(version in VERSIONS, 'UNAPPROVED_CANDIDATE')
    expected = {'timezone': 'Asia/Tokyo', 'approved_candidates': list(VERSIONS),
                'max_new_candidates': 2, 'max_attempts_per_candidate': 3,
                'retry_http_status': 504, 'retry_wait_seconds': 60,
                'baseline_version': 'v5', 'trials': TRIALS,
                'approved': True, 'stop_on_execution_error': True,
                'started_at': '2026-10-14T14:14:17+09:00',
                'candidate_start_before': '2026-10-14T15:44:17+09:00',
                'soft_finish_by': '2026-10-14T16:14:17+09:00'}
    require(json.dumps({k: window.get(k) for k in expected}, sort_keys=True)
            == json.dumps(expected, sort_keys=True), 'INVALID_TRAIN_WINDOW_SCOPE')
    start, cutoff, finish = (datetime.fromisoformat(window[k]) for k in
                            ('started_at', 'candidate_start_before', 'soft_finish_by'))
    require(now.tzinfo is not None and now.utcoffset() is not None
            and all(t.utcoffset() == t.astimezone(ZoneInfo('Asia/Tokyo')).utcoffset()
                    for t in (start, cutoff, finish))
            and cutoff - start == timedelta(minutes=90)
            and finish - start == timedelta(minutes=120)
            and start <= now < cutoff, 'TRAIN_START_WINDOW_CLOSED')


def check_window(version):
    validate_window(version, load(WINDOW), datetime.now(timezone.utc))


def validate_metadata(version, meta, candidate):
    require(version in VERSIONS, 'UNAPPROVED_CANDIDATE')
    expected = {'version': version, 'proposed_trials': TRIALS, 'approved_trials': TRIALS,
                'inference_approved': True,
                'approval_scope': {'candidate': version, **TRIALS},
                'baseline_prompt_sha256': V5, 'candidate_prompt_sha256': old.digest(candidate)}
    # JSON comparison rejects bools masquerading as integer trial counts.
    require(json.dumps({k: meta.get(k) for k in expected}, sort_keys=True)
            == json.dumps(expected, sort_keys=True), 'FRESH_EXACT_TRAIN_APPROVAL_REQUIRED')
    previous = [old.digest((PROMPTS / 'v0-system.txt').read_bytes())]
    previous += [old.prior_prompt_hash(f'v{i}') for i in range(1, 14)]
    require(meta['candidate_prompt_sha256'] not in previous, 'DUPLICATE_CANDIDATE')
    other = 'v15' if version == 'v14' else 'v14'
    if (PROMPTS / f'{other}-system.txt').exists():
        require(candidate != (PROMPTS / f'{other}-system.txt').read_bytes(), 'DUPLICATE_TRAIN_CANDIDATES')


def candidate_payload(version):
    payload = {version + suffix: (PROMPTS / (version + suffix)).read_bytes()
               for suffix in old.ARTIFACT_SUFFIXES}
    validate_metadata(version, json.loads(payload[version + '.json']), payload[version + '-system.txt'])
    return payload


def baseline_paths():
    """Only TRAIN individual prediction/response records, never combined canonical outputs."""
    ids, _ = train_split()
    paths = [ROOT / 'evals/c-system-prompt/split.json', PROMPTS / 'v5-system.txt',
             OUT / 'preparation-provenance.json', OUT / 'official-rescore-evidence/provenance.json']
    dest = OUT / 'hillclimb-v5-analysis'
    paths += [dest / 'aggregate.json', dest / 'train-cases.jsonl', dest / 'train-expected.jsonl']
    for repeat in range(1, 6):
        job = OUT / f'prompt-C-v5-r{repeat}'
        m = load(job / 'manifest.json')
        require(len(m['frozen']) == 54 and old.sources(m)[RUNNER] == OLD_RUNNER, 'BASELINE_NOT_FROZEN54')
        require(not any((job / name).exists() for name in FENCES), 'BASELINE_FENCE')
        paths += [job / 'manifest.json', job / 'state.json', job / 'summary.json',
                  OUT / f'prompt-C-v5-r{repeat}-provenance.json',
                  dest / f'train-r{repeat}.json', dest / f'train-r{repeat}-predictions.jsonl']
        state = load(job / 'state.json')
        selected = {i for i, x in enumerate(m['frozen']) if x['case']['id'] in ids}
        require(len(selected) == 36, 'BASELINE_TRAIN_MISSING')
        # Names are fixed by the saved ledger; select indices before opening records.
        for category in ('cases', 'attempts'):
            for name in state[category]:
                require('/' not in name and '\\' not in name and name.endswith('.json'), 'BASELINE_RECORD_PATH')
                if any(name.startswith(f'70b-{i:02}-') for i in selected):
                    paths.append(job / name)
    return paths


def protocol_paths():
    paths = [ROOT / p for p in ('.auto/train_run.py', '.auto/train_results.py',
             '.auto/train_measure.sh', '.auto/checks.sh', '.auto/run_candidate.py', '.auto/usage.py',
             'evals/c-system-prompt/grader.py', '.auto/train-window.json')]
    paths += list((ROOT / 'track_2a/src').glob('*.py'))
    paths += [p for folder in ('track_2a/dev/cscs', 'track_2a/dev/format')
              for p in (ROOT / folder).iterdir() if p.is_file() and p.suffix in ('.py', '.ts', '.mjs', '.json')]
    paths += baseline_paths()
    historical = load(OUT / 'preparation-provenance.json')
    paths += [ROOT / path for path in historical['pdf_mapping'].values()]
    for version in VERSIONS:
        candidate_payload(version)
        paths += [PROMPTS / (version + suffix) for suffix in old.ARTIFACT_SUFFIXES]
    return sorted(set(paths))


def hashes(paths):
    require(all(p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(ROOT)
                for p in paths), 'NONLOCAL_PROTOCOL_ARTIFACT')
    return {str(p.relative_to(ROOT)): old.digest(p.read_bytes()) for p in paths}


def runtime_fingerprint():
    """Read-only installed runtime fingerprint, without importing SDKs or credentials."""
    sdk = Path(old.ENV['PI_PACKAGE_ROOT'])
    child = Path(old.ENV['PI_SUBAGENTS_ROOT'])
    roots = [sdk, child] + [sdk.parent / name for name in ('pi-ai', 'pi-agent-core', 'pi-tui')]
    paths = [Path(shutil.which('node')).resolve(), Path(old.PYTHON).resolve(),
             Path('/tmp/ost-official-evaluator-3U4yO9/env/bin/python').resolve()]
    for root in roots:
        paths.append(root / 'package.json')
        paths += sorted((root / 'dist').rglob('*.js'))
        paths += sorted((root / 'dist').rglob('*.mjs'))
    require(load(sdk / 'package.json')['version'] == '1.1.0'
            and load(child / 'package.json')['version'] == '0.19.0', 'RUNTIME_VERSION_CHANGED')
    return {str(p): old.digest(p.read_bytes()) for p in sorted(set(paths))}


def freeze_protocol():
    """Owner-operated offline freeze, exclusive and before preparation or inference."""
    window = load(WINDOW)
    for version in VERSIONS:
        validate_window(version, window, datetime.fromisoformat(window['started_at']))
        require(not list(OUT.glob(f'prompt-C-{version}-a*')), 'FREEZE_AFTER_TRIAL_REFUSED')
        old.preserve_candidate(version)
    ids, _ = train_split()
    exclusive(CONTROL, {'version': 'train36x5-1', 'case_ids': ids,
                        'runner_sha256': old.digest((ROOT / RUNNER).read_bytes()),
                        'files': hashes(protocol_paths()), 'runtime': runtime_fingerprint()})


def verify_protocol(checkpoint=False):
    control = load(CONTROL)
    require(control['version'] == 'train36x5-1' and control['case_ids'] == train_split()[0], 'CONTROL_SCOPE_CHANGED')
    require(control['files'] == hashes(protocol_paths()), 'FROZEN_PROTOCOL_CHANGED')
    require(control['runner_sha256'] == old.digest((ROOT / RUNNER).read_bytes()), 'RUNNER_CHANGED')
    require(control['runtime'] == runtime_fingerprint(), 'FROZEN_RUNTIME_CHANGED')
    for version in VERSIONS:
        old.verify_candidate_artifacts(version, candidate_payload(version))
    require(old.digest((PROMPTS / 'v5-system.txt').read_bytes()) == V5
            and old.digest(old.system((ROOT / 'track_2a/src/predict.py').read_text()).encode()) == V5, 'ADOPTED_V5_CHANGED')
    if checkpoint:
        for relative, sha in control['files'].items():
            if relative.startswith(('track_2a/', '.auto/')) and relative != '.auto/train-window.json':
                require(old.digest(subprocess.check_output(['git', 'show', f'HEAD:{relative}'], cwd=ROOT)) == sha,
                        'HEAD_CHECKPOINT_REQUIRED: ' + relative)
    return control


def job_name(version, attempt, repeat):
    require(version in VERSIONS and type(attempt) is int and attempt in (1, 2, 3)
            and type(repeat) is int and repeat in range(1, 6), 'INVALID_ATTEMPT_ID')
    return f'prompt-C-{version}-a{attempt}-r{repeat}'


def attempt_path(version, attempt):
    job_name(version, attempt, 1)
    return OUT / f'prompt-C-{version}-a{attempt}-attempt.json'


def validate_history(version, attempt, candidate_hash, now):
    """Return required wait. Never remove fences, reuse a prefix, or retry quality."""
    job_name(version, attempt, 1)
    for future in range(attempt, 4):
        require(not list(OUT.glob(f'prompt-C-{version}-a{future}-*')), 'PREEXISTING_OR_FUTURE_ATTEMPT')
    wait = 0
    for prior in range(1, attempt):
        record = load(attempt_path(version, prior))
        require(record['status'] == 'STOP504' and record['candidate_sha256'] == candidate_hash
                and record['attempt'] == prior and record['candidate'] == version
                and record['protocol_sha256'] == old.digest(CONTROL.read_bytes()), 'RETRY_REQUIRES_IDENTICAL_STOP504')
        stops = []
        complete = 0
        for repeat in range(1, 6):
            job = OUT / job_name(version, prior, repeat)
            complete += (job / 'summary.json').exists()
            if (job / 'STOP.json').exists():
                stop = load(job / 'STOP.json')
                stops.append(stop)
        require(complete < 5 and len(stops) == 1 and stops[0].get('status') == 'STOP'
                and type(stops[0].get('http_status')) is int and stops[0]['http_status'] == 504,
                'RETRY_REQUIRES_INCOMPLETE_HTTP504')
        require(type(record['ended_at']) in (int, float) and record['ended_at'] <= now, 'INVALID_FAILURE_CLOCK')
        wait = max(wait, 60 - (now - record['ended_at']))
    if version == 'v15':
        records = [load(attempt_path('v14', i)) for i in range(1, 4) if attempt_path('v14', i).exists()]
        require(records and records[-1]['status'] == 'completed'
                and [r['attempt'] for r in records] == list(range(1, len(records) + 1))
                and all(r['status'] == 'STOP504' for r in records[:-1]), 'V14_NOT_COMPLETED_STOP_ROUND')
        require(all((OUT / job_name('v14', records[-1]['attempt'], repeat) / 'summary.json').is_file()
                    for repeat in range(1, 6)), 'V14_NOT_COMPLETED_5X')
    return max(0, wait)


def audit(manifest, baseline, mapping, runner_hash, candidate):
    ids = train_split()[0]
    selected = [x for x in baseline['frozen'] if x['case']['id'] in ids]
    require(len(manifest['frozen']) == len(selected) == 36, 'TRAIN_COUNT_CHANGED')
    require(manifest['selected_case_ids'] == [x['case']['id'] for x in selected]
            and manifest['selected_case_count'] == 36, 'TRAIN_ORDER_CHANGED')
    require({k: v for k, v in manifest.items() if k not in ('frozen', 'sources', 'selected_case_ids', 'selected_case_count')}
            == {k: v for k, v in baseline.items() if k not in ('frozen', 'sources')}, 'PROTOCOL_SEMANTICS_CHANGED')
    bs, cs = old.sources(baseline), old.sources(manifest)
    require(bs.keys() == cs.keys(), 'SOURCE_SET_CHANGED')
    require(cs[RUNNER] == runner_hash, 'FROZEN_SELECTION_RUNNER_CHANGED')
    require(all(cs[k] == bs[k] for k in bs if k not in (RUNNER, 'track_2a/src/predict.py')), 'NON_PROMPT_SOURCE_CHANGED')
    for actual, saved in zip(manifest['frozen'], selected):
        case = dict(saved['case'])
        if 'booklet' in case:
            case['booklet'] = {**case['booklet'], 'path': mapping[case['booklet']['path']]}
        require(actual['case'] == case and actual['messages'][1:] == saved['messages'][1:], 'MODEL_INPUT_CHANGED')
        for key in ('pages', 'candidate_ids', 'schema_sha256'):
            require(actual[key] == saved[key], 'FROZEN_INPUT_CHANGED: ' + key)
        require(actual['messages'][0]['content'] == candidate + '\n\n' + baseline['protocol_reminder'], 'SYSTEM_CHANGED')
        require(old.digest(json.dumps(actual['messages'], ensure_ascii=False, sort_keys=True, allow_nan=False).encode())
                == actual['messages_sha256'], 'MESSAGE_DIGEST_CHANGED')


def prepare(version, execute=False):
    control = verify_protocol(checkpoint=execute)
    payload = candidate_payload(version)
    candidate = payload[version + '-system.txt'].decode()
    archive = subprocess.check_output(['git', 'archive', 'HEAD', 'track_2a/src', 'track_2a/dev/cscs', 'track_2a/dev/format'], cwd=ROOT)
    baseline = load(OUT / 'prompt-C-v5-r5/manifest.json')
    historical = load(OUT / 'prompt-C-v5-r5-provenance.json')['pdf_mapping']
    local = load(OUT / 'preparation-provenance.json')['pdf_mapping']
    pdfs = {historical[old_path]: ROOT / path for old_path, path in local.items()}
    workroot = OUT / 'train-workspaces'
    workroot.mkdir(exist_ok=True)
    workspaces = []
    for repeat in range(1, 6):
        workspace = Path(tempfile.mkdtemp(prefix=f'{version}-r{repeat}-', dir=workroot))
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(workspace, filter='data')
        # Only newly approved runner bytes may differ from the saved54 protocol.
        # Offline preparation can precede HEAD checkpoint. Execution cannot.
        (workspace / RUNNER).write_bytes((ROOT / RUNNER).read_bytes())
        (workspace / 'booklets').mkdir()
        (workspace / 'output/cscs/tmp').mkdir(parents=True)
        mapping = {}
        for saved_path, source in pdfs.items():
            require(not source.is_symlink() and source.resolve().is_relative_to(ROOT), 'NONLOCAL_PDF')
            target = workspace / 'booklets' / Path(saved_path).name
            shutil.copyfile(source, target)
            require(old.digest(target.read_bytes()) == old.digest(source.read_bytes()), 'PDF_CHANGED')
            mapping[saved_path] = str(target)
        target = workspace / 'track_2a/src/predict.py'
        require(old.digest(old.system(target.read_text()).encode()) == V5, 'ARCHIVE_NOT_V5')
        target.write_text(old.candidate_source(target.read_text(), candidate))
        exclusive(workspace / 'train-ids.json', control['case_ids'])
        env = old.workspace_env(workspace, execute)
        offline_env = {k: v for k, v in env.items() if not any(x in k.upper() for x in ('KEY', 'TOKEN', 'SECRET', 'PASSWORD', 'AUTH', 'BASE_URL'))}
        export = "import runpy,json; m=runpy.run_path('track_2a/dev/format/run_comparison.py'); m['legacy'].c.protect(); open('prepared.json','x').write(json.dumps(m['prepare']('C',json.load(open('train-ids.json')))))"
        result = subprocess.run([old.PYTHON, '-B', '-c', export], cwd=workspace, env=offline_env, capture_output=True, text=True)
        (workspace / 'prepare.log').write_text(result.stdout + result.stderr)
        require(result.returncode == 0, 'OFFLINE_PREPARE_FAILED: ' + str(workspace))
        manifest = load(workspace / 'prepared.json')
        audit(manifest, baseline, mapping, control['runner_sha256'], candidate)
        frozen_files = {str(p.relative_to(workspace)): old.digest(p.read_bytes())
                        for p in workspace.rglob('*') if p.is_file()}
        workspaces.append((workspace, env, manifest, mapping, frozen_files))
    verify_protocol(checkpoint=execute)
    return workspaces


def guarded_command(job, first_repeat, retry_after=0):
    """Gold-free subprocess shim. Gate the actual first POST, not later repeats.

    Transport itself and its payload/caps/retry semantics remain unchanged.
    """
    args = ['--user-run', '--strategy', 'C', '--repeat', '1',
            '--case-ids-file', 'train-ids.json', '--job', str(job)]
    if not first_repeat:
        return [old.PYTHON, '-B', RUNNER, *args]
    window = load(WINDOW)
    shim = '''import runpy,sys,time
from datetime import datetime,timezone
m=runpy.run_path(sys.argv[1])
start=datetime.fromisoformat(sys.argv[2]); cutoff=datetime.fromisoformat(sys.argv[3]); retry_after=float(sys.argv[4])
sys.argv=[sys.argv[1]]+sys.argv[5:]
original=m['Transport']
class Guarded(original):
    first=True
    def request(self,*args,**kwargs):
        if Guarded.first:
            now=datetime.now(timezone.utc)
            if not start <= now < cutoff or time.time() < retry_after:
                raise m['Stop']('FIRST_REQUEST_WINDOW_OR_RETRY_WAIT_REFUSED')
            Guarded.first=False
        return super().request(*args,**kwargs)
m['main'].__globals__['Transport']=Guarded
m['main']()
'''
    return [old.PYTHON, '-B', '-c', shim, RUNNER, window['started_at'],
            window['candidate_start_before'], str(retry_after), *args]


def execute(version, attempt):
    check_window(version)
    control = verify_protocol(checkpoint=True)
    sha = json.loads(candidate_payload(version)[version + '.json'])['candidate_prompt_sha256']
    wait = validate_history(version, attempt, sha, time.time())
    if wait:
        time.sleep(wait)
    check_window(version)
    workspaces = prepare(version, execute=True)
    require(validate_history(version, attempt, sha, time.time()) == 0, 'RETRY_WAIT_INCOMPLETE')
    record_path = attempt_path(version, attempt)
    record = {'candidate': version, 'attempt': attempt, 'candidate_sha256': sha,
              'protocol_sha256': old.digest(CONTROL.read_bytes()), 'status': 'inflight', 'started_at': time.time()}
    exclusive(record_path, record)  # Permanent batch fence, even if the orchestrator crashes.
    for repeat, (workspace, env, manifest, mapping, frozen_files) in enumerate(workspaces, 1):
        verify_protocol(checkpoint=True)
        require({str(p.relative_to(workspace)): old.digest(p.read_bytes())
                 for p in workspace.rglob('*') if p.is_file()} == frozen_files, 'WORKSPACE_ARTIFACT_CHANGED')
        for relative, expected in old.sources(manifest).items():
            require(old.digest((workspace / relative).read_bytes()) == expected, 'WORKSPACE_SOURCE_CHANGED')
        if repeat == 1:
            check_window(version)  # Actual UTC, immediately before first subprocess/API; not later repeats.
        name = job_name(version, attempt, repeat)
        for future in range(repeat, 6):
            require(not list(OUT.glob(job_name(version, attempt, future) + '*')), 'PREEXISTING_JOB_NO_RESUME')
        prefix, job = OUT / name, OUT / name
        exclusive(Path(str(prefix) + '-provenance.json'), {'workspace': str(workspace), 'pdf_mapping': mapping,
                  'protocol_sha256': record['protocol_sha256'], 'runner_sha256': control['runner_sha256'],
                  'manifest_sha256': old.digest(json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode())})
        started = time.time()
        retry_after = load(attempt_path(version, attempt - 1))['ended_at'] + 60 if attempt > 1 else 0
        with Path(str(prefix) + '-run.log').open('x') as stdout, Path(str(prefix) + '-stderr.log').open('x') as stderr:
            result = subprocess.run(guarded_command(job, repeat == 1, retry_after), cwd=workspace,
                                    env=env, stdout=stdout, stderr=stderr)
        ended = time.time()
        exclusive(Path(str(prefix) + '-timing.json'), {'start': started, 'end': ended, 'exit_code': result.returncode})
        if result.returncode:
            stop = load(job / 'STOP.json') if (job / 'STOP.json').exists() else {}
            record.update(status='STOP504' if stop.get('status') == 'STOP' and type(stop.get('http_status')) is int
                          and stop['http_status'] == 504 else 'OTHER_STOP', ended_at=ended,
                          failed_repeat=repeat, failed_request_usage='unknown; not included in completed-batch tokens')
            record_path.write_text(json.dumps(record, indent=2) + '\n')
            raise SystemExit('EXECUTION_STOP: preserve all fences; only explicit fresh HTTP504 attempt may retry')
        require(load(job / 'manifest.json') == manifest and load(job / 'summary.json')['status'] == 'completed', 'BATCH_INCOMPLETE')
    record.update(status='grading', ended_at=time.time())
    record_path.write_text(json.dumps(record, indent=2) + '\n')
    # Grading occurs outside every isolated model workspace, only after all five complete.
    try:
        subprocess.run(['/tmp/ost-official-evaluator-3U4yO9/env/bin/python', '-B', '.auto/train_results.py', '--candidate', version, '--attempt', str(attempt), '--score'], cwd=ROOT, check=True)
    except BaseException:
        record.update(status='OTHER_STOP', stage='grading_or_reporting', ended_at=time.time())
        record_path.write_text(json.dumps(record, indent=2) + '\n')
        raise
    record.update(status='completed', ended_at=time.time())
    record_path.write_text(json.dumps(record, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--freeze-protocol', action='store_true')
    mode.add_argument('--prepare-candidate', choices=VERSIONS)
    mode.add_argument('--execute-approved', choices=VERSIONS)
    parser.add_argument('--attempt', type=int, choices=(1, 2, 3))
    args = parser.parse_args()
    if args.freeze_protocol:
        require(args.attempt is None, 'UNEXPECTED_ATTEMPT')
        freeze_protocol()
    elif args.prepare_candidate:
        require(args.attempt is None, 'UNEXPECTED_ATTEMPT')
        prepare(args.prepare_candidate)
        print('Prepared 5 isolated TRAIN36 workspaces. Zero requests, credentials or jobs. No grading.')
    else:
        require(args.attempt is not None, 'EXPLICIT_ATTEMPT_REQUIRED')
        execute(args.execute_approved, args.attempt)


if __name__ == '__main__':
    main()
