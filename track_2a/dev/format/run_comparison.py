#!/usr/bin/env python3
"""Separate finite source-only A/B comparison. Legacy Client is not modified."""
import argparse
from collections import Counter
import fcntl
import http.client
import importlib.util
import json
import math
import os
from pathlib import Path
import select
import shutil
import signal
import ssl
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / 'track_2a/src'))
import submission
from source_spans import candidates
spec = importlib.util.spec_from_file_location('format_legacy', HERE.parent / 'cscs/cscs_dev54.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
Stop = legacy.c.Stop
MODELS = legacy.MODELS
LIMITS = {'A': 216, 'B': 540, 'C': 270, 'S': 180, 'R': 180}
TOKEN_BUDGET = 6_000_000
RESERVE = 262400
CASE_SECONDS = 300


def case_model(strategy, nominal, case):
    """Route from input structure only, never from labels or model output."""
    return MODELS[0] if strategy == 'R' and 'reference' in case else nominal


def fixed_role_model(strategy, case_owner_model, role, case=None):
    """Enforce the approved role policy, with input-only routing for R."""
    if strategy not in LIMITS or role not in ('parent', 'child') or case_owner_model not in MODELS:
        raise Stop('ROLE_MODEL_REFUSED')
    if strategy == 'C':
        if case_owner_model != MODELS[1]:
            raise Stop('ROLE_MODEL_REFUSED')
        return MODELS[1] if role == 'parent' else MODELS[0]
    if strategy in ('A', 'S', 'R') and role != 'parent':
        raise Stop('ROLE_MODEL_REFUSED')
    return case_model(strategy, case_owner_model, case or {})


def validate_role_models(manifest):
    if manifest['strategy'] == 'C':
        expected = {'parent': MODELS[1], 'child': MODELS[0]}
        if manifest.get('models', [manifest.get('model')]) != [MODELS[1]] or manifest.get('role_models') != expected:
            raise Stop('ROLE_MODEL_REFUSED')

    if manifest['strategy'] in ('S', 'R'):
        models = manifest.get('models')
        if not isinstance(models, list) or len(models) != 1 or models[0] not in MODELS or 'role_models' in manifest or manifest.get('model', models[0]) != models[0]:
            raise Stop('ROLE_MODEL_REFUSED')
        if manifest['strategy'] == 'R' and models != [MODELS[1]]:
            raise Stop('ROLE_MODEL_REFUSED')


def schemas(ids, child=False, strategy=None):
    submit = {'type': 'function', 'function': {'name': 'submit', 'description': 'Select NLI label and exact supporting candidate IDs.', 'parameters': {'type': 'object', 'additionalProperties': False, 'required': ['label', 'candidate_ids'], 'properties': {'label': {'enum': [0, 1, 2], 'type': 'integer'}, 'candidate_ids': {'type': 'array', 'maxItems': 5, 'items': {'type': 'string', 'enum': ids}}}}}}
    delegate = {'type': 'function', 'function': {'name': 'subagent', 'description': 'One fixed source-only child recommendation.', 'parameters': {'type': 'object', 'additionalProperties': False, 'required': ['mode'], 'properties': {'mode': {'type': 'string', 'enum': ['source_only']}}}}}
    return [submit] if child or strategy in ('S', 'R') else [submit, delegate]


class Transport:
    """No redirects, HTTP retries, provider discovery, or credentials in Node."""
    def __init__(self, model, *, submitted=False, factory=None):
        if model not in MODELS:
            raise Stop('MODEL_REFUSED')
        self.model = model
        self.submitted = submitted
        self.factory = factory
        self.__key = None
        if submitted:
            # Submitted calls never have a CSCS/default credential fallback.
            base = os.environ.get('BASE_URL')
            if not base or not os.environ.get('API_KEY'):
                raise Stop('INJECTED_BASE_URL_API_KEY_REQUIRED')
            self.base = base.rstrip('/')
        else:
            self.base = legacy.c.BASE
        parsed = urlsplit(self.base)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise Stop('BASE_URL_REFUSED')
        if not submitted and self.base != legacy.c.BASE:
            raise Stop('DEV_ENDPOINT_REFUSED')
        self.parsed = parsed

    def request(self, method, path, payload):
        if method != 'POST' or path != '/v1/chat/completions' or payload.get('model') != self.model or payload.get('max_tokens') != 256 or payload.get('stream') is not False:
            raise Stop('REQUEST_REFUSED')
        if set(payload) - {'model', 'messages', 'temperature', 'max_tokens', 'stream', 'tools', 'tool_choice'} or payload.get('temperature') != 0:
            raise Stop('PARAMETERS_REFUSED')
        if 'tools' in payload:
            try:
                source = submission.strict_json(next(m['content'] for m in payload['messages'] if m['role'] == 'user'))
                ids = [s['span_id'] for s in source['source_spans']]
                names = {t['function']['name'] for t in payload['tools']}
                enforce_tools(payload, ids, 'parent' if 'subagent' in names else 'child')
            except (KeyError, ValueError, TypeError, StopIteration):
                raise Stop('UNDECLARED_TOOLS_REFUSED') from None
        if not self.__key:
            self.__key = os.environ['API_KEY'] if self.submitted else legacy.c.read_key(legacy.c.DEFAULT_KEY_FILE)
        cls = self.factory or (http.client.HTTPSConnection if self.parsed.scheme == 'https' else http.client.HTTPConnection)
        kwargs = {'timeout': 45}
        if self.parsed.scheme == 'https':
            kwargs['context'] = ssl.create_default_context()
        connection = cls(self.parsed.hostname, self.parsed.port, **kwargs)
        connection.set_debuglevel(0)
        try:
            target = self.parsed.path.rstrip('/') + '/chat/completions'
            connection.request('POST', target, body=legacy.encode(payload), headers={'Authorization': 'Bearer ' + self.__key, 'Content-Type': 'application/json', 'Accept-Encoding': 'identity'})
            response = connection.getresponse()
            if response.status != 200:
                error = Stop('HTTP_FAILURE_NO_RETRY')
                error.http_status = response.status
                raise error
            blob = response.read(2_000_001)
            if len(blob) > 2_000_000:
                raise Stop('RESPONSE_LIMIT')
            return submission.strict_json(blob.decode('utf-8'))
        except Stop:
            raise
        except BaseException:
            raise Stop('TRANSPORT_UNCERTAIN_NO_RETRY') from None
        finally:
            connection.close()


def select_cases(manifest, case_ids):
    """Gold-free explicit research selection, preserving frozen source order."""
    if (not isinstance(case_ids, list) or not case_ids
            or any(not isinstance(case_id, str) for case_id in case_ids)
            or len(set(case_ids)) != len(case_ids)):
        raise Stop('INVALID_CASE_SELECTION')
    available = {item['case']['id'] for item in manifest['frozen']}
    if not set(case_ids) <= available:
        raise Stop('UNKNOWN_CASE_SELECTION')
    manifest['frozen'] = [item for item in manifest['frozen'] if item['case']['id'] in set(case_ids)]
    manifest['selected_case_ids'] = [item['case']['id'] for item in manifest['frozen']]
    manifest['selected_case_count'] = len(manifest['frozen'])
    return manifest


def prepare(strategy, case_ids=None):
    manifest = legacy.prepare()
    manifest.update(version='format-1', strategy=strategy, request_limit=LIMITS[strategy], token_budget=TOKEN_BUDGET,
                    request_token_reserve=RESERVE, request_wall_seconds=60, socket_seconds=45, case_wall_seconds=CASE_SECONDS,
                    parent_completion_limit=2 if strategy == 'A' else 3, child_completion_limit=0 if strategy in ('A', 'S', 'R') else 2,
                    schema_repair_limit=1, native_schema='OpenAI tools only for B/C; no structured_output or json_schema' if strategy == 'C' else 'OpenAI tools only for B; no structured_output or json_schema', pi_version='1.1.0')
    if strategy == 'C':
        manifest.update(models=[MODELS[1]], role_models={'parent': MODELS[1], 'child': MODELS[0]})
    if strategy == 'R':
        manifest['models'] = [MODELS[1]]
    files = [REPO / 'track_2a/src/submission.py'] + [p for p in HERE.iterdir() if p.suffix in ('.py', '.ts', '.mjs', '.json') and p.is_file()]
    manifest['sources'].update({str(p.relative_to(REPO)): legacy.digest(p.read_bytes()) for p in files})
    for item in manifest['frozen']:
        item['candidate_ids'] = [x['span_id'] for x in candidates(item['pages'], 'reference' in item['case'])]
        item['schema_sha256'] = legacy.digest(legacy.encode(schemas(item['candidate_ids'], strategy=strategy)))
    return select_cases(manifest, case_ids) if case_ids is not None else manifest


def initialize(job, manifest):
    if not job.exists():
        job.mkdir(mode=0o700, parents=True)
        legacy.syncdir(job.parent)
    legacy.c.private_directory(job)
    if not (job / 'manifest.json').exists():
        legacy.exclusive(job / 'manifest.json', manifest)
        legacy.exclusive(job / 'state.json', {'version': 'format-1', 'manifest_sha256': legacy.digest(legacy.encode(manifest)), 'requests': 0, 'tokens': 0, 'reserved_tokens': 0, 'blocked': False, 'attempts': {}, 'cases': {}})
    elif legacy.digest(legacy.encode(legacy.load(job / 'manifest.json'))) != legacy.digest(legacy.encode(manifest)):
        raise Stop('MANIFEST_CHANGED')


class Ledger:
    def __init__(self, job, manifest, client_factory):
        validate_role_models(manifest)
        self.job, self.manifest, self.client_factory = job, manifest, client_factory
        self.fence = job / 'inflight.json'
        if self.fence.exists() or (job / 'state.pending').exists() or (job / 'STOP.json').exists():
            raise Stop('UNCERTAIN_FENCE_NO_RETRY')
        self.state = legacy.load(job / 'state.json')
        if self.state.get('version') != 'format-1' or self.state['manifest_sha256'] != legacy.digest(legacy.encode(manifest)) or self.state['blocked'] or self.state['reserved_tokens']:
            raise Stop('STATE_BLOCKED_OR_CHANGED')
        self.records = {}
        for group in ('attempts', 'cases'):
            for name, sha in self.state[group].items():
                record = legacy.load(job / name)
                if sha != legacy.digest(legacy.encode(record)):
                    raise Stop('RECORD_CHANGED')
                self.records[name] = record
        attempts = [self.records[n] for n in self.state['attempts']]
        if len(attempts) != self.state['requests'] or any(not legacy.usage_valid(r['usage']) for r in attempts) or sum(r['usage']['total_tokens'] for r in attempts) != self.state['tokens']:
            raise Stop('LEDGER_MISMATCH')

    def save_case(self, name, result):
        legacy.exclusive(self.job / name, result)
        self.state['cases'][name] = legacy.digest(legacy.encode(result))
        legacy.state_write(self.job / 'state.json', self.state)
        self.records[name] = result

    def post(self, model, index, role, number, payload, deadline=None):
        # R receives the routed target, but persists all records under its
        # single nominal owner so filenames and metric grouping stay stable.
        if self.manifest['strategy'] == 'R':
            model = self.manifest['models'][0]
        actual_target = fixed_role_model(self.manifest['strategy'], model, role, self.manifest['frozen'][index]['case'])
        if payload.get('model') != actual_target:
            raise Stop('ROLE_MODEL_REFUSED')
        name = legacy.result_name(model, index).replace('.json', f'-{role}-{number}.json')
        sha = legacy.digest(legacy.encode(payload))
        if name in self.state['attempts']:
            record = self.records[name]
            if record['payload_sha256'] != sha:
                raise Stop('REPLAY_PAYLOAD_CHANGED')
            return record['response']
        state = self.state
        if deadline is not None and deadline <= time.monotonic():
            raise Stop('CASE_DEADLINE_ALL_STOP')
        if state['requests'] >= self.manifest['request_limit'] or state['tokens'] + RESERVE > self.manifest['token_budget']:
            raise Stop('HARD_BUDGET_STOP_BEFORE_SEND')
        legacy.exclusive(self.fence, {'model': model, 'request_model': actual_target, 'index': index, 'role': role, 'number': number, 'record': name, 'payload_sha256': sha, 'reserved_tokens': RESERVE})
        state['requests'] += 1
        state['reserved_tokens'] = RESERVE
        legacy.state_write(self.job / 'state.json', state)
        started = time.monotonic()
        started_unix_ms = time.time() * 1000
        timeout = min(60, deadline - started) if deadline is not None else 60
        if timeout <= 0:
            raise Stop('CASE_DEADLINE_ALL_STOP')
        previous = signal.signal(signal.SIGALRM, legacy.deadline_stop)
        timer = signal.setitimer(signal.ITIMER_REAL, timeout)
        try:
            response = self.client_factory(actual_target).request('POST', '/v1/chat/completions', payload)
        finally:
            signal.setitimer(signal.ITIMER_REAL, *timer)
            signal.signal(signal.SIGALRM, previous)
        elapsed = (time.monotonic() - started) * 1000
        usage = response.get('usage') if isinstance(response, dict) else None
        safe = legacy.usage_valid(usage) and response.get('model') == actual_target and 'error' not in response
        safe = safe and valid_usage_details(usage)
        choices = response.get('choices') if isinstance(response, dict) else None
        safe = safe and isinstance(choices, list) and len(choices) == 1 and isinstance(choices[0], dict) and choices[0].get('finish_reason') in ('stop', 'tool_calls', 'length') and isinstance(choices[0].get('message'), dict)
        safe = safe and wire_shape_safe(choices[0]['message'])
        record = {'model': model, 'request_model': actual_target, 'case_index': index, 'role': role, 'number': number, 'payload_sha256': sha, 'source_sha256': self.manifest['frozen'][index]['messages_sha256'], 'schema_sha256': legacy.digest(legacy.encode(payload.get('tools'))), 'assembler_schema_sha256': self.manifest['frozen'][index]['schema_sha256'], 'usage': usage, 'usage_known': legacy.usage_known(usage), 'usage_valid': legacy.usage_valid(usage), 'started_unix_ms': started_unix_ms, 'completed_unix_ms': time.time() * 1000, 'api_wait_ms': elapsed, 'generation_requests': 1, 'server_model_matches': isinstance(response, dict) and response.get('model') == actual_target, 'has_api_error': isinstance(response, dict) and 'error' in response, 'response': response if safe else None, 'safe': safe}
        legacy.exclusive(self.job / name, record)
        if legacy.usage_known(usage):
            state['tokens'] += usage['total_tokens']
        state['attempts'][name] = legacy.digest(legacy.encode(record))
        safe = safe and state['tokens'] <= self.manifest['token_budget']
        if safe:
            state['reserved_tokens'] = 0
        else:
            state['blocked'] = True
        legacy.state_write(self.job / 'state.json', state)
        if not safe:
            raise Stop('UNKNOWN_MODEL_USAGE_OR_RESPONSE_ALL_STOP')
        self.fence.unlink()
        self.records[name] = record
        return response


def wire_shape_safe(message):
    if message.get('content') is not None and not isinstance(message.get('content'), str):
        return False
    calls = message.get('tool_calls', [])
    return isinstance(calls, list) and all(isinstance(call, dict) and call.get('type') == 'function' and isinstance(call.get('id'), str) and isinstance(call.get('function'), dict) and isinstance(call['function'].get('name'), str) and isinstance(call['function'].get('arguments'), str) for call in calls)


def valid_usage_details(u):
    if not legacy.usage_known(u):
        return False
    for details, key, maximum in [('prompt_tokens_details', 'cached_tokens', u['prompt_tokens']), ('completion_tokens_details', 'reasoning_tokens', u['completion_tokens'])]:
        if details in u:
            value = u[details].get(key, 0) if isinstance(u[details], dict) else None
            if type(value) is not int or not 0 <= value <= maximum:
                return False
    return True


def metrics_for(ledger, model, index, wall_ms):
    subset = [r for name, r in ledger.records.items() if name in ledger.state['attempts'] and r['model'] == model and r['case_index'] == index]
    return {'input_tokens': sum(r['usage']['prompt_tokens'] for r in subset), 'output_tokens': sum(r['usage']['completion_tokens'] for r in subset), 'inference_time_ms': wall_ms}, sum(r['api_wait_ms'] for r in subset)


def run_a(item, model, post):
    messages = [dict(m) for m in item['messages']]
    for number in range(2):
        response = post('parent', number, {'model': model, 'messages': messages, 'temperature': 0, 'max_tokens': 256, 'stream': False})
        choice = response['choices'][0]
        raw = choice['message'].get('content')
        try:
            if choice['finish_reason'] != 'stop':
                raise ValueError('INCOMPLETE_TEXT')
            args = submission.text_args(raw)
            submission.assemble_tool(args, item['case'], item['pages'], {'input_tokens': 0, 'output_tokens': 0, 'inference_time_ms': 0})
            return args, []
        except (ValueError, TypeError) as exc:
            code = str(exc) if str(exc).isupper() else 'SOURCE_OR_SCHEMA_INVALID'
            if number == 0:
                messages += [{'role': 'assistant', 'content': raw if isinstance(raw, str) else ''}, {'role': 'user', 'content': 'Schema repair only: ' + code + '. Return label/evidence JSON with exact supplied IDs. Do not change source or invent IDs.'}]
    return None, [code]


# Only fixed protocol codes may cross the SDK bridge, never exception bodies.
SAFE_TOOL_ERRORS = frozenset({
    'DUPLICATE_JSON_KEY', 'NONFINITE_JSON', 'JSON_TEXT_REQUIRED',
    'TOOL_SCHEMA', 'LABEL_SCHEMA', 'IDS_SCHEMA', 'DUPLICATE_ID', 'UNKNOWN_ID',
    'CANONICAL_KEYS', 'CANONICAL_ID', 'METRICS_KEYS', 'METRICS_VALUE',
    'SUBMIT_LIMIT', 'SUBAGENT_ARGUMENTS', 'DUPLICATE_SUBMIT',
})
SUPPORTING_SPAN_MESSAGE = (
    'Labels 0 and 2 require supplied supporting candidate IDs. '
    'Recheck the source judgment and cite supporting supplied IDs; '
    'do not invent IDs or change the label only to satisfy formatting.'
)


def tool_error_code(exc):
    if type(exc) is ValueError and str(exc) == 'supporting span required':
        return 'SUPPORTING_SPAN_REQUIRED'
    code = str(exc)
    return code if code in SAFE_TOOL_ERRORS else 'SOURCE_OR_SCHEMA_INVALID'


def missing_support_args(args):
    # Forward only this strict schema-compatible failure, never coercible values.
    return (type(args) is dict and set(args) == {'label', 'candidate_ids'}
            and type(args['label']) is int and args['label'] in (0, 2)
            and type(args['candidate_ids']) is list and args['candidate_ids'] == [])


def run_b(item, model, post, seconds=CASE_SECONDS, isolation_guard=False, strategy='B'):
    """Python owns the assembler and all requests. Node receives no credentials."""
    fixed_role_model(strategy, model, 'parent')
    child_model = None if strategy in ('S', 'R') else fixed_role_model(strategy, model, 'child')
    with tempfile.TemporaryDirectory(prefix='ost-pi-', dir='/tmp') as home:
        node = shutil.which('node')
        if not node:
            raise Stop('NODE_EXECUTABLE_MISSING')
        env = {'PATH': os.defpath, 'HOME': home, 'PI_CODING_AGENT_DIR': home, 'PI_OFFLINE': '1'}
        if os.environ.get('PI_PACKAGE_ROOT'):
            env['PI_PACKAGE_ROOT'] = os.environ['PI_PACKAGE_ROOT']
        if os.environ.get('PI_SUBAGENTS_ROOT'):
            env['PI_SUBAGENTS_ROOT'] = os.environ['PI_SUBAGENTS_ROOT']
        command = [node] + (['--import', str(HERE / 'isolation-guard.mjs')] if isolation_guard else []) + [str(HERE / 'entry.ts')]
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, env=env)
        deadline = time.monotonic() + seconds
        counters = Counter()
        submit_calls = Counter()
        accepted = None
        diagnostics = []
        def send(value):
            process.stdin.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + '\n')
            process.stdin.flush()
        send({'model': model, 'strategy': strategy, 'child_model': child_model, 'ids': item['candidate_ids'], 'system': item['messages'][0]['content'], 'user': item['messages'][1]['content']})
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not select.select([process.stdout], [], [], remaining)[0]:
                    raise Stop('CASE_DEADLINE_ALL_STOP')
                line = process.stdout.readline()
                if not line:
                    raise Stop('SDK_EOF_ALL_STOP')
                message = submission.strict_json(line)
                kind = message['kind']
                if kind == 'done':
                    if strategy not in ('S', 'R') and not message['result']['counts']['child']:
                        diagnostics.append('NO_SUBAGENT_CALL')
                    return accepted, diagnostics, message['result']
                if kind == 'fatal':
                    raise Stop('SDK_FATAL_ALL_STOP')
                data = message['data']
                role = data.get('role')
                if role not in (('parent',) if strategy in ('S', 'R') else ('parent', 'child')):
                    raise Stop('ROLE_REFUSED')
                if kind == 'request':
                    payload = data['payload']
                    if payload.get('model') != fixed_role_model(strategy, model, role):
                        raise Stop('ROLE_MODEL_REFUSED')
                    enforce_tools(payload, item['candidate_ids'], role, strategy=strategy)
                    if counters[role] >= (3 if role == 'parent' else 2) or accepted is not None:
                        raise Stop('SDK_REQUEST_LIMIT')
                    response = post(role, counters[role], payload)
                    counters[role] += 1
                    # Add strictly parsed arguments for Pi. Never scrape response text.
                    response = json.loads(json.dumps(response))
                    choice = response['choices'][0]
                    calls = choice['message'].get('tool_calls', [])
                    if not calls:
                        diagnostics.append('NO_NATIVE_TOOL_CALL')
                    if not isinstance(calls, list):
                        raise Stop('MALFORMED_TOOL_CALLS_ALL_STOP')
                    for call in calls:
                        if not isinstance(call, dict) or call.get('type') != 'function' or not isinstance(call.get('id'), str) or not isinstance(call.get('function'), dict):
                            raise Stop('MALFORMED_TOOL_CALL_ALL_STOP')
                        if call['function'].get('name') == 'submit':
                            submit_calls[role] += 1
                            if submit_calls[role] > 2:
                                call['parsed_arguments'] = {'invalid_schema': 'SUBMIT_LIMIT'}
                                diagnostics.append('SUBMIT_LIMIT')
                                continue
                        try:
                            call['parsed_arguments'] = submission.strict_json(call['function']['arguments'])
                        except (ValueError, TypeError, KeyError) as exc:
                            code = 'INVALID_TOOL_JSON' if isinstance(exc, json.JSONDecodeError) else tool_error_code(exc)
                            call['parsed_arguments'] = {'invalid_schema': code}
                            diagnostics.append(code)
                            continue
                        try:
                            # Pi's TypeBox validator may coerce strings. Keep all
                            # strict gates before forwarding to tool execution.
                            if call['function'].get('name') == 'submit':
                                submission.assemble_tool(call['parsed_arguments'], item['case'], item['pages'], {'input_tokens': 0, 'output_tokens': 0, 'inference_time_ms': 0})
                            elif call['function'].get('name') == 'subagent' and call['parsed_arguments'] != {'mode': 'source_only'}:
                                raise ValueError('SUBAGENT_ARGUMENTS')
                        except (ValueError, TypeError, KeyError) as exc:
                            code = tool_error_code(exc)
                            if (call['function'].get('name') == 'submit'
                                    and code == 'SUPPORTING_SPAN_REQUIRED'
                                    and missing_support_args(call['parsed_arguments'])):
                                # Execute submit with the exact parsed args. The
                                # assembler must reject again and deliver feedback;
                                # count the rejection only there, not twice here.
                                continue
                            call['parsed_arguments'] = {'invalid_schema': code}
                            diagnostics.append(code)
                    if choice['finish_reason'] == 'length':
                        choice['message']['tool_calls'] = []
                    result = response
                elif kind == 'assemble':
                    try:
                        submission.assemble_tool(data['args'], item['case'], item['pages'], {'input_tokens': 0, 'output_tokens': 0, 'inference_time_ms': 0})
                        if role == 'parent':
                            if accepted is not None:
                                raise ValueError('DUPLICATE_SUBMIT')
                            accepted = data['args']
                        result = {'ok': True, 'recommendation': data['args']}
                    except (ValueError, TypeError) as exc:
                        code = tool_error_code(exc)
                        diagnostics.append(code)
                        result = {'ok': False, 'error': code}
                        if code == 'SUPPORTING_SPAN_REQUIRED':
                            result['message'] = SUPPORTING_SPAN_MESSAGE
                else:
                    raise Stop('BRIDGE_KIND_REFUSED')
                send({'sequence': message['sequence'], 'result': result})
        finally:
            process.stdin.close()
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            process.stdout.close()


