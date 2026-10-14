#!/usr/bin/env python3
"""Owner-approved PUBLIC60 continuation, derived from frozen public_validation.py. Preparation/checks never instantiate a transport.

Only the isolated runner's legacy.prepare hook is replaced. No legacy fixture is
copied or opened. Live phases are exclusive, non-resumable owner operations.
"""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / 'output/validation/v16-public-v2-completion'
OUT = ROOT / 'output/cscs'
CONTROL = OUT / 'public60-continue-v16-protocol.json'
RUNNER = 'track_2a/dev/format/run_comparison.py'
PYTHON = '/tmp/hackapertus-ost-contract/.venv/bin/python'
OFFICIAL = Path('/tmp/ost-official-evaluator-3U4yO9/repo')
SCORER_PYTHON = '/tmp/ost-official-evaluator-3U4yO9/env/bin/python'
SDK = Path('/home/yasuhito/.pi/agent/install/releases/1.1.0/node_modules/@earendil-works/pi-coding-agent')
CHILD = Path('/home/yasuhito/.pi/agent/npm/node_modules/@tintinweb/pi-subagents')
SELECTION = 'acf1805ca02358e8913ead392e587247b2b0f36d7300e8114e790307807e8007'
COMPLETION = '530708f506490841e922c6ce99c88d7f5cbc5f4902e14c9f599317354ec1dfbf'
MANIFEST = 'b08743451bdbb67476ce2fc8641c34824fe1ae1d1fa10a7c2d14d512d4036dc4'
V5 = '06c89db1756d54d04cc5f1650b855acda2e2986d4c0c84943d2e54866383313c'
FENCES = ('STOP.json', 'inflight.json', 'state.pending')
VARIANTS = ('v5', 'v16')
CAP = 300
BUDGET = 78_720_000
BATCH_SECONDS = 5400
BYTE_CAP = 240_000


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()


def load(path):
    require(not path.is_symlink(), 'SYMLINK_REFUSED')
    return json.loads(path.read_bytes())


def rows(path):
    require(not path.is_symlink(), 'SYMLINK_REFUSED')
    return [json.loads(line) for line in path.read_bytes().splitlines()]


def exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(encode(value)); stream.flush(); os.fsync(stream.fileno())


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def safe_relative(base, relative):
    path = base / relative
    require(not any(p.is_symlink() for p in [path, *path.parents]) and path.resolve().is_relative_to(base.resolve())
            and path.is_file(), 'NONLOCAL_ARTIFACT')
    return path


def bundle_manifest():
    path = BUNDLE / 'selection-manifest.json'
    require(sha(path.read_bytes()) == MANIFEST, 'PUBLIC_MANIFEST_CHANGED')
    m = load(path)
    require(m['selection_freeze_sha256'] == SELECTION and m['freeze_sha256'] == COMPLETION,
            'PUBLIC_SELECTION_CHANGED')
    for relative, digest in m['artifact_sha256'].items():
        require(sha(safe_relative(BUNDLE, relative).read_bytes()) == digest, 'PUBLIC_ARTIFACT_CHANGED')
    for relative, digest in m['code_sha256'].items():
        require(sha(safe_relative(ROOT, relative).read_bytes()) == digest, 'PUBLIC_PREPARATION_SOURCE_CHANGED')
    selection = m['selection']
    used = m['used_source']['used_rows']
    require(len(selection) == 30 and len(used) == 27, 'PUBLIC_PAIR_SCOPE_CHANGED')
    used_indices = {r['source_index'] for r in used}
    blocked = {key: {r['group_digests'][key] for r in used} for key in ('claim', 'reference')}
    require(len(used_indices) == 27 and len(m['used_source']['mapping']) == 54,
            'UNKNOWN_USED_MAPPING')
    mapping = m['used_source']['mapping']
    require({r['source_index'] for r in mapping} == used_indices
            and all(sum(x['source_index'] == i for x in mapping) == 2 for i in used_indices),
            'UNKNOWN_USED_MAPPING')
    require(all(r['source_index'] not in used_indices and all(
        r['group_digests'][key] not in blocked[key] for key in blocked) for r in selection),
        'PUBLIC_USED_OVERLAP')
    require(len({r['group_digests']['reference'] for r in selection}) == 30,
            'PUBLIC_REFERENCE_DUPLICATE')
    cases = rows(BUNDLE / 'cases.jsonl')
    require(len(cases) == 60 and len({r['id'] for r in cases}) == 60
            and [r['id'] for r in cases] == [cid for r in selection for cid in r['case_ids']]
            and sum('booklet' in r for r in cases) == 30, 'PUBLIC_INPUT_SCOPE_CHANGED')
    for case in cases:
        require(set(case) <= {'id', 'claim', 'vote', 'booklet', 'reference'}
                and ('booklet' in case) != ('reference' in case), 'NON_INPUT_METADATA')
    return m


def source_files():
    # Explicit source-only allowlist: no fixture, dataset, response, gold or
    # historical job directories. Runtime package-lock is retained unchanged.
    paths = list((ROOT / 'track_2a/src').glob('*.py'))
    for directory in ('track_2a/dev/format', 'track_2a/dev/cscs'):
        paths += [p for p in (ROOT / directory).iterdir()
                  if p.is_file() and p.suffix in ('.py', '.ts', '.mjs', '.json')]
    return sorted(set(paths))


def fingerprint(paths, base=None):
    result = {}
    for path in sorted(set(paths)):
        require(path.is_file() and not path.is_symlink(), 'NONREGULAR_SOURCE')
        result[str(path.relative_to(base)) if base else str(path)] = sha(path.read_bytes())
    return result


