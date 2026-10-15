"""Hand-formed fictional fixtures on the real native SDK/core seam."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import diagnose_format_failures as diagnosis


@pytest.fixture
def r():
    return diagnosis.runner()


def fictional_item(r):
    case = {'id': 'fictional', 'claim': {'text': 'A fictional lamp is lit.'}, 'reference': {'text': 'A fictional lamp is lit.'}}
    pages, messages = r.legacy.engine().context(case, Path('.'))
    return {'case': case, 'pages': pages, 'messages': messages,
            'candidate_ids': [c['span_id'] for c in r.candidates(pages, True)]}


def replay_fiction(r, duplicate=False, observations=None):
    item = fictional_item(r)
    sequence = []
    def cached(role, number, payload):
        sequence.append((role, number + 1))
        if observations is not None:
            observations.append((role, number, payload))
        function = payload['tool_choice']['function']['name']
        # Entirely fictional; no captured labels, claims or IDs are fixtures.
        args = {'mode': 'source_only'} if function == 'subagent' else {'label': 0, 'candidate_ids': []}
        if duplicate and role == 'child':
            args['candidate_ids'] = [item['candidate_ids'][0]] * 2
        raw = json.dumps(args, separators=(',', ':'))
        assert r.submission.strict_json(raw) == args
        return {'id': 'fictional-response', 'model': payload['model'],
                'usage': {'prompt_tokens': 20, 'completion_tokens': 13, 'total_tokens': 33},
                'choices': [{'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': None,
                    'tool_calls': [{'id': f'fictional-{role}-{number}', 'type': 'function',
                        'function': {'name': function, 'arguments': raw}}]}}]}
    with diagnosis.offline(r):
        result = r.run_b(item, r.MODELS[1], cached, seconds=45, isolation_guard=True)
    return result, sequence


@pytest.mark.parametrize('duplicate', [False, True])
def test_valid_json_can_reproduce_fallback(r, duplicate):
    (accepted, diagnostics, sdk), sequence = replay_fiction(r, duplicate)
    assert accepted is None
    assert diagnostics == (['DUPLICATE_ID'] * 2 + ['SUPPORTING_SPAN_REQUIRED'] * 2 if duplicate else ['SUPPORTING_SPAN_REQUIRED'] * 4)
    assert sdk['counts'] == {'parent': 3, 'child': 2}
    assert sequence == [('parent', 1), ('child', 1), ('child', 2), ('parent', 2), ('parent', 3)]
    assert not any(e['type'].startswith('auto_') for e in sdk['events'])


def test_valid_json_missing_support_is_not_accepted(r):
    (accepted, _, _), _ = replay_fiction(r)
    assert accepted is None


def test_network_and_transport_factories_are_forbidden(r):
    with diagnosis.offline(r):
        with pytest.raises(AssertionError, match='OFFLINE_NETWORK'):
            r.http.client.HTTPSConnection('fictional.invalid')
        with pytest.raises(AssertionError, match='OFFLINE_NETWORK'):
            r.Transport(r.MODELS[1])
        with pytest.raises(AssertionError, match='OFFLINE_NETWORK'):
            diagnosis.socket.create_connection(('fictional.invalid', 443))


def test_instrumentation_identifies_real_prebridge_exception(r):
    with diagnosis.Instrument(r) as instrument:
        (accepted, diagnostics, sdk), _ = replay_fiction(r)
    assert accepted is None
    assert diagnostics == ['SUPPORTING_SPAN_REQUIRED'] * 4
    assert sdk['counts'] == {'parent': 3, 'child': 2}
    assert len(instrument.events) == 8
    assert {e['code'] for e in instrument.events} == {'SUPPORTING_SPAN_REQUIRED'}
    assert {e['stage'] for e in instrument.events} == {'restore'}
    assert {e['exception'] for e in instrument.events} == {'ValueError'}
    item = fictional_item(r)
    direct = diagnosis.direct_probe(r, '{"label":0,"candidate_ids":[]}', item)
    assert all(e['argument_hash'] == direct['argument_hash'] for e in instrument.events)


def test_missing_support_feedback_reaches_real_sdk_tool_message(r):
    observations = []
    (_, diagnostics, _), _ = replay_fiction(r, observations=observations)
    message = ('Labels 0 and 2 require supplied supporting candidate IDs. '
               'Recheck the source judgment and cite supporting supplied IDs; '
               'do not invent IDs or change the label only to satisfy formatting.')
    for role, number in [('child', 1), ('parent', 2)]:
        payload = next(p for rr, n, p in observations if (rr, n) == (role, number))
        results = [json.loads(m['content']) for m in payload['messages'] if m['role'] == 'tool']
        assert {'ok': False, 'error': 'SUPPORTING_SPAN_REQUIRED', 'message': message} in results
        assert 'invalid_schema' not in json.dumps(payload['messages'])
        assert 'INVALID_TOOL_JSON' not in json.dumps(payload['messages'])
    assert diagnostics == ['SUPPORTING_SPAN_REQUIRED'] * 4


def test_observer_preserves_acceptance_and_strict_types(r):
    item = fictional_item(r)
    for args, code in [
        ({'label': 0, 'candidate_ids': []}, 'SUPPORTING_SPAN_REQUIRED'),
        ({'label': '0', 'candidate_ids': []}, 'LABEL_SCHEMA'),
        ({'label': 1, 'candidate_ids': []}, 'ACCEPTED'),
        ({'label': 0, 'candidate_ids': item['candidate_ids'][:1]}, 'ACCEPTED'),
        ({'label': 1, 'candidate_ids': item['candidate_ids'][:1]}, 'ACCEPTED'),
        ({'label': 0, 'candidate_ids': item['candidate_ids'][:1] * 2}, 'DUPLICATE_ID'),
    ]:
        with diagnosis.Instrument(r) as instrument:
            try:
                observed = r.submission.assemble_tool(args, item['case'], item['pages'], diagnosis.METRICS)
            except ValueError as observed_exc:
                with pytest.raises(type(observed_exc)) as original_exc:
                    instrument.stack.close()
                    r.submission.assemble_tool(args, item['case'], item['pages'], diagnosis.METRICS)
                assert str(original_exc.value) == str(observed_exc)
            else:
                instrument.stack.close()
                assert observed == r.submission.assemble_tool(args, item['case'], item['pages'], diagnosis.METRICS)
        assert instrument.events[0]['code'] == code
