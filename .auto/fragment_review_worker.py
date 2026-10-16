"""Candidate-only worker hooks. No transport selection or data preparation at import."""
from collections import Counter
from contextlib import contextmanager
import json
import hashlib
import os
from pathlib import Path
import select
import shutil
import subprocess
import tempfile
import time

import fragment_review_contract as contract

VARIANT = 'fragment-review-v1-candidate'
TEMPLATES = Path(__file__).with_name('fragment-review-templates')


def install_templates(format_dir):
    """Only call on a fresh isolated workspace, never the production format dir."""
    production = Path(__file__).resolve().parents[1] / 'track_2a/dev/format'
    if format_dir.resolve() == production.resolve():
        raise ValueError('PRODUCTION_WORKSPACE_REFUSED')
    for source in TEMPLATES.iterdir():
        if source.is_file():
            target = format_dir / source.name
            with target.open('xb') as stream:
                stream.write(source.read_bytes())


def enforce_review(core, payload, ids):
    tools = payload.get('tools')
    if payload.get('model') != core.MODELS[0] or type(tools) is not list or len(tools) != 1:
        raise core.Stop('REVIEW_TOOLS_REFUSED')
    tool = tools[0]
    if (type(tool) is not dict or set(tool) != {'type', 'function'} or tool['type'] != 'function'
            or type(tool['function']) is not dict or set(tool['function']) != {'name', 'description', 'parameters'}
            or tool['function']['name'] != 'review_source' or type(tool['function']['description']) is not str
            or core.legacy.encode(tool['function']['parameters']) != core.legacy.encode(contract.schema(core._fragment_view))
            or payload.get('tool_choice') != {'type': 'function', 'function': {'name': 'review_source'}}):
        raise core.Stop('REVIEW_TOOLS_REFUSED')


def enforce_bridge_tools(core, payload, ids, role):
    if role == 'reviewer':
        enforce_review(core, payload, ids)
    else:
        core._role_review_original_enforce(payload, ids, role)


@contextmanager
def candidate_hooks(core, manifest):
    """Dedicated worker process only. Baseline must never enter these hooks."""
    if manifest.get('variant') != VARIANT:
        raise core.Stop('VARIANT_REFUSED')
    old = {name: getattr(core, name) for name in ('fixed_role_model', 'validate_role_models', 'enforce_tools', 'run_b')}
    def fixed(strategy, owner, role):
        if strategy != 'C' or owner != core.MODELS[1] or role not in ('parent', 'child', 'reviewer'):
            raise core.Stop('ROLE_MODEL_REFUSED')
        return core.MODELS[1] if role == 'parent' else core.MODELS[0]
    def validate(m):
        if (m.get('variant') != VARIANT or m.get('strategy') != 'C' or m.get('models') != [core.MODELS[1]]
                or m.get('role_models') != {'parent': core.MODELS[1], 'child': core.MODELS[0], 'reviewer': core.MODELS[0]}):
            raise core.Stop('ROLE_MODEL_REFUSED')
    def transport_tools(payload, ids, role):
        # Root Transport infers child for any non-parent tools. The actual
        # bridge still applies exact role-specific guards before Ledger.post.
        if (role == 'child' and type(payload.get('tools')) is list and len(payload['tools']) == 1
                and type(payload['tools'][0]) is dict and type(payload['tools'][0].get('function')) is dict
                and payload['tools'][0]['function'].get('name') == 'review_source'):
            return enforce_review(core, payload, ids)
        return old['enforce_tools'](payload, ids, role)
    validate(manifest)
    core._role_review_original_enforce = old['enforce_tools']
    core.fixed_role_model, core.validate_role_models = fixed, validate
    core.enforce_tools = transport_tools
    core.run_b = lambda *args, **kwargs: run_candidate(core, *args, **kwargs)
    try:
        yield core
    finally:
        for name, value in old.items():
            setattr(core, name, value)
        del core._role_review_original_enforce
        if hasattr(core, '_fragment_view'):
            del core._fragment_view


