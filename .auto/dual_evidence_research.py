"""Exclusive candidate controller with immutable saved reference. Preparation/export are credential-free."""
import hashlib
import json
import math
from pathlib import Path
import statistics

import span_retrieval_contract as contract
from dual_evidence_worker import VARIANT

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / 'output/validation/role-review-v1'
BASELINE = 'role-review-v1-baseline'
ARMS = ('candidate',)
JOBS = tuple(f'dual-evidence-v1-{arm}-r{repeat}' for arm in ARMS for repeat in range(1, 6))
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
    """Bind precise documented-exposure scope and all five audited input-only candidate jobs."""
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
    require(set(job_bindings) == set(JOBS), 'ALL_FIVE_JOBS_REQUIRED')
    for name, binding in job_bindings.items():
        arm = 'candidate' if '-candidate-' in name else 'baseline'
        require(binding.get('variant') == (VARIANT if arm == 'candidate' else BASELINE), 'VARIANT_REFUSED')
        require(binding.get('canonical_cases') == 60 and binding.get('gold_free') is True, 'MODEL_WORKSPACE_NOT_BLINDED')
        require(binding.get('all_packets_within_bounds') is True, 'OFFLINE_PACKET_BOUNDS_REQUIRED')
        require(binding.get('caps') == CAPS and binding.get('input_sha256') == bundle_binding['input_sha256'], 'FROZEN_BOUNDS_OR_INPUT_CHANGED')
        for key in ('source', 'runtime', 'helpers', 'tests', 'wire', 'prompt', 'schema', 'native_packets', 'protocol'):
            require(type(binding.get(key + '_sha256')) is str and len(binding[key + '_sha256']) == 64, 'JOB_BINDING_MISSING')
    frozen = {'version': 'dual-evidence-v1', 'bundle': bundle_binding, 'jobs': job_bindings, 'caps': CAPS,
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
from dual_evidence_worker import candidate_hooks, install_templates

OUT = ROOT / 'output/cscs'
CONTROL = OUT / 'dual-evidence-v1-protocol.json'
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
             Path(__file__).with_name('span_retrieval_contract.py'), Path(__file__).with_name('dual_evidence_worker.py')]
    return files + list(Path(__file__).with_name('dual-evidence-templates').iterdir())


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
    for item in manifest['frozen']:
        view = contract.inventory(core.submission.strict_json(item['messages'][1]['content']))
        item['span_view_sha256'] = sha(encode(view))
        item['review_user_sha256'] = sha(contract.projection(core.submission.strict_json(item['messages'][1]['content']), view).encode())
        item['review_schema_sha256'] = sha(encode(contract.schema(view)))
    return core, manifest


def source_files_local(workspace):
    return [p for p in (workspace / 'track_2a').rglob('*') if p.is_file()]


def root_fake_request(core, payload, respond):
    """Exercise unchanged Root Transport with injected dummy credentials, no sockets."""
    from unittest.mock import patch
    require(len(core.legacy.encode(payload)) <= CAPS['input_bytes'], 'NATIVE_PACKET_BYTE_LIMIT')
    sent = []
    class Connection:
        def __init__(self, host, port, **kwargs):
            require(host == 'fictional.invalid' and kwargs['timeout'] == 45, 'FAKE_ENDPOINT_CHANGED')
        def set_debuglevel(self, value):
            require(value == 0, 'FAKE_DEBUG_CHANGED')
        def request(self, method, path, body, headers):
            require(method == 'POST' and path == '/v1/chat/completions', 'FAKE_ROUTE_CHANGED')
            require(body == core.legacy.encode(payload), 'ROOT_PACKET_BYTES_CHANGED')
            require(headers['Authorization'] == 'Bearer evidence-offline-dummy', 'FAKE_KEY_CHANGED')
            sent.append(body)
        def getresponse(self):
            class Response:
                status = 200
                def read(self, limit):
                    require(limit == 2000001, 'ROOT_RESPONSE_BOUND_CHANGED')
                    return json.dumps(respond(), ensure_ascii=True, allow_nan=False).encode()
            return Response()
        def close(self):
            pass
    with patch.dict(os.environ, {'BASE_URL': 'http://fictional.invalid/v1', 'API_KEY': 'evidence-offline-dummy'}):
        result = core.Transport(payload['model'], submitted=True, factory=Connection).request(
            'POST', '/v1/chat/completions', payload)
    require(len(sent) == 1, 'ROOT_HTTP_NOT_REACHED')
    return result