def runtime():
    require(load(SDK / 'package.json')['version'] == '1.1.0'
            and load(CHILD / 'package.json')['version'] == '0.19.0', 'PINNED_RUNTIME_REQUIRED')
    roots = [SDK, CHILD] + [SDK.parent / n for n in ('pi-ai', 'pi-agent-core', 'pi-tui')]
    paths = [Path(shutil.which('node')).resolve(), Path(PYTHON).resolve(),
             Path(SCORER_PYTHON).resolve(), OFFICIAL / 'evaluate.py']
    for root in roots:
        paths += [root / 'package.json'] + list((root / 'dist').rglob('*.js')) + list((root / 'dist').rglob('*.mjs'))
    commit = subprocess.check_output(['git', '-C', str(OFFICIAL), 'rev-parse', 'HEAD'], text=True).strip()
    require(commit == '5e6957729b77a126006049305ad1ef241211a5b4', 'EVALUATOR_COMMIT_CHANGED')
    require(not subprocess.check_output(['git', '-C', str(OFFICIAL), 'status', '--porcelain', '--', 'evaluate.py']),
            'EVALUATOR_MODIFIED')
    return fingerprint(paths)


def controls():
    paths = source_files() + [ROOT / p for p in (
        '.auto/public_validation.py', '.auto/test_public_validation.py',
        '.auto/public_validation_continue.py', '.auto/test_public_validation_continue.py', '.auto/checks.sh',
        '.auto/measure.sh',
        '.auto/train_route.py', '.auto/run_candidate.py', 'evals/c-system-prompt/grader.py',
        'evals/c-system-prompt/prompts/v5-system.txt',
        'output/cscs/candidate-archive/v15/v15-system.txt',
        'evals/c-system-prompt/prompts/v16-system.txt')]
    return fingerprint(paths, ROOT)


def environment(workspace):
    # Never inspect credentials. Transport uses its existing provider path.
    env = {k: v for k, v in os.environ.items() if not any(
        s in k.upper() for s in ('KEY', 'TOKEN', 'SECRET', 'PASSWORD', 'AUTH', 'BASE_URL'))}
    env.update(PI_PACKAGE_ROOT=str(SDK), PI_SUBAGENTS_ROOT=str(CHILD),
               PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(workspace / 'output/cscs/tmp'))
    return env


def copy_workspace(workspace, variant):
    require(variant in VARIANTS, 'UNAPPROVED_VARIANT')
    import run_candidate as old
    import train_route as route
    for path in source_files():
        target = workspace / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    # These helpers are controls only, never imported historical validation.
    for relative in ('.auto/public_validation_continue.py', '.auto/train_route.py', '.auto/run_candidate.py'):
        target = workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    (workspace / 'output/cscs/tmp').mkdir(parents=True)
    (workspace / 'booklets').mkdir()
    cases = rows(BUNDLE / 'cases.jsonl')
    for case in cases:
        if 'booklet' in case:
            name = Path(case['booklet']['path']).name
            source = safe_relative(BUNDLE, 'booklets/' + name)
            target = workspace / 'booklets' / name
            if not target.exists():
                shutil.copyfile(source, target)
            case['booklet'] = {**case['booklet'], 'path': str(target)}
    # Model workspace has input-only cases. No manifest/audit/source metadata or expected file.
    exclusive(workspace / 'public-inputs.json', cases)
    target = workspace / 'track_2a/src/predict.py'
    require(sha(old.system(target.read_text()).encode()) == V5, 'SOURCE_SYSTEM_NOT_V5')
    if variant == 'v16':
        raw = (ROOT / 'evals/c-system-prompt/prompts/v16-system.txt').read_bytes()
        route.bundle(raw, ROOT, sha)
        target.write_text(route.candidate_source(target.read_text(), raw.decode(), old))
    return fingerprint([p for p in workspace.rglob('*') if p.is_file()], workspace)


def external_base(runner, workspace):
    """Same base keys as legacy.prepare, but only external input cases."""
    legacy = runner.legacy
    e = legacy.engine()
    cases = load(workspace / 'public-inputs.json')
    require(len(cases) == 60, 'PUBLIC60_REQUIRED')
    frozen = []
    for case in cases:
        require(set(case) <= {'id', 'claim', 'vote', 'booklet', 'reference'}, 'NON_INPUT_METADATA')
        pages, messages = e.context(case, workspace, selection_strategy='vote_pages')
        messages[0]['content'] += '\n\n' + legacy.PROTOCOL_REMINDER
        require(len(legacy.encode(messages)) <= BYTE_CAP, 'CONTEXT_BYTE_LIMIT')
        frozen.append({'case': case, 'pages': pages, 'messages': messages,
                       'messages_sha256': sha(encode(messages))})
    files = [legacy.c.APP_SRC / n for n in ('predict.py', 'source_spans.py', 'document_selection.py')]
    files += [workspace / 'track_2a/dev/cscs/cscs_check.py', workspace / 'track_2a/dev/cscs/cscs_dev54.py']
    return {'version': 2, 'protocol_reminder': legacy.PROTOCOL_REMINDER,
            'native_schema': 'offline proposal only, not sent',
            'case_sha256': sha((workspace / 'public-inputs.json').read_bytes()),
            'models': legacy.MODELS, 'request_limit': legacy.MAX_REQUESTS,
            'token_budget': legacy.TOKEN_BUDGET, 'request_token_reserve': legacy.RESERVE,
            'output_limit': 256, 'temperature': 0, 'selection_strategy': 'vote_pages',
            'sources': fingerprint(files), 'frozen': frozen}