def enforce_tools(payload, ids, role, strategy=None):
    tools = payload.get('tools')
    names = ['submit', 'subagent'] if role == 'parent' and strategy not in ('S', 'R') else ['submit']
    if not isinstance(tools, list) or any(not isinstance(t, dict) or not isinstance(t.get('function'), dict) or not isinstance(t['function'].get('name'), str) for t in tools) or sorted(t['function']['name'] for t in tools) != sorted(names):
        raise Stop('TOOLS_REFUSED')
    # Native HTTP declarations are a compatibility projection, not the stronger
    # Pi TypeBox schema. Compare canonical JSON exactly (bool is not integer).
    expected = {t['function']['name']: t['function']['parameters'] for t in schemas(ids, child=role == 'child', strategy=strategy)}
    for t in tools:
        if set(t) != {'type', 'function'} or t.get('type') != 'function':
            raise Stop('TOOL_SCHEMA_REFUSED')
        function = t['function']
        if set(function) != {'name', 'description', 'parameters'} or not isinstance(function['description'], str):
            raise Stop('TOOL_SCHEMA_REFUSED')
        if legacy.encode(function['parameters']) != legacy.encode(expected[function['name']]):
            raise Stop('TOOL_SCHEMA_REFUSED')
    choice = payload.get('tool_choice', {}).get('function', {}).get('name')
    if choice not in names:
        raise Stop('TOOL_CHOICE_REFUSED')


