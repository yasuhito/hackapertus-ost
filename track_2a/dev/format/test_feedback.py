"""Fictional native Pi feedback regressions; no inference or gold labels."""
import copy
import json

import pytest

from test_comparison import offline, item, response, tool, r

MESSAGE = ('Labels 0 and 2 require supplied supporting candidate IDs. '
           'Recheck the source judgment and cite supporting supplied IDs; '
           'do not invent IDs or change the label only to satisfy formatting.')


@pytest.mark.parametrize('label', [0, 2])
def test_support_feedback_causes_fake_provider_repair_in_both_roles(label):
    x = item()
    before = copy.deepcopy(x)
    requests = []
    visible = []
    def post(role, number, payload):
        requests.append((role, number, payload))
        assert payload['max_tokens'] == 256 and payload['model'] == r.MODELS[1]
        r.enforce_tools(payload, x['candidate_ids'], role)
        name = payload['tool_choice']['function']['name']
        if name == 'subagent':
            args = {'mode': 'source_only'}
        else:
            feedback = {'ok': False, 'error': 'SUPPORTING_SPAN_REQUIRED', 'message': MESSAGE}
            seen = any(m['role'] == 'tool' and json.loads(m['content']) == feedback
                       for m in payload['messages'])
            if seen:
                visible.append(role)
                assert 'invalid_schema' not in json.dumps(payload['messages'])
                assert 'INVALID_TOOL_JSON' not in json.dumps(payload['messages'])
            # The fake alone makes the source decision; adapter cannot change label.
            args = {'label': label, 'candidate_ids': x['candidate_ids'] if seen else []}
        return response(r.MODELS[1], calls=[tool(name, args)])
    accepted, diagnostics, sdk = r.run_b(x, r.MODELS[1], post, seconds=45, isolation_guard=True)
    assert accepted == {'label': label, 'candidate_ids': x['candidate_ids']}
    assert visible == ['child', 'parent']
    assert diagnostics == ['SUPPORTING_SPAN_REQUIRED'] * 2
    assert sdk['counts'] == {'parent': 3, 'child': 2}
    assert [(role, number) for role, number, _ in requests] == [('parent', 0), ('child', 0), ('child', 1), ('parent', 1), ('parent', 2)]
    assert x == before
    for role in ('parent', 'child'):
        role_requests = [p for rr, _, p in requests if rr == role]
        assert all(p['messages'][0] == role_requests[0]['messages'][0] for p in role_requests)
        assert all(p['tools'] == role_requests[0]['tools'] for p in role_requests)
    assert not any(e['type'].startswith('auto_') for e in sdk['events'])


@pytest.mark.parametrize('bad,code', [
    ('syntax', 'INVALID_TOOL_JSON'), ('keys', 'DUPLICATE_JSON_KEY'),
    ('unknown', 'UNKNOWN_ID'), ('duplicate', 'DUPLICATE_ID'),
    ('string', 'LABEL_SCHEMA'), ('bool', 'LABEL_SCHEMA'),
    ('extra', 'TOOL_SCHEMA'), ('missing', 'TOOL_SCHEMA'), ('nonarray', 'IDS_SCHEMA'),
])
def test_other_invalid_submits_never_forward_to_assembler(bad, code, monkeypatch):
    x = item()
    assembly = []
    original = r.submission.assemble_tool
    def assemble(args, *rest):
        assembly.append(copy.deepcopy(args))
        return original(args, *rest)
    monkeypatch.setattr(r.submission, 'assemble_tool', assemble)
    args = {'label': 0, 'candidate_ids': []}
    if bad == 'unknown': args['candidate_ids'] = ['fictional-unknown']
    if bad == 'duplicate': args['candidate_ids'] = x['candidate_ids'] * 2
    if bad == 'string': args['label'] = '0'
    if bad == 'bool': args['label'] = False
    if bad == 'extra': args['extra'] = 'fictional'
    if bad == 'missing': del args['label']
    if bad == 'nonarray': args['candidate_ids'] = ''
    raw = json.dumps(args)
    if bad == 'syntax': raw = '{'
    if bad == 'keys': raw = '{"label":0,"label":0,"candidate_ids":[]}'
    def post(role, number, payload):
        name = payload['tool_choice']['function']['name']
        call = tool(name, {'mode': 'source_only'})
        if name == 'submit': call['function']['arguments'] = raw
        if (role == 'child' and number == 1) or (role == 'parent' and number == 2):
            text = json.dumps(payload['messages'])
            assert code in text and 'invalid_schema' in text
            assert 'SUPPORTING_SPAN_REQUIRED' not in text
        return response(r.MODELS[1], calls=[call])
    accepted, diagnostics, sdk = r.run_b(x, r.MODELS[1], post, seconds=45, isolation_guard=True)
    assert accepted is None and diagnostics == [code] * 4
    assert sdk['counts'] == {'parent': 3, 'child': 2}
    # All calls here are prechecks. Invalid arguments must not execute submit.
    assert len(assembly) == (0 if bad in ('syntax', 'keys') else 4)
    # Pi emits execution_start before TypeBox validation, not just execute().
    endings = [e for e in sdk['events'] if e['type'] == 'tool_execution_end' and e.get('toolName') == 'submit']
    # Only the parent session subscribes to these events; child payloads above
    # independently verify its validation feedback.
    assert len(endings) == 2 and all(e['role'] == 'parent' and e['isError'] for e in endings)


@pytest.mark.parametrize('exc,expected', [
    (ValueError('supporting span required'), 'SUPPORTING_SPAN_REQUIRED'),
    (TypeError('supporting span required'), 'SOURCE_OR_SCHEMA_INVALID'),
    (ValueError('UNKNOWN_ID'), 'UNKNOWN_ID'),
    (ValueError('SECRET_UPPERCASE'), 'SOURCE_OR_SCHEMA_INVALID'),
    (KeyError('UNKNOWN_ID'), 'SOURCE_OR_SCHEMA_INVALID'),
    (ValueError('fictional private body'), 'SOURCE_OR_SCHEMA_INVALID'),
])
def test_error_classifier_does_not_leak_unmatched_bodies(exc, expected):
    assert r.tool_error_code(exc) == expected


@pytest.mark.parametrize('args', [
    {'label': '0', 'candidate_ids': []}, {'label': False, 'candidate_ids': []},
    {'label': 1, 'candidate_ids': []}, {'label': 0, 'candidate_ids': ()},
    {'label': 0, 'candidate_ids': [], 'extra': 1}, [], None,
])
def test_forwarding_guard_is_strict(args):
    assert not r.missing_support_args(args)