def isolated_prepare(workspace):
    runner = module(workspace / RUNNER, 'public60_runner')
    # This module is loaded only in a dedicated subprocess per workspace.
    runner.legacy.prepare = lambda: external_base(runner, workspace)
    m = runner.prepare('C', [c['id'] for c in load(workspace / 'public-inputs.json')])
    m.update(request_limit=CAP, token_budget=BUDGET)
    return runner, m


def export(workspace, capture=False):
    command = [PYTHON, '-B', '.auto/public_validation_continue.py', '--export-workspace']
    if capture:
        command.append('--capture-sdk')
    result = subprocess.run(command, cwd=workspace, env=environment(workspace), capture_output=True)
    require(result.returncode == 0, 'OFFLINE_WORKSPACE_PREPARATION_FAILED')
    return load(workspace / 'prepared.json')


def audit(m, variant, workspace):
    import run_candidate as old
    import train_route as route
    prepared = rows(BUNDLE / 'prepared-contexts.jsonl')
    audits = rows(BUNDLE / 'context-audit.jsonl')
    cases = rows(BUNDLE / 'cases.jsonl')
    schema_runner = module(ROOT / RUNNER, 'public60_schema_runner')
    require(len(m['frozen']) == len(prepared) == len(audits) == 60, 'PUBLIC60_COUNT')
    require(m['request_limit'] == CAP and m['token_budget'] == BUDGET
            and m['parent_completion_limit'] == 3 and m['child_completion_limit'] == 2
            and m['schema_repair_limit'] == 1 and m['temperature'] == 0
            and m['output_limit'] == 256 and m['request_wall_seconds'] == 60
            and m['socket_seconds'] == 45 and m['case_wall_seconds'] == 300,
            'EXECUTION_POLICY_CHANGED')
    for item, saved, a, original in zip(m['frozen'], prepared, audits, cases):
        case = json.loads(json.dumps(original))
        if 'booklet' in case:
            case['booklet']['path'] = str(workspace / 'booklets' / Path(case['booklet']['path']).name)
        require(item['case'] == case and item['case']['id'] == saved['id'] == a['id'], 'CASE_MAPPING_CHANGED')
        require(item['messages'][1:] == saved['messages'][1:], 'MESSAGES1_CHANGED')
        require(item['candidate_ids'] == a['candidate_ids']
                and [n for n, p in enumerate(item['pages'], 1) if p.strip()] == a['selected_pages'],
                'PAGE_OR_CANDIDATE_CHANGED')
        audit_encode = lambda x: (json.dumps(x, ensure_ascii=False, sort_keys=True,
                                            separators=(',', ':'), allow_nan=False) + '\n').encode()
        require(sha(audit_encode(item['pages'])) == a['selected_page_text_sha256'], 'PAGE_TEXT_CHANGED')
        payload = json.loads(item['messages'][1]['content'])
        require(sorted(payload) == a['payload_keys']
                and sha(audit_encode(sorted(payload['source_spans'][0]))) == a['span_schema_sha256'],
                'SPAN_SCHEMA_CHANGED')
        require(sha(encode(schema_runner.schemas(item['candidate_ids']))) == item['schema_sha256'],
                'NATIVE_SCHEMA_CHANGED')
        task = 'A' if 'booklet' in case else 'B'
        system = (ROOT / route.SOURCE_ARTIFACTS[task]).read_text() if variant == 'v16' else old.system((ROOT / 'track_2a/src/predict.py').read_text())
        require(sha(system.encode()) == (route.SYSTEM_HASHES[task] if variant == 'v16' else V5), 'SYSTEM_HASH_CHANGED')
        require(item['messages'][0] == {**saved['messages'][0], 'content': system + '\n\n' + m['protocol_reminder']}
                and sha(encode(item['messages'])) == item['messages_sha256'], 'MESSAGE_SYSTEM_CHANGED')
    for path, digest in m['sources'].items():
        source = Path(path) if Path(path).is_absolute() else workspace / path
        require(source.resolve().is_relative_to(workspace.resolve()) and sha(source.read_bytes()) == digest,
                'WORKSPACE_SOURCE_CHANGED')


ORIGINAL_CONTROL = OUT / 'public60-v16-protocol.json'
ORIGINAL_SHA = '719f36396fb3807862dd8403425462a47e0a1cb7de1bfa794404e405ce22e2e0'
CHECKPOINT = OUT / 'public60-continuation-original-checkpoint.json'
CHECKPOINT_SHA = '7c67d1ccf25c10b81eff0e4de118d9b3e60ad0fc495b552a8f1e64cf503af375'


def new_scope():
    return [('v5', r) for r in range(2, 6)] + [('v16', r) for r in range(1, 6)]


def workspace_inventory(workspace, files):
    require(not any(p.is_symlink() for p in [workspace, *workspace.parents])
            and not any(p.is_symlink() for p in workspace.rglob('*')), 'SYMLINK_REFUSED')
    require({str(p.relative_to(workspace)) for p in workspace.rglob('*') if p.is_file()} == set(files),
            'UNFROZEN_WORKSPACE_FILE')


