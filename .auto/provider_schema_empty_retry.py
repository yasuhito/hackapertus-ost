#!/usr/bin/env python3
"""Future-only bounded HTTP 500 retries. Prepare/check are offline; never resume."""
import argparse
import math
import signal
import sys
import time

import provider_schema_empty_source as empty
import provider_schema_probe as old
import provider_schema_probe_recovery as recovery

ROOT = old.ROOT
CONTROL = old.OUT / 'provider-schema-empty-retry-v1-protocol.json'
JOB = old.OUT / 'provider-schema-empty-retry-v1'
MODE = 'provider_schema_empty_retry'
POLICY = dict(max_attempts=5, retry_statuses=[500], delays=[2, 4, 8, 16],
              logical_requests=12, max_physical_posts=60, reservation=4096,
              budget=32768, call_seconds=60, phase_seconds=900, socket_seconds=45,
              input_usage_cap=1000, output_usage_cap=256,
              unknown_usage_retry_authorized=True)
save = recovery.save


def protocol():
    p = empty.protocol()
    p.update(mode=MODE, retry_policy=POLICY.copy(), policy_sha256=old.sha(old.encode(POLICY)))
    names = ['provider_schema_empty_retry.py', 'test_provider_schema_empty_retry.py',
             'provider-schema-empty-retry-plan.md',
             'protocol-archive/provider-empty-retry-pre-measure.sh',
             'protocol-archive/provider-empty-retry-pre-checks.sh']
    p['sources'].update(recovery.digests([ROOT / '.auto' / n for n in names]))
    return p


def shape(p):
    old.require(p['mode'] == MODE and old.encode(p['retry_policy']) == old.encode(POLICY) and
                p['policy_sha256'] == old.sha(old.encode(POLICY)), 'RETRY_POLICY_CHANGED')
    old.require(old.encode(p['frames']) == old.encode(empty.frames()), 'LOGICAL_SHAPE_CHANGED')
    for key in ('budget', 'reservation', 'phase_seconds', 'call_seconds', 'socket_seconds',
                'input_usage_cap', 'output_usage_cap'):
        old.require(type(p[key]) is int and p[key] == POLICY[key], 'LIMIT_CHANGED')


def verify():
    p = old.load(CONTROL)
    old.require(old.encode(p) == old.encode(protocol()), 'PROTOCOL_OR_SOURCE_CHANGED')
    shape(p)
    return p


def finite(value, maximum):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= maximum


def preflight(state, logical_elapsed, phase_elapsed, wait=0):
    old.require(state['physical_posts'] < POLICY['max_physical_posts'], 'POST_CAP')
    old.require(state['charged_tokens'] + 4096 <= 32768, 'TOKEN_RESERVATION_REFUSED')
    old.require(logical_elapsed + wait < 60 and phase_elapsed + wait < 900,
                'WAIT_DEADLINE_REFUSED' if wait else 'WALL_LIMIT')


