"""Exclusive prospective two-arm controller. Preparation/export are credential-free."""
import hashlib
import json
import math
from pathlib import Path
import statistics

import role_review_contract as contract
from role_review_worker import VARIANT

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / 'output/validation/role-review-v1'
BASELINE = 'role-review-v1-baseline'
ARMS = ('baseline', 'candidate')
JOBS = tuple(f'role-review-v1-{arm}-r{repeat}' for arm in ARMS for repeat in range(1, 6))
CAPS = {'physical_posts': 300, 'charged_tokens': 78720000, 'reserve': 262400,
        'case_seconds': 300, 'request_seconds': 60, 'socket_seconds': 45,
        'input_bytes': 240000, 'output_tokens': 256, 'temperature': 0,
        'parent_completions': 3, 'child_completions': 2, 'reviewer_completions': 2,
        'schema_repairs': 1, 'arm_seconds': 5400, 'in_progress_allowance_seconds': 300}
EVALUATOR_COMMIT = '5e6957729b77a126006049305ad1ef241211a5b4'


def require(value, code):
    if not value:
        raise ValueError(code)


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def quality(f1a, f1b):
    require(all(type(v) in (float, int) and math.isfinite(v) and 0 <= v <= 1 for v in (f1a, f1b)), 'INVALID_F1')
    return (.30 * f1a + .28 * f1b) / .58


def baseline_integrity(repeats):
    """No candidate F1/gain guards on freshly measured baseline."""
    require(type(repeats) is list and len(repeats) == 5, 'INCOMPLETE_ARM_NO_GRADING')
    for repeat in repeats:
        require(repeat['canonical_count'] == 60 and repeat['complete'] is True, 'INCOMPLETE_ARM_NO_GRADING')
        require(all(repeat[k] is True for k in ('source_valid', 'model_valid', 'usage_known', 'ledger_valid')), 'ARM_INTEGRITY')
        quality(repeat['f1a'], repeat['f1b'])
        require(type(repeat['hita']) in (float, int) and math.isfinite(repeat['hita']) and 0 <= repeat['hita'] <= 1, 'INVALID_HITA')
        require(type(repeat['fallbacks']) is int and 0 <= repeat['fallbacks'] <= 60, 'INVALID_FALLBACK_COUNT')
    return True


def candidate_gates(baseline, candidate):
    baseline_integrity(baseline)
    baseline_integrity(candidate)
    bq = [quality(r['f1a'], r['f1b']) for r in baseline]
    cq = [quality(r['f1a'], r['f1b']) for r in candidate]
    gain = statistics.mean(cq) - statistics.mean(bq)
    noise = 2 * math.sqrt(2) * statistics.stdev(bq) / math.sqrt(5)
    available = sum(r['review_available'] for r in candidate)
    require(all(type(r['review_available']) is int and 0 <= r['review_available'] <= 60 for r in candidate), 'REVIEW_COUNTS')
    gates = {'gain_at_least_02': gain >= .02, 'gain_above_baseline_noise': gain > noise,
             'each_f1a_60': all(r['f1a'] >= .60 for r in candidate),
             'each_f1b_75': all(r['f1b'] >= .75 for r in candidate),
             'mean_hita_not_lower': statistics.mean(r['hita'] for r in candidate) >= statistics.mean(r['hita'] for r in baseline),
             'fallbacks_not_more': sum(r['fallbacks'] for r in candidate) <= sum(r['fallbacks'] for r in baseline),
             'review_availability_95': available / 300 >= .95}
    return {'research_keep': all(gates.values()), 'gates': gates, 'baseline_mean_Q': statistics.mean(bq),
            'candidate_mean_Q': statistics.mean(cq), 'gain': gain, 'baseline_noise': noise,
            'review_available': available, 'review_coverage': available / 300,
            'deployment_approved': False}


def prospective_bindings(bundle_binding, job_bindings):
    """Bind precise documented-exposure scope and all ten audited input-only jobs."""
    require(type(bundle_binding) is dict and bundle_binding.get('blinded_selection_frozen') is True
            and bundle_binding.get('provenance_scope') == 'outside_documented_local_real_llm_prompt_development'
            and bundle_binding.get('universal_unseen_claim') is False
            and type(bundle_binding.get('provenance_evidence_sha256')) is dict
            and bool(bundle_binding['provenance_evidence_sha256'])
            and all(type(name) is str and type(digest) is str and len(digest) == 64
                    and set(digest) <= set('0123456789abcdef')
                    for name, digest in bundle_binding['provenance_evidence_sha256'].items()), 'DATA_ADAPTER_NOT_READY')
    for key in ('selection_sha256', 'provenance_sha256', 'input_sha256', 'expected_sha256', 'case_order_sha256'):
        require(type(bundle_binding.get(key)) is str and len(bundle_binding[key]) == 64, 'BUNDLE_BINDING_MISSING')
    require(set(job_bindings) == set(JOBS), 'ALL_TEN_JOBS_REQUIRED')
    for name, binding in job_bindings.items():
        arm = 'candidate' if '-candidate-' in name else 'baseline'
        require(binding.get('variant') == (VARIANT if arm == 'candidate' else BASELINE), 'VARIANT_REFUSED')
        require(binding.get('canonical_cases') == 60 and binding.get('gold_free') is True, 'MODEL_WORKSPACE_NOT_BLINDED')
        require(binding.get('all_packets_within_bounds') is True, 'OFFLINE_PACKET_BOUNDS_REQUIRED')
        require(binding.get('caps') == CAPS and binding.get('input_sha256') == bundle_binding['input_sha256'], 'FROZEN_BOUNDS_OR_INPUT_CHANGED')
        for key in ('source', 'runtime', 'helpers', 'tests', 'wire', 'prompt', 'schema', 'native_packets', 'protocol'):
            require(type(binding.get(key + '_sha256')) is str and len(binding[key + '_sha256']) == 64, 'JOB_BINDING_MISSING')
    frozen = {'version': 'role-review-v1', 'bundle': bundle_binding, 'jobs': job_bindings, 'caps': CAPS,
              'primary': 'mean_Q', 'direction': 'higher', 'formula': '(.30*F1A+.28*F1B)/.58',
              'review_prompt_sha256': sha(contract.REVIEW_SYSTEM.encode()), 'evaluator_commit': EVALUATOR_COMMIT,
              'baseline_before_candidate': True, 'grade_only_after_five_complete': True}
    return {**frozen, 'freeze_sha256': sha(encode(frozen))}