def verify_original():
    # Only approved complete r1 is importable. Parent phase STOP stays untouched.
    require(sha(ORIGINAL_CONTROL.read_bytes()) == ORIGINAL_SHA, 'ORIGINAL_PROTOCOL_CHANGED')
    require(sha(CHECKPOINT.read_bytes()) == CHECKPOINT_SHA, 'ORIGINAL_CHECKPOINT_CHANGED')
    checkpoint = load(CHECKPOINT)
    for name, digest in checkpoint.items():
        require(sha(safe_relative(ROOT, name).read_bytes()) == digest, 'ORIGINAL_ARTIFACT_CHANGED')
    original = load(ORIGINAL_CONTROL)
    require(original['version'] == 'public60-v16-1' and original['runtime'] == runtime(),
            'ORIGINAL_RUNTIME_CHANGED')
    for name, digest in original['files'].items():
        if name not in ('.auto/measure.sh', '.auto/checks.sh'):
            require(sha(safe_relative(ROOT, name).read_bytes()) == digest, 'ORIGINAL_SOURCE_CHANGED')
    require([j['name'] for j in original['jobs']] ==
            [f'public60-{v}-r{r}' for v in VARIANTS for r in range(1, 6)], 'ORIGINAL_SCOPE_CHANGED')
    for j in original['jobs']:
        w = Path(j['workspace'])
        workspace_inventory(w, j['files'])
        for name, digest in j['files'].items():
            require(sha(safe_relative(w, name).read_bytes()) == digest, 'ORIGINAL_WORKSPACE_CHANGED')
        m = load(w / 'prepared.json')
        require(sha(encode(m)) == j['manifest_sha256'], 'ORIGINAL_MANIFEST_CHANGED')
        audit(m, j['variant'], w)
    first = original['jobs'][0]
    require(first['name'] == 'public60-v5-r1' and first['variant'] == 'v5' and first['repeat'] == 1,
            'IMPORT_ID_CHANGED')
    job = OUT / first['name']
    require(sha(encode(load(job / 'manifest.json'))) == first['manifest_sha256'], 'IMPORT_MANIFEST_CHANGED')
    stats = completed_result(job, bind=False)
    require(stats['valid'] == 59 and stats['fallback'] == 1 and stats['requests'] == 187
            and stats['tokens'] == 1782477 and stats['usage_known'], 'IMPORT_COMPLETE_USAGE_REQUIRED')
    return {'protocol_sha256': ORIGINAL_SHA, 'checkpoint_sha256': CHECKPOINT_SHA,
            'artifacts': checkpoint, 'first_repeat': first, 'stats': stats}


def equivalent_baseline(manifest, workspace, first):
    old_workspace = Path(first['workspace'])
    old_manifest = load(old_workspace / 'prepared.json')
    def normalized(m, w):
        require(m['case_sha256'] == sha((w / 'public-inputs.json').read_bytes()), 'INPUT_FINGERPRINT_CHANGED')
        value = json.loads(json.dumps(m).replace(str(w), '<WORKSPACE>'))
        # Path-dependent hash is independently checked above and normalized inputs below.
        value.pop('case_sha256')
        return value
    require(normalized(manifest, workspace) == normalized(old_manifest, old_workspace),
            'BASELINE_CONTRACT_NOT_EQUIVALENT')
    require(json.loads(json.dumps(load(workspace / 'public-inputs.json')).replace(str(workspace), '<WORKSPACE>')) ==
            json.loads(json.dumps(load(old_workspace / 'public-inputs.json')).replace(str(old_workspace), '<WORKSPACE>')),
            'BASELINE_INPUT_NOT_EQUIVALENT')


def prepare_only():
    require(not CONTROL.exists(), 'PROTOCOL_ALREADY_FROZEN')
    bundle_manifest()
    legacy = verify_original()
    require(not any((OUT / job_name(v, r)).exists() for v, r in new_scope()), 'FREEZE_AFTER_JOB_REFUSED')
    files, installed = controls(), runtime()
    workroot = OUT / 'public60b-workspaces'
    workroot.mkdir(mode=0o700)  # Exclusive new generation, never reuse partial preparation.
    jobs = []
    for variant, repeat in new_scope():
        workspace = Path(tempfile.mkdtemp(prefix=f'{variant}-r{repeat}-', dir=workroot))
        frozen_files = copy_workspace(workspace, variant)
        m = export(workspace, capture=(variant, repeat) in (('v5', 2), ('v16', 1)))
        audit(m, variant, workspace)
        if variant == 'v5':
            equivalent_baseline(m, workspace, legacy['first_repeat'])
        if (variant, repeat) in (('v5', 2), ('v16', 1)):
            frozen_files['payload-audit.json'] = sha((workspace / 'payload-audit.json').read_bytes())
        frozen_files['prepared.json'] = sha((workspace / 'prepared.json').read_bytes())
        jobs.append({'name': job_name(variant, repeat), 'variant': variant, 'repeat': repeat,
                     'workspace': str(workspace), 'files': frozen_files,
                     'manifest_sha256': sha(encode(m)), 'request_limit': CAP, 'token_budget': BUDGET})
    require(files == controls() and installed == runtime() and legacy == verify_original(),
            'PREPARATION_CONTROL_CHANGED')
    first = load(ORIGINAL_CONTROL)['jobs'][0]
    imported = {**first, 'imported': True}
    exclusive(CONTROL, {'version': 'public60-continue-v16-1', 'selection': SELECTION,
                        'completion': COMPLETION, 'bundle_manifest': MANIFEST,
                        'files': files, 'runtime': installed, 'jobs': [imported] + jobs,
                        'original': legacy, 'phase_namespace': 'public60b',
                        'approval': 'owner: retain completed v5 r1; collect remaining four v5 and five v16 despite decoder fallback; no transport retry',
                        'batch_seconds': BATCH_SECONDS, 'byte_cap': BYTE_CAP,
                        'byte_guard': 'encoded UTF8 bytes, not native token measurement',
                        'case_cap_seconds': 300, 'batch_soft_overrun_seconds': 300, 'no_retry': True,
                        'target': 'public_Q_gain_v5', 'minimum_gain': .02,
                        'noise_formula': '2*sqrt(2)*SD(Q_v5)/sqrt(5)',
                        'bootstrap_seed': 20261016, 'bootstrap_samples': 20000})
    verify()
    print('PUBLIC60 continuation manifests=9 cases=540 imported_complete=60 remote_calls=0 credential_reads=0 protocol_sha256=' + sha(CONTROL.read_bytes()))


