#!/usr/bin/env python3
"""Prospective fictional edge workload. Preparation and checking never use an API."""
import argparse
import copy
from pathlib import Path
import signal
import sys
import time

import provider_schema_probe as old
import provider_schema_probe_recovery as recovery

ROOT = old.ROOT
CONTROL = old.OUT / 'provider-schema-edge-probe-v1-protocol.json'
JOB = old.OUT / 'provider-schema-edge-probe-v1'
RESERVE, BUDGET, PHASE_SECONDS = 4096, 32768, 900
METRIC = 'edge_schema_contract_violations'
save = recovery.save
SOURCES = [ROOT / '.auto' / name for name in (
    'provider_schema_edge_probe.py', 'test_provider_schema_edge_probe.py',
    'provider-schema-edge-probe-plan.md', 'provider_schema_probe_recovery.py',
    'test_provider_schema_probe_recovery.py')]


def pages():
    return ['Fictional marker ' + letter + '.' for letter in 'ABCDEF']


def frames():
    r = old.root_runner()
    spans = r.candidates(pages(), False)
    ids = [s['span_id'] for s in spans]
    old.require(len(ids) == len(set(ids)) == 6, 'CANDIDATE_ARITY')
    rows = []
    for model in r.MODELS:
        for label, selected in ((1, ids[:2]), (0, ids[:5]), (2, ids[-5:])):
            requested = dict(label=label, candidate_ids=selected)
            messages = [dict(role='system', content=old.SYSTEM), dict(role='user', content=old.encode(
                dict(source_spans=spans, requested_arguments=requested)).decode())]
            for arm in ('simple', 'complete_branch'):
                common = r.schemas(ids, child=True)[0]['function']['parameters']
                if arm == 'complete_branch':
                    neutral, nonneutral = copy.deepcopy(common), copy.deepcopy(common)
                    neutral['properties']['label']['enum'] = [1]
                    nonneutral['properties']['label']['enum'] = [0, 2]
                    nonneutral['properties']['candidate_ids']['minItems'] = 1
                    common['anyOf'] = [neutral, nonneutral]
                payload = dict(model=model, messages=messages, temperature=0, max_tokens=256,
                    stream=False, tools=[{'type': 'function', 'function': {
                        'name': 'submit', 'description': 'Emit the requested probe arguments.',
                        'parameters': common}}],
                    tool_choice={'type': 'function', 'function': {'name': 'submit'}})
                old.require(len(old.encode(messages)) + len(old.encode(payload['tools'])) + 128
                            <= RESERVE - 256, 'INPUT_ESTIMATE_EXCEEDED')
                rows.append(dict(index=len(rows), model=model, arm=arm, requested=requested,
                                 payload=payload, payload_sha256=old.sha(old.encode(payload))))
    old.require(len(rows) == len({f['payload_sha256'] for f in rows}) == 12, 'FRAME_ARITY')
    return rows


def protocol():
    r = old.root_runner()
    # Fresh pinset only. No old controls, captures, reference verification or replay.
    sourcepack = sorted((ROOT / 'track_2a/src').glob('*.py'))
    sourcepack += sorted(p for p in (ROOT / 'track_2a/dev/format').iterdir()
                         if p.is_file() and p.suffix in ('.py', '.mjs', '.ts', '.json'))
    return dict(version=1, mode='provider_schema_edge', metric=METRIC,
        origin=r.legacy.c.BASE, models=list(r.MODELS), frames=frames(),
        budget=BUDGET, reservation=RESERVE, phase_seconds=PHASE_SECONDS,
        call_seconds=60, socket_seconds=45, response_bytes=2_000_000,
        input_usage_cap=1000, output_usage_cap=256,
        sources={**old.pins(), **recovery.digests(SOURCES + sourcepack)})


def verify():
    frozen = old.load(CONTROL)
    old.require(frozen == protocol(), 'PROTOCOL_OR_SOURCE_CHANGED')
    return frozen


