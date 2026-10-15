#!/usr/bin/env python3
"""One prospective paired uniqueItems batch; candidate reporting never performs inference."""
import argparse
import copy
import math
from pathlib import Path
import signal
import sys
import time

import provider_schema_empty_source as empty
import provider_schema_probe as old
import provider_schema_probe_recovery as recovery

ROOT = old.ROOT
CONTROL = old.OUT / 'provider-schema-unique-ids-v1-protocol.json'
JOB = old.OUT / 'provider-schema-unique-ids-v1'
MODE = 'provider_schema_unique_ids'
METRIC = 'unique_id_assembler_violations'
PAGES = ['Fictional amber marker.', 'Fictional blue marker.']
ARMS = ('control', 'unique')
POLICY = dict(max_attempts=5, retry_statuses=[500], delays=[2, 4, 8, 16],
              logical_requests=12, max_physical_posts=60, reservation=4096,
              budget=32768, call_seconds=60, phase_seconds=900, socket_seconds=45,
              input_usage_cap=1000, output_usage_cap=256,
              unknown_usage_retry_authorized=True)
save = recovery.save
LEDGER = ROOT / '.auto/protocol-archive/provider-unique-immutable-sha256.json'


def schemas(ids):
    common = old.root_runner().schemas(ids, child=True)[0]['function']['parameters']
    neutral, supported = copy.deepcopy(common), copy.deepcopy(common)
    neutral['properties']['label']['enum'] = [1]
    supported['properties']['label']['enum'] = [0, 2]
    supported['properties']['candidate_ids']['minItems'] = 1
    common['anyOf'] = [neutral, supported]
    unique = copy.deepcopy(common)
    for schema in [unique] + unique['anyOf']:
        schema['properties']['candidate_ids']['uniqueItems'] = True
    return common, unique


def frames():
    r = old.root_runner()
    spans = r.candidates(PAGES, False)
    ids = [s['span_id'] for s in spans]
    old.require(len(ids) == 2 and all(len(x) == 36 for x in ids), 'SOURCE_IDS_CHANGED')
    parameters = schemas(ids)
    rows = []
    for model in r.MODELS:
        for label, selected in ((0, [ids[0], ids[0]]), (2, [ids[1], ids[1]]), (1, ids)):
            requested = dict(label=label, candidate_ids=selected)
            messages = [dict(role='system', content=empty.SYSTEM), dict(role='user', content=old.encode(
                dict(source_spans=spans, requested_arguments=requested)).decode())]
            for arm, schema in zip(ARMS, parameters):
                payload = dict(model=model, messages=copy.deepcopy(messages), temperature=0,
                    max_tokens=256, stream=False, tools=[dict(type='function', function=dict(
                        name='submit', description=empty.DESCRIPTION, parameters=copy.deepcopy(schema)))],
                    tool_choice=dict(type='function', function=dict(name='submit')))
                old.require(old.encode(payload).isascii(), 'NON_ASCII_REQUEST')
                old.require(len(old.encode(payload)) <= 4096 - 256, 'INPUT_ESTIMATE_EXCEEDED')
                rows.append(dict(index=len(rows), model=model, arm=arm, requested=copy.deepcopy(requested),
                    payload=payload, payload_sha256=old.sha(old.encode(payload))))
    old.require(len(rows) == len({f['payload_sha256'] for f in rows}) == 12, 'FRAME_ARITY')
    return rows


def audit():
    for name, digest in old.load(LEDGER).items():
        old.require(old.sha((ROOT / name).read_bytes()) == digest, 'HISTORICAL_ARTIFACT_CHANGED')
    # Check original Root/runtime pins against their original source bytes. Only
    # dispatcher relocation is allowed, matched by exact archived digest.
    original = old.load(old.CONTROL)
    for name, digest in original['sources'].items():
        if name in (str(ROOT / '.auto/measure.sh'), str(ROOT / '.auto/checks.sh')):
            archived = list((ROOT / '.auto/protocol-archive').glob('*.sh'))
            old.require(any(old.sha(p.read_bytes()) == digest for p in archived), 'ARCHIVE_CHANGED')
        else:
            old.require(old.sha(Path(name).read_bytes()) == digest, 'ORIGINAL_SOURCE_CHANGED')


def protocol():
    audit()
    p = empty.protocol()
    names = ['provider_schema_unique_ids.py', 'test_provider_schema_unique_ids.py',
             'provider-schema-unique-ids-plan.md', 'provider_schema_branch_closure.py',
             'provider_schema_empty_retry.py', 'test_provider_schema_empty_retry.py',
             'protocol-archive/provider-unique-pre-measure.sh',
             'protocol-archive/provider-unique-pre-checks.sh',
             'protocol-archive/provider-unique-immutable-sha256.json']
    p.update(mode=MODE, metric=METRIC, frames=frames(), retry_policy=copy.deepcopy(POLICY),
        policy_sha256=old.sha(old.encode(POLICY)),
        reporting_policy=dict(batch='prospective_paired_once', baseline_arm='control',
            candidate_arm='unique', candidate_new_api_calls=0, shared_cost_counted_once=True))
    p['sources'].update(recovery.digests([ROOT / '.auto' / n for n in names]))
    return p