def job_name(variant, repeat):
    require(variant in VARIANTS and type(repeat) is int and repeat in range(1, 6), 'JOB_ID_REFUSED')
    return 'public60-v5-r1' if variant == 'v5' and repeat == 1 else f'public60b-{variant}-r{repeat}'


def verify():
    bundle_manifest()
    c = load(CONTROL)
    require(c['version'] == 'public60-continue-v16-1' and c['files'] == controls()
            and c['runtime'] == runtime() and c['original'] == verify_original(), 'FROZEN_CONTROL_CHANGED')
    require([j['name'] for j in c['jobs']] == [job_name(v, r) for v in VARIANTS for r in range(1, 6)],
            'EXCLUSIVE_JOB_SCOPE_CHANGED')
    for j in c['jobs']:
        w = Path(j['workspace'])
        workspace_inventory(w, j['files'])
        for name, digest in j['files'].items():
            require(sha(safe_relative(w, name).read_bytes()) == digest, 'WORKSPACE_CHANGED')
        m = load(w / 'prepared.json')
        require(sha(encode(m)) == j['manifest_sha256'], 'MANIFEST_CHANGED')
        audit(m, j['variant'], w)
        if j['variant'] == 'v5':
            equivalent_baseline(m, w, c['original']['first_repeat'])
    return c


def phase_path(variant):
    return OUT / f'public60b-{variant}-phase.json'


def phase_complete(variant):
    require(not (OUT / f'public60b-{variant}-STOP.json').exists(), 'PHASE_STOP_FATAL')
    p = load(phase_path(variant))
    require(p == load(OUT / f'public60b-{variant}-analysis.json'), 'PHASE_ANALYSIS_CHANGED')
    require(p.get('status') == 'completed' and p.get('protocol_sha256') == sha(CONTROL.read_bytes()),
            'PHASE_NOT_COMPLETE')
    for name, digest in p['artifacts'].items():
        require(sha(safe_relative(ROOT, name).read_bytes()) == digest, 'PHASE_ARTIFACT_CHANGED')
    require(len(p['results']) == 5 and p['results'] ==
            [official_result(OUT / job_name(variant, r)) for r in range(1, 6)],
            'PHASE_RESULTS_CHANGED')
    require(p['accepted_total'] == sum(r['valid'] for r in p['results'])
            and p['fallback_total'] == sum(r['fallback'] for r in p['results']), 'PHASE_COUNTS_CHANGED')
    return p


def quality(baseline, candidate=None):
    require(len(baseline) == 5, 'FIVE_ACTUAL_BASELINES_REQUIRED')
    for r in baseline + (candidate or []):
        require(r['valid'] + r['fallback'] == 60 and r['usage_known'], 'VALIDITY_OR_USAGE_FAILURE')
    q = statistics.mean(r['Q'] for r in baseline)
    sd = statistics.stdev(r['Q'] for r in baseline)
    noise = 2 * math.sqrt(2) * sd / math.sqrt(5)
    result = {'baseline_Q': q, 'baseline_SD': sd, 'noise': noise, 'gain': 0.0}
    if candidate is not None:
        require(len(candidate) == 5, 'FIVE_ACTUAL_CANDIDATES_REQUIRED')
        require(all(r['valid'] == 60 and r['fallback'] == 0 for r in candidate), 'CANDIDATE_FALLBACK_FAILED')
        gain = statistics.mean(r['Q'] for r in candidate) - q
        require(gain >= .02 and gain > noise, 'CANDIDATE_GAIN_FAILED')
        require(all(r['F1A'] >= .60 and r['F1B'] >= .75 for r in candidate), 'CANDIDATE_F1_FAILED')
        require(statistics.mean(r['HitA'] for r in candidate) >= statistics.mean(r['HitA'] for r in baseline),
                'CANDIDATE_EVIDENCE_FAILED')
        result.update(gain=gain, strict_supplement=gain >= noise + .02)
    return result


