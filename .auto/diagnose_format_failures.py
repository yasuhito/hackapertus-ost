#!/usr/bin/env python3
"""Gold-free cached PUBLIC60 structural audit. No inference or scoring."""
import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/diagnostics/public60-format'
JOBS = ['public60-v5-r1'] + [f'public60b-v5-r{i}' for i in range(2, 6)] + [f'public60b-v16-r{i}' for i in range(1, 6)]
SDK = '/home/yasuhito/.pi/agent/install/releases/1.1.0/node_modules/@earendil-works/pi-coding-agent'
CHILD = '/home/yasuhito/.pi/agent/npm/node_modules/@tintinweb/pi-subagents'


def load(path):
    return json.loads(path.read_text())


def trace(job, index):
    return hashlib.sha256(f'{job}:{index}'.encode()).hexdigest()[:12]


def runner():
    sys.path.insert(0, str(ROOT / 'track_2a/dev/format'))
    spec = importlib.util.spec_from_file_location('format_diagnosis_runner', ROOT / 'track_2a/dev/format/run_comparison.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def forbidden(*args, **kwargs):
    raise AssertionError('OFFLINE_NETWORK_OR_CREDENTIAL_ACCESS_FORBIDDEN')


def offline(r):
    stack = ExitStack()
    for obj, name in [(socket, 'socket'), (socket, 'create_connection'), (r.legacy.c, 'read_key'), (r, 'Transport'), (r.http.client, 'HTTPConnection'), (r.http.client, 'HTTPSConnection')]:
        stack.enter_context(patch.object(obj, name, forbidden))
    stack.enter_context(patch.dict(os.environ, {'PI_PACKAGE_ROOT': SDK, 'PI_SUBAGENTS_ROOT': CHILD, 'PYTHON': '/tmp/hackapertus-ost-contract/.venv/bin/python', 'PYTHONDONTWRITEBYTECODE': '1'}))
    return stack


def protected_paths():
    # Hash existing controls, phases, source, states and records, never evaluator data.
    base = ROOT / 'output/cscs'
    paths = set()
    for name in JOBS:
        job = base / name
        paths.update(job.glob('70b-*-case.json'))
        paths.update(job.glob('70b-*-parent-*.json'))
        paths.update(job.glob('70b-*-child-*.json'))
        paths.update(job / n for n in ('state.json', 'manifest.json'))
    for pattern in ('public60*-protocol.json', 'public60*-phase.json'):
        paths.update(base.glob(pattern))
    for directory in [ROOT / 'track_2a/src', ROOT / 'track_2a/dev/format']:
        paths.update(p for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for workroot in ('public60-workspaces', 'public60b-workspaces'):
        for directory in (base / workroot).glob('*/track_2a'):
            paths.update(p for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths.update(ROOT / '.auto' / n for n in ('public_validation.py', 'public_validation_continue.py'))
    return sorted(p for p in paths if p.is_file())


def snapshot():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected_paths()}


def shape(r, call, ids):
    raw = call['function']['arguments']
    result = {'function': call['function']['name'], 'characters': len(raw), 'bytes': len(raw.encode()), 'whitespace_only': not raw.strip(), 'ends_closing_brace': raw.rstrip().endswith('}')}
    try:
        args = r.submission.strict_json(raw)
    except json.JSONDecodeError as exc:
        result.update(parse='invalid_json', error_offset=exc.pos, json_error=exc.msg)
        return result
    except ValueError:
        result.update(parse='strict_json_rejected')
        return result
    result['parse'] = 'valid_json'
    if isinstance(args, dict):
        result['keys'] = sorted(k if k in ('label', 'candidate_ids', 'mode') else '<other>' for k in args)
        result['label_type'] = type(args.get('label')).__name__
        chosen = args.get('candidate_ids')
        if isinstance(chosen, list):
            strings = [s for s in chosen if isinstance(s, str)]
            result.update(id_count=len(chosen), duplicate_same_id=len(strings) != len(set(strings)), unknown_id_count=sum(s not in ids for s in strings))
    return result


def audit(r):
    counters = defaultdict(Counter)
    counters['at_cap'].update({f'{group}:{role}': 0 for group in ('success', 'failure') for role in ('parent', 'child')})
    failures, controls, selected = [], [], []
    for jobname in JOBS:
        job = ROOT / 'output/cscs' / jobname
        cases = [load(p) for p in sorted(job.glob('70b-*-case.json'))]
        manifest = load(job / 'manifest.json')
        requests = defaultdict(list)
        for path in list(job.glob('70b-*-parent-*.json')) + list(job.glob('70b-*-child-*.json')):
            record = load(path)
            requests[record['case_index']].append(record)
        for case in cases:
            index = case['case_index']
            group = 'success' if case['output_valid'] else 'failure'
            variant = 'v16' if 'v16' in jobname else 'v5'
            counters['cases'][variant + ':' + group] += 1
            counters[group + '_diagnostics'].update(case['diagnostics'])
            ids = set(manifest['frozen'][index]['candidate_ids'])
            seq = []
            for rec in sorted(requests[index], key=lambda x: x['started_unix_ms']):
                choice = rec['response']['choices'][0]
                reason = choice['finish_reason']
                cap = rec['usage']['completion_tokens'] == 256
                for key in ('all_finish', group + '_finish'):
                    counters[key][rec['role'] + ':' + reason] += 1
                if cap:
                    counters['at_cap'][group + ':' + rec['role']] += 1
                calls = [shape(r, c, ids) for c in choice['message'].get('tool_calls', [])]
                for call in calls:
                    counters[group + '_argument_parse'][call['parse']] += 1
                seq.append({'role': rec['role'], 'completion_number': rec['number'] + 1, 'finish_reason': reason, 'completion_tokens': rec['usage']['completion_tokens'], 'calls': calls})
            safe_events = [{k: event[k] for k in ('role', 'type', 'toolName', 'isError') if k in event} for event in case['sdk']['events']]
            data = {'trace': trace(jobname, index), 'variant': variant, 'diagnostics': case['diagnostics'], 'error': case['error'], 'counts': case['sdk']['counts'], 'sequence': seq, 'events': safe_events}
            if group == 'failure':
                failures.append(data)
                selected.append((jobname, index, case))
            elif case['diagnostics']:
                controls.append(data)
    assert sum(counters['cases'].values()) == 600
    assert sum(counters['all_finish'].values()) == 1884
    assert len(failures) == 19
    return {'counts': {k: dict(v) for k, v in counters.items()}, 'failures': failures, 'successful_diagnostic_controls': controls}, selected


def replay(r, jobname, index, expected, request_observations=None):
    job = ROOT / 'output/cscs' / jobname
    manifest = load(job / 'manifest.json')
    frozen = manifest['frozen'][index]
    # Pass only permitted source-only fields. Never display them or write fixtures.
    item = {k: frozen[k] for k in ('case', 'pages', 'messages', 'candidate_ids')}
    assert not any(k in item['case'] for k in ('expected', 'gold', 'label'))
    records = {}
    for role in ('parent', 'child'):
        for p in job.glob(f'70b-{index:02d}-{role}-*.json'):
            rec = load(p)
            records[(role, rec['number'])] = rec
    used = []
    def cached(role, number, payload):
        rec = records[(role, number)]
        assert payload['model'] == rec.get('request_model', rec['model'])
        if request_observations is not None:
            messages = payload.get('messages', [])
            text = json.dumps(messages, ensure_ascii=False)
            request_observations.append({
                'role': role, 'completion_number': number + 1,
                'messages_hash': digest(messages),
                'generic_code_present': 'INVALID_TOOL_JSON' in text,
                'invalid_schema_marker_present': 'invalid_schema' in text,
                'underlying_fixed_message_present': 'supporting span required' in text,
                'tool_message_count': sum(m.get('role') == 'tool' for m in messages),
            })
        used.append((role, number))
        return rec['response']
    with offline(r):
        args, diagnostics, sdk = r.run_b(item, expected['model'], cached, seconds=45, isolation_guard=True, strategy=manifest['strategy'])
    assert args is None, 'Cached failure unexpectedly accepted'
    assert diagnostics == expected['diagnostics'], 'Cached diagnostics diverged'
    assert sdk['counts'] == expected['sdk']['counts']
    assert len(used) == len(records)
    return {'trace': trace(jobname, index), 'error': 'NO_ACCEPTED_SUBMIT', 'diagnostics': diagnostics, 'counts': sdk['counts'], 'cached_requests': len(used)}


# Only exact, source-defined fixed messages may leave the diagnostic process.
SAFE_ERRORS = {
    'TOOL_SCHEMA': 'TOOL_SCHEMA', 'LABEL_SCHEMA': 'LABEL_SCHEMA',
    'IDS_SCHEMA': 'IDS_SCHEMA', 'DUPLICATE_ID': 'DUPLICATE_ID',
    'UNKNOWN_ID': 'UNKNOWN_ID',
    'supporting span required': 'SUPPORTING_SPAN_REQUIRED',
    'source span mismatch': 'SOURCE_SPAN_MISMATCH',
    'document evidence exceeds 5000 characters': 'DOCUMENT_TOO_LONG',
    'citation context unavailable or exceeds 5000 characters': 'CONTEXT_UNAVAILABLE_OR_TOO_LONG',
    'citation context exceeds five evidence items': 'CONTEXT_TOO_MANY_ITEMS',
    'supporting evidence required': 'SUPPORTING_EVIDENCE_REQUIRED',
}
METRICS = {'input_tokens': 0, 'output_tokens': 0, 'inference_time_ms': 0}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class Instrument:
    """Runtime wrappers only. Preserve return values and re-raise identical exceptions."""
    def __init__(self, r):
        self.r, self.events, self.stack = r, [], ExitStack()
        self.current = None

    def __enter__(self):
        for name in ('restore', 'validate', 'validate_prediction', 'assemble_tool'):
            original = getattr(self.r.submission, name)
            def wrapped(*args, _name=name, _original=original, **kwargs):
                if _name == 'assemble_tool':
                    event = {'argument_hash': digest(args[0]), 'stage': 'accepted', 'code': 'ACCEPTED'}
                    self.events.append(event)
                    previous, self.current = self.current, event
                try:
                    return _original(*args, **kwargs)
                except (ValueError, TypeError, KeyError) as exc:
                    if self.current is not None and self.current['stage'] == 'accepted':
                        self.current.update(stage=_name, exception=type(exc).__name__,
                                            code=SAFE_ERRORS.get(str(exc), 'UNMAPPED_FIXED_ERROR'))
                    raise
                finally:
                    if _name == 'assemble_tool':
                        self.current = previous
            self.stack.enter_context(patch.object(self.r.submission, name, wrapped))
        return self

    def __exit__(self, *exc):
        return self.stack.__exit__(*exc)


def direct_probe(r, raw, item):
    with Instrument(r) as instrument:
        try:
            args = r.submission.strict_json(raw)
        except (ValueError, TypeError):
            return {'stage': 'jsondecode', 'code': 'STRICT_JSON_REJECTED'}
        try:
            r.submission.assemble_tool(args, item['case'], item['pages'], METRICS)
        except (ValueError, TypeError, KeyError):
            pass
    event = instrument.events[0]
    event.update(raw_hash=hashlib.sha256(raw.encode()).hexdigest(),
                 label_type=type(args.get('label')).__name__ if isinstance(args, dict) else 'not_dict')
    if isinstance(args, dict):
        event['nonneutral'] = args.get('label') != 1
        ids = args.get('candidate_ids')
        event['ids_empty'] = ids == []
    return event


def probes(r):
    counts = defaultdict(Counter)
    sequences = []
    for jobname in JOBS:
        job = ROOT / 'output/cscs' / jobname
        manifest = load(job / 'manifest.json')
        cases = {c['case_index']: c for c in (load(p) for p in job.glob('70b-*-case.json'))}
        records = defaultdict(list)
        for role in ('parent', 'child'):
            for path in job.glob(f'70b-*-{role}-*.json'):
                rec = load(path)
                records[rec['case_index']].append(rec)
        for index, rows in records.items():
            case = cases[index]
            group = 'success' if case['output_valid'] else 'failure'
            item = manifest['frozen'][index]
            seq = []
            seen = defaultdict(set)
            for rec in sorted(rows, key=lambda x: x['started_unix_ms']):
                for call in rec['response']['choices'][0]['message'].get('tool_calls', []):
                    counts['functions'][call['function']['name']] += 1
                    if call['function']['name'] != 'submit':
                        continue
                    event = direct_probe(r, call['function']['arguments'], item)
                    key = event['argument_hash']
                    event.update(role=rec['role'], completion_number=rec['number'] + 1,
                                 same_role_repeated_argument=key in seen[rec['role']])
                    seen[rec['role']].add(key)
                    counts[group + '_submit_codes'][event['code']] += 1
                    counts[group + '_stages'][event['stage']] += 1
                    seq.append(event)
            if not case['output_valid'] or case['diagnostics']:
                sequences.append({'trace': trace(jobname, index), 'group': group,
                                  'diagnostics': case['diagnostics'], 'sequence': seq})
    return {'counts': {k: dict(v) for k, v in counts.items()}, 'sequences': sequences}


def probe_main(r, before, artifact):
    if Path(artifact).name != artifact or not artifact.endswith('.json'):
        raise ValueError('PROBE_ARTIFACT_MUST_BE_JSON_BASENAME')
    target = OUT / artifact
    if target.exists():
        raise FileExistsError('Choose a new --probe-artifact; initial evidence is preserved')
    result = probes(r)
    # Cached failed cases only; runtime observers are the sole changed variable.
    _, chosen = audit(r)
    result['sdk_replays'] = []
    for entry in chosen:
        with Instrument(r) as instrument:
            observations = []
            replay_result = replay(r, *entry, request_observations=observations)
        replay_result['request_observations'] = observations
        replay_result['assembler_events'] = instrument.events
        direct = next(x for x in result['sequences'] if x['trace'] == replay_result['trace'])
        assert [(e['argument_hash'], e['code']) for e in instrument.events] == [
            (e['argument_hash'], e['code']) for e in direct['sequence']]
        replay_result['direct_vs_prebridge_exact_hash_and_error_equal'] = True
        result['sdk_replays'].append(replay_result)
    result['repair_comparisons'] = {}
    for group in ('failure', 'success'):
        pairs = []
        for row in result['sequences']:
            if row['group'] != group:
                continue
            prior = {}
            for event in row['sequence']:
                if event['role'] in prior:
                    old = prior[event['role']]
                    pairs.append({
                        'raw_equal': event['raw_hash'] == old['raw_hash'],
                        'parsed_equal': event['argument_hash'] == old['argument_hash'],
                        'same_violation': event['code'] == old['code'],
                        'corrected_to_accepted': event['code'] == 'ACCEPTED' and old['code'] != 'ACCEPTED',
                    })
                prior[event['role']] = event
        result['repair_comparisons'][group] = {
            'same_role_pairs': len(pairs),
            **{k: sum(pair[k] for pair in pairs) for k in pairs[0]},
        }
    assert snapshot() == before == load(OUT / 'integrity.json')
    assert len(before) == 3348
    result['protected_files'] = len(before)
    result['protected_sha256_unchanged'] = True
    with target.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps(result['counts'], sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--replay', action='store_true')
    parser.add_argument('--probes', action='store_true')
    parser.add_argument('--probe-artifact', default='validation-probes-all-failures.json')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    before = snapshot()
    r = runner()
    if args.probes:
        probe_main(r, before, args.probe_artifact)
        return
    summary, failures = audit(r)
    replays = []
    if args.replay:
        invalid = [x for x in failures if 'INVALID_TOOL_JSON' in x[2]['diagnostics']][:2]
        duplicate = [x for x in failures if 'DUPLICATE_ID' in x[2]['diagnostics']][:1]
        for entry in invalid + duplicate:
            result = replay(r, *entry)
            replays.append(result)
            print(json.dumps(result, sort_keys=True))
    assert snapshot() == before, 'Protected files changed'
    summary.update(replays=replays, protected_files=len(before), protected_sha256_unchanged=True)
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (OUT / 'integrity.json').write_text(json.dumps(before, indent=2) + '\n')
    print(json.dumps(summary['counts'], sort_keys=True))


if __name__ == '__main__':
    main()