def shape(p):
    old.require(p['mode'] == MODE and old.encode(p['retry_policy']) == old.encode(POLICY) and
                p['policy_sha256'] == old.sha(old.encode(POLICY)), 'RETRY_POLICY_CHANGED')
    old.require(old.encode(p['frames']) == old.encode(frames()), 'LOGICAL_SHAPE_CHANGED')
    for key in ('budget', 'reservation', 'phase_seconds', 'call_seconds', 'socket_seconds',
                'input_usage_cap', 'output_usage_cap'):
        old.require(type(p[key]) is int and p[key] == POLICY[key], 'LIMIT_CHANGED')


def verify():
    p = old.load(CONTROL)
    old.require(old.encode(p) == old.encode(protocol()), 'PROTOCOL_OR_SOURCE_CHANGED')
    shape(p)
    return p


def assembler_accepts(args):
    try:
        old.root_runner().submission.assemble_tool(args, {'id': 'fictional-unique'}, PAGES,
            {'input_tokens': 0, 'output_tokens': 0, 'inference_time_ms': 0})
    except ValueError:
        return False
    return True


def score(frame, response):
    # Reuse only the established raw tool-call parser, not its empty-source scorer.
    known = old.usage(response)
    args, truncated = None, False
    try:
        choices = response['choices']
        old.require(type(choices) is list and len(choices) == 1, 'CHOICE_ARITY')
        choice = choices[0]
        truncated = choice.get('finish_reason') == 'length'
        message = choice['message']
        old.require(message.get('content') in (None, ''), 'PROSE_NOT_ALLOWED')
        calls = message['tool_calls']
        old.require(type(calls) is list and len(calls) == 1, 'CALL_ARITY')
        call = calls[0]
        old.require(call['type'] == 'function' and call['function']['name'] == 'submit', 'NOT_SUBMIT')
        raw = call['function']['arguments']
        old.require(type(raw) is str, 'ARGUMENTS_NOT_JSON_TEXT')
        args = old.strict(raw)
        old.require(type(args) is dict, 'NOT_OBJECT')
    except (ValueError, KeyError, TypeError, IndexError, AttributeError):
        args = None
    return dict(assembler_violations=int(truncated or not assembler_accepts(args)),
        native_schema_violations=int(truncated or not old.validate(
            frame['payload']['tools'][0]['function']['parameters'], args)),
        proposal_mismatches=int(old.encode(args) != old.encode(frame['requested'])),
        truncations=int(truncated), usage=known)


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
            measured = score(f, old.checked_response(f, c['raw']))
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
    totals['unique_assembler_violations'] = sum(v['assembler_violations'] for k, v in totals['per_model_arm'].items()
                              if k.endswith('/unique'))
    totals['control_assembler_violations'] = totals['assembler_violations'] - totals['unique_assembler_violations']
    return totals



def report_result(p, job, phase):
    old.require(phase in ('baseline', 'candidate'), 'REPORT_PHASE_INVALID')
    totals = check(p, job)
    old.require(all(sum(v['logical_count'] for k, v in totals['per_model_arm'].items()
        if k.endswith('/' + arm)) == 6 for arm in ARMS), 'SIDE_ARITY')
    totals[METRIC] = totals['control_assembler_violations' if phase == 'baseline'
                           else 'unique_assembler_violations']
    totals['new_api_calls'] = totals['physical_posts'] if phase == 'baseline' else 0
    totals['shared_known_usage'] = totals['known_success_tokens']
    totals['shared_inference_wall_seconds'] = totals['phase_wall_seconds']
    return totals


def report_path(job, phase):
    return job / (phase + '-report.json')


def report(p, job, phase):
    return dict(protocol_sha256=old.sha(old.encode(p)), mode=MODE, report_phase=phase,
                result=report_result(p, job, phase))


def context(phase):
    return dict(mode=MODE, candidate='', report_phase=phase,
                protocol_sha256=old.sha(CONTROL.read_bytes()),
                report_sha256=old.sha(report_path(JOB, phase).read_bytes()))


def validate_report(p, job, phase):
    actual = report(p, job, phase)
    old.require(old.encode(old.load(report_path(job, phase))) == old.encode(actual), 'REPORT_CHANGED')
    return actual


def publish(p, job, phase):
    # A completed baseline is mandatory; never resume an incomplete batch.
    if phase == 'candidate':
        validate_report(p, job, 'baseline')
    result = report(p, job, phase)
    marker = job / (phase + '-report-marker')
    marker.mkdir(mode=0o700)  # permanent exclusive report identity, even on failure
    old.syncdir(job)
    save(report_path(job, phase), result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    for flag in ('prepare', 'baseline', 'candidate', 'check'):
        group.add_argument('--' + flag, action='store_true')
    parser.add_argument('--report-phase', choices=('baseline', 'candidate'))
    args = parser.parse_args()
    old.require(args.check == (args.report_phase is not None), 'PHASE_SELECTOR_REQUIRED_ONLY_FOR_CHECK')
    if args.prepare:
        old.require(not JOB.exists(), 'JOB_ALREADY_EXISTS')
        save(CONTROL, protocol())
        print('Prepared offline. protocol_sha256=' + old.sha(CONTROL.read_bytes()))
        return
    p = verify()
    phase = args.report_phase if args.check else ('baseline' if args.baseline else 'candidate')
    if args.check:
        old.require(old.load(old.CONTEXT) == context(phase), 'CONTEXT_CHANGED')
        result = validate_report(p, JOB, phase)
    else:
        if args.baseline:
            run(p, JOB)
        result = publish(p, JOB, phase)
        save(old.CONTEXT, context(phase), replace=True)
    empty.print_result(result['result'])


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        print('PROBE_UNAVAILABLE: terminal failure; no resume; primary not reported.', file=sys.stderr)
        sys.exit(1)