def ordinary_recommendation_bound(core, item):
    """Input-only conservative advice bound, no semantic inference.

    A valid recommendation has at most five original IDs and one digit label.
    Rank double-escaped IDs, pad actual valid neutral[] advice by the additive
    maximum. No citation semantics or assembler acceptance is assumed for IDs.
    """
    def weight(sid):
        return len(core.legacy.encode(json.dumps(sid, ensure_ascii=False, separators=(',', ':'))))
    ids_allowance = sum(weight(sid) + 1 for sid in sorted(item['candidate_ids'], key=weight, reverse=True)[:5])
    unavailable = {'status': 'recommendation_unavailable', 'reason': 'NO_CHILD_SUBMIT'}
    normal = {'label': 1, 'candidate_ids': []}
    def nested_size(value):
        return len(core.legacy.encode(json.dumps(value, ensure_ascii=False, separators=(',', ':'))))
    return max(ids_allowance, nested_size(unavailable) - nested_size(normal))


def capture_sdk(core, manifest, populated=True):
    """Pinned SDK -> bridge -> unchanged Root -> fake HTTP for every packet."""
    packets = []
    for index, item in enumerate(manifest['frozen']):
        roles, case_packets = [], []
        source = core.submission.strict_json(item['messages'][1]['content'])
        ids = [span['span_id'] for span in source['source_spans']]
        invalid_ids = [ids[0], ids[0]] if ids else ['offline-invalid-original-id']
        normal = {'label': 1, 'candidate_ids': []}
        core.submission.assemble_tool(normal, item['case'], item['pages'],
            {'input_tokens': 0, 'output_tokens': 0, 'inference_time_ms': 0})
        def post(role, number, payload):
            from dual_evidence_worker import enforce_bridge_tools
            size = len(core.legacy.encode(payload))
            require(size <= CAPS['input_bytes'], 'NATIVE_PACKET_BYTE_LIMIT')
            # A neutral empty recommendation is legal. Bound every possible
            # largest valid 0/1/2 recommendation conservatively without using
            # source meaning, and without putting fabricated advice on the wire.
            bound = size + (ordinary_recommendation_bound(core, item)
                            if role == 'parent' and number else 0)
            require(bound <= CAPS['input_bytes'], 'NATIVE_ADVICE_BOUND_BYTE_LIMIT')
            enforce_bridge_tools(core, payload, item['candidate_ids'], role)
            roles.append(role)
            packet = {'case_index': index, 'role': role, 'number': number, 'bytes': size,
                      'advice_bound_bytes': bound,
                      'payload': payload, 'sha256': sha(core.legacy.encode(payload))}
            packets.append(packet); case_packets.append(packet)
            name = payload['tool_choice']['function']['name']
            args = ({'mode': 'source_only'} if name == 'subagent' else
                    {'candidate_ids': invalid_ids} if role == 'reviewer' and populated and number == 0 else
                    fictional_selection(item, populated) if role == 'reviewer' else
                    normal if role == 'child' else
                    {'label': 2 if populated and number == 1 else 1, 'candidate_ids': []})
            raw = ('{"label":1,"label":1,"candidate_ids":[]}'
                   if role == 'child' and populated and number == 0 else json.dumps(args))
            value = {'id': 'fictional', 'model': payload['model'], 'choices': [{'finish_reason': 'tool_calls', 'message': {
                'role': 'assistant', 'content': None, 'tool_calls': [{'id': f'fictional-{role}-{number}', 'type': 'function',
                'function': {'name': name, 'arguments': raw}}]}}],
                'usage': {'prompt_tokens': 80, 'completion_tokens': 20, 'total_tokens': 100}}
            return root_fake_request(core, payload, lambda: value)
        args, diagnostics, sdk = core.run_b(item, core.MODELS[1], post, strategy='C', isolation_guard=True)
        expected = ['parent','child','child','reviewer','reviewer','parent','parent'] if populated else ['parent','child','reviewer','parent']
        require(args == normal and roles == expected, 'OFFLINE_SDK_ROUTE_CHANGED')
        require(sdk['counts'] == {'parent': 3 if populated else 2, 'child': 2 if populated else 1,
                                'reviewer': 2 if populated else 1}, 'DUAL_ROLE_ROUTE_REQUIRED')
        require(len(diagnostics) == (3 if populated else 0), 'OFFLINE_REPAIR_DIAGNOSTICS_CHANGED')
        if populated:
            require(diagnostics[-2:] == [('RETRIEVAL_DUPLICATE_ID' if ids else 'RETRIEVAL_UNKNOWN_ID'),
                                         'SUPPORTING_SPAN_REQUIRED'], 'OFFLINE_REPAIR_DIAGNOSTICS_CHANGED')
        require(len(sdk['review_audit']['raw_helper_args']) == (2 if populated else 1), 'OFFLINE_HELPER_AUDIT_CHANGED')
        require(sdk['review_audit']['normal_child_recommendation'] == normal, 'ORDINARY_ADVICE_CHANGED')
        helper_usage = [e['usage'] for e in sdk['events'] if e['type'] == 'subagent_usage']
        helper_calls = 4 if populated else 2
        require(len(helper_usage) == 1 and helper_usage[0]['input'] == 80 * helper_calls
                and helper_usage[0]['output'] == 20 * helper_calls
                and helper_usage[0]['totalTokens'] == 100 * helper_calls, 'HELPER_USAGE_CHANGED')
        report = {'recommendation': normal, 'source_evidence': contract.validate(fictional_selection(item, populated), source)}
        require(sdk['source_evidence'] == report['source_evidence'], 'RETRIEVAL_REPORT_CHANGED')
        require(sdk['review_audit']['parent_tool_reports'] == [report], 'PARENT_REPORT_NOT_DELIVERED')
        for packet in case_packets:
            if packet['role'] != 'parent' or packet['number'] == 0:
                continue
            reports = []
            for message in packet['payload']['messages']:
                if message['role'] != 'tool':
                    continue
                try:
                    parsed = core.submission.strict_json(message['content'])
                except (ValueError, TypeError):
                    continue
                if type(parsed) is dict and 'source_evidence' in parsed:
                    reports.append(parsed)
            require(reports == [report], 'DUAL_PARENT_REPORT_REQUIRED')
            if populated and packet['number'] == 2:
                require(any(m['role'] == 'tool' and core.SUPPORTING_SPAN_MESSAGE in m['content']
                            for m in packet['payload']['messages']), 'ORIGINAL_SUPPORT_FEEDBACK_REQUIRED')
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
        packets = capture_sdk(core, manifest) + capture_sdk(core, manifest, populated=False)
    exclusive(ROOT / 'prepared.json', manifest)
    exclusive(ROOT / 'offline-packets.json', {'cases': 60, 'packets': packets, 'remote_calls': 0,
        'credential_reads': 0, 'root_transport_packets': len(packets), 'populated_and_no_pair': True,
        'selected_with_both_repairs': True, 'no_selection_normal_path': True})


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


