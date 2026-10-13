"""Offline wire-only compatibility. Local typed/assembler checks stay stronger."""
import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import run_comparison as r
from test_comparison import item, offline, response, tool


def assert_simple(value):
    if isinstance(value, dict):
        assert not {'anyOf', 'const', 'uniqueItems'} & set(value)
        for child in value.values():
            assert_simple(child)
    elif isinstance(value, list):
        for child in value:
            assert_simple(child)


def test_actual_package_native_schema_projection_exact_and_simple():
    x = item()
    frozen = copy.deepcopy(x)
    calls = []
    def post(role, number, payload):
        calls.append((role, payload))
        assert next(m['content'] for m in payload['messages'] if m['role'] == 'user') == frozen['messages'][1]['content']
        if role == 'parent':
            assert 'First call subagent with compact arguments {"mode":"source_only"}; no blank lines.' in payload['messages'][0]['content']
        else:
            assert 'Use compact JSON arguments, no blank lines.' in payload['messages'][0]['content']
        assert 'Submit arguments must contain exactly label (integer 0, 1, or 2) and candidate_ids (array of exact IDs from this case). No evidence or label_name keys.' in payload['messages'][0]['content']
        expected = {t['function']['name']: t['function']['parameters'] for t in r.schemas(x['candidate_ids'], child=role == 'child')}
        for declaration in payload['tools']:
            if declaration['function']['name'] == 'submit':
                assert 'No evidence or label_name keys.' in declaration['function']['description']
            assert declaration['function']['parameters'] == expected[declaration['function']['name']]
            assert_simple(declaration['function']['parameters'])
        name = payload['tool_choice']['function']['name']
        args = {'mode': 'source_only'} if name == 'subagent' else {'label': 0, 'candidate_ids': x['candidate_ids']}
        return response(r.MODELS[0], calls=[tool(name, args)])
    args, diagnostics, sdk = r.run_b(x, r.MODELS[0], post, seconds=30, isolation_guard=True)
    assert args and not diagnostics and len(calls) == 3 and x == frozen
    assert sdk['counts'] == {'parent': 2, 'child': 1}
    assert any(e['type'] == 'package_child_completed' for e in sdk['events'])


@pytest.mark.parametrize('args', [{}, {'mode': 'other'}, {'mode': 'source_only', 'task': 'arbitrary'}, {'mode': True}])
def test_subagent_fixed_mode_raw_validation_before_pi(args):
    x = item()
    calls = []
    def post(role, number, payload):
        calls.append(role)
        if number == 0:
            return response(r.MODELS[0], calls=[tool('subagent', args)])
        return response(r.MODELS[0], content='no accepted submit')
    accepted, diagnostics, sdk = r.run_b(x, r.MODELS[0], post, seconds=30)
    assert accepted is None and sdk['counts'] == {'parent': 2, 'child': 0}
    assert calls == ['parent', 'parent'] and 'SUBAGENT_ARGUMENTS' in diagnostics
    assert not any(e['type'] == 'package_child_started' for e in sdk['events'])


def test_length_tool_call_remains_flagged_fallback_no_new_loop():
    calls = []
    def post(role, number, payload):
        calls.append(role)
        result = response(r.MODELS[0], calls=[{'id': 'truncated', 'type': 'function', 'function': {'name': 'subagent', 'arguments': '{' + ' ' * 255}}])
        result['choices'][0]['finish_reason'] = 'length'
        result['usage'] = {'prompt_tokens': 80, 'completion_tokens': 256, 'total_tokens': 336}
        return result
    accepted, diagnostics, sdk = r.run_b(item(), r.MODELS[0], post, seconds=30)
    assert accepted is None and calls == ['parent']
    assert sdk['counts'] == {'parent': 1, 'child': 0}
    assert 'INVALID_TOOL_JSON' in diagnostics and 'NO_SUBAGENT_CALL' in diagnostics


def test_reconstructed_old_http400_declaration_rejected_new_projection_passes():
    path = r.REPO / 'output/cscs/format-B-failed-child-payload.json'
    if not path.exists():
        pytest.skip('historical source-only reconstructed payload not installed')
    before = path.read_bytes()
    expected_sha = '1cf94f784f4a613d5a09cbc2ff9a7bab3294c0212343ade7e88a29c2806e805d'
    assert hashlib.sha256(before).hexdigest() == expected_sha
    old = r.submission.strict_json(before.decode())
    ids = [span['span_id'] for span in r.submission.strict_json(old['messages'][1]['content'])['source_spans']]
    assert len(ids) == 15
    assert [entry['const'] for entry in old['tools'][0]['function']['parameters']['properties']['candidate_ids']['items']['anyOf']] == ids
    with pytest.raises(r.Stop, match='TOOL_SCHEMA_REFUSED'):
        r.enforce_tools(old, ids, 'child')
    projected = copy.deepcopy(old)
    projected['tools'][0]['function']['parameters'] = r.schemas(ids, child=True)[0]['function']['parameters']
    r.enforce_tools(projected, ids, 'child')
    assert_simple(projected['tools'][0]['function']['parameters'])
    assert projected['tools'][0]['function']['parameters']['properties']['candidate_ids']['items']['enum'] == ids
    assert path.read_bytes() == before


@pytest.mark.parametrize('mutate', [
    lambda s: s.update(additionalProperties=True),
    lambda s: s['properties']['label'].update(enum=[False, True, 2]),
    lambda s: s['properties']['candidate_ids'].update(uniqueItems=True),
    lambda s: s['properties']['candidate_ids']['items'].update(enum=['unknown']),
    lambda s: s['properties']['candidate_ids'].update(maxItems=6),
])
def test_wire_guard_rejects_looser_or_unknown_schema(mutate):
    x = item()
    declarations = r.schemas(x['candidate_ids'], child=True)
    mutate(declarations[0]['function']['parameters'])
    with pytest.raises(r.Stop, match='TOOL_SCHEMA_REFUSED'):
        r.enforce_tools({'tools': declarations, 'tool_choice': {'type': 'function', 'function': {'name': 'submit'}}}, x['candidate_ids'], 'child')


@pytest.mark.parametrize('bad', ['duplicate', 'unknown_id', 'unknown_label', 'bool_label', 'float_label'])
def test_simple_native_schema_does_not_weaken_local_submit_validation(bad):
    x = item()
    calls = []
    def post(role, number, payload):
        calls.append((role, number, payload))
        assert_simple(payload['tools'])
        name = payload['tool_choice']['function']['name']
        args = {'mode': 'source_only'} if name == 'subagent' else {'label': 0, 'candidate_ids': x['candidate_ids']}
        if role == 'parent' and number == 1:
            if bad == 'duplicate':
                args['candidate_ids'] = x['candidate_ids'] * 2
            elif bad == 'unknown_id':
                args['candidate_ids'] = ['unknown']
            else:
                args['label'] = {'unknown_label': 3, 'bool_label': True, 'float_label': 0.0}[bad]
        return response(r.MODELS[0], calls=[tool(name, args)])
    accepted, diagnostics, sdk = r.run_b(x, r.MODELS[0], post, seconds=30)
    assert accepted == {'label': 0, 'candidate_ids': x['candidate_ids']}
    assert sdk['counts'] == {'parent': 3, 'child': 1} and len(calls) == 4
    expected = {'duplicate': 'DUPLICATE_ID', 'unknown_id': 'UNKNOWN_ID'}.get(bad, 'LABEL_SCHEMA')
    assert expected in diagnostics
    assert any(m['role'] == 'tool' and ('error' in m['content'].lower() or 'validation' in m['content'].lower()) for m in calls[-1][2]['messages'])
