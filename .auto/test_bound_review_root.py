"""Actual Root guard regression using only fictional SDK packets."""
import copy
import json
import sys
from pathlib import Path

import pytest
sys.path.insert(0, str(Path(__file__).parent))
from test_bound_review import candidate, offline, candidate_manifest, r
import bound_review_research as research
import fragment_review_contract as old_contract


def reviewer_packet():
    manifest = candidate_manifest()
    packets = research.capture_sdk(r, manifest)
    packet = next(p['payload'] for p in packets if p['role'] == 'reviewer')
    return manifest, packet


@pytest.mark.parametrize('mutation', ['plaintext', 'missing', 'subset', 'reordered', 'tampered', 'duplicate', 'schema', 'model', 'tool_choice'])
def test_actual_root_rejects_before_http_constructor(candidate, monkeypatch, mutation):
    manifest, packet = reviewer_packet()
    packet = copy.deepcopy(packet)
    # Use two real fictional source IDs so reversal is substantive.
    source = json.loads(manifest['frozen'][0]['messages'][1]['content'])
    source['source_spans'].append({**source['source_spans'][0], 'span_id': 'second-fictional-id'})
    import bound_review_contract as contract
    r._bound_view = contract.inventory(source)
    packet['tools'][0]['function']['parameters'] = contract.schema(r._bound_view)
    packet['messages'][1]['content'] = contract.projection(source)
    dto = json.loads(packet['messages'][1]['content'])
    if mutation == 'plaintext':
        packet['messages'][1]['content'] = old_contract.projection(source)
    elif mutation == 'missing':
        del dto['source_spans']
    elif mutation == 'subset':
        dto['source_spans'].pop()
    elif mutation == 'reordered':
        dto['source_spans'].reverse()
    elif mutation == 'tampered':
        dto['source_spans'][0]['span_id'] = 'tampered'
    elif mutation == 'duplicate':
        dto['source_spans'][1] = dto['source_spans'][0]
    elif mutation == 'schema':
        packet['tools'][0]['function']['parameters']['additionalProperties'] = True
    elif mutation == 'model':
        packet['model'] = r.MODELS[1]
    elif mutation == 'tool_choice':
        packet['tool_choice'] = 'auto'
    if mutation != 'plaintext':
        packet['messages'][1]['content'] = json.dumps(dto, separators=(',', ':'))
    monkeypatch.setenv('BASE_URL', 'http://fictional.invalid/v1')
    monkeypatch.setenv('API_KEY', 'dummy-not-real')
    constructed = []
    def factory(*a, **kw):
        constructed.append(True)
        pytest.fail('guard must run before HTTP construction')
    with pytest.raises(r.Stop) as error:
        r.Transport(packet['model'], submitted=True, factory=factory).request('POST', '/v1/chat/completions', packet)
    assert not constructed
    if mutation == 'plaintext':
        assert str(error.value) == 'UNDECLARED_TOOLS_REFUSED'


def test_every_export_packet_actual_root_and_environment_restored(candidate, monkeypatch):
    monkeypatch.setenv('BASE_URL', 'untouched-original-base')
    monkeypatch.setenv('API_KEY', 'untouched-original-dummy')
    request = r.Transport.request
    seen = []
    def observed(self, method, path, payload):
        seen.append(copy.deepcopy(payload))
        return request(self, method, path, payload)
    monkeypatch.setattr(r.Transport, 'request', observed)
    # No fixture wrapper: capture_sdk's own post must invoke Root for every packet.
    import bound_review_worker as worker
    r.run_b = lambda *a, **kw: worker.run_candidate(r, *a, **kw)
    manifest = candidate_manifest()
    packets = research.capture_sdk(r, manifest) + research.capture_sdk(r, manifest, populated=False)
    assert seen == [p['payload'] for p in packets]
    assert len(seen) == 8
    import os
    assert os.environ['BASE_URL'] == 'untouched-original-base'
    assert os.environ['API_KEY'] == 'untouched-original-dummy'
    assert all(len(r.legacy.encode(p)) <= 240000 for p in seen)


@pytest.mark.parametrize('mutation', ['fragment_archive', 'role_archive', 'duplicate_bound', 'duplicate_fragment', 'old_bytes'])
def test_dispatch_requires_exact_two_layer_archive_chain(tmp_path, monkeypatch, mutation):
    root = tmp_path
    archive = root / '.auto/protocol-archive'
    archive.mkdir(parents=True)
    role = b'original role bytes\n'
    fragment_block = b'# BEGIN fragment-review-v1 additive\nfragment\n# END fragment-review-v1 additive\n'
    bound_block = b'# BEGIN bound-review-v1 additive\nbound\n# END bound-review-v1 additive\n'
    fragment = fragment_block + role
    current = bound_block + fragment
    role_path = archive / 'role-review-v1-measure.sh'
    fragment_path = archive / 'fragment-review-v1-measure.sh'
    current_path = root / '.auto/measure.sh'
    role_path.write_bytes(role)
    fragment_path.write_bytes(fragment)
    current_path.write_bytes(current)
    monkeypatch.setattr(research, 'ROOT', root)
    research.verify_additive_dispatch('.auto/measure.sh', research.sha(role), research.sha(fragment))
    if mutation == 'fragment_archive':
        fragment_path.write_bytes(fragment + b'changed\n')
    elif mutation == 'role_archive':
        role_path.write_bytes(role + b'changed\n')
    elif mutation == 'duplicate_bound':
        current_path.write_bytes(bound_block + current)
    elif mutation == 'duplicate_fragment':
        fragment_path.write_bytes(fragment_block + fragment)
    else:
        current_path.write_bytes(current + b'changed\n')
    with pytest.raises(ValueError):
        research.verify_additive_dispatch('.auto/measure.sh', research.sha(role), research.sha(fragment))