OLD_PROTOCOL_SHA256 = '5aad8b8db06e725613f661275d596c61ff6f74930b5406dcce2ebd4ff0bb6b1d'
OLD_CONTROL = OUT / 'role-review-v1-protocol.json'


def native_selection_weight(span):
    """Exact additive contribution inside the native JSON tool-content string.

    Pi JSON.stringify renders the report compactly, then Root encodes that text
    as messages.tool.content. Count both escaping layers for the full object
    AND its repeated candidate ID. Array separators and report fields are fixed
    for two selections. Object key order cannot change this byte count.
    """
    def compact(value):
        return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    return len(encode(compact(span))) + len(encode(compact(span['span_id'])))


def fictional_selection(item, populated=True):
    source = json.loads(item['messages'][1]['content'])
    if not populated:
        return {'candidate_ids': []}
    spans = sorted(source['source_spans'], key=native_selection_weight, reverse=True)
    return {'candidate_ids': [span['span_id'] for span in spans[:2]]}


FRAGMENT_PROTOCOL_SHA256 = '5ef5c8f006bf7b3130e1f19b00c1ee38cea7e4ff5bf034490b2aa427f7e5ae78'
FRAGMENT_CONTROL = OUT / 'fragment-review-v1-protocol.json'


def strip_dispatch(raw, protocol):
    start = ('# BEGIN ' + protocol + ' additive\n').encode()
    end = ('# END ' + protocol + ' additive\n').encode()
    require(raw.count(start) == raw.count(end) == 1, 'DISPATCH_NOT_ADDITIVE')
    before, rest = raw.split(start)
    _, after = rest.split(end)
    return before + after


