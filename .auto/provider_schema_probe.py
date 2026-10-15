#!/usr/bin/env python3
"""One exclusive fictional schema diagnostic. No historical data, scorer or SDK calls."""
import argparse
import hashlib
import http.client
import importlib.util
import json
import math
import os
from pathlib import Path
import signal
import ssl
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/cscs'
CONTROL = OUT / 'provider-schema-probe-v1-protocol.json'
JOB = OUT / 'provider-schema-probe-v1'
CONTEXT = ROOT / '.auto/check-context.json'
TYPEBOX = Path('/home/yasuhito/.pi/agent/install/releases/1.1.0/node_modules/typebox/build')
RESERVE, BUDGET, PHASE_SECONDS = 1256, 32768, 900
SYSTEM = 'For this API compatibility probe, call submit exactly once with the arguments requested in user JSON. Do not emit prose.'


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(',', ':')).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    def constant(_):
        raise ValueError('NONFINITE_JSON')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def load(path):
    require(not path.is_symlink(), 'SYMLINK_REFUSED')
    return strict(path.read_bytes())


def syncdir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def save(path, value, *, replace=False):
    """Publish fsynced private bytes atomically, without replacing immutable artifacts."""
    require(not path.is_symlink(), 'SYMLINK_REFUSED')
    fd, name = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(encode(value)); stream.flush(); os.fsync(stream.fileno())
        if replace:
            os.replace(name, path)
        else:
            os.link(name, path)
        os.unlink(name)
        syncdir(path.parent)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def root_runner():
    path = ROOT / 'track_2a/dev/format/run_comparison.py'
    spec = importlib.util.spec_from_file_location('schema_probe_root', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frames():
    r = root_runner()
    rows = []
    for model in r.MODELS:
        for label, ids in [(0, ['toy-a']), (1, []), (2, ['toy-b'])]:
            requested = {'label': label, 'candidate_ids': ids}
            messages = [dict(role='system', content=SYSTEM), dict(role='user', content=encode({
                'source_spans': [{'span_id': 'toy-a', 'text': 'Fictional amber toy.'},
                                 {'span_id': 'toy-b', 'text': 'Fictional blue toy.'}],
                'requested_arguments': requested}).decode())]
            for arm in ('simple', 'conditional'):
                schema = r.schemas(['toy-a', 'toy-b'], child=True)[0]['function']['parameters']
                if arm == 'conditional':
                    schema['anyOf'] = [{'properties': {'label': {'enum': [1]}}},
                                       {'properties': {'candidate_ids': {'minItems': 1}}}]
                payload = dict(model=model, messages=messages, temperature=0, max_tokens=256,
                               stream=False, tools=[{'type': 'function', 'function': {
                                   'name': 'submit', 'description': 'Emit the requested probe arguments.',
                                   'parameters': schema}}],
                               tool_choice={'type': 'function', 'function': {'name': 'submit'}})
                # Byte estimate bounds ordinary small fictional text conservatively by <=1000 input tokens.
                require(len(encode(messages)) + len(encode(payload['tools'])) + 128 <= 1000, 'INPUT_ESTIMATE_EXCEEDED')
                rows.append(dict(index=len(rows), arm=arm, model=model, requested=requested,
                                 payload=payload, payload_sha256=sha(encode(payload))))
    require(len(rows) == 12 and len({x['payload_sha256'] for x in rows}) == 12, 'FRAME_ARITY')
    return rows


def pins():
    paths = [ROOT / p for p in (
        '.auto/provider_schema_probe.py', '.auto/test_provider_schema_probe.py',
        '.auto/provider_schema_validator.mjs', '.auto/provider-schema-probe-plan.md',
        '.auto/measure.sh', '.auto/checks.sh',
        'track_2a/dev/format/run_comparison.py', 'track_2a/dev/cscs/cscs_dev54.py',
        'track_2a/dev/cscs/cscs_check.py', 'track_2a/src/submission.py',
        'track_2a/dev/format/package-child.mjs', 'track_2a/dev/format/dependencies.mjs',
        'track_2a/dev/format/isolation-guard.mjs', 'track_2a/dev/format/package-lock.json',
        'track_2a/dev/format/entry.ts', 'track_2a/dev/format/sdk.ts',
        'track_2a/dev/format/safe-submit-child.ts', 'track_2a/dev/format/submit-extension.ts')]
    # Pin entire standalone validator implementation and runtime, not just its barrel entry.
    paths += sorted(TYPEBOX.rglob('*.mjs'))
    paths += [Path(sys.executable).resolve(), Path(subprocess.check_output(['which', 'node'], text=True).strip()).resolve()]
    return {str(p): sha(p.read_bytes()) for p in paths}


def protocol():
    r = root_runner()
    return dict(version=1, metric='schema_contract_violations', sources=pins(),
                origin=r.legacy.c.BASE, models=list(r.MODELS), frames=frames(),
                budget=BUDGET, reservation=RESERVE, phase_seconds=PHASE_SECONDS,
                call_seconds=60, socket_seconds=45, response_bytes=2_000_000)


def verify():
    p = load(CONTROL)
    require(p == protocol(), 'PROTOCOL_OR_SOURCE_CHANGED')
    return p


def validate(schema, value):
    result = subprocess.run(['node', str(ROOT / '.auto/provider_schema_validator.mjs')],
                            input=encode([dict(schema=schema, value=value)]), capture_output=True,
                            timeout=20, check=True)
    answer = strict(result.stdout)
    require(type(answer) is list and len(answer) == 1 and type(answer[0]) is bool, 'VALIDATOR_FAILURE')
    return answer[0]


def usage(response):
    u = response.get('usage', {})
    values = [u.get(k) for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')]
    require(all(type(x) is int and x >= 0 for x in values), 'UNKNOWN_USAGE')
    require(values[0] + values[1] == values[2] and values[0] <= 1000 and values[1] <= 256, 'INCONSISTENT_USAGE')
    return dict(zip(('prompt_tokens', 'completion_tokens', 'total_tokens'), values))


def checked_response(frame, raw):
    response = strict(raw)
    require(type(response) is dict and response.get('model') == frame['model']
            and 'error' not in response, 'RESPONSE_IDENTITY_OR_API_ERROR')
    return response


def score(frame, response):
    known = usage(response)
    args, truncated, missing = None, False, False
    try:
        choices = response['choices']
        require(type(choices) is list and len(choices) == 1, 'CHOICE_ARITY')
        choice = choices[0]
        truncated = choice.get('finish_reason') == 'length'
        calls = choice['message']['tool_calls']
        require(type(calls) is list and len(calls) == 1, 'CALL_ARITY')
        call = calls[0]
        require(call['type'] == 'function' and call['function']['name'] == 'submit', 'NOT_SUBMIT')
        args = strict(call['function']['arguments'])
        require(type(args) is dict, 'NOT_OBJECT')
        missing = not {'label', 'candidate_ids'} <= args.keys()
    except (ValueError, KeyError, TypeError, IndexError, AttributeError):
        args = None
    compliant = validate(frame['payload']['tools'][0]['function']['parameters'], args)
    compliant = compliant and not truncated
    return dict(violation=int(not compliant), missing_field=int(missing), truncation=int(truncated),
                exact_copy_mismatch=int(compliant and args != frame['requested']), usage=known)


class Transport:
    """Only frozen hashes, default origin and default credential; never retries."""
    def __init__(self, p):
        self.allowed = {f['payload_sha256'] for f in p['frames']}
        r = root_runner()
        require(p['origin'] == r.legacy.c.BASE, 'ORIGIN_DRIFT')
        self.parsed = urlsplit(r.legacy.c.BASE)
        require(self.parsed.scheme == 'https' and self.parsed.hostname and
                not self.parsed.username and not self.parsed.password and
                not self.parsed.query and not self.parsed.fragment, 'ORIGIN_REFUSED')
        self.read_key = lambda: r.legacy.c.read_key(r.legacy.c.DEFAULT_KEY_FILE)

    def request(self, payload):
        raw = encode(payload)
        require(sha(raw) in self.allowed, 'PAYLOAD_REFUSED')
        self.allowed.remove(sha(raw))
        connection = http.client.HTTPSConnection(self.parsed.hostname, self.parsed.port,
                                                timeout=45, context=ssl.create_default_context())
        connection.set_debuglevel(0)
        try:
            connection.request('POST', self.parsed.path.rstrip('/') + '/chat/completions', body=raw,
                               headers={'Authorization': 'Bearer ' + self.read_key(),
                                        'Content-Type': 'application/json', 'Accept-Encoding': 'identity'})
            response = connection.getresponse()
            # Preserve status/body only, never request headers or credentials.
            blob = response.read(2_000_001)
            require(len(blob) <= 2_000_000, 'RESPONSE_LIMIT')
            return response.status, blob.decode('utf-8')
        finally:
            connection.close()


def deadline(*_):
    raise TimeoutError('CALL_WALL_LIMIT')


def run(p, job, transport):
    job.mkdir(mode=0o700)  # permanent exclusive identity even if anything later fails
    syncdir(job.parent)
    start, spent, digests = time.monotonic(), 0, []
    try:
        save(job / 'protocol.json', p)
        for f in p['frames']:
            require(time.monotonic() - start < PHASE_SECONDS - 60, 'PHASE_WALL_LIMIT')
            require(BUDGET - spent >= RESERVE, 'TOKEN_RESERVATION_REFUSED')
            request_path = job / f"{f['index']:02d}-request.json"
            save(request_path, f)
            save(job / 'inflight.json', dict(index=f['index'], reserved=RESERVE))
            previous = signal.signal(signal.SIGALRM, deadline)
            timer = signal.setitimer(signal.ITIMER_REAL, 60)
            before = time.monotonic()
            try:
                status, raw = transport.request(f['payload'])
            finally:
                signal.setitimer(signal.ITIMER_REAL, *timer)
                signal.signal(signal.SIGALRM, previous)
            capture = dict(index=f['index'], request_sha256=sha(request_path.read_bytes()),
                           payload_sha256=f['payload_sha256'], status=status, raw=raw,
                           wall_seconds=time.monotonic() - before)
            capture_path = job / f"{f['index']:02d}-capture.json"
            save(capture_path, capture)
            require(status == 200, 'HTTP_FAILURE_NO_RETRY')
            measured = score(f, checked_response(f, raw))
            spent += measured['usage']['total_tokens']
            require(spent <= BUDGET, 'TOKEN_BUDGET_EXCEEDED')
            digests.append(sha(capture_path.read_bytes()))
            (job / 'inflight.json').unlink(); syncdir(job)
        save(job / 'completed.json', dict(capture_sha256=digests, wall_seconds=time.monotonic()-start))
    except BaseException:
        # Do not serialize exceptions: they can contain credentials/HTTP headers.
        save(job / 'STOP.json', {'status': 'terminal_unavailable', 'primary': None})
        raise


def check(p, job):
    require(not any((job / name).exists() for name in ('inflight.json', 'STOP.json')), 'TERMINAL_OR_INFLIGHT')
    require(load(job / 'protocol.json') == p, 'JOB_PROTOCOL_CHANGED')
    done = load(job / 'completed.json')
    require(len(done['capture_sha256']) == 12, 'INCOMPLETE_CAPTURE_SET')
    require(0 <= done['wall_seconds'] <= PHASE_SECONDS, 'PHASE_WALL_INVALID')
    totals = dict(schema_contract_violations=0, missing_field=0, truncation=0,
                  exact_copy_mismatch=0, prompt_tokens=0, completion_tokens=0, total_tokens=0,
                  request_wall_seconds=0, phase_wall_seconds=done['wall_seconds'], per_model_arm={})
    require(len(list(job.glob('*-capture.json'))) == 12 and len(list(job.glob('*-request.json'))) == 12, 'CAPTURE_ARITY')
    for f, digest in zip(p['frames'], done['capture_sha256']):
        request_path = job / f"{f['index']:02d}-request.json"
        require(load(request_path) == f, 'REQUEST_CHANGED')
        capture_path = job / f"{f['index']:02d}-capture.json"
        require(sha(capture_path.read_bytes()) == digest, 'CAPTURE_CHANGED')
        c = load(capture_path)
        require(c['index'] == f['index'] and c['status'] == 200 and
                c['payload_sha256'] == f['payload_sha256'] and
                c['request_sha256'] == sha(request_path.read_bytes()), 'CAPTURE_REQUEST_CHANGED')
        require(type(c['wall_seconds']) in (int, float) and math.isfinite(c['wall_seconds']) and
                0 <= c['wall_seconds'] <= 60, 'CALL_WALL_INVALID')
        totals['request_wall_seconds'] += c['wall_seconds']
        s = score(f, checked_response(f, c['raw']))
        key = f['model'] + '/' + f['arm']
        side = totals['per_model_arm'].setdefault(key, dict(requests=0, violations=0, missing_field=0,
                                                          truncation=0, exact_copy_mismatch=0))
        side['requests'] += 1; side['violations'] += s['violation']
        totals['schema_contract_violations'] += s['violation']
        for name in ('missing_field', 'truncation', 'exact_copy_mismatch'):
            totals[name] += s[name]; side[name] += s[name]
        for name, value in s['usage'].items():
            totals[name] += value
    require(totals['total_tokens'] <= BUDGET, 'TOKEN_BUDGET_EXCEEDED')
    return totals


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    for flag in ('prepare', 'execute', 'check'):
        group.add_argument('--' + flag, action='store_true')
    args = parser.parse_args()
    if args.prepare:
        require(not JOB.exists(), 'JOB_ALREADY_EXISTS')
        save(CONTROL, protocol())
        print('Prepared fictional diagnostic only. protocol_sha256=' + sha(CONTROL.read_bytes()))
        return
    p = verify()
    if args.execute:
        run(p, JOB, Transport(p))
        result = check(p, JOB)
        save(CONTEXT, dict(mode='provider_schema_probe', candidate='', protocol_sha256=sha(CONTROL.read_bytes()),
                           completed_sha256=sha((JOB / 'completed.json').read_bytes())), replace=True)
    else:
        context = load(CONTEXT)
        require(context == dict(mode='provider_schema_probe', candidate='', protocol_sha256=sha(CONTROL.read_bytes()),
                                completed_sha256=sha((JOB / 'completed.json').read_bytes())), 'CONTEXT_CHANGED')
        result = check(p, JOB)
    print(json.dumps(result, sort_keys=True))
    print('METRIC schema_contract_violations=' + str(result['schema_contract_violations']))


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        print('PROBE_UNAVAILABLE: terminal failure, no retry or resume; primary not reported.', file=sys.stderr)
        sys.exit(1)