def physical_role_totals(core, job, physical_verify):
    """Add reviewer counts to existing authoritative physical verifier output."""
    totals = physical_verify(core, job)
    records = [core.legacy.load(p) for p in sorted((job / 'physical').glob('*-result.json'))]
    counts = {role: sum(r['role'] == role for r in records) for role in ('parent', 'child', 'reviewer')}
    require(sum(counts.values()) == totals['physical_requests'], 'PHYSICAL_ROLE_BIJECTION')
    return {**totals, 'physical_calls_by_role': counts}

# Operational paths are owned exclusively by this protocol, never historical jobs.
import argparse
from contextlib import nullcontext
import importlib.util
import os
import shutil
import signal
import subprocess
import sys
import time
import role_review_transport as transport
from role_review_worker import candidate_hooks, install_templates

OUT = ROOT / 'output/cscs'
CONTROL = OUT / 'role-review-v1-protocol.json'
RUNNER = 'track_2a/dev/format/run_comparison.py'
PYTHON = '/tmp/hackapertus-ost-contract/.venv/bin/python'
SDK = Path('/home/yasuhito/.pi/agent/install/releases/1.1.0/node_modules/@earendil-works/pi-coding-agent')
CHILD = Path('/home/yasuhito/.pi/agent/npm/node_modules/@tintinweb/pi-subagents')
OFFICIAL = Path('/tmp/ost-official-evaluator-3U4yO9/repo')
SCORER_PYTHON = '/tmp/ost-official-evaluator-3U4yO9/env/bin/python'
ABSOLUTE_STOP = transport.ABSOLUTE_STOP
SCOPE = 'outside_documented_local_real_llm_prompt_development'


def load(path):
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)), 'NONREGULAR_ARTIFACT')
    return json.loads(path.read_bytes())


def rows(path):
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)), 'NONREGULAR_ARTIFACT')
    return [json.loads(line) for line in path.read_bytes().splitlines()]


def exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(encode(value)); stream.flush(); os.fsync(stream.fileno())


def module(path):
    spec = importlib.util.spec_from_file_location('role_review_core', path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def fingerprint(paths, base=None):
    result = {}
    for path in sorted(set(paths)):
        require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)), 'NONREGULAR_SOURCE')
        result[str(path.relative_to(base)) if base else str(path)] = sha(path.read_bytes())
    return result


def source_files():
    # Source only: no fixture, labels, selection, expected, source JSONL or caches.
    files = []
    for directory in ('track_2a/src', 'track_2a/dev/format'):
        files += [p for p in (ROOT / directory).iterdir() if p.is_file()
                  and p.suffix in ('.py', '.ts', '.mjs', '.json')
                  and not p.name.startswith('test') and p.name != 'package-lock.json']
    files += [ROOT / 'track_2a/dev/cscs' / n for n in ('cscs_check.py', 'cscs_dev54.py')]
    vendor = ROOT / 'track_2a/dev/cscs/vendor'
    files += [p for p in vendor.rglob('*.py') if '__pycache__' not in p.parts]
    return sorted(files)


def helpers():
    files = [Path(__file__), Path(__file__).with_name('role_review_transport.py'),
             Path(__file__).with_name('role_review_contract.py'), Path(__file__).with_name('role_review_worker.py')]
    return files + list(Path(__file__).with_name('role-review-templates').iterdir())


def runtime():
    require(load(SDK / 'package.json')['version'] == '1.1.0'
            and load(CHILD / 'package.json')['version'] == '0.19.0', 'PINNED_RUNTIME_REQUIRED')
    require(Path(SCORER_PYTHON).is_file() and (OFFICIAL / 'evaluate.py').is_file(), 'OFFICIAL_RUNTIME_REQUIRED')
    require(subprocess.check_output(['git', '-C', str(OFFICIAL), 'rev-parse', 'HEAD'], text=True).strip() == EVALUATOR_COMMIT,
            'OFFICIAL_EVALUATOR_COMMIT_CHANGED')
    require(not subprocess.check_output(['git', '-C', str(OFFICIAL), 'status', '--porcelain', '--', 'evaluate.py'], text=True),
            'OFFICIAL_EVALUATOR_MODIFIED')
    # Pin both scoring and inference dependencies before spending model tokens.
    paths = [OFFICIAL / 'evaluate.py', Path(SCORER_PYTHON).resolve(), Path(SCORER_PYTHON).parent.parent / 'pyvenv.cfg']
    site_paths = json.loads(subprocess.check_output([SCORER_PYTHON, '-B', '-I', '-c',
        'import json,site; print(json.dumps(site.getsitepackages()))'], text=True))
    for root in {Path(p).resolve() for p in site_paths}:
        paths += [p for p in root.rglob('*') if p.is_file() and not p.is_symlink()
                  and '__pycache__' not in p.parts and p.suffix != '.pyc']
    for root in (SDK.parent.parent, CHILD.parent.parent):
        paths += [p for p in root.rglob('*') if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts]
    paths += [Path(shutil.which('node')).resolve(), Path(PYTHON).resolve()]
    return fingerprint(paths)