BOUND_PROTOCOL_SHA256 = '8c85711dcfd05e5893bcaac88939edb688b57767c6582ca766e1c2496240eea4'
BOUND_CONTROL = OUT / 'bound-review-v1-protocol.json'
EVIDENCE_CONTROL = OUT / 'evidence-only-v1-protocol.json'
EVIDENCE_PROTOCOL_SHA256 = 'a262e26aa4272827219f412e733b7c427c381628c3a032a0afa371115d1db9e3'
EVIDENCE_DISPATCH_SHA256 = {'.auto/measure.sh': 'facef1976b83cf19c1028a2efca5fc495b54743992881e5d2b8aee8f13761a07', '.auto/checks.sh': '188ada6736d4bf3e1dd465a5e9255a1f550e2dcc176c2e41a7102c457bda2bd4'}
BOUND_DISPATCH_SHA256 = {
    '.auto/measure.sh': '7de56cab510fbb1d97a47d61d07c348b53078b9987b28e65f84763badf923066',
    '.auto/checks.sh': 'e6df1c82e96856d95bd129653cd2f13754cb40966b231c91991e489055818fcf',
}


SPAN_PROTOCOL_SHA256 = '1846cfd036a14e966d3213c991e1ee297cc9ed41a636b94a7e9b41287de7a409'
SPAN_CONTROL = OUT / 'span-retrieval-v1-protocol.json'
SPAN_DISPATCH_SHA256 = {'.auto/measure.sh': '595a15be94e217d3570fc639290c0839b986904e38f9fdd91d079cea4dd79208',
                        '.auto/checks.sh': '89608331eb67b68c3404111c0f3790c58ae3d1e957adbe50a1ef97dc2186018e'}


def verify_additive_dispatch(relative, *unused):
    archives = ROOT / '.auto/protocol-archive'
    layers = ('role-review-v1','fragment-review-v1','bound-review-v1','evidence-only-v1','span-retrieval-v1')
    controls = (OLD_CONTROL, FRAGMENT_CONTROL, BOUND_CONTROL, EVIDENCE_CONTROL, SPAN_CONTROL)
    previous = None
    for layer, path in zip(layers, controls):
        raw = (archives / (layer + '-' + Path(relative).name)).read_bytes()
        require(sha(raw) == load(path)['controls'][relative], 'DISPATCH_ARCHIVE_CHANGED')
        if previous is not None:
            require(strip_dispatch(raw, layer) == previous, 'OLD_DISPATCH_CHANGED')
        previous = raw
    require(sha(previous) == SPAN_DISPATCH_SHA256[relative], 'SPAN_DISPATCH_ARCHIVE_CHANGED')
    require(strip_dispatch((ROOT / relative).read_bytes(), 'dual-evidence-v1') == previous, 'OLD_DISPATCH_CHANGED')