def run(job, manifest, client_factory):
    try:
        return run_locked(job, manifest, client_factory)
    except BaseException as exc:
        # Even a SDK/deadline failure between confirmed POSTs permanently fences
        # this identity. Do not clear it or silently restart in another job.
        if not (job / 'STOP.json').exists():
            legacy.exclusive(job / 'STOP.json', {'status': 'STOP', 'reason': 'RUN_FAILED_NO_AUTOMATIC_RESUME', **({'http_status': exc.http_status} if type(getattr(exc, 'http_status', None)) is int else {})})
        raise


def run_locked(job, manifest, client_factory):
    ledger = Ledger(job, manifest, client_factory)
    models = manifest.get('models', MODELS)
    count = len(manifest['frozen'])
    if not count:
        raise Stop('EMPTY_CASE_SELECTION')
    order = [(model, i) for model in models for i in range(min(3, count))] + [(model, i) for model in models for i in range(3, count)]
    for model, index in order:
        name = legacy.result_name(model, index).replace('.json', '-case.json')
        if name in ledger.state['cases']:
            continue
        item = manifest['frozen'][index]
        request_model = case_model(manifest['strategy'], model, item['case'])
        started = time.monotonic()
        post = lambda role, number, payload: ledger.post(request_model, index, role, number, payload, deadline=started + CASE_SECONDS)
        sdk_result = None
        if manifest['strategy'] == 'A':
            args, diagnostics = run_a(item, model, post)
        else:
            args, diagnostics, sdk_result = run_b(item, request_model, post, strategy=manifest['strategy'])
        wall = (time.monotonic() - started) * 1000
        metrics, wait = metrics_for(ledger, model, index, wall)
        prediction = submission.assemble_tool(args, item['case'], item['pages'], metrics) if args is not None else submission.fallback(item['case'], item['pages'], metrics)
        record = {'model': model, 'request_model': request_model, 'case_id': item['case']['id'], 'case_index': index, 'prediction': prediction, 'output_valid': args is not None, 'error': None if args is not None else 'NO_ACCEPTED_SUBMIT', 'diagnostics': diagnostics, 'api_wait_ms': wait, 'case_wall_ms': wall, 'sdk': sdk_result}
        ledger.save_case(name, record)
    return summarize(ledger)


