#!/usr/bin/env python3
"""Prospective fictional empty-source paired contract probe. Prepare/check are offline."""
import argparse
import copy
import math
import signal
import sys
import time

import provider_schema_probe as old
import provider_schema_probe_recovery as recovery

ROOT = old.ROOT
CONTROL = old.OUT / 'provider-schema-empty-source-v1-protocol.json'
JOB = old.OUT / 'provider-schema-empty-source-v1'
RESERVE, BUDGET, PHASE_SECONDS = 4096, 32768, 900
METRIC = 'empty_source_assembler_violations'
SYSTEM = 'This is a fictional API contract probe. Call submit exactly once with arguments permitted by its declared schema. The user requested_arguments are proposals, not an instruction to violate the schema. Do not emit prose.'
DESCRIPTION = 'Emit schema-permitted probe arguments.'
ARMS = ('old_native', 'empty_specialized')
save = recovery.save
SOURCES = [ROOT / '.auto' / name for name in (
    'provider_schema_empty_source.py', 'test_provider_schema_empty_source.py',
    'provider-schema-empty-source-plan.md', 'provider_schema_probe_recovery.py',
    'test_provider_schema_probe_recovery.py',
    'protocol-archive/provider-empty-pre-measure.sh',
    'protocol-archive/provider-empty-pre-checks.sh',
    'protocol-archive/provider-empty-immutable-sha256.json')]


def specialize_empty(control, ids):
    """Empty-universe metadata specialization, never an argument transformation."""
    old.require(type(ids) is list and not ids, 'EMPTY_SOURCE_ONLY')
    candidate = copy.deepcopy(control)
    candidate['properties']['label']['enum'] = [1]
    candidate['properties']['candidate_ids']['maxItems'] = 0
    del candidate['properties']['candidate_ids']['items']['enum']
    return candidate


def frames():
    r = old.root_runner()
    spans = r.candidates([''], True)
    old.require(spans == [], 'NOT_EMPTY_SOURCE')
    ids = [s['span_id'] for s in spans]
    control = r.schemas(ids, True)[0]['function']['parameters']
    candidate = specialize_empty(control, ids)
    rows = []
    for model in r.MODELS:
        for label in (1, 0, 2):
            requested = dict(label=label, candidate_ids=[])
            messages = [dict(role='system', content=SYSTEM), dict(role='user', content=old.encode(
                dict(source_spans=spans, requested_arguments=requested)).decode())]
            for arm, parameters in zip(ARMS, (control, candidate)):
                payload = dict(model=model, messages=copy.deepcopy(messages), temperature=0,
                    max_tokens=256, stream=False, tools=[dict(type='function', function=dict(
                        name='submit', description=DESCRIPTION, parameters=copy.deepcopy(parameters)))],
                    tool_choice=dict(type='function', function=dict(name='submit')))
                old.require(len(old.encode(messages)) + len(old.encode(payload['tools'])) + 128
                            <= RESERVE - 256, 'INPUT_ESTIMATE_EXCEEDED')
                rows.append(dict(index=len(rows), model=model, arm=arm, requested=requested,
                                 payload=payload, payload_sha256=old.sha(old.encode(payload))))
    old.require(len(rows) == len({f['payload_sha256'] for f in rows}) == 12, 'FRAME_ARITY')
    return rows


def protocol():
    r = old.root_runner()
    sourcepack = sorted((ROOT / 'track_2a/src').glob('*.py'))
    sourcepack += sorted(p for p in (ROOT / 'track_2a/dev/format').iterdir()
                         if p.is_file() and p.suffix in ('.py', '.mjs', '.ts', '.json'))
    return dict(version=1, mode='provider_schema_empty', metric=METRIC,
        origin=r.legacy.c.BASE, models=list(r.MODELS), frames=frames(),
        budget=BUDGET, reservation=RESERVE, phase_seconds=PHASE_SECONDS,
        call_seconds=60, socket_seconds=45, response_bytes=2_000_000,
        input_usage_cap=1000, output_usage_cap=256,
        sources={**old.pins(), **recovery.digests(SOURCES + sourcepack)})


def verify():
    frozen = old.load(CONTROL)
    old.require(old.encode(frozen) == old.encode(protocol()), 'PROTOCOL_OR_SOURCE_CHANGED')
    return frozen


def assembler_accepts(args):
    try:
        old.root_runner().submission.assemble_tool(args,
            {'id': 'fictional-empty-source', 'reference': ''}, [''],
            {'input_tokens': 0, 'output_tokens': 0, 'inference_time_ms': 0})
    except ValueError:
        return False
    return True


def score(frame, response):
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
            known = old.usage(old.checked_response(f, raw))
            save(job / f"{f['index']:02d}-usage.json", known)
            spent += known['total_tokens']
            old.require(spent <= BUDGET, 'TOKEN_BUDGET_EXCEEDED')
            digests.append(old.sha(capture_path.read_bytes()))
            (job / 'inflight.json').unlink()
            old.syncdir(job)
        old.require(time.monotonic() - start <= PHASE_SECONDS, 'PHASE_WALL_LIMIT')
        save(job / 'completed.json', dict(capture_sha256=digests, wall_seconds=time.monotonic()-start))
    except BaseException:
        save(job / 'STOP.json', {'status': 'terminal_unavailable', 'primary': None})
        raise