def completed_result(job, bind=True):
    require(job.is_dir() and not any(p.is_symlink() for p in [job, *job.parents])
            and not any(p.is_symlink() for p in job.rglob('*')), 'SYMLINK_REFUSED')
    runner = module(ROOT / RUNNER, 'public60_verify_runner')
    require(not any((job / fence).exists() for fence in FENCES), 'STOP_OR_ORPHAN_FATAL')
    m = load(job / 'manifest.json')
    if bind and CONTROL.exists():
        matches = [j for j in load(CONTROL)['jobs'] if j['name'] == job.name]
        require(len(matches) == 1 and sha(encode(m)) == matches[0]['manifest_sha256'],
                'JOB_MANIFEST_CHANGED')
    ledger = runner.Ledger(job, m, lambda model: (_ for _ in ()).throw(ValueError('OFFLINE_ONLY')))
    model = runner.MODELS[1]
    require(len(ledger.state['cases']) == 60, 'INCOMPLETE_JOB')
    records = [ledger.records[runner.legacy.result_name(model, i).replace('.json', '-case.json')] for i in range(60)]
    require(all(type(r['output_valid']) is bool and r['error'] == (None if r['output_valid'] else 'NO_ACCEPTED_SUBMIT') for r in records), 'INVALID_DECODER_RECORD')
    canonical = rows(job / '70b-canonical.jsonl')
    require(all(r['model'] == model and r['case_index'] == i
                and r['case_id'] == m['frozen'][i]['case']['id'] for i, r in enumerate(records)),
            'CASE_RECORD_CHANGED')
    require(canonical == [r['prediction'] for r in records], 'CANONICAL_CHANGED')
    require(len(canonical) == 60 and len({r['id'] for r in canonical}) == 60, 'CANONICAL60_REQUIRED')
    for prediction, item in zip(canonical, m['frozen']):
        runner.submission.validate(prediction, item['case'], item['pages'])
    require(ledger.state['requests'] <= CAP and ledger.state['tokens'] <= BUDGET, 'BUDGET_CHANGED')
    attempts = [ledger.records[n] for n in ledger.state['attempts']]
    require(all(r['role'] in ('parent', 'child')
                and r['model'] == model
                and r['request_model'] == runner.fixed_role_model(m['strategy'], model, r['role'])
                and type(r['case_index']) is int and 0 <= r['case_index'] < 60
                and r['source_sha256'] == m['frozen'][r['case_index']]['messages_sha256']
                and r['assembler_schema_sha256'] == m['frozen'][r['case_index']]['schema_sha256']
                and r['usage_known'] and r['safe'] and r['usage_valid'] and r['server_model_matches']
                and not r['has_api_error'] and runner.valid_usage_details(r['usage'])
                for r in attempts), 'UNSAFE_REQUEST_USAGE')
    require([r['id'] for r in canonical] == [i['case']['id'] for i in m['frozen']], 'CANONICAL_IDS_CHANGED')
    require(load(job / 'summary.json')['status'] == 'completed', 'SUMMARY_INCOMPLETE')
    return {'input_tokens': sum(r['usage']['prompt_tokens'] for r in attempts),
            'output_tokens': sum(r['usage']['completion_tokens'] for r in attempts),
            'parent_calls': sum(r['role'] == 'parent' for r in attempts),
            'child_calls': sum(r['role'] == 'child' for r in attempts),
            'api_wait_ms': sum(r['api_wait_ms'] for r in attempts),
            'valid': sum(r['output_valid'] for r in records),
            'fallback': sum(not r['output_valid'] for r in records), 'usage_known': True,
            'requests': ledger.state['requests'], 'tokens': ledger.state['tokens'],
            'case_wall_ms': sum(r['case_wall_ms'] for r in records),
            'repairs': sum('repair' in d.lower() for r in records for d in r['diagnostics'])}


def grade_job(job):
    stats = completed_result(job)
    report = OUT / (job.name + '-official.json')
    require(not report.exists(), 'GRADER_REPLAY_REFUSED')
    # Reserve an exclusive output name; unchanged grader writes only this owned file.
    exclusive(report, {'status': 'grading'})
    command = [SCORER_PYTHON, '-B', str(ROOT / 'evals/c-system-prompt/grader.py'),
               '--official-repo', str(OFFICIAL), '--python', SCORER_PYTHON,
               '--predictions', str(job / '70b-canonical.jsonl'), '--expected', str(BUNDLE / 'expected.jsonl'),
               '--cases', str(BUNDLE / 'cases.jsonl'), '--output', str(report)]
    result = subprocess.run(command, capture_output=True)
    require(result.returncode == 0, 'OFFICIAL_GRADING_FAILED')
    return official_result(job, stats)


def official_result(job, stats=None):
    stats = completed_result(job) if stats is None else stats
    g = load(OUT / (job.name + '-official.json'))
    a, b = (g['official_report']['tasks'][t]['macro_f1'] for t in ('A', 'B'))
    q = (.30 * a + .28 * b) / .58
    require(q == g['classification_objective']['value'], 'OFFICIAL_Q_CHANGED')
    return {**stats, 'Q': q, 'F1A': a, 'F1B': b,
            'HitA': g['primary_evidence_objective']['value']}


def check_binding(context, variant):
    require(context.get('mode') == ('public_continue_baseline' if variant == 'v5' else 'public_continue_candidate')
            and context.get('candidate') == ('' if variant == 'v5' else 'v16')
            and context.get('phase') == variant
            and context.get('protocol_sha256') == sha(CONTROL.read_bytes()), 'PUBLIC_CONTEXT_BINDING_FAILED')


def check():
    verify()
    context = load(ROOT / '.auto/check-context.json')
    variant = context.get('phase')
    require(variant in VARIANTS, 'PUBLIC_CONTEXT_PHASE_REQUIRED')
    check_binding(context, variant)
    b = phase_complete('v5')['results']
    for r in range(1, 6):
        completed_result(OUT / job_name('v5', r))
    if variant == 'v16':
        c = phase_complete('v16')['results']
        for r in range(1, 6):
            completed_result(OUT / job_name('v16', r))
        quality(b, c)
    else:
        quality(b)
    print('PUBLIC60 offline checks passed')