def run(p, job, *, client_factory=None, clock=time.monotonic, sleep=time.sleep):
    shape(p)
    factory = client_factory or old.Transport
    job.mkdir(mode=0o700)  # permanent exclusive identity, even on terminal failure
    old.syncdir(job.parent)
    start = clock()
    state = dict(physical_posts=0, known_success_tokens=0, unknown_usage_count=0,
                 reserved_budget_charge=0, charged_tokens=0)
    trace = []
    try:
        save(job / 'protocol.json', p)
        save(job / 'budget.json', state)
        for f in p['frames']:
            logical_start = clock()
            old.require(logical_start - start < 900, 'PHASE_WALL_LIMIT')
            save(job / 'inflight.json', dict(index=f['index']))
            previous = signal.signal(signal.SIGALRM, old.deadline)
            timer = signal.setitimer(signal.ITIMER_REAL, min(60, 900 - (logical_start-start)))
            try:
                for number in range(1, POLICY['max_attempts'] + 1):
                    preflight(state, clock()-logical_start, clock()-start)
                    attempt = job / f"{f['index']:02d}-{number}-attempt"
                    attempt.mkdir(mode=0o700)
                    old.syncdir(job)
                    identity = dict(index=f['index'], attempt=number,
                        physical_post=state['physical_posts'] + 1,
                        payload_sha256=f['payload_sha256'], reservation=4096,
                        charged_before=state['charged_tokens'],
                        logical_elapsed=clock()-logical_start, phase_elapsed=clock()-start,
                        wait_before=0 if number == 1 else POLICY['delays'][number-2])
                    save(attempt / 'request.json', dict(identity=identity, frame=f))
                    state['physical_posts'] += 1
                    state['unknown_usage_count'] += 1
                    state['reserved_budget_charge'] += 4096
                    state['charged_tokens'] += 4096
                    save(job / 'budget.json', state, replace=True)
                    # All durable reservation writes precede client construction and POST.
                    status, raw = None, None
                    try:
                        old.require(clock()-logical_start < 60 and clock()-start < 900, 'WALL_LIMIT')
                        status, raw = factory(p).request(f['payload'])  # fresh strict allowlist per POST
                    except BaseException:
                        save(attempt / 'capture.json', dict(status=None, raw=None,
                            actual_usage=None, logical_elapsed=clock()-logical_start))
                        raise
                    capture = dict(status=status, raw=raw, actual_usage=None,
                                   logical_elapsed=clock()-logical_start)
                    # Raw HTTP body is persisted before parsing or any retry decision.
                    save(attempt / 'capture.json', capture)
                    old.require(clock()-logical_start <= 60 and clock()-start <= 900, 'WALL_LIMIT')
                    known = None
                    if status == 200:
                        known = old.usage(old.checked_response(f, raw))
                        state['unknown_usage_count'] -= 1
                        state['reserved_budget_charge'] -= 4096
                        state['known_success_tokens'] += known['total_tokens']
                        state['charged_tokens'] += known['total_tokens'] - 4096
                        save(job / 'budget.json', state, replace=True)
                    save(attempt / 'result.json', dict(actual_usage=known))
                    trace.append(dict(index=f['index'], attempt=number,
                        files={n: old.sha((attempt / n).read_bytes())
                               for n in ('request.json', 'capture.json', 'result.json')}))
                    if status == 200:
                        break
                    old.require(status == 500 and number < POLICY['max_attempts'], 'HTTP_TERMINAL')
                    wait = POLICY['delays'][number-1]
                    preflight(state, clock()-logical_start, clock()-start, wait)
                    sleep(wait)
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, previous)
                if timer[0] or timer[1]:
                    signal.setitimer(signal.ITIMER_REAL, *timer)
            (job / 'inflight.json').unlink()
            old.syncdir(job)
        old.require(clock()-start <= 900, 'PHASE_WALL_LIMIT')
        save(job / 'completed.json', dict(trace=trace, wall_seconds=clock()-start))
    except BaseException:
        save(job / 'STOP.json', dict(status='terminal_unavailable', primary=None))
        raise