def run(p, job, transport):
    job.mkdir(mode=0o700)
    old.syncdir(job.parent)
    start, spent, digests = time.monotonic(), 0, []
    try:
        save(job / 'protocol.json', p)
        for f in p['frames']:
            old.require(time.monotonic() - start < PHASE_SECONDS - 60, 'PHASE_WALL_LIMIT')
            old.require(BUDGET - spent >= RESERVE, 'TOKEN_RESERVATION_REFUSED')
            request_path = job / f"{f['index']:02d}-request.json"
            save(request_path, f)
            save(job / 'inflight.json', dict(index=f['index'], reserved=RESERVE))
            previous = signal.signal(signal.SIGALRM, old.deadline)
            timer = signal.setitimer(signal.ITIMER_REAL, 60)
            before = time.monotonic()
            try:
                status, raw = transport.request(f['payload'])
            finally:
                signal.setitimer(signal.ITIMER_REAL, *timer)
                signal.signal(signal.SIGALRM, previous)
            capture = dict(index=f['index'], request_sha256=old.sha(request_path.read_bytes()),
                           payload_sha256=f['payload_sha256'], status=status, raw=raw,
                           wall_seconds=time.monotonic() - before)
            capture_path = job / f"{f['index']:02d}-capture.json"
            save(capture_path, capture)
            old.require(status == 200, 'HTTP_FAILURE_NO_RETRY')
            measured = old.score(f, old.checked_response(f, raw))
            spent += measured['usage']['total_tokens']
            old.require(spent <= BUDGET, 'TOKEN_BUDGET_EXCEEDED')
            digests.append(old.sha(capture_path.read_bytes()))
            (job / 'inflight.json').unlink()
            old.syncdir(job)
        save(job / 'completed.json', dict(capture_sha256=digests, wall_seconds=time.monotonic()-start))
    except BaseException:
        save(job / 'STOP.json', {'status': 'terminal_unavailable', 'primary': None})
        raise


def check(p, job):
    # Reuse the full native independent scorer and immutable capture checker.
    result = old.check(p, job)
    result[METRIC] = result.pop('schema_contract_violations')
    # Preserve old exact-copy semantics, but additionally report all mismatches,
    # including malformed/noncompliant arguments, without masking them.
    result['all_exact_copy_mismatches'] = 0
    for frame in p['frames']:
        capture = old.load(job / f"{frame['index']:02d}-capture.json")
        response = old.checked_response(frame, capture['raw'])
        measured = old.score(frame, response)
        try:
            arguments = old.strict(response['choices'][0]['message']['tool_calls'][0]['function']['arguments'])
        except (KeyError, IndexError, TypeError, ValueError):
            arguments = None
        mismatch = int(arguments != frame['requested'])
        result['all_exact_copy_mismatches'] += mismatch
        side = result['per_model_arm'][frame['model'] + '/' + frame['arm']]
        side['all_exact_copy_mismatches'] = side.get('all_exact_copy_mismatches', 0) + mismatch
        side['request_wall_seconds'] = side.get('request_wall_seconds', 0) + capture['wall_seconds']
        for name, value in measured['usage'].items():
            side[name] = side.get(name, 0) + value
    return result


def context():
    return dict(mode='provider_schema_edge', candidate='',
                protocol_sha256=old.sha(CONTROL.read_bytes()),
                completed_sha256=old.sha((JOB / 'completed.json').read_bytes()))


def print_result(result):
    print(old.encode(result).decode())
    for key, value in result.items():
        if key != 'per_model_arm':
            print('METRIC ' + key + '=' + str(value))
    for side, values in result['per_model_arm'].items():
        model, arm = side.rsplit('/', 1)
        prefix = ('model70b' if model.endswith('-70B') else 'model8b') + '_' + arm + '_'
        for key, value in values.items():
            print('METRIC ' + prefix + key + '=' + str(value))
    print('METRIC requests=' + str(sum(s['requests'] for s in result['per_model_arm'].values())))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    for flag in ('prepare', 'execute', 'check'):
        group.add_argument('--' + flag, action='store_true')
    args = parser.parse_args()
    if args.prepare:
        old.require(not JOB.exists(), 'JOB_ALREADY_EXISTS')
        save(CONTROL, protocol())
        print('Prepared offline. protocol_sha256=' + old.sha(CONTROL.read_bytes()))
        return
    frozen = verify()
    if args.execute:
        run(frozen, JOB, old.Transport(frozen))
        result = check(frozen, JOB)
        save(old.CONTEXT, context(), replace=True)
    else:
        old.require(old.load(old.CONTEXT) == context(), 'CONTEXT_CHANGED')
        result = check(frozen, JOB)
    print_result(result)


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        print('PROBE_UNAVAILABLE: terminal failure, no retry or resume; primary not reported.', file=sys.stderr)
        sys.exit(1)
