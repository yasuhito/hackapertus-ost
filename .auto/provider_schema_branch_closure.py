#!/usr/bin/env python3
"""Exclusive fictional branch-closure experiment; preparation is entirely offline."""
import argparse
import copy
from pathlib import Path
import signal
import sys
import time

import provider_schema_probe as old
import provider_schema_probe_recovery as recovery

ROOT = old.ROOT
CONTROL = old.OUT / 'provider-schema-probe-branch-closure-v1-protocol.json'
JOB = old.OUT / 'provider-schema-probe-branch-closure-v1'
RESERVE, BUDGET, PHASE_SECONDS = 1800, 32768, 900
save = recovery.save
ARCHIVES = {str(ROOT / ('.auto/' + name + '.sh')):
            ROOT / ('.auto/protocol-archive/provider-branch-closure-pre-' + name + '.sh')
            for name in ('measure', 'checks')}
SOURCES = [ROOT / ('.auto/' + name) for name in (
    'provider_schema_branch_closure.py', 'test_provider_schema_branch_closure.py',
    'provider-schema-branch-closure-plan.md', 'measure.sh', 'checks.sh')]


def frames():
    rows = copy.deepcopy(old.frames())
    for frame in rows:
        if frame['arm'] == 'conditional':
            common = copy.deepcopy(frame['payload']['tools'][0]['function']['parameters'])
            del common['anyOf']
            neutral, nonneutral = copy.deepcopy(common), copy.deepcopy(common)
            neutral['properties']['label']['enum'] = [1]
            nonneutral['properties']['label']['enum'] = [0, 2]
            nonneutral['properties']['candidate_ids']['minItems'] = 1
            common['anyOf'] = [neutral, nonneutral]
            frame['payload']['tools'][0]['function']['parameters'] = common
        payload = frame['payload']
        old.require(len(old.encode(payload['messages'])) + len(old.encode(payload['tools'])) + 128
                    <= RESERVE - 256, 'INPUT_ESTIMATE_EXCEEDED')
        frame['payload_sha256'] = old.sha(old.encode(payload))
    return rows


def reference():
    """Validate both historical pinsets, relocating only the changed dispatchers."""
    original = recovery.original()  # Original dispatcher pins use original archives.
    frozen = old.load(recovery.CONTROL)
    for name, digest in frozen['sources'].items():
        path = ARCHIVES.get(name, Path(name))
        old.require(recovery.digests([path])[str(path)] == digest, 'RECOVERY_SOURCE_CHANGED')
    expected = recovery.protocol()
    expected['sources'] = frozen['sources']  # Individually verified above, no blanket bypass.
    old.require(frozen == expected, 'RECOVERY_PROTOCOL_CHANGED')
    report = old.load(recovery.JOB / 'report.json')
    old.require(report['protocol_sha256'] == old.sha(recovery.CONTROL.read_bytes()), 'REFERENCE_REPORT_CHANGED')
    actual = old.check(original, old.JOB)
    old.require(report['result'] == actual and actual['schema_contract_violations'] == 3,
                'REFERENCE_RESULT_CHANGED')
    return original, actual


def protocol():
    original, actual = reference()
    return dict(version=1, mode='provider_schema_branch_closure', metric='schema_contract_violations',
                origin=original['origin'], models=original['models'], frames=frames(),
                budget=BUDGET, reservation=RESERVE, phase_seconds=PHASE_SECONDS,
                call_seconds=60, socket_seconds=45, response_bytes=2_000_000,
                input_usage_cap=1000, output_usage_cap=256,
                sources={**old.pins(), **recovery.digests(recovery.SOURCES + SOURCES + list(ARCHIVES.values()))},
                reference=dict(control_sha256=old.sha(old.CONTROL.read_bytes()),
                    recovery_control_sha256=old.sha(recovery.CONTROL.read_bytes()),
                    artifacts=recovery.digests(sorted(old.JOB.iterdir()) + sorted(recovery.JOB.iterdir())),
                    frame_sha256=[old.sha(old.encode(f)) for f in original['frames']], result=actual))


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


def context():
    return dict(mode='provider_schema_branch_closure', candidate='',
                protocol_sha256=old.sha(CONTROL.read_bytes()),
                completed_sha256=old.sha((JOB / 'completed.json').read_bytes()))


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
        result = old.check(frozen, JOB)
        save(old.CONTEXT, context(), replace=True)
    else:
        old.require(old.load(old.CONTEXT) == context(), 'CONTEXT_CHANGED')
        result = old.check(frozen, JOB)
    # Stable run30 keys. Zero is reporting overhead only: this is not a recovery run.
    recovery.print_report(dict(result=result, recovery_wall_seconds=0))


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        print('PROBE_UNAVAILABLE: terminal failure, no retry or resume; primary not reported.', file=sys.stderr)
        sys.exit(1)