def execute(variant, approved_at):
    c = verify()
    require(approved_at is not None and 0 <= time.time() - approved_at < 180,
            'CURRENT_BOUNDED_OPERATOR_APPROVAL_REQUIRED')
    if variant == 'v16':
        quality(phase_complete('v5')['results'])
        for repeat in range(1, 6):
            completed_result(OUT / job_name('v5', repeat))
    require(not phase_path(variant).exists()
            and not (OUT / f'public60b-{variant}-STOP.json').exists(), 'PHASE_REPLAY_FATAL')
    jobs = [j for j in c['jobs'] if j['variant'] == variant and not j.get('imported')]
    all_jobs = [j for j in c['jobs'] if j['variant'] == variant]
    require(all(not (OUT / j['name']).exists() for j in jobs), 'JOB_REPLAY_FATAL')
    started = time.monotonic()
    deadline = time.time() + BATCH_SECONDS
    exclusive(phase_path(variant), {'status': 'running', 'protocol_sha256': sha(CONTROL.read_bytes())})
    try:
        for j in jobs:
            require(time.monotonic() - started < BATCH_SECONDS, 'BATCH_DEADLINE_STOP')
            w = Path(j['workspace'])
            command = [PYTHON, '-B', '.auto/public_validation_continue.py', '--run-workspace',
                       '--job', str(OUT / j['name']), '--deadline', str(deadline),
                       '--manifest-sha256', j['manifest_sha256']]
            result = subprocess.run(command, cwd=w, env=environment(w), capture_output=True)
            require(result.returncode == 0, 'WORKSPACE_RUN_STOP_NO_RETRY')
            completed_result(OUT / j['name'])
        # No prefix grading or aggregation: all five must first pass ledger checks.
        for j in all_jobs:
            completed_result(OUT / j['name'])
        results = [grade_job(OUT / j['name']) for j in all_jobs]
        baseline = results if variant == 'v5' else phase_complete('v5')['results']
        analysis = quality(baseline)  # Candidate acceptance belongs to --check.
        if variant == 'v16':
            analysis['gain'] = statistics.mean(r['Q'] for r in results) - analysis['baseline_Q']
        artifacts = []
        for j in all_jobs:
            job = OUT / j['name']
            artifacts += [f for f in job.iterdir() if f.is_file() and f.name != 'lock']
            artifacts.append(OUT / (job.name + '-official.json'))
        phase = {'status': 'completed', 'protocol_sha256': sha(CONTROL.read_bytes()),
                 'results': results, 'analysis': analysis,
                 'accepted_total': sum(r['valid'] for r in results),
                 'fallback_total': sum(r['fallback'] for r in results),
                 'prior_repeat_case_wall_seconds': (results[0]['case_wall_ms'] / 1000 if variant == 'v5' else 0),
                 'wall_seconds': time.monotonic() - started,
                 'artifacts': fingerprint(artifacts, ROOT)}
        exclusive(OUT / f'public60b-{variant}-analysis.json', phase)
        # Replace only this invocation's reserved running marker, never a completed phase.
        phase_path(variant).write_bytes(encode(phase))
        context = {'mode': 'public_continue_baseline' if variant == 'v5' else 'public_continue_candidate',
                   'candidate': '' if variant == 'v5' else 'v16', 'phase': variant,
                   'protocol_sha256': sha(CONTROL.read_bytes())}
        (ROOT / '.auto/check-context.json').write_bytes(encode(context))
        print_metrics(results, analysis, phase['wall_seconds'])
    except BaseException:
        exclusive(OUT / f'public60b-{variant}-STOP.json',
                  {'status': 'STOP', 'quality': 'unknown', 'failed_request_usage': 'unknown',
                   'no_retry': True, 'protocol_sha256': sha(CONTROL.read_bytes())})
        raise


def print_metrics(results, analysis, wall):
    require(len(results) == 5, 'FIVE_ACTUAL_RESULTS_REQUIRED')
    values = {'public_Q_gain_v5': analysis['gain'], 'public_baseline_Q': analysis['baseline_Q'],
              'public_noise': analysis['noise'], 'public_wall_seconds': wall,
              'public_new_command_wall_seconds': wall,
              'public_all_repeat_case_wall_seconds': sum(r['case_wall_ms'] for r in results) / 1000}
    for key in ('Q', 'F1A', 'F1B', 'HitA'):
        values['public_mean_' + key] = statistics.mean(r[key] for r in results)
    for key in ('valid', 'fallback', 'requests', 'tokens', 'input_tokens', 'output_tokens',
                'parent_calls', 'child_calls', 'case_wall_ms', 'api_wait_ms'):
        values['public_total_' + key] = sum(r[key] for r in results)
    values['public_usage_known'] = int(all(r['usage_known'] for r in results))
    values['public_total_accepted'] = values['public_total_valid']
    for repeat, r in enumerate(results, 1):
        values[f'public_r{repeat}_accepted'] = r['valid']
        values[f'public_r{repeat}_fallback'] = r['fallback']
    for key, value in values.items():
        print(f'METRIC {key}={value}')


def guarded_transport(runner, deadline, base=None):
    base = base or runner.Transport
    class Guarded(base):
        def request(self, method, path, payload):
            if time.monotonic() >= deadline:
                raise runner.Stop('BATCH_DEADLINE_STOP')
            if len(runner.legacy.encode(payload)) > BYTE_CAP:
                raise runner.Stop('PAYLOAD_BYTE_LIMIT')
            return super().request(method, path, payload)
    return Guarded