def run_candidate(core, item, model, post, seconds=300, isolation_guard=True, strategy='C'):
    """Python owns the assembler and all requests. Node receives no credentials."""
    Stop, submission = core.Stop, core.submission
    fixed_role_model = core.fixed_role_model
    tool_error_code = core.tool_error_code
    missing_support_args = core.missing_support_args
    SUPPORTING_SPAN_MESSAGE = core.SUPPORTING_SPAN_MESSAGE
    HERE = core.HERE
    source = submission.strict_json(item['messages'][1]['content'])
    core._fragment_view = contract.inventory(source)
    review_user = contract.projection(source, core._fragment_view)
    accepted_review = None
    child_recommendation = None
    parent_tool_reports = []
    fixed_role_model(strategy, model, 'parent')
    child_model = fixed_role_model(strategy, model, 'child')
    with tempfile.TemporaryDirectory(prefix='ost-pi-', dir='/tmp') as home:
        node = shutil.which('node')
        if not node:
            raise Stop('NODE_EXECUTABLE_MISSING')
        env = {'PATH': os.defpath, 'HOME': home, 'PI_CODING_AGENT_DIR': home, 'PI_OFFLINE': '1'}
        if os.environ.get('PI_PACKAGE_ROOT'):
            env['PI_PACKAGE_ROOT'] = os.environ['PI_PACKAGE_ROOT']
        if os.environ.get('PI_SUBAGENTS_ROOT'):
            env['PI_SUBAGENTS_ROOT'] = os.environ['PI_SUBAGENTS_ROOT']
        command = [node] + (['--import', str(HERE / 'isolation-guard.mjs')] if isolation_guard else []) + [str(HERE / 'role-review-entry.ts')]
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, env=env)
        deadline = time.monotonic() + seconds
        counters = Counter()
        submit_calls = Counter()
        accepted = None
        diagnostics = []
        def send(value):
            process.stdin.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + '\n')
            process.stdin.flush()
        send({'model': model, 'strategy': strategy, 'child_model': child_model, 'ids': item['candidate_ids'], 'system': item['messages'][0]['content'], 'user': item['messages'][1]['content'], 'reviewer_model': core.MODELS[0], 'review_user': review_user, 'review_schema': contract.schema(core._fragment_view), 'review_system': contract.REVIEW_SYSTEM, 'review_note': contract.NOTE})
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
                    if not message['result']['counts']['child']:
                        diagnostics.append('NO_SUBAGENT_CALL')
                    sdk_result = message['result']
                    sdk_result['review_audit'] = {'input_sha256': hashlib.sha256(item['messages'][1]['content'].encode()).hexdigest(), 'parent_tool_reports': parent_tool_reports, 'normal_child_recommendation': child_recommendation, 'role_models': {'parent': model, 'child': child_model, 'reviewer': core.MODELS[0]}}
                    return accepted, diagnostics, sdk_result
                if kind == 'fatal':
                    raise Stop('SDK_FATAL_ALL_STOP')
                data = message['data']
                role = data.get('role')
                if role not in ('parent', 'child', 'reviewer'):
                    raise Stop('ROLE_REFUSED')
                if kind == 'request':
                    payload = data['payload']
                    if payload.get('model') != fixed_role_model(strategy, model, role):
                        raise Stop('ROLE_MODEL_REFUSED')
                    enforce_bridge_tools(core, payload, item['candidate_ids'], role)
                    if role in ('parent', 'child'):
                        users = [m for m in payload['messages'] if m['role'] == 'user']
                        if users != [{'role': 'user', 'content': item['messages'][1]['content']}]:
                            raise Stop('ORIGINAL_USER_CHANGED')
                    if role == 'reviewer' and counters[role] == 0:
                        users = [m for m in payload['messages'] if m['role'] == 'user']
                        if users != [{'role': 'user', 'content': review_user}] or any(m['role'] not in ('system', 'user') for m in payload['messages']):
                            raise Stop('REVIEW_INDEPENDENCE_REFUSED')
                    if role == 'parent':
                        for msg in payload['messages']:
                            if msg['role'] == 'tool':
                                try:
                                    report = submission.strict_json(msg['content'])
                                except (ValueError, TypeError):
                                    continue
                                if type(report) is dict and set(report) == {'recommendation', 'source_review'} and report not in parent_tool_reports:
                                    if report['recommendation'] != (child_recommendation if child_recommendation is not None else {'status': 'recommendation_unavailable', 'reason': 'NO_CHILD_SUBMIT'}):
                                        raise Stop('CHILD_RESULT_AUDIT_REFUSED')
                                    if accepted_review is not None and report['source_review'] != accepted_review:
                                        raise Stop('REVIEW_RESULT_AUDIT_REFUSED')
                                    parent_tool_reports.append(report)
                    if counters[role] >= (3 if role == 'parent' else 2) or accepted is not None or (role == 'reviewer' and accepted_review is not None):
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
                        if call['function'].get('name') not in ({'review_source'} if role == 'reviewer' else {'submit', 'subagent'} if role == 'parent' else {'submit'}):
                            raise Stop('ROLE_TOOL_REFUSED')
                        if call['function'].get('name') in ('submit', 'review_source'):
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
                            if role == 'reviewer':
                                response['review_rejection'] = code
                            continue
                        try:
                            # Pi's TypeBox validator may coerce strings. Keep all
                            # strict gates before forwarding to tool execution.
                            if role == 'reviewer':
                                contract.structural(call['parsed_arguments'], core._fragment_view)
                            elif call['function'].get('name') == 'submit':
                                submission.assemble_tool(call['parsed_arguments'], item['case'], item['pages'], {'input_tokens': 0, 'output_tokens': 0, 'inference_time_ms': 0})
                            elif call['function'].get('name') == 'subagent' and call['parsed_arguments'] != {'mode': 'source_only'}:
                                raise ValueError('SUBAGENT_ARGUMENTS')
                        except (ValueError, TypeError, KeyError) as exc:
                            code = str(exc) if type(exc) is ValueError and str(exc) in contract.ERRORS else tool_error_code(exc)
                            if (call['function'].get('name') == 'submit'
                                    and code == 'SUPPORTING_SPAN_REQUIRED'
                                    and missing_support_args(call['parsed_arguments'])):
                                # Execute submit with the exact parsed args. The
                                # assembler must reject again and deliver feedback;
                                # count the rejection only there, not twice here.
                                continue
                            call['parsed_arguments'] = {'invalid_schema': code}
                            diagnostics.append(code)
                            if role == 'reviewer':
                                response['review_rejection'] = code
                    if choice['finish_reason'] == 'length':
                        choice['message']['tool_calls'] = []
                    result = response
                elif kind == 'review':
                    if role != 'reviewer' or accepted_review is not None:
                        raise Stop('ROLE_TOOL_REFUSED')
                    try:
                        accepted_review = contract.validate(data['args'], source)
                        result = {'ok': True, 'source_review': accepted_review}
                    except (ValueError, TypeError) as exc:
                        code = str(exc) if type(exc) is ValueError and str(exc) in contract.ERRORS else 'REVIEW_SCHEMA'
                        diagnostics.append(code)
                        result = {'ok': False, 'error': code}
                elif kind == 'assemble':
                    if role == 'reviewer':
                        raise Stop('ROLE_TOOL_REFUSED')
                    try:
                        submission.assemble_tool(data['args'], item['case'], item['pages'], {'input_tokens': 0, 'output_tokens': 0, 'inference_time_ms': 0})
                        if role == 'parent':
                            if accepted is not None:
                                raise ValueError('DUPLICATE_SUBMIT')
                            accepted = data['args']
                        else:
                            child_recommendation = data['args']
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