def check(p, job):
    shape(p)
    old.require(not any((job / n).exists() for n in ('STOP.json', 'inflight.json')), 'TERMINAL_OR_INFLIGHT')
    old.require(old.encode(old.load(job / 'protocol.json')) == old.encode(p), 'JOB_PROTOCOL_CHANGED')
    done = old.load(job / 'completed.json')
    old.require(finite(done['wall_seconds'], 900), 'PHASE_WALL_INVALID')
    trace = done['trace']
    old.require(12 <= len(trace) <= POLICY['max_physical_posts'] and len(list(job.glob('*-attempt'))) == len(trace), 'TRACE_ARITY')
    totals = dict(logical_count=0, physical_posts=0, retry_count=0, unknown_usage_count=0,
        known_success_tokens=0, reserved_budget_charge=0, charged_tokens=0,
        assembler_violations=0, native_schema_violations=0, proposal_mismatches=0,
        truncations=0, per_model_arm={}, observations=[], phase_wall_seconds=done['wall_seconds'])
    cursor, last_phase = 0, 0
    for f in p['frames']:
        side = totals['per_model_arm'].setdefault(f['model'] + '/' + f['arm'],
            dict(logical_count=0, physical_posts=0, retry_count=0, unknown_usage_count=0,
                 known_success_tokens=0, reserved_budget_charge=0, assembler_violations=0))
        prior_elapsed = 0
        for number in range(1, POLICY['max_attempts'] + 1):
            old.require(cursor < len(trace), 'INCOMPLETE_TRACE')
            entry = trace[cursor]
            old.require(entry['index'] == f['index'] and entry['attempt'] == number, 'TRACE_ORDER')
            attempt = job / f"{f['index']:02d}-{number}-attempt"
            old.require(not attempt.is_symlink() and sorted(x.name for x in attempt.iterdir()) ==
                        ['capture.json', 'request.json', 'result.json'], 'ATTEMPT_FILES')
            old.require(set(entry['files']) == {'request.json', 'capture.json', 'result.json'}, 'TRACE_FILES')
            for name, digest in entry['files'].items():
                old.require(old.sha((attempt/name).read_bytes()) == digest, 'ATTEMPT_CHANGED')
            request, c, result = [old.load(attempt/n) for n in ('request.json', 'capture.json', 'result.json')]
            ident = request['identity']
            wait = 0 if number == 1 else POLICY['delays'][number-2]
            expected = dict(index=f['index'], attempt=number, physical_post=cursor+1,
                payload_sha256=f['payload_sha256'], reservation=4096,
                charged_before=totals['charged_tokens'], logical_elapsed=ident['logical_elapsed'],
                phase_elapsed=ident['phase_elapsed'], wait_before=wait)
            old.require(old.encode(request) == old.encode(dict(identity=expected, frame=f)), 'REQUEST_CHANGED')
            old.require(finite(ident['logical_elapsed'], 60) and finite(c['logical_elapsed'], 60)
                and prior_elapsed + wait <= ident['logical_elapsed'] <= c['logical_elapsed']
                and finite(ident['phase_elapsed'], 900)
                and last_phase <= ident['phase_elapsed'] <= done['wall_seconds'], 'ATTEMPT_WALL_INVALID')
            old.require(totals['charged_tokens'] + 4096 <= 32768, 'TOKEN_RESERVATION_REFUSED')
            old.require(c['actual_usage'] is None and type(c['status']) is int and type(c['raw']) is str,
                        'CAPTURE_SHAPE')
            cursor += 1
            totals['physical_posts'] += 1
            side['physical_posts'] += 1
            totals['retry_count'] += int(number > 1)
            side['retry_count'] += int(number > 1)
            prior_elapsed, last_phase = c['logical_elapsed'], ident['phase_elapsed']
            if c['status'] == 500:
                old.require(number < POLICY['max_attempts'] and result == dict(actual_usage=None), 'HTTP_TERMINAL')
                for group in (totals, side):
                    group['unknown_usage_count'] += 1
                    group['reserved_budget_charge'] += 4096
                totals['charged_tokens'] += 4096
                continue
            old.require(c['status'] == 200, 'HTTP_TERMINAL')
            measured = empty.score(f, old.checked_response(f, c['raw']))
            known = measured.pop('usage')
            old.require(result == dict(actual_usage=known), 'USAGE_CHANGED')
            for group in (totals, side):
                group['logical_count'] += 1
                group['known_success_tokens'] += known['total_tokens']
            totals['charged_tokens'] += known['total_tokens']
            for key, value in measured.items():
                totals[key] += value
                side[key] = side.get(key, 0) + value
            totals['observations'].append(dict(index=f['index'], model=f['model'], arm=f['arm'], **measured))
            break
    old.require(cursor == len(trace) and totals['logical_count'] == 12, 'TRACE_ARITY')
    budget = {k: totals[k] for k in ('physical_posts', 'known_success_tokens', 'unknown_usage_count',
                                   'reserved_budget_charge', 'charged_tokens')}
    old.require(old.load(job/'budget.json') == budget, 'BUDGET_CHANGED')
    totals['full_usage_known'] = totals['unknown_usage_count'] == 0
    totals['full_total_tokens'] = totals['known_success_tokens'] if totals['full_usage_known'] else None
    totals['financial_cost'] = None
    totals[empty.METRIC] = sum(v['assembler_violations'] for k, v in totals['per_model_arm'].items()
                              if k.endswith('/empty_specialized'))
    totals['control_assembler_violations'] = totals['assembler_violations'] - totals[empty.METRIC]
    return totals


def context():
    return dict(mode=MODE, candidate='', protocol_sha256=old.sha(CONTROL.read_bytes()),
                report_sha256=old.sha((JOB/'report.json').read_bytes()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    for flag in ('prepare', 'execute', 'check'):
        group.add_argument('--'+flag, action='store_true')
    args = parser.parse_args()
    if args.prepare:
        old.require(not JOB.exists(), 'JOB_ALREADY_EXISTS')
        save(CONTROL, protocol())
        print('Prepared offline. protocol_sha256=' + old.sha(CONTROL.read_bytes()))
        return
    p = verify()
    if args.execute:
        run(p, JOB)
        try:
            result = check(p, JOB)
            save(JOB/'report.json', dict(protocol_sha256=old.sha(CONTROL.read_bytes()), result=result))
            save(old.CONTEXT, context(), replace=True)
        except BaseException:
            save(JOB/'STOP.json', dict(status='terminal_unavailable', primary=None))
            raise
    else:
        old.require(old.load(old.CONTEXT) == context(), 'CONTEXT_CHANGED')
        result = check(p, JOB)
        old.require(old.encode(old.load(JOB/'report.json')) == old.encode(dict(
            protocol_sha256=old.sha(CONTROL.read_bytes()), result=result)), 'REPORT_CHANGED')
    empty.print_result(result)


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        print('PROBE_UNAVAILABLE: terminal failure; no resume; primary not reported.', file=sys.stderr)
        sys.exit(1)