def run_workspace(job, deadline_epoch, manifest_sha256):
    workspace = ROOT
    require(job.is_absolute() and job.name in [job_name(v, r) for v, r in new_scope()]
            and job.parent.resolve() == Path(__file__).resolve().parents[2].parent
            and not job.is_symlink(), 'JOB_SCOPE_REFUSED')
    control_path = job.parent / CONTROL.name
    control = load(control_path)
    variant = job.name.split('-')[1]
    phase = load(job.parent / f'public60b-{variant}-phase.json')
    require(control['version'] == 'public60-continue-v16-1' and control['byte_cap'] == BYTE_CAP
            and phase['status'] == 'running'
            and phase['protocol_sha256'] == sha(control_path.read_bytes())
            and not (job.parent / f'public60b-{variant}-STOP.json').exists(),
            'ACTIVE_PHASE_REQUIRED')
    matches = [j for j in control['jobs'] if j['name'] == job.name]
    require(len(matches) == 1 and Path(matches[0]['workspace']) == workspace
            and matches[0]['manifest_sha256'] == manifest_sha256, 'WORKSPACE_BINDING_FAILED')
    workspace_inventory(workspace, matches[0]['files'])
    for name, digest in matches[0]['files'].items():
        require(sha(safe_relative(workspace, name).read_bytes()) == digest, 'WORKSPACE_CHANGED')
    m = load(workspace / 'prepared.json')
    require(sha(encode(m)) == manifest_sha256, 'MANIFEST_CHANGED')
    for name, digest in m['sources'].items():
        source = Path(name) if Path(name).is_absolute() else workspace / name
        require(source.resolve().is_relative_to(workspace.resolve())
                and not source.is_symlink() and sha(source.read_bytes()) == digest,
                'WORKSPACE_SOURCE_CHANGED')
    require(time.time() < deadline_epoch, 'BATCH_DEADLINE_STOP')
    deadline = time.monotonic() + deadline_epoch - time.time()
    runner = module(workspace / RUNNER, 'public60_live_runner')
    runner.legacy.c.protect()
    job.mkdir(mode=0o700)  # Exclusive identity; never resume.
    with os.fdopen(os.open(job / 'lock', os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        runner.initialize(job, m)
        transport = guarded_transport(runner, deadline)
        clients = {}
        def client(model):
            if model not in clients:
                clients[model] = transport(model)
            return clients[model]
        runner.run(job, m, client)


def capture_sdk(runner, manifest, workspace):
    # Actual pinned SDK bridge, fictional submissions only. No Transport selected.
    maximum = 0
    calls = 0
    roles = set()
    for item in manifest['frozen']:
        seen = []
        def post(role, number, payload):
            nonlocal maximum, calls
            size = len(runner.legacy.encode(payload))
            require(size <= BYTE_CAP, 'SDK_PAYLOAD_BYTE_LIMIT')
            runner.enforce_tools(payload, item['candidate_ids'], role)
            maximum = max(maximum, size)
            calls += 1
            roles.add(role)
            seen.append(role)
            name = payload['tool_choice']['function']['name']
            args = {'mode': 'source_only'} if name == 'subagent' else {'label': 1, 'candidate_ids': []}
            return {'id': 'offline', 'model': payload['model'],
                    'choices': [{'finish_reason': 'tool_calls', 'message': {
                        'role': 'assistant', 'content': None, 'tool_calls': [{
                            'id': 'offline-' + role + str(number), 'type': 'function',
                            'function': {'name': name, 'arguments': json.dumps(args)}}]}}],
                    'usage': {'prompt_tokens': 80, 'completion_tokens': 20, 'total_tokens': 100}}
        args, diagnostics, sdk = runner.run_b(item, runner.MODELS[1], post,
                                             strategy='C', isolation_guard=True)
        require(args == {'label': 1, 'candidate_ids': []}
                and seen == ['parent', 'child', 'parent'], 'SDK_OFFLINE_ROUTE_CHANGED')
    exclusive(workspace / 'payload-audit.json', {
        'cases': 60, 'calls': calls, 'roles': sorted(roles), 'max_payload_bytes': maximum,
        'max_context_bytes': max(len(runner.legacy.encode(i['messages'])) for i in manifest['frozen']),
        'byte_cap': BYTE_CAP, 'native_tokens_counted': False, 'remote_calls': 0,
        'credential_reads': 0})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    for flag in ('prepare-only', 'baseline-continue', 'candidate', 'check', 'export-workspace', 'run-workspace'):
        group.add_argument('--' + flag, action='store_true')
    parser.add_argument('--capture-sdk', action='store_true')
    parser.add_argument('--approved-at', type=float)
    parser.add_argument('--job', type=Path)
    parser.add_argument('--deadline', type=float)
    parser.add_argument('--manifest-sha256')
    args = parser.parse_args()
    if args.run_workspace:
        run_workspace(args.job, args.deadline, args.manifest_sha256)
    elif args.export_workspace:
        workspace = ROOT
        runner, m = isolated_prepare(workspace)
        exclusive(workspace / 'prepared.json', m)
        if args.capture_sdk:
            capture_sdk(runner, m, workspace)
    elif args.prepare_only:
        prepare_only()
    elif args.check:
        check()
    else:
        execute('v5' if args.baseline_continue else 'v16', args.approved_at)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Never display underlying SDK, HTTP, raw input or grader exception text.
        reason = str(exc) if type(exc) is ValueError and str(exc).replace('_', '').isalnum() else 'OFFLINE_OR_CONTROL_FAILURE'
        print('STOP: ' + reason, file=sys.stderr)
        sys.exit(1)