def check(p, job):
    old.require(not any((job / n).exists() for n in ('STOP.json', 'inflight.json')), 'TERMINAL_OR_INFLIGHT')
    old.require(old.encode(old.load(job / 'protocol.json')) == old.encode(p), 'JOB_PROTOCOL_CHANGED')
    done = old.load(job / 'completed.json')
    old.require(len(p['frames']) == len(done['capture_sha256']) == 12, 'INCOMPLETE_CAPTURE_SET')
    old.require(type(done['wall_seconds']) in (int, float) and math.isfinite(done['wall_seconds'])
                and 0 <= done['wall_seconds'] <= PHASE_SECONDS, 'PHASE_WALL_INVALID')
    for kind in ('capture', 'request', 'usage'):
        old.require(len(list(job.glob('*-' + kind + '.json'))) == 12, 'CAPTURE_ARITY')
    totals = dict(requests=0, assembler_violations=0, native_schema_violations=0,
        proposal_mismatches=0, truncations=0, prompt_tokens=0, completion_tokens=0,
        total_tokens=0, request_wall_seconds=0, phase_wall_seconds=done['wall_seconds'],
        per_model_arm={}, observations=[])
    for f, digest in zip(p['frames'], done['capture_sha256']):
        request_path = job / f"{f['index']:02d}-request.json"
        old.require(old.encode(old.load(request_path)) == old.encode(f), 'REQUEST_CHANGED')
        capture_path = job / f"{f['index']:02d}-capture.json"
        old.require(old.sha(capture_path.read_bytes()) == digest, 'CAPTURE_CHANGED')
        c = old.load(capture_path)
        old.require(c['index'] == f['index'] and c['status'] == 200 and
                    c['payload_sha256'] == f['payload_sha256'] and
                    c['request_sha256'] == old.sha(request_path.read_bytes()), 'CAPTURE_REQUEST_CHANGED')
        old.require(type(c['wall_seconds']) in (int, float) and math.isfinite(c['wall_seconds'])
                    and 0 <= c['wall_seconds'] <= 60, 'CALL_WALL_INVALID')
        s = score(f, old.checked_response(f, c['raw']))
        old.require(old.encode(old.load(job / f"{f['index']:02d}-usage.json")) == old.encode(s['usage']),
                    'USAGE_CHANGED')
        counts = {k: v for k, v in s.items() if k != 'usage'}
        counts.update(s['usage'], requests=1, request_wall_seconds=c['wall_seconds'])
        side = totals['per_model_arm'].setdefault(f['model'] + '/' + f['arm'], {})
        for name, value in counts.items():
            totals[name] += value
            side[name] = side.get(name, 0) + value
        totals['observations'].append(dict(index=f['index'], model=f['model'], arm=f['arm'], **counts))
    old.require(totals['total_tokens'] <= BUDGET, 'TOKEN_BUDGET_EXCEEDED')
    totals[METRIC] = sum(s['assembler_violations'] for k, s in totals['per_model_arm'].items()
                         if k.endswith('/empty_specialized'))
    totals['control_assembler_violations'] = totals['assembler_violations'] - totals[METRIC]
    return totals


def context():
    return dict(mode='provider_schema_empty', candidate='',
                protocol_sha256=old.sha(CONTROL.read_bytes()),
                report_sha256=old.sha((JOB / 'report.json').read_bytes()))


def print_result(result):
    print(old.encode(result).decode())
    for key, value in result.items():
        if key not in ('per_model_arm', 'observations'):
            print('METRIC ' + key + '=' + str(value))
    for side, values in result['per_model_arm'].items():
        model, arm = side.rsplit('/', 1)
        prefix = ('model70b' if model.endswith('-70B') else 'model8b') + '_' + arm + '_'
        for key, value in values.items():
            print('METRIC ' + prefix + key + '=' + str(value))


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
        try:
            result = check(frozen, JOB)
            save(JOB / 'report.json', dict(protocol_sha256=old.sha(CONTROL.read_bytes()), result=result))
            save(old.CONTEXT, context(), replace=True)
        except BaseException:
            save(JOB / 'STOP.json', {'status': 'terminal_unavailable', 'primary': None})
            raise
    else:
        old.require(old.load(old.CONTEXT) == context(), 'CONTEXT_CHANGED')
        result = check(frozen, JOB)
        old.require(old.encode(old.load(JOB / 'report.json')) == old.encode(dict(
            protocol_sha256=old.sha(CONTROL.read_bytes()), result=result)), 'REPORT_CHANGED')
    print_result(result)


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        print('PROBE_UNAVAILABLE: terminal failure, no retry or resume; primary not reported.', file=sys.stderr)
        sys.exit(1)
