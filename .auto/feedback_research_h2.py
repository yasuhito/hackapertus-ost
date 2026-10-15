#!/usr/bin/env python3
"""Exclusive owner-approved H2 conditional research on exposed PUBLIC60 development.

Derived core ledger/workspace/SDK logic from public_validation_continue.py.
Historical files are read-only; no old verification is run against modified root.
Preparation and checks never select a transport.
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
CONTROL = OUT / 'public60-feedback-h2-protocol.json'
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
VARIANTS = ('v5',)
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
    # Match original source-only inventory exactly; newly added fictional tests
    # are pinned as controls, not added to model workspaces.
    c = load(HISTORICAL)
    require(sha(HISTORICAL.read_bytes()) == HISTORICAL_SHA, 'HISTORICAL_PROTOCOL_CHANGED')
    first = c['jobs'][0]
    return sorted(ROOT / name for name in first['files'] if name.startswith('track_2a/'))


def fingerprint(paths, base=None):
    result = {}
    for path in sorted(set(paths)):
        require(path.is_file() and not path.is_symlink(), 'NONREGULAR_SOURCE')
        result[str(path.relative_to(base)) if base else str(path)] = sha(path.read_bytes())
    return result




def controls():
    paths = source_files() + [ROOT / p for p in (
        '.auto/public_validation_continue.py', '.auto/feedback_research.py', '.auto/test_feedback_research.py',
        'track_2a/dev/format/test_h2_schema.py',
        '.auto/feedback_research_h2.py', '.auto/test_feedback_research_h2.py', '.auto/checks.sh',
        '.auto/measure.sh',
        '.auto/train_route.py', '.auto/run_candidate.py', 'evals/c-system-prompt/grader.py',
        'evals/c-system-prompt/prompts/v5-system.txt',
        'track_2a/dev/format/test_feedback.py', '.auto/test_format_failure_repro.py')]
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
    for path in source_files():
        target = workspace / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    # These helpers are controls only, never imported historical validation.
    for relative in ('.auto/feedback_research_h2.py', '.auto/train_route.py', '.auto/run_candidate.py'):
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
    command = [PYTHON, '-B', '.auto/feedback_research_h2.py', '--export-workspace']
    if capture:
        command.append('--capture-sdk')
    result = subprocess.run(command, cwd=workspace, env=environment(workspace), capture_output=True)
    require(result.returncode == 0, 'OFFLINE_WORKSPACE_PREPARATION_FAILED')
    return load(workspace / 'prepared.json')


def audit(m, variant, workspace):
    import run_candidate as old
    prepared = rows(BUNDLE / 'prepared-contexts.jsonl')
    audits = rows(BUNDLE / 'context-audit.jsonl')
    cases = rows(BUNDLE / 'cases.jsonl')
    schema_runner = module(workspace / RUNNER, 'public60_schema_runner')
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
        system = old.system((ROOT / 'track_2a/src/predict.py').read_text())
        require(sha(system.encode()) == V5, 'SYSTEM_HASH_CHANGED')
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
    return [('v5', r) for r in range(1, 6)]


def workspace_inventory(workspace, files):
    require(not any(p.is_symlink() for p in [workspace, *workspace.parents])
            and not any(p.is_symlink() for p in workspace.rglob('*')), 'SYMLINK_REFUSED')
    require({str(p.relative_to(workspace)) for p in workspace.rglob('*') if p.is_file()} == set(files),
            'UNFROZEN_WORKSPACE_FILE')








def job_name(variant, repeat):
    require(variant in VARIANTS and type(repeat) is int and repeat in range(1, 6), 'JOB_ID_REFUSED')
    return f'public60-feedback-h2-r{repeat}'




def phase_path(variant):
    return OUT / 'public60-feedback-h2-phase.json'






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
    stats = completed_result(job, bind=job.name.startswith('public60-feedback-')) if stats is None else stats
    g = load(OUT / (job.name + '-official.json'))
    a, b = (g['official_report']['tasks'][t]['macro_f1'] for t in ('A', 'B'))
    q = (.30 * a + .28 * b) / .58
    require(q == g['classification_objective']['value'], 'OFFICIAL_Q_CHANGED')
    return {**stats, 'Q': q, 'F1A': a, 'F1B': b,
            'HitA': g['primary_evidence_objective']['value']}










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
    variant = 'v5'
    phase = load(job.parent / 'public60-feedback-h2-phase.json')
    require(control['version'] == 'feedback-h2-1' and control['byte_cap'] == BYTE_CAP
            and phase['status'] == 'running'
            and phase['protocol_sha256'] == sha(control_path.read_bytes())
            and not (job.parent / 'public60-feedback-h2-STOP.json').exists(),
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





HISTORICAL = OUT / 'public60-continue-v16-protocol.json'
HISTORICAL_SHA = '944b3f98519bb6e5592317f86a623cc824fa8a69cfce28befbf4da0f77b8f7e2'
REFERENCE = OUT / 'public60-feedback-h2-reference.json'
REFERENCE_PHASE = OUT / 'public60b-v5-phase.json'
REFERENCE_ANALYSIS = OUT / 'public60b-v5-analysis.json'
Q_REF = .8051187036988255
NOISE_REF = .0021732024568427814
# Exact owner-approved engineering change, never a wildcard permission.
FIX_SHA = '01dff6b930a546dbe1b0f8651cebe0cec5f4d3987eeecf2bb9309b4ecea799b6'


WIRE_SDK = 'track_2a/dev/format/sdk.ts'
H1_CONTROL = OUT / 'public60-feedback-protocol.json'
H1_CONTROL_SHA = '9afd74206ae8e035142f20b9c22ef2dd87f8fcf527d406f4b29b61f0ce7b4335'
H1_REFERENCE = OUT / 'public60-feedback-reference.json'
H1_REFERENCE_SHA = 'fd9c8f9f5cb20da164488fb019772b421f94c343e1f3f2dad7744c41809c2a8c'
PY_INSERT = " 'anyOf': [{'properties': {'label': {'enum': [1]}}}, {'properties': {'candidate_ids': {'minItems': 1}}}],"
TS_INSERT = "      anyOf: [{ properties: { label: { enum: [1] } } }, { properties: { candidate_ids: { minItems: 1 } } }],\n"


def wire_source_binding():
    require(sha(H1_CONTROL.read_bytes()) == H1_CONTROL_SHA
            and sha(H1_REFERENCE.read_bytes()) == H1_REFERENCE_SHA, 'H1_BINDING_CHANGED')
    h1 = load(H1_CONTROL)
    require(load(H1_REFERENCE)['reference']['historical_protocol_sha256'] == HISTORICAL_SHA,
            'H1_NOT_ORIGINAL_REFERENCE')
    for name in (RUNNER, WIRE_SDK):
        original = safe_relative(Path(h1['jobs'][0]['workspace']), name).read_bytes()
        require(sha(original) == h1['files'][name], 'H1_SOURCE_CHANGED')
        current = (ROOT / name).read_bytes()
        insertion = (PY_INSERT if name == RUNNER else TS_INSERT).encode()
        require(current.count(insertion) == 1 and current.replace(insertion, b'', 1) == original,
                'NON_WIRE_CHANGE_REFUSED')


def runtime():
    """Verify every previously frozen runtime byte, without invoking git."""
    require(sha(HISTORICAL.read_bytes()) == HISTORICAL_SHA, 'HISTORICAL_PROTOCOL_CHANGED')
    pinned = load(HISTORICAL)['runtime']
    require(load(SDK / 'package.json')['version'] == '1.1.0'
            and load(CHILD / 'package.json')['version'] == '0.19.0', 'PINNED_RUNTIME_REQUIRED')
    require(fingerprint([Path(p) for p in pinned]) == pinned, 'RUNTIME_CHANGED')
    return pinned


def reference_binding():
    require(sha(HISTORICAL.read_bytes()) == HISTORICAL_SHA, 'HISTORICAL_PROTOCOL_CHANGED')
    c = load(HISTORICAL)
    require(c['runtime'] == runtime(), 'REFERENCE_RUNTIME_CHANGED')
    # Root dispatcher changes are legitimate; archived historical controls remain pinned.
    for name, digest in c['files'].items():
        if name not in (RUNNER, WIRE_SDK, '.auto/measure.sh', '.auto/checks.sh'):
            require(sha(safe_relative(ROOT, name).read_bytes()) == digest, 'UNCHANGED_SOURCE_CHANGED')
    wire_source_binding()
    require(sha(ORIGINAL_CONTROL.read_bytes()) == ORIGINAL_SHA
            and sha(CHECKPOINT.read_bytes()) == CHECKPOINT_SHA, 'ORIGINAL_BINDING_CHANGED')
    checkpoint = load(CHECKPOINT)
    for name, digest in checkpoint.items():
        require(sha(safe_relative(ROOT, name).read_bytes()) == digest, 'ORIGINAL_ARTIFACT_CHANGED')
    phase = load(REFERENCE_PHASE)
    require(phase == load(REFERENCE_ANALYSIS) and phase['status'] == 'completed'
            and phase['protocol_sha256'] == HISTORICAL_SHA, 'REFERENCE_PHASE_CHANGED')
    for name, digest in phase['artifacts'].items():
        require(sha(safe_relative(ROOT, name).read_bytes()) == digest, 'REFERENCE_ARTIFACT_CHANGED')
    jobs = [j for j in c['jobs'] if j['variant'] == 'v5']
    require([j['name'] for j in jobs] == ['public60-v5-r1'] +
            [f'public60b-v5-r{r}' for r in range(2, 6)], 'REFERENCE_SCOPE_CHANGED')
    results = []
    for j in jobs:
        w = Path(j['workspace'])
        workspace_inventory(w, j['files'])
        for name, digest in j['files'].items():
            require(sha(safe_relative(w, name).read_bytes()) == digest, 'REFERENCE_WORKSPACE_CHANGED')
        # Archived original source must match the old source control, not new root.
        for name, digest in c['files'].items():
            if name in j['files'] and name.startswith('track_2a/'):
                require(j['files'][name] == digest, 'REFERENCE_SOURCE_CHANGED')
        m = load(w / 'prepared.json')
        require(sha(encode(m)) == j['manifest_sha256'] ==
                sha(encode(load(OUT / j['name'] / 'manifest.json'))), 'REFERENCE_MANIFEST_CHANGED')
        audit(m, 'v5', w)
        results.append(official_result(OUT / j['name']))
    require(results == phase['results'], 'REFERENCE_STATS_CHANGED')
    require(sum(r['fallback'] for r in results) == 7
            and sum(r['valid'] for r in results) == 293
            and sum(r['requests'] for r in results) == 941
            and sum(r['tokens'] for r in results) == 8950166, 'REFERENCE_KNOWN_TOTALS_CHANGED')
    q = statistics.mean(r['Q'] for r in results)
    noise = 2 * math.sqrt(2) * statistics.stdev(r['Q'] for r in results) / math.sqrt(5)
    require(q == Q_REF and noise == NOISE_REF
            and statistics.mean(r['F1A'] for r in results) == .7009478538890304
            and statistics.mean(r['F1B'] for r in results) == .9167303284950343
            and statistics.mean(r['HitA'] for r in results) == .30, 'REFERENCE_SECONDARIES_CHANGED')
    return {'results': results, 'jobs': jobs, 'historical_protocol_sha256': HISTORICAL_SHA,
            'phase_sha256': sha(REFERENCE_PHASE.read_bytes()),
            'analysis_sha256': sha(REFERENCE_ANALYSIS.read_bytes()),
            'original_checkpoint_sha256': CHECKPOINT_SHA,
            'artifacts': phase['artifacts']}


def equivalent_baseline(manifest, workspace, first):
    old_workspace = Path(first['workspace'])
    old_manifest = load(old_workspace / 'prepared.json')
    def normalized(m, w, historical):
        require(m['case_sha256'] == sha((w / 'public-inputs.json').read_bytes()), 'INPUT_FINGERPRINT_CHANGED')
        value = json.loads(json.dumps(m).replace(str(w), '<WORKSPACE>'))
        value.pop('case_sha256')
        sources = value['sources']
        matches = [p for p in sources if p.endswith(RUNNER)]
        require(len(matches) == 1, 'RUNNER_SOURCE_MISSING')
        key = matches[0]
        expected = load(HISTORICAL)['files'][RUNNER] if historical else sha((ROOT / RUNNER).read_bytes())
        require(sources[key] == expected, 'FEEDBACK_SOURCE_NOT_APPROVED')
        sources[key] = '<EXPLICIT_APPROVED_FEEDBACK_CHANGE>'
        sdk_keys = [p for p in sources if p.endswith(WIRE_SDK)]
        require(len(sdk_keys) == 1, 'SDK_SOURCE_MISSING')
        sdk_key = sdk_keys[0]
        expected_sdk = load(HISTORICAL)['files'][WIRE_SDK] if historical else sha((ROOT / WIRE_SDK).read_bytes())
        require(sources[sdk_key] == expected_sdk, 'WIRE_SDK_NOT_APPROVED')
        sources[sdk_key] = '<EXPLICIT_H2_WIRE_PROJECTION>'
        for frozen in value['frozen']:
            ids = frozen['candidate_ids']
            runner = module((old_workspace if historical else workspace) / RUNNER, 'equivalence_schema')
            require(frozen['schema_sha256'] == sha(encode(runner.schemas(ids))), 'SCHEMA_NOT_APPROVED')
            frozen['schema_sha256'] = '<EXPLICIT_H2_WIRE_CONDITION>'
        return value
    require(normalized(manifest, workspace, False) == normalized(old_manifest, old_workspace, True),
            'BASELINE_CONTRACT_NOT_EQUIVALENT')
    require(json.loads(json.dumps(load(workspace / 'public-inputs.json')).replace(str(workspace), '<WORKSPACE>')) ==
            json.loads(json.dumps(load(old_workspace / 'public-inputs.json')).replace(str(old_workspace), '<WORKSPACE>')),
            'BASELINE_INPUT_NOT_EQUIVALENT')


def prepare_only():
    require(not CONTROL.exists(), 'PROTOCOL_ALREADY_FROZEN')
    bundle_manifest()
    reference = reference_binding()
    require(not any((OUT / job_name(v, r)).exists() for v, r in new_scope()), 'FREEZE_AFTER_JOB_REFUSED')
    files, installed = controls(), runtime()
    workroot = OUT / 'public60-feedback-h2-workspaces'
    partial = list(workroot.iterdir()) if workroot.exists() else []
    require(not partial or (len(partial) == 1 and partial[0].name == 'h2-r1-n9gat6jx'),
            'UNEXPECTED_OFFLINE_PARTIAL')
    workroot.mkdir(mode=0o700, exist_ok=True)
    jobs = []
    for variant, repeat in new_scope():
        if repeat == 1 and partial:
            # No inference identity exists. Complete the original offline generation,
            # never rename, adopt a model prefix, or regenerate its SDK capture.
            workspace = partial[0]
            expected = {str(p.relative_to(ROOT)) for p in source_files()}
            expected.update(('.auto/feedback_research_h2.py', '.auto/train_route.py',
                             '.auto/run_candidate.py', 'public-inputs.json',
                             'prepared.json', 'payload-audit.json'))
            expected.update('booklets/' + Path(c['booklet']['path']).name
                            for c in rows(BUNDLE / 'cases.jsonl') if 'booklet' in c)
            frozen_files = fingerprint([p for p in workspace.rglob('*') if p.is_file()], workspace)
            require(set(frozen_files) == expected, 'OFFLINE_PARTIAL_INVENTORY_CHANGED')
            for name in expected:
                if name.startswith(('track_2a/', '.auto/')):
                    require(frozen_files[name] == sha((ROOT / name).read_bytes()),
                            'OFFLINE_PARTIAL_SOURCE_CHANGED')
            capture = load(workspace / 'payload-audit.json')
            require(capture['calls'] == 180 and capture['cases'] == 60
                    and capture['remote_calls'] == capture['credential_reads'] == 0
                    and capture['max_payload_bytes'] <= BYTE_CAP, 'OFFLINE_PARTIAL_CAPTURE_CHANGED')
            m = load(workspace / 'prepared.json')
        else:
            workspace = Path(tempfile.mkdtemp(prefix=f'h2-r{repeat}-', dir=workroot))
            frozen_files = copy_workspace(workspace, variant)
            m = export(workspace, capture=repeat == 1)
        audit(m, variant, workspace)
        equivalent_baseline(m, workspace, reference['jobs'][0])
        if repeat == 1:
            frozen_files['payload-audit.json'] = sha((workspace / 'payload-audit.json').read_bytes())
        frozen_files['prepared.json'] = sha((workspace / 'prepared.json').read_bytes())
        jobs.append({'name': job_name(variant, repeat), 'variant': variant, 'repeat': repeat,
                     'workspace': str(workspace), 'files': frozen_files,
                     'manifest_sha256': sha(encode(m)), 'request_limit': CAP, 'token_budget': BUDGET})
    require(files == controls() and installed == runtime() and reference == reference_binding(),
            'PREPARATION_CONTROL_CHANGED')
    exclusive(CONTROL, {'version': 'feedback-h2-1', 'files': files, 'runtime': installed,
                        'reference': reference, 'jobs': jobs, 'byte_cap': BYTE_CAP,
                        'batch_seconds': BATCH_SECONDS, 'case_cap_seconds': 300,
                        'selection': SELECTION, 'completion': COMPLETION, 'bundle_manifest': MANIFEST,
                        'no_retry': True, 'target': 'format_fallbacks', 'reference_fallbacks': 7,
                        'Q_floor': Q_REF - NOISE_REF, 'F1A_floor': .60, 'F1B_floor': .75,
                        'meanHitA_floor': .30, 'approved_feedback_sha256': FIX_SHA,
                        'h2_wire_sources': fingerprint([ROOT / RUNNER, ROOT / WIRE_SDK], ROOT),
                        'provider_conditional_support': 'UNCONFIRMED',
                        'h1_control_sha256': H1_CONTROL_SHA, 'h1_reference_sha256': H1_REFERENCE_SHA,
                        'system_sha256': V5, 'phase_namespace': 'public60-feedback-h2'})
    exclusive(REFERENCE, {'status': 'imported', 'protocol_sha256': sha(CONTROL.read_bytes()),
                          'reference': reference, 'historical': True, 'offline_historical_binding': True})
    verify()
    print('FEEDBACK_PREPARED manifests=5 cases=300 remote_calls=0 credential_reads=0 protocol_sha256=' + sha(CONTROL.read_bytes()))


def verify():
    bundle_manifest()
    c = load(CONTROL)
    require(c['version'] == 'feedback-h2-1' and c['files'] == controls()
            and c['runtime'] == runtime() and c['reference'] == reference_binding(), 'FROZEN_CONTROL_CHANGED')
    require([j['name'] for j in c['jobs']] == [job_name(v, r) for v, r in new_scope()], 'JOB_SCOPE_CHANGED')
    for j in c['jobs']:
        w = Path(j['workspace'])
        workspace_inventory(w, j['files'])
        for name, digest in j['files'].items():
            require(sha(safe_relative(w, name).read_bytes()) == digest, 'WORKSPACE_CHANGED')
        m = load(w / 'prepared.json')
        require(sha(encode(m)) == j['manifest_sha256'], 'MANIFEST_CHANGED')
        audit(m, 'v5', w)
        equivalent_baseline(m, w, c['reference']['jobs'][0])
    return c


def quality(results):
    require(len(results) == 5, 'FIVE_ACTUAL_CANDIDATES_REQUIRED')
    require(all(r['valid'] + r['fallback'] == 60 and r['usage_known'] for r in results), 'VALIDITY_OR_USAGE_FAILURE')
    require(all(r['F1A'] >= .60 and r['F1B'] >= .75 for r in results), 'CANDIDATE_F1_FAILED')
    require(statistics.mean(r['Q'] for r in results) >= Q_REF - NOISE_REF, 'CANDIDATE_Q_FAILED')
    require(statistics.mean(r['HitA'] for r in results) >= .30, 'CANDIDATE_EVIDENCE_FAILED')
    require(sum(r['fallback'] for r in results) < 7, 'PRIMARY_NOT_IMPROVED')


def phase_complete():
    require(not (OUT / 'public60-feedback-h2-STOP.json').exists(), 'PHASE_STOP_FATAL')
    p = load(phase_path('v5'))
    require(p == load(OUT / 'public60-feedback-h2-analysis.json')
            and p['status'] == 'completed' and p['protocol_sha256'] == sha(CONTROL.read_bytes()), 'PHASE_NOT_COMPLETE')
    for name, digest in p['artifacts'].items():
        require(sha(safe_relative(ROOT, name).read_bytes()) == digest, 'PHASE_ARTIFACT_CHANGED')
    require(p['results'] == [official_result(OUT / job_name('v5', r)) for r in range(1, 6)], 'PHASE_RESULTS_CHANGED')
    return p


def context(mode):
    return {'mode': 'feedback_h2_' + mode, 'candidate': '' if mode == 'reference' else 'h2',
            'round': 'feedback-h2', 'phase': mode, 'protocol_sha256': sha(CONTROL.read_bytes())}


def print_metrics(results, elapsed, historical):
    require(len(results) == 5, 'FIVE_ACTUAL_RESULTS_REQUIRED')
    q = statistics.mean(r['Q'] for r in results)
    values = {'format_fallbacks': sum(r['fallback'] for r in results), 'reference_Q': Q_REF,
              'reference_noise': NOISE_REF, 'Q_delta': q - Q_REF, 'historical_reference': int(historical),
              'Q_SD': statistics.stdev(r['Q'] for r in results),
              'Q_noise': 2 * math.sqrt(2) * statistics.stdev(r['Q'] for r in results) / math.sqrt(5),
              'usage_historical': int(historical), 'usage_known': int(all(r['usage_known'] for r in results)),
              'reference_import_seconds' if historical else 'candidate_command_wall_seconds': elapsed,
              'historical_total_case_wall_seconds' if historical else 'candidate_total_case_wall_seconds':
              sum(r['case_wall_ms'] for r in results) / 1000}
    values['reference_import_seconds'] = 8.121229351032525
    values['historical_total_case_wall_seconds'] = 2238.1406852069777
    for key in ('Q', 'F1A', 'F1B', 'HitA'):
        values['mean_' + key] = statistics.mean(r[key] for r in results)
    for key in ('valid', 'fallback', 'requests', 'tokens', 'input_tokens', 'output_tokens', 'parent_calls', 'child_calls', 'api_wait_ms'):
        values['total_' + key] = sum(r[key] for r in results)
    values['accepted'] = values['total_valid']
    for repeat, r in enumerate(results, 1):
        values[f'r{repeat}_fallbacks'] = r['fallback']
        values[f'r{repeat}_accepted'] = r['valid']
    for key, value in values.items():
        print(f'METRIC {key}={value}')


def fresh_approval(approved_at):
    require(approved_at is not None and 0 <= time.time() - approved_at < 180, 'CURRENT_BOUNDED_OPERATOR_APPROVAL_REQUIRED')


def import_reference(approved_at):
    started = time.monotonic()
    fresh_approval(approved_at)
    c = verify()
    exclusive(REFERENCE, {'status': 'imported', 'protocol_sha256': sha(CONTROL.read_bytes()),
                          'reference': c['reference'], 'historical': True,
                          'import_elapsed_seconds': time.monotonic() - started})
    (ROOT / '.auto/check-context.json').write_bytes(encode(context('reference')))
    print_metrics(c['reference']['results'], time.monotonic() - started, True)


def check_reference(c):
    marker = load(REFERENCE)
    require(marker['status'] == 'imported' and marker['historical'] is True
            and marker['protocol_sha256'] == sha(CONTROL.read_bytes())
            and marker['reference'] == c['reference'], 'REFERENCE_CHECKPOINT_CHANGED')


def check():
    c = verify()
    ctx = load(ROOT / '.auto/check-context.json')
    mode = ctx.get('phase')
    require(mode in ('reference', 'candidate') and ctx == context(mode), 'FEEDBACK_CONTEXT_BINDING_FAILED')
    check_reference(c)
    if mode == 'candidate':
        quality(phase_complete()['results'])
    print('FEEDBACK offline checks passed')


def execute(approved_at):
    started = time.monotonic()
    fresh_approval(approved_at)
    c = verify()
    check_reference(c)
    require(not phase_path('v5').exists() and not (OUT / 'public60-feedback-h2-STOP.json').exists(), 'PHASE_REPLAY_FATAL')
    require(all(not (OUT / j['name']).exists() for j in c['jobs']), 'JOB_REPLAY_FATAL')
    deadline = time.time() + BATCH_SECONDS
    exclusive(phase_path('v5'), {'status': 'running', 'protocol_sha256': sha(CONTROL.read_bytes())})
    try:
        for j in c['jobs']:
            require(time.time() < deadline, 'BATCH_DEADLINE_STOP')
            w = Path(j['workspace'])
            command = [PYTHON, '-B', '.auto/feedback_research_h2.py', '--run-workspace', '--job', str(OUT / j['name']),
                       '--deadline', str(deadline), '--manifest-sha256', j['manifest_sha256']]
            result = subprocess.run(command, cwd=w, env=environment(w), capture_output=True)
            require(result.returncode == 0, 'WORKSPACE_RUN_STOP_NO_RETRY')
            completed_result(OUT / j['name'])
        # Only after all 300 records are complete and known may grading begin.
        for j in c['jobs']:
            completed_result(OUT / j['name'])
        verify()
        results = [grade_job(OUT / j['name']) for j in c['jobs']]
        artifacts = []
        for j in c['jobs']:
            artifacts += [f for f in (OUT / j['name']).iterdir() if f.is_file() and f.name != 'lock']
            artifacts.append(OUT / (j['name'] + '-official.json'))
        phase = {'status': 'completed', 'protocol_sha256': sha(CONTROL.read_bytes()), 'results': results,
                 'wall_seconds': time.monotonic() - started, 'artifacts': fingerprint(artifacts, ROOT)}
        exclusive(OUT / 'public60-feedback-h2-analysis.json', phase)
        phase_path('v5').write_bytes(encode(phase))
        (ROOT / '.auto/check-context.json').write_bytes(encode(context('candidate')))
        print_metrics(results, phase['wall_seconds'], False)
    except BaseException:
        exclusive(OUT / 'public60-feedback-h2-STOP.json', {'status': 'STOP', 'quality': 'unavailable',
                  'primary': 'unavailable', 'failed_request_usage': 'unknown', 'no_retry': True,
                  'protocol_sha256': sha(CONTROL.read_bytes())})
        print('PRIMARY unavailable; quality unavailable; no measured zero', file=sys.stderr)
        raise


def main():
    parser = argparse.ArgumentParser(description='Exclusive fixed-feedback v5 research; PUBLIC60 is exposed development.')
    group = parser.add_mutually_exclusive_group(required=True)
    for flag in ('prepare-only', 'reference', 'candidate', 'check', 'export-workspace', 'run-workspace'):
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
        runner, m = isolated_prepare(ROOT)
        exclusive(ROOT / 'prepared.json', m)
        if args.capture_sdk:
            capture_sdk(runner, m, ROOT)
    elif args.prepare_only:
        prepare_only()
    elif args.check:
        check()
    elif args.reference:
        import_reference(args.approved_at)
    else:
        execute(args.approved_at)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        reason = str(exc) if type(exc) is ValueError and str(exc).replace('_', '').isalnum() else 'OFFLINE_OR_CONTROL_FAILURE'
        print('STOP: ' + reason, file=sys.stderr)
        sys.exit(1)