def reference_binding():
    """Explicit all-layer immutable lineage, no frozen verifier monkeypatch."""
    layers = [('role-review-v1', OLD_CONTROL, OLD_PROTOCOL_SHA256),
              ('fragment-review-v1', FRAGMENT_CONTROL, FRAGMENT_PROTOCOL_SHA256),
              ('bound-review-v1', BOUND_CONTROL, BOUND_PROTOCOL_SHA256),
              ('evidence-only-v1', EVIDENCE_CONTROL, EVIDENCE_PROTOCOL_SHA256),
              ('span-retrieval-v1', SPAN_CONTROL, SPAN_PROTOCOL_SHA256)]
    paths = []
    for prefix, path, digest in layers:
        require(sha(path.read_bytes()) == digest, 'OLD_PROTOCOL_CHANGED')
        control = load(path); paths.append(path)
        for relative, value in control['controls'].items():
            if relative in SPAN_DISPATCH_SHA256:
                verify_additive_dispatch(relative)
            else:
                require(sha((ROOT / relative).read_bytes()) == value, 'OLD_CONTROL_CHANGED')
        for relative, value in control.get('reference', {}).get('files', {}).items():
            require(sha((ROOT / relative).read_bytes()) == value, 'OLD_REFERENCE_HISTORY_CHANGED')
            paths.append(ROOT / relative)
        require(fingerprint([Path(p) for p in control['runtime']]) == control['runtime'], 'OLD_RUNTIME_CHANGED')
        for name, job in control['jobs'].items():
            workspace = Path(job['workspace'])
            require(workspace == OUT / (name + '-workspace'), 'OLD_WORKSPACE_SCOPE')
            require(fingerprint([p for p in workspace.rglob('*') if p.is_file()], workspace) == job['files'], 'OLD_WORKSPACE_CHANGED')
        paths += [ROOT / '.auto/protocol-archive' / (prefix + '-' + name) for name in ('measure.sh','checks.sh')]
        for historic in OUT.glob(prefix + '-*'):
            if historic.is_file():
                paths.append(historic)
            elif historic.is_dir():
                paths += [p for p in historic.rglob('*') if p.is_file()]
    import role_review_research as saved
    old = load(OLD_CONTROL)
    _, bundle = saved.bundle_manifest()
    require(saved.prospective_bindings(bundle, old['policy']['jobs']) == old['policy'], 'OLD_POLICY_CHANGED')
    result = saved.checked_analysis(old, 'baseline')
    require(result['mean_Q'] == 0.7293563908542025 and sum(r['fallbacks'] for r in result['repeats']) == 0, 'SAVED_BASELINE_CHANGED')
    names = [f'role-review-v1-baseline-r{i}' for i in range(1, 6)]
    paths.append(saved.analysis_path('baseline'))
    for name in names:
        packets = load(Path(old['jobs'][name]['workspace']) / 'offline-packets.json')
        require(packets['cases'] == 60 and packets['remote_calls'] == 0 and
                {p['case_index'] for p in packets['packets']} == set(range(60)), 'SAVED_CONTROL_PATHS_INCOMPLETE')
        for packet in packets['packets']:
            require(len(encode(packet['payload'])) <= CAPS['input_bytes'] and
                    sha(encode(packet['payload'])) == packet['sha256'], 'SAVED_CONTROL_PACKET_CHANGED')
    return {'span_protocol_sha256': SPAN_PROTOCOL_SHA256, 'files': fingerprint(paths, ROOT),
            'analysis': result, 'baseline_jobs': names, 'saved_sdk_case_paths': 300}


def checked_reference(control):
    actual = reference_binding()
    require(actual == control['reference'], 'REFERENCE_BINDING_CHANGED')
    return actual['analysis']