def summarize(ledger):
    count = len(ledger.manifest['frozen'])
    summary = {'status': 'completed', 'mode': ledger.manifest.get('mode', 'user-run'), 'cost': 'unknown; no financial cap asserted', 'strategy': ledger.manifest['strategy'], 'generation_requests': ledger.state['requests'], 'actual_total_tokens': ledger.state['tokens'], 'token_budget': ledger.manifest['token_budget'], 'models': {}}
    summary['calls_by_actual_model'] = dict(Counter(r.get('request_model', r['model']) for n, r in ledger.records.items() if n in ledger.state['attempts']))
    if 'role_models' in ledger.manifest:
        summary['role_models'] = ledger.manifest['role_models']
    for model in ledger.manifest.get('models', MODELS):
        subset = [ledger.records[legacy.result_name(model, i).replace('.json', '-case.json')] for i in range(count)]
        wall = sorted(r['case_wall_ms'] for r in subset)
        waits = sorted(r['api_wait_ms'] for r in subset)
        attempts = [record for name, record in ledger.records.items() if name in ledger.state['attempts'] and record['model'] == model]
        summary['models'][model] = {'cases': count, 'output_valid': sum(r['output_valid'] for r in subset), 'evaluation_failures': sum(not r['output_valid'] for r in subset), 'invalid_reasons': dict(Counter(r['error'] for r in subset if r['error'])), 'diagnostic_counts': dict(Counter(d for r in subset for d in r['diagnostics'])), 'prompt_tokens': sum(r['prediction']['metrics']['input_tokens'] for r in subset), 'completion_tokens': sum(r['prediction']['metrics']['output_tokens'] for r in subset), 'total_tokens': sum(r['prediction']['metrics']['input_tokens'] + r['prediction']['metrics']['output_tokens'] for r in subset), 'mean_ms': sum(wall) / count, 'p95_ms': wall[math.ceil(.95 * count) - 1], 'api_wait_ms': sum(waits), 'mean_api_wait_ms': sum(waits) / count, 'p95_api_wait_ms': waits[math.ceil(.95 * count) - 1], 'generation_requests': len(attempts), 'calls_by_role': dict(Counter(record['role'] for record in attempts))}
        prefix = '8b' if model == MODELS[0] else '70b'
        rows = [r['prediction'] if r['output_valid'] else {**r['prediction'], 'error': r['error']} for r in subset]
        for suffix, values in [('predictions', rows), ('canonical', [r['prediction'] for r in subset]), ('diagnostics', [{'id': r['case_id'], 'error': r['error'], 'diagnostics': r['diagnostics']} for r in subset])]:
            path = ledger.job / f'{prefix}-{suffix}.jsonl'
            if not path.exists():
                legacy.exclusive_jsonl(path, values)
    if not (ledger.job / 'summary.json').exists():
        legacy.exclusive(ledger.job / 'summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--user-run', action='store_true')
    parser.add_argument('--strategy', choices=['A', 'B', 'C', 'R'], required=True)
    parser.add_argument('--repeat', type=int, choices=[1, 2], default=1)
    parser.add_argument('--job', type=Path)
    parser.add_argument('--case-ids-file', type=Path, help='Nonempty gold-free JSON list of frozen research input IDs')
    args = parser.parse_args()
    legacy.c.protect()
    if not args.prepare_only and not args.user_run:
        raise Stop('EXPLICIT_USER_RUN_REQUIRED')
    case_ids = json.loads(args.case_ids_file.read_text()) if args.case_ids_file else None
    if args.case_ids_file and not isinstance(case_ids, list):
        raise Stop('INVALID_CASE_SELECTION')
    manifest = prepare(args.strategy, case_ids)
    if args.prepare_only:
        print(json.dumps({'prepared_cases': len(manifest['frozen']), 'strategy': args.strategy, 'manifest_sha256': legacy.digest(legacy.encode(manifest)), 'request_limit': manifest['request_limit'], 'token_budget': manifest['token_budget'], 'credential_reads': 0, 'remote_calls': 0}))
        return
    job = args.job or REPO / f'output/cscs/format-{args.strategy}-r{args.repeat}'
    job.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(job / 'lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        initialize(job, manifest)
        print(json.dumps({'status': 'starting', 'strategy': args.strategy, 'job': str(job), 'models': manifest['models'], 'request_limit': manifest['request_limit'], 'token_budget': manifest['token_budget'], 'output_limit': 256, 'no_automatic_retry': True}), flush=True)
        clients = {}
        def client(model):
            if model not in clients:
                clients[model] = Transport(model)
            return clients[model]
        print(json.dumps(run(job, manifest, client), ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except BaseException:
        print('STOP: uncertain/budget/schema transport failure. Preserve inflight.json and state.pending. No retry, secret or HTTP error body logged.', file=sys.stderr)
        sys.exit(1)