def bundle_manifest():
    m = load(BUNDLE / 'selection-manifest.json')
    compact = lambda v: (json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    require(m.get('freeze_sha256') == sha(compact({k: v for k, v in m.items() if k != 'freeze_sha256'})), 'BUNDLE_FREEZE_CHANGED')
    require(m.get('source_sha256') == '87ee4afd9c0ee8861106c50f05884481402ca668aecf927df68fc52d915b02fd'
            and m.get('revision', m.get('source_revision')) == 'fc2b27600310778da6bbf445651ddbca22d86269', 'SOURCE_PIN_CHANGED')
    artifacts = m['artifact_sha256']
    required = {'cases.jsonl', 'expected.jsonl', 'prepared-contexts.jsonl', 'context-audit.jsonl', 'source-metadata.jsonl', 'booklets/manifest.json'}
    require(required <= set(artifacts), 'BUNDLE_BINDING_MISSING')
    for relative, digest in artifacts.items():
        path = BUNDLE / relative
        require(path.resolve().is_relative_to(BUNDLE.resolve()) and sha(path.read_bytes()) == digest and not path.is_symlink(), 'BUNDLE_ARTIFACT_CHANGED')
    selection = BUNDLE / 'selection-freeze.json'
    selected = load(selection)
    require(sha(selection.read_bytes()) == m['selection_file_sha256']
            and m['selection_freeze_sha256'] == selected['selection_freeze_sha256']
            and sha(compact({k:v for k,v in selected.items() if k != 'freeze_sha256'})) == selected['freeze_sha256'], 'SELECTION_CHANGED')
    require(m.get('provenance_scope') == selected.get('provenance_scope') == SCOPE
            and m.get('universal_unseen_claim') is False and selected.get('universal_unseen_claim') is False, 'PROVENANCE_SCOPE_REQUIRED')
    require(m.get('selection_before_expected') is True and m.get('reserved_confirmation_prepared') is False
            and len(selected['selection']) == 60 and m['selection'] == selected['selection'][:30], 'SELECTION_SCOPE_CHANGED')
    provenance = {'scope': SCOPE, 'universal_unseen_claim': False, 'selection_file_sha256': m['selection_file_sha256']}
    evidence = selected.get('exclusion_evidence_sha256', {})
    require(type(evidence) is dict and bool(evidence), 'PROVENANCE_EVIDENCE_REQUIRED')
    for name, digest in evidence.items():
        require(name not in ('.auto/prompt.md', '.auto/log.jsonl'), 'FORBIDDEN_HISTORY_REFUSED')
        path = ROOT / name
        require(path.resolve().is_relative_to(ROOT) and sha(path.read_bytes()) == digest and not path.is_symlink(), 'PROVENANCE_EVIDENCE_CHANGED')
    for name, digest in m['code_sha256'].items():
        require(name not in ('.auto/prompt.md', '.auto/log.jsonl') and sha((ROOT / name).read_bytes()) == digest, 'DATA_BUILDER_CHANGED')
    cases = rows(BUNDLE / 'cases.jsonl')
    require(len(cases) == 60 and len({c['id'] for c in cases}) == 60 and m['case_order'] == [c['id'] for c in cases], 'CASE_ORDER_CHANGED')
    require(len(m['selection']) == 30, 'DEVELOPMENT30_REQUIRED')
    for case in cases:
        require(set(case) <= {'id', 'claim', 'vote', 'booklet', 'reference'} and ('booklet' in case) != ('reference' in case), 'NON_INPUT_METADATA')
        if 'booklet' in case:
            require('booklets/' + Path(case['booklet']['path']).name in artifacts, 'PDF_NOT_BOUND')
    binding = {'blinded_selection_frozen': True, 'provenance_scope': SCOPE, 'universal_unseen_claim': False,
               'provenance_evidence_sha256': evidence, 'selection_sha256': sha(selection.read_bytes()),
               'provenance_sha256': sha(encode(provenance)), 'input_sha256': artifacts['cases.jsonl'],
               'expected_sha256': artifacts['expected.jsonl'], 'case_order_sha256': sha(encode(m['case_order']))}
    return m, binding


def environment(workspace):
    env = {k: v for k, v in os.environ.items() if not any(s in k.upper() for s in ('KEY', 'TOKEN', 'SECRET', 'PASSWORD', 'AUTH', 'BASE_URL'))}
    env.update(PATH=str(Path(shutil.which('node')).resolve().parent) + os.pathsep + os.defpath, PI_PACKAGE_ROOT=str(SDK), PI_SUBAGENTS_ROOT=str(CHILD), PYTHONDONTWRITEBYTECODE='1')
    return env


def copy_workspace(workspace, arm):
    require(arm in ARMS and not workspace.exists(), 'EXCLUSIVE_WORKSPACE_REQUIRED')
    workspace.mkdir(parents=True, mode=0o700)
    for path in source_files() + helpers():
        target = workspace / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    (workspace / 'booklets').mkdir()
    cases = rows(BUNDLE / 'cases.jsonl')
    for case in cases:
        if 'booklet' in case:
            name = Path(case['booklet']['path']).name
            target = workspace / 'booklets' / name
            if not target.exists():
                shutil.copyfile(BUNDLE / 'booklets' / name, target)
            case['booklet'] = {**case['booklet'], 'path': str(target)}
    exclusive(workspace / 'public-inputs.json', cases)
    if arm == 'candidate':
        install_templates(workspace / 'track_2a/dev/format')


def isolated_prepare(workspace, arm):
    core = module(workspace / RUNNER)
    engine = core.legacy.engine()
    cases = load(workspace / 'public-inputs.json')
    require(len(cases) == 60, 'SIXTY_INPUTS_REQUIRED')
    frozen = []
    for case in cases:
        pages, messages = engine.context(case, workspace, selection_strategy='vote_pages')
        messages[0]['content'] += '\n\n' + core.legacy.PROTOCOL_REMINDER
        require(len(core.legacy.encode(messages)) <= CAPS['input_bytes'], 'CONTEXT_BYTE_LIMIT')
        frozen.append({'case': case, 'pages': pages, 'messages': messages, 'messages_sha256': sha(encode(messages))})
    base = {'version': 2, 'protocol_reminder': core.legacy.PROTOCOL_REMINDER, 'native_schema': 'offline proposal only, not sent',
            'case_sha256': sha((workspace / 'public-inputs.json').read_bytes()), 'models': core.MODELS,
            'request_limit': 300, 'token_budget': CAPS['charged_tokens'], 'request_token_reserve': transport.RESERVE,
            'output_limit': 256, 'temperature': 0, 'selection_strategy': 'vote_pages',
            'sources': fingerprint(source_files_local(workspace), workspace), 'frozen': frozen}
    core.legacy.prepare = lambda: base
    manifest = core.prepare('C', [c['id'] for c in cases])
    manifest.update(variant=VARIANT if arm == 'candidate' else BASELINE, request_limit=300, token_budget=CAPS['charged_tokens'])
    if arm == 'candidate':
        manifest.update(reviewer_completion_limit=2, role_models={'parent': core.MODELS[1], 'child': core.MODELS[0], 'reviewer': core.MODELS[0]})
    return core, manifest


def source_files_local(workspace):
    return [p for p in (workspace / 'track_2a').rglob('*') if p.is_file()]


def capture_sdk(core, manifest):
    packets = []
    for index, item in enumerate(manifest['frozen']):
        roles = []
        def post(role, number, payload):
            from role_review_worker import enforce_bridge_tools
            size = len(core.legacy.encode(payload))
            require(size <= CAPS['input_bytes'], 'NATIVE_PACKET_BYTE_LIMIT')
            if role == 'reviewer':
                enforce_bridge_tools(core, payload, item['candidate_ids'], role)
            else:
                core.enforce_tools(payload, item['candidate_ids'], role)
            roles.append(role)
            packets.append({'case_index': index, 'role': role, 'number': number, 'bytes': size, 'payload': payload, 'sha256': sha(core.legacy.encode(payload))})
            name = payload['tool_choice']['function']['name']
            args = ({'mode': 'source_only'} if name == 'subagent' else
                    {'axis': 'none', 'candidate_ids': [], 'claim_quote': '', 'source_quote': ''} if role == 'reviewer' else
                    {'label': 1, 'candidate_ids': []})
            return {'id': 'fictional', 'model': payload['model'], 'choices': [{'finish_reason': 'tool_calls', 'message': {
                'role': 'assistant', 'content': None, 'tool_calls': [{'id': f'fictional-{role}-{number}', 'type': 'function',
                'function': {'name': name, 'arguments': json.dumps(args)}}]}}],
                'usage': {'prompt_tokens': 80, 'completion_tokens': 20, 'total_tokens': 100}}
        args, _, sdk = core.run_b(item, core.MODELS[1], post, strategy='C', isolation_guard=True)
        expected = (['parent', 'child', 'reviewer', 'parent'] if item['candidate_ids'] else ['parent', 'child', 'parent']) if manifest['variant'] == VARIANT else ['parent', 'child', 'parent']
        require(args == {'label': 1, 'candidate_ids': []} and roles == expected, 'OFFLINE_SDK_ROUTE_CHANGED')
        if manifest['variant'] == VARIANT:
            require(len(sdk['review_audit']['parent_tool_reports']) == 1, 'PARENT_REPORT_NOT_DELIVERED')
    return packets


def export_workspace(arm):
    # Offline only: prohibit Python credential reads and outbound connections too.
    import http.client
    import urllib.request
    def forbidden(*args, **kwargs):
        raise ValueError('OFFLINE_EXTERNAL_ACCESS_REFUSED')
    http.client.HTTPConnection.connect = forbidden
    urllib.request.urlopen = forbidden
    core, manifest = isolated_prepare(ROOT, arm)
    core.legacy.c.read_key = forbidden
    with candidate_hooks(core, manifest) if arm == 'candidate' else nullcontext():
        packets = capture_sdk(core, manifest)
    exclusive(ROOT / 'prepared.json', manifest)
    exclusive(ROOT / 'offline-packets.json', {'cases': 60, 'packets': packets, 'remote_calls': 0, 'credential_reads': 0})


def subprocess_group(command, workspace, timeout):
    require(timeout > 0, 'DEADLINE_STOP')
    process = subprocess.Popen(command, cwd=workspace, env=environment(workspace), start_new_session=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise ValueError('PROCESS_GROUP_DEADLINE_STOP') from None
    require(process.returncode == 0, 'WORKSPACE_SUBPROCESS_FAILED')
    return stdout


def audit_contexts(manifest):
    prepared = rows(BUNDLE / 'prepared-contexts.jsonl')
    audits = rows(BUNDLE / 'context-audit.jsonl')
    require(len(prepared) == len(audits) == len(manifest['frozen']) == 60, 'CONTEXT_COUNT_CHANGED')
    for item, saved, audit in zip(manifest['frozen'], prepared, audits):
        require(item['case']['id'] == saved['id'] == audit['id'] and item['messages'][1:] == saved['messages'][1:], 'ORIGINAL_CONTEXT_CHANGED')
        require(item['messages'][0]['content'] == saved['messages'][0]['content'] + '\n\n' + manifest['protocol_reminder'], 'SYSTEM_CHANGED')
        require(item['candidate_ids'] == audit['candidate_ids'], 'CANDIDATE_IDS_CHANGED')
        system = item['messages'][0]['content'].removesuffix('\n\n' + manifest['protocol_reminder'])
        require(sha(system.encode()) == load(BUNDLE / 'selection-manifest.json')['system_sha256'], 'V5_SYSTEM_CHANGED')
        compact = (json.dumps(item['pages'], ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode()
        require(sha(compact) == audit['selected_page_text_sha256'], 'PAGE_TEXT_CHANGED')


def prepare_only():
    require(not CONTROL.exists(), 'PROTOCOL_ALREADY_FROZEN')
    _, bundle = bundle_manifest()
    rt = runtime()
    controls = fingerprint(source_files() + helpers() + list(Path(__file__).parent.glob('test_role_review*.py'))
                           + [ROOT / '.auto/measure.sh', ROOT / '.auto/checks.sh', ROOT / 'evals/c-system-prompt/grader.py', ROOT / '.auto/role-review-plan.md', ROOT / '.auto/role-review-implementation.md'], ROOT)
    bindings, jobs = {}, {}
    for name in JOBS:
        arm = 'candidate' if '-candidate-' in name else 'baseline'
        require(not (OUT / name).exists(), 'JOB_ALREADY_EXISTS')
        workspace = OUT / (name + '-workspace')
        copy_workspace(workspace, arm)
        subprocess_group([PYTHON, '-B', '.auto/role_review_research.py', '--export-workspace', arm], workspace, 5700)
        m = load(workspace / 'prepared.json')
        audit_contexts(m)
        files = fingerprint([p for p in workspace.rglob('*') if p.is_file()], workspace)
        packets = load(workspace / 'offline-packets.json')
        require(packets['cases'] == 60 and packets['remote_calls'] == 0, 'OFFLINE_AUDIT_REQUIRED')
        jobs[name] = {'workspace': str(workspace), 'files': files, 'manifest_sha256': sha(encode(m))}
        bindings[name] = {'variant': m['variant'], 'canonical_cases': 60, 'gold_free': True, 'all_packets_within_bounds': True,
                          'caps': CAPS, 'input_sha256': bundle['input_sha256'],
                          'source_sha256': sha(encode(files)), 'runtime_sha256': sha(encode(rt)), 'helpers_sha256': sha(encode(controls)),
                          'tests_sha256': sha(encode({k:v for k,v in controls.items() if '/test_' in k})),
                          'wire_sha256': sha((workspace / 'track_2a/dev/format/sdk.ts').read_bytes()),
                          'prompt_sha256': sha(encode([i['messages'][0] for i in m['frozen']])),
                          'schema_sha256': sha(encode([i['schema_sha256'] for i in m['frozen']])),
                          'native_packets_sha256': files['offline-packets.json'], 'protocol_sha256': controls['.auto/role-review-plan.md']}
    frozen = prospective_bindings(bundle, bindings)
    exclusive(CONTROL, {'policy': frozen, 'jobs': jobs, 'runtime': rt, 'controls': controls, 'absolute_stop': ABSOLUTE_STOP})
    print(json.dumps({'status': 'frozen', 'jobs': 10, 'offline_cases': 600, 'remote_calls': 0}))


def verify_freeze():
    control = load(CONTROL)
    require(control['absolute_stop'] == ABSOLUTE_STOP, 'DEADLINE_CHANGED')
    _, bundle = bundle_manifest()
    require(prospective_bindings(bundle, control['policy']['jobs']) == control['policy'], 'POLICY_CHANGED')
    require(fingerprint([ROOT / p for p in control['controls']], ROOT) == control['controls'], 'CONTROLS_CHANGED')
    require(fingerprint([Path(p) for p in control['runtime']]) == control['runtime'], 'RUNTIME_CHANGED')
    for name, job in control['jobs'].items():
        workspace = Path(job['workspace'])
        require(name in JOBS and workspace == OUT / (name + '-workspace'), 'WORKSPACE_SCOPE_CHANGED')
        require(fingerprint([p for p in workspace.rglob('*') if p.is_file()], workspace) == job['files'], 'WORKSPACE_CHANGED')
    return control


def worker(name, cutoff, manifest_sha):
    # Executed from the frozen workspace. Never historical CLI/patch/prepare.
    require(name in JOBS and ROOT.name == name + '-workspace', 'WORKER_SCOPE_REFUSED')
    parent = ROOT.parent
    control = load(parent / CONTROL.name)
    binding = control['jobs'][name]
    require(binding['workspace'] == str(ROOT) and binding['manifest_sha256'] == manifest_sha, 'WORKER_BINDING_CHANGED')
    require(fingerprint([p for p in ROOT.rglob('*') if p.is_file()], ROOT) == binding['files'], 'WORKSPACE_CHANGED')
    arm = 'candidate' if '-candidate-' in name else 'baseline'
    phase = load(parent / f'role-review-v1-{arm}-phase.json')
    require(phase['status'] == 'running' and phase['protocol_sha256'] == sha((parent / CONTROL.name).read_bytes())
            and not (parent / f'role-review-v1-{arm}-STOP.json').exists(), 'ACTIVE_PHASE_REQUIRED')
    phase_end = min(cutoff, ABSOLUTE_STOP)
    cutoff = min(phase_end + 300, ABSOLUTE_STOP)
    require(time.time() < phase_end, 'ABSOLUTE_DEADLINE_STOP')
    core = module(ROOT / RUNNER)
    manifest = load(ROOT / 'prepared.json')
    require(sha(encode(manifest)) == manifest_sha, 'MANIFEST_CHANGED')
    job = parent / name
    job.mkdir(mode=0o700)
    core.legacy.c.protect()
    with candidate_hooks(core, manifest) if arm == 'candidate' else nullcontext():
        original = core.run_b
        def bounded(*args, **kwargs):
            if time.time() >= phase_end:
                raise core.Stop('PHASE_DEADLINE_STOP')
            remaining = min(300, cutoff - time.time())
            if remaining <= 0:
                raise core.Stop('ABSOLUTE_DEADLINE_STOP')
            return original(*args, **kwargs, seconds=remaining)
        core.run_b = bounded
        core.initialize(job, manifest)
        side = transport.PhysicalLedger(core, job, time.monotonic() + cutoff - time.time())
        core.run(job, manifest, side.client)


def review_available_to_parent(report, delivered):
    require(all(p['source_review'] == report for p in delivered), 'PARENT_REPORT_CHANGED')
    return report['status'] != 'review_unavailable' and bool(delivered)


def completed_result(name, binding):
    require(name in JOBS, 'JOB_SCOPE_REFUSED')
    job = OUT / name
    require(not any((job / f).exists() for f in ('STOP.json', 'inflight.json', 'state.pending')), 'STOP_OR_ORPHAN_FATAL')
    m = load(job / 'manifest.json')
    require(sha(encode(m)) == binding['manifest_sha256'], 'MANIFEST_CHANGED')
    core = module(ROOT / RUNNER)
    candidate = m['variant'] == VARIANT
    with candidate_hooks(core, m) if candidate else nullcontext():
        ledger = core.Ledger(job, m, lambda _: require(False, 'OFFLINE_ONLY'))
        require(len(ledger.state['cases']) == 60 and len(m['frozen']) == 60, 'INCOMPLETE_JOB')
        records = [ledger.records[core.legacy.result_name(core.MODELS[1], i).replace('.json', '-case.json')] for i in range(60)]
        canonical = rows(job / '70b-canonical.jsonl')
        require(len(canonical) == 60 and canonical == [r['prediction'] for r in records], 'CANONICAL_CHANGED')
        for index, (record, prediction, item) in enumerate(zip(records, canonical, m['frozen'])):
            require(record['model'] == core.MODELS[1] and record['case_index'] == index and record['case_id'] == item['case']['id'] == prediction['id']
                    and type(record['output_valid']) is bool and record['error'] == (None if record['output_valid'] else 'NO_ACCEPTED_SUBMIT'), 'CASE_RECORD_CHANGED')
            core.submission.validate(prediction, item['case'], item['pages'])
            expected_metrics, _ = core.metrics_for(ledger, core.MODELS[1], index, record['case_wall_ms'])
            require(prediction['metrics'] == expected_metrics, 'CANONICAL_USAGE_CHANGED')
        attempts = [ledger.records[n] for n in ledger.state['attempts']]
        for attempt in attempts:
            index = attempt['case_index']
            require(type(index) is int and 0 <= index < 60 and attempt['model'] == core.MODELS[1]
                    and attempt['request_model'] == core.fixed_role_model('C', core.MODELS[1], attempt['role'])
                    and all(attempt[k] is True for k in ('safe', 'usage_known', 'usage_valid', 'server_model_matches'))
                    and not attempt['has_api_error'] and core.valid_usage_details(attempt['usage'])
                    and attempt['source_sha256'] == m['frozen'][index]['messages_sha256']
                    and attempt['assembler_schema_sha256'] == m['frozen'][index]['schema_sha256'], 'UNSAFE_REQUEST_USAGE')
        for index in range(60):
            for role in ('parent', 'child', 'reviewer'):
                subset = [a for a in attempts if a['case_index'] == index and a['role'] == role]
                require(sorted(a['number'] for a in subset) == list(range(len(subset)))
                        and len(subset) <= (3 if role == 'parent' else 2), 'ROLE_COMPLETION_LIMIT_CHANGED')
        require(load(job / 'summary.json')['status'] == 'completed', 'SUMMARY_INCOMPLETE')
        stats = physical_role_totals(core, job, transport.verify)
    statuses, reasons, report_coverage = {}, {}, 0
    available = 0
    review_records = []
    for record in records if candidate else []:
        sdk = record['sdk']
        report = sdk['source_review']
        if report['status'] != 'review_unavailable':
            source = core.submission.strict_json(m['frozen'][record['case_index']]['messages'][1]['content'])
            require(contract.validate(report['report'], source) == report, 'REVIEW_GROUNDING_CHANGED')
        status = report['status']
        require(status in ('review_unavailable', 'difference_reported', 'no_specific_difference_reported'), 'REVIEW_STATE_CHANGED')
        statuses[status] = statuses.get(status, 0) + 1
        if status == 'review_unavailable':
            reason = report['reason']; reasons[reason] = reasons.get(reason, 0) + 1
        delivered = sdk['review_audit']['parent_tool_reports']
        available += review_available_to_parent(report, delivered)
        report_coverage += bool(delivered)
        review_records.append({'id': record['case_id'], 'source_review': report, 'parent_tool_reports': delivered,
                               'diagnostics': record['diagnostics']})
    role_usage = {role: {'calls': sum(a['role'] == role for a in attempts),
                        'input_tokens': sum(a['usage']['prompt_tokens'] for a in attempts if a['role'] == role),
                        'output_tokens': sum(a['usage']['completion_tokens'] for a in attempts if a['role'] == role),
                        'api_wait_ms': sum(a['api_wait_ms'] for a in attempts if a['role'] == role)}
                  for role in ('parent', 'child', 'reviewer')}
    return {**stats, 'complete': True, 'canonical_count': 60, 'source_valid': True, 'model_valid': True,
            'usage_known': True, 'ledger_valid': True, 'fallbacks': sum(not r['output_valid'] for r in records),
            'review_available': available, 'review_states': statuses, 'review_unavailable_reasons': reasons,
            'parent_tool_report_cases': report_coverage, 'review_records': review_records,
            'literal_quote_validation_failures': sum(r['diagnostics'].count('REVIEW_LITERAL_QUOTE') for r in records),
            'canonical_successful_calls': len(attempts), 'role_usage': role_usage,
            'known_successful_input_tokens': sum(a['usage']['prompt_tokens'] for a in attempts),
            'known_successful_output_tokens': sum(a['usage']['completion_tokens'] for a in attempts),
            'case_wall_ms': sum(r['case_wall_ms'] for r in records)}


def complete_arm(control, arm):
    names = [n for n in JOBS if f'-{arm}-' in n]
    return {n: completed_result(n, control['jobs'][n]) for n in names}


def grade_arm(control, arm):
    # This check happens before the FIRST grading call, never per-prefix grading.
    complete = complete_arm(control, arm)
    results = []
    for name, stats in complete.items():
        report = OUT / (name + '-official.json')
        require(not report.exists(), 'GRADING_REPLAY_REFUSED')
        command = [SCORER_PYTHON, '-B', str(ROOT / 'evals/c-system-prompt/grader.py'),
                   '--official-repo', str(OFFICIAL), '--python', SCORER_PYTHON,
                   '--predictions', str(OUT / name / '70b-canonical.jsonl'), '--expected', str(BUNDLE / 'expected.jsonl'),
                   '--cases', str(BUNDLE / 'cases.jsonl'), '--output', str(report)]
        exclusive(report, {'status': 'grading'})
        subprocess.run(command, check=True, capture_output=True)
        g = load(report)
        require(g['official_commit'] == EVALUATOR_COMMIT, 'OFFICIAL_COMMIT_CHANGED')
        a, b = (g['official_report']['tasks'][task]['macro_f1'] for task in ('A', 'B'))
        require(quality(a, b) == g['classification_objective']['value'], 'OFFICIAL_Q_CHANGED')
        results.append({**stats, 'f1a': a, 'f1b': b, 'hita': g['primary_evidence_objective']['value'], 'official': g})
    baseline_integrity(results)
    return results


def analysis_path(arm):
    require(arm in ARMS, 'ARM_REFUSED')
    return OUT / f'role-review-v1-{arm}-analysis.json'


def execute(arm):
    require(arm in ARMS, 'ARM_REFUSED')
    require(ABSOLUTE_STOP - time.time() >= 5700, 'INSUFFICIENT_COMPLETE_ARM_TIME')
    control = verify_freeze()
    if arm == 'candidate':
        baseline = checked_analysis(control, 'baseline')
    require(ABSOLUTE_STOP - time.time() >= 5700, 'INSUFFICIENT_COMPLETE_ARM_TIME')
    started = time.time()
    phase_end = min(started + 5400, ABSOLUTE_STOP)
    phase = OUT / f'role-review-v1-{arm}-phase.json'
    stop = OUT / f'role-review-v1-{arm}-STOP.json'
    require(not stop.exists(), 'PHASE_FENCED')
    protocol_sha = sha(CONTROL.read_bytes())
    exclusive(phase, {'status': 'running', 'started': started, 'phase_end': phase_end,
                      'absolute_stop': ABSOLUTE_STOP, 'protocol_sha256': protocol_sha})
    try:
        for name in [n for n in JOBS if f'-{arm}-' in n]:
            require(time.time() < phase_end, 'PHASE_DEADLINE_STOP')
            binding = control['jobs'][name]
            require(not (OUT / name).exists(), 'JOB_REPLAY_REFUSED')
            subprocess_group([PYTHON, '-B', '.auto/role_review_research.py', '--worker', name,
                              '--cutoff', str(phase_end), '--manifest-sha256', binding['manifest_sha256']],
                             Path(binding['workspace']), min(phase_end + 300, ABSOLUTE_STOP) - time.time())
        results = grade_arm(control, arm)
        result = {'arm': arm, 'protocol_sha256': protocol_sha, 'repeats': results,
                  'mean_Q': statistics.mean(quality(r['f1a'], r['f1b']) for r in results),
                  'elapsed_seconds': time.time() - started}
        if arm == 'candidate':
            result['comparison'] = candidate_gates(baseline['repeats'], results)
        exclusive(analysis_path(arm), result)
        # Shared canonical context is operational dispatch state, never research history.
        context = ROOT / '.auto/check-context.json'
        context.write_bytes(encode({'mode': 'role_review', 'candidate': VARIANT if arm == 'candidate' else '',
                                    'arm': arm, 'protocol_sha256': protocol_sha}))
        print_metrics(result)
    except BaseException as exc:
        if not stop.exists():
            exclusive(stop, {'status': 'STOP', 'reason': type(exc).__name__, 'protocol_sha256': protocol_sha})
        raise


def checked_analysis(control, arm):
    result = load(analysis_path(arm))
    require(result['arm'] == arm and result['protocol_sha256'] == sha(CONTROL.read_bytes()), 'ANALYSIS_BINDING_CHANGED')
    actual = complete_arm(control, arm)
    require(len(result['repeats']) == 5, 'INCOMPLETE_ARM_NO_GRADING')
    for name, saved in zip(actual, result['repeats']):
        require(all(saved[k] == v for k, v in actual[name].items()), 'ANALYSIS_CHANGED')
        official = load(OUT / (name + '-official.json'))
        require(official == saved['official'] and official['official_commit'] == EVALUATOR_COMMIT, 'OFFICIAL_REPORT_CHANGED')
        a, b = (official['official_report']['tasks'][task]['macro_f1'] for task in ('A', 'B'))
        require((saved['f1a'], saved['f1b'], saved['hita']) == (a, b, official['primary_evidence_objective']['value'])
                and quality(a, b) == official['classification_objective']['value'], 'OFFICIAL_METRICS_CHANGED')
    baseline_integrity(result['repeats'])
    require(result['mean_Q'] == statistics.mean(quality(r['f1a'], r['f1b']) for r in result['repeats']), 'MEAN_Q_CHANGED')
    return result


def print_metrics(result):
    repeats = result['repeats']
    values = {'mean_Q': result['mean_Q'], 'elapsed_seconds': result['elapsed_seconds'],
              'mean_F1A': statistics.mean(r['f1a'] for r in repeats),
              'mean_F1B': statistics.mean(r['f1b'] for r in repeats),
              'mean_HitA': statistics.mean(r['hita'] for r in repeats),
              'format_fallbacks': sum(r['fallbacks'] for r in repeats),
              'review_available': sum(r['review_available'] for r in repeats),
              'parent_tool_report_cases': sum(r['parent_tool_report_cases'] for r in repeats),
              'canonical_successful_calls': sum(r['canonical_successful_calls'] for r in repeats),
              'full_usage_known': int(all(r['full_usage_known'] for r in repeats)),
              'financial_cost': 'unavailable'}
    for key in ('physical_requests', 'unknown_failed_count', 'reserved_unknown_charge', 'charged_tokens',
                'known_successful_tokens', 'known_successful_input_tokens', 'known_successful_output_tokens',
                'physical_network_seconds', 'physical_backoff_seconds'):
        values['total_' + key] = sum(r[key] for r in repeats)
    values['full_total_tokens'] = sum(r['full_total_tokens'] for r in repeats) if values['full_usage_known'] else 'unavailable'
    for role in ('parent', 'child', 'reviewer'):
        values['physical_' + role + '_calls'] = sum(r['physical_calls_by_role'][role] for r in repeats)
        for key in ('calls', 'input_tokens', 'output_tokens', 'api_wait_ms'):
            values[role + '_' + key] = sum(r['role_usage'][role][key] for r in repeats)
    for index, repeat in enumerate(repeats, 1):
        for key in ('f1a', 'f1b', 'hita', 'fallbacks', 'review_available'):
            values[f'r{index}_{key}'] = repeat[key]
    if 'comparison' in result:
        for key in ('baseline_mean_Q', 'candidate_mean_Q', 'gain', 'baseline_noise', 'review_coverage'):
            values[key] = result['comparison'][key]
        values['research_keep'] = int(result['comparison']['research_keep'])
        values.update({'guard_' + k: int(v) for k, v in result['comparison']['gates'].items()})
    for key, value in values.items():
        print(f'METRIC {key}={value}')


def check_context():
    context = load(ROOT / '.auto/check-context.json')
    require(context['mode'] == 'role_review' and context['arm'] in ARMS, 'CONTEXT_REFUSED')
    control = verify_freeze()
    require(context['protocol_sha256'] == sha(CONTROL.read_bytes())
            and context['candidate'] == (VARIANT if context['arm'] == 'candidate' else ''), 'CONTEXT_BINDING_CHANGED')
    result = checked_analysis(control, context['arm'])
    if context['arm'] == 'candidate':
        baseline = checked_analysis(control, 'baseline')
        require(candidate_gates(baseline['repeats'], result['repeats']) == result['comparison'], 'COMPARISON_CHANGED')
        require(result['comparison']['research_keep'], 'CANDIDATE_QUALITY_GATES_FAILED')
    print_metrics(result)


def main():
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare-only', action='store_true')
    action.add_argument('--baseline', action='store_true')
    action.add_argument('--candidate', action='store_true')
    action.add_argument('--check-context', action='store_true')
    action.add_argument('--export-workspace', choices=ARMS)
    action.add_argument('--worker', choices=JOBS)
    parser.add_argument('--cutoff', type=float)
    parser.add_argument('--manifest-sha256')
    args = parser.parse_args()
    if args.prepare_only:
        prepare_only()
    elif args.export_workspace:
        export_workspace(args.export_workspace)
    elif args.worker:
        require(args.cutoff is not None and args.manifest_sha256 is not None, 'WORKER_BINDING_REQUIRED')
        worker(args.worker, args.cutoff, args.manifest_sha256)
    elif args.check_context:
        check_context()
    else:
        execute('candidate' if args.candidate else 'baseline')


if __name__ == '__main__':
    main()