def prepare_only():
    require(not CONTROL.exists(), 'PROTOCOL_ALREADY_FROZEN')
    reference = reference_binding()
    _, bundle = bundle_manifest()
    rt = runtime()
    controls = fingerprint(source_files() + helpers() + list(Path(__file__).parent.glob('test_dual_evidence*.py'))
                           + [ROOT / '.auto/measure.sh', ROOT / '.auto/checks.sh', ROOT / 'evals/c-system-prompt/grader.py', ROOT / '.auto/dual-evidence-plan.md', ROOT / '.auto/dual-evidence-implementation.md'], ROOT)
    bindings, jobs = {}, {}
    for name in JOBS:
        arm = 'candidate' if '-candidate-' in name else 'baseline'
        require(not (OUT / name).exists(), 'JOB_ALREADY_EXISTS')
        workspace = OUT / (name + '-workspace')
        copy_workspace(workspace, arm)
        subprocess_group([PYTHON, '-B', '.auto/dual_evidence_research.py', '--export-workspace', arm], workspace, 5700)
        m = load(workspace / 'prepared.json')
        audit_contexts(m)
        files = fingerprint([p for p in workspace.rglob('*') if p.is_file()], workspace)
        packets = load(workspace / 'offline-packets.json')
        require(packets['cases'] == 60 and packets['remote_calls'] == packets['credential_reads'] == 0
                and packets['root_transport_packets'] == len(packets['packets']) == 660
                and packets['populated_and_no_pair'] is True
                and packets['selected_with_both_repairs'] is True and packets['no_selection_normal_path'] is True
                and {p['case_index'] for p in packets['packets']} == set(range(60)), 'OFFLINE_AUDIT_REQUIRED')
        jobs[name] = {'workspace': str(workspace), 'files': files, 'manifest_sha256': sha(encode(m))}
        bindings[name] = {'variant': m['variant'], 'canonical_cases': 60, 'gold_free': True, 'all_packets_within_bounds': True,
                          'caps': CAPS, 'input_sha256': bundle['input_sha256'],
                          'source_sha256': sha(encode(files)), 'runtime_sha256': sha(encode(rt)), 'helpers_sha256': sha(encode(controls)),
                          'tests_sha256': sha(encode({k:v for k,v in controls.items() if '/test_' in k})),
                          'wire_sha256': sha((workspace / 'track_2a/dev/format/sdk.ts').read_bytes()),
                          'prompt_sha256': sha(encode([i['messages'][0] for i in m['frozen']])),
                          'schema_sha256': sha(encode([i['schema_sha256'] for i in m['frozen']])),
                          'native_packets_sha256': files['offline-packets.json'], 'protocol_sha256': controls['.auto/dual-evidence-plan.md']}
    frozen = prospective_bindings(bundle, bindings)
    exclusive(CONTROL, {'policy': frozen, 'jobs': jobs, 'runtime': rt, 'controls': controls, 'absolute_stop': ABSOLUTE_STOP, 'reference': reference})
    print(json.dumps({'status': 'frozen', 'jobs': 5, 'offline_cases': 300, 'saved_control_cases_verified': 300, 'remote_calls': 0}))


def verify_freeze():
    control = load(CONTROL)
    checked_reference(control)
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


GUARD_STOP_CODES = frozenset((
    'UNDECLARED_TOOLS_REFUSED', 'HARD_BUDGET_STOP_BEFORE_SEND', 'CASE_DEADLINE_ALL_STOP',
    'REVIEW_SOURCE_IDENTITY_REFUSED', 'REVIEW_TOOLS_REFUSED', 'SDK_REQUEST_LIMIT',
    'ROLE_SYSTEM_REFUSED', 'ORIGINAL_USER_CHANGED', 'ROLE_MODEL_REFUSED',
    'PHYSICAL_DEADLINE_STOP', 'PHYSICAL_BUDGET_STOP', 'PAYLOAD_BYTE_LIMIT',
    'PHASE_DEADLINE_STOP', 'ABSOLUTE_DEADLINE_STOP', 'RETRY_EXHAUSTED',
    'TRANSPORT_UNCERTAIN_NO_RETRY', 'UNKNOWN_MODEL_USAGE_OR_RESPONSE_ALL_STOP',
    'request_wall_deadline_no_retry'))


def run_guarded_job(core, job, manifest, cutoff):
    """New-job diagnostic only; never change Root fences or physical accounting."""
    try:
        core.initialize(job, manifest)
        side = transport.PhysicalLedger(core, job, time.monotonic() + cutoff - time.time())
        return core.run(job, manifest, side.client)
    except core.Stop as exc:
        code = exc.args[0] if len(exc.args) == 1 and type(exc.args[0]) is str else None
        # Persist a member of the fixed allowlist, never arbitrary exception text.
        safe = next((allowed for allowed in GUARD_STOP_CODES if code == allowed), 'unavailable')
        diagnostic = job / 'guard-stop.json'
        if not diagnostic.exists():
            exclusive(diagnostic, {'code': safe, 'type': 'Stop'})
        raise


def worker(name, cutoff, manifest_sha):
    # Executed from the frozen workspace. Never historical CLI/patch/prepare.
    require(name in JOBS and ROOT.name == name + '-workspace', 'WORKER_SCOPE_REFUSED')
    parent = ROOT.parent
    control = load(parent / CONTROL.name)
    binding = control['jobs'][name]
    require(binding['workspace'] == str(ROOT) and binding['manifest_sha256'] == manifest_sha, 'WORKER_BINDING_CHANGED')
    require(fingerprint([p for p in ROOT.rglob('*') if p.is_file()], ROOT) == binding['files'], 'WORKSPACE_CHANGED')
    arm = 'candidate' if '-candidate-' in name else 'baseline'
    phase = load(parent / f'dual-evidence-v1-{arm}-phase.json')
    require(phase['status'] == 'running' and phase['protocol_sha256'] == sha((parent / CONTROL.name).read_bytes())
            and not (parent / f'dual-evidence-v1-{arm}-STOP.json').exists(), 'ACTIVE_PHASE_REQUIRED')
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
        run_guarded_job(core, job, manifest, cutoff)


def review_available_to_parent(report, delivered):
    require(all(type(p) is dict and set(p) == {'recommendation', 'source_evidence'} and p['source_evidence'] == report for p in delivered), 'PARENT_REPORT_CHANGED')
    return report['status'] in ('source_spans_selected', 'no_source_spans_selected') and bool(delivered)


def completed_result(name, binding):
    require(name in JOBS, 'JOB_SCOPE_REFUSED')
    job = OUT / name
    require(not any((job / f).exists() for f in ('STOP.json', 'inflight.json', 'state.pending', 'guard-stop.json')), 'STOP_OR_ORPHAN_FATAL')
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
    statuses = {status: 0 for status in ('source_spans_selected', 'no_source_spans_selected', 'evidence_unavailable')}
    reasons, report_coverage = {}, 0
    selected_span_count = 0
    available = 0
    review_records = []
    for record in records if candidate else []:
        sdk = record['sdk']
        require(sdk['counts']['reviewer'] <= 2 and sdk['counts']['child'] <= 2, 'SOURCE_ONLY_ROLE_COUNTS')
        require(set(sdk['review_audit']) == {'input_sha256', 'parent_tool_reports', 'raw_helper_args', 'role_models', 'normal_child_recommendation'}, 'SOURCE_ONLY_AUDIT')
        require(sdk['review_audit']['role_models'] == {'parent': core.MODELS[1], 'child': core.MODELS[0], 'reviewer': core.MODELS[0]}, 'SOURCE_ONLY_MODELS')
        item = m['frozen'][record['case_index']]
        require(sdk['review_audit']['input_sha256'] == sha(item['messages'][1]['content'].encode()), 'AUDIT_INPUT_CHANGED')
        require(all(sdk['counts'][role] == sum(a['case_index'] == record['case_index'] and a['role'] == role for a in attempts)
                    for role in ('parent', 'child', 'reviewer')), 'ROLE_COUNTS_CHANGED')
        report = sdk['source_evidence']
        if report['status'] == 'evidence_unavailable':
            require(report == contract.unavailable(report['reason']), 'REVIEW_GROUNDING_CHANGED')
        else:
            source = core.submission.strict_json(m['frozen'][record['case_index']]['messages'][1]['content'])
            require(contract.validate({'candidate_ids': report['candidate_ids']}, source) == report, 'REVIEW_GROUNDING_CHANGED')
        selected_span_count += len(report['candidate_ids'])
        status = report['status']
        require(status in ('evidence_unavailable', 'source_spans_selected', 'no_source_spans_selected'), 'REVIEW_STATE_CHANGED')
        statuses[status] = statuses.get(status, 0) + 1
        if status == 'evidence_unavailable':
            reason = report['reason']; reasons[reason] = reasons.get(reason, 0) + 1
        normal = sdk['review_audit']['normal_child_recommendation']
        expected_advice = normal if normal is not None else {'status': 'recommendation_unavailable', 'reason': 'NO_CHILD_SUBMIT'}
        if normal is not None:
            item = m['frozen'][record['case_index']]
            core.submission.assemble_tool(normal, item['case'], item['pages'], {'input_tokens': 0, 'output_tokens': 0, 'inference_time_ms': 0})
        delivered = sdk['review_audit']['parent_tool_reports']
        require(all(p.get('recommendation') == expected_advice for p in delivered), 'ORDINARY_ADVICE_CHANGED')
        available += review_available_to_parent(report, delivered)
        report_coverage += bool(delivered)
        review_records.append({'id': record['case_id'], 'source_evidence': report, 'parent_tool_reports': delivered,
                               'normal_child_recommendation': normal,
                               'parent_label_matches_child': normal is not None and record['output_valid'] and record['prediction']['label'] == normal['label'],
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
            'fragment_selection_rejections': 0, 'retrieval_selected_span_count': selected_span_count,
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
    require(set(complete) == set(JOBS) and len(complete) == 5, 'INCOMPLETE_ARM_NO_GRADING')
    require(all(r.get('complete') is True and r.get('canonical_count') == 60 for r in complete.values()), 'INCOMPLETE_ARM_NO_GRADING')
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
    return OUT / f'dual-evidence-v1-{arm}-analysis.json'


def execute(arm):
    require(arm in ARMS, 'ARM_REFUSED')
    require(ABSOLUTE_STOP - time.time() >= 5700, 'INSUFFICIENT_COMPLETE_ARM_TIME')
    control = verify_freeze()
    if arm == 'candidate':
        baseline = checked_reference(control)
    require(ABSOLUTE_STOP - time.time() >= 5700, 'INSUFFICIENT_COMPLETE_ARM_TIME')
    started = time.time()
    phase_end = min(started + 5400, ABSOLUTE_STOP)
    phase = OUT / f'dual-evidence-v1-{arm}-phase.json'
    stop = OUT / f'dual-evidence-v1-{arm}-STOP.json'
    require(not stop.exists(), 'PHASE_FENCED')
    protocol_sha = sha(CONTROL.read_bytes())
    exclusive(phase, {'status': 'running', 'started': started, 'phase_end': phase_end,
                      'absolute_stop': ABSOLUTE_STOP, 'protocol_sha256': protocol_sha})
    try:
        for name in [n for n in JOBS if f'-{arm}-' in n]:
            require(time.time() < phase_end, 'PHASE_DEADLINE_STOP')
            binding = control['jobs'][name]
            require(not (OUT / name).exists(), 'JOB_REPLAY_REFUSED')
            subprocess_group([PYTHON, '-B', '.auto/dual_evidence_research.py', '--worker', name,
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
        context.write_bytes(encode({'mode': 'dual_evidence', 'candidate': VARIANT if arm == 'candidate' else '',
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
    values.update(review_fact_pair_selected=0, review_no_fact_pair_selected=0, review_unavailable=0)
    for metric, status in (('selected', 'source_spans_selected'), ('noselection', 'no_source_spans_selected'), ('unavailable', 'evidence_unavailable')):
        values['retrieval_' + metric] = sum(r['review_states'][status] for r in repeats)
    values['retrieval_selected_span_count'] = sum(r['retrieval_selected_span_count'] for r in repeats)
    values['fragment_selection_rejections'] = sum(r['fragment_selection_rejections'] for r in repeats)
    for key in ('physical_requests', 'unknown_failed_count', 'reserved_unknown_charge', 'charged_tokens',
                'known_successful_tokens', 'known_successful_input_tokens', 'known_successful_output_tokens',
                'physical_network_seconds', 'physical_backoff_seconds'):
        values['total_' + key] = sum(r[key] for r in repeats)
    values['full_total_tokens'] = sum(r['full_total_tokens'] for r in repeats) if values['full_usage_known'] else -1
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
    require(context['mode'] == 'dual_evidence' and context['arm'] in ARMS, 'CONTEXT_REFUSED')
    control = verify_freeze()
    require(context['protocol_sha256'] == sha(CONTROL.read_bytes())
            and context['candidate'] == (VARIANT if context['arm'] == 'candidate' else ''), 'CONTEXT_BINDING_CHANGED')
    result = checked_analysis(control, context['arm'])
    if context['arm'] == 'candidate':
        baseline = checked_reference(control)
        require(candidate_gates(baseline['repeats'], result['repeats']) == result['comparison'], 'COMPARISON_CHANGED')
        require(result['comparison']['research_keep'], 'CANDIDATE_QUALITY_GATES_FAILED')
    print_metrics(result)


def main():
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare-only', action='store_true')
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
        execute('candidate')


if __name__ == '__main__':
    main()
