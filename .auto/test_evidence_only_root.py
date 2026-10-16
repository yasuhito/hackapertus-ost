"""Actual Root guard regression using only fictional SDK packets."""
import copy
import json
import sys
from pathlib import Path

import pytest
sys.path.insert(0, str(Path(__file__).parent))
from test_evidence_only import candidate, offline, candidate_manifest, r
import evidence_only_research as research
import fragment_review_contract as old_contract


def reviewer_packet():
    manifest = candidate_manifest()
    packets = research.capture_sdk(r, manifest)
    packet = next(p['payload'] for p in packets if p['role'] == 'child')
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
    import evidence_only_worker as worker
    r.run_b = lambda *a, **kw: worker.run_candidate(r, *a, **kw)
    manifest = candidate_manifest()
    packets = research.capture_sdk(r, manifest) + research.capture_sdk(r, manifest, populated=False)
    assert seen == [p['payload'] for p in packets]
    assert len(seen) == 6
    import os
    assert os.environ['BASE_URL'] == 'untouched-original-base'
    assert os.environ['API_KEY'] == 'untouched-original-dummy'
    assert all(len(r.legacy.encode(p)) <= 240000 for p in seen)




def test_real_three_archive_chain_pins_and_current_addition():
    import hashlib
    role = research.load(research.OLD_CONTROL)
    fragment = research.load(research.FRAGMENT_CONTROL)
    bound = research.load(research.BOUND_CONTROL)
    for relative in research.BOUND_DISPATCH_SHA256:
        research.verify_additive_dispatch(relative, role['controls'][relative],
                                         fragment['controls'][relative], bound['controls'][relative])
    # Source hashes only: no old verifier, execution, grading or individual cases.
    for control in (role, fragment, bound):
        for relative, digest in control['controls'].items():
            if relative not in research.BOUND_DISPATCH_SHA256:
                assert hashlib.sha256((research.ROOT / relative).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize('mutation', ['role', 'fragment', 'bound', 'current', 'duplicate', 'bound_hash'])
def test_full_archive_chain_mutations_fence(tmp_path, monkeypatch, mutation):
    root = tmp_path
    archive = root / '.auto/protocol-archive'; archive.mkdir(parents=True)
    role = b'original role bytes\n'
    def block(name):
        return f'# BEGIN {name} additive\nfictional dispatch\n# END {name} additive\n'.encode()
    fragment = block('fragment-review-v1') + role
    bound = block('bound-review-v1') + fragment
    current = block('evidence-only-v1') + bound
    paths = {}
    for name, raw in [('role', role), ('fragment', fragment), ('bound', bound)]:
        paths[name] = archive / (name + '-review-v1-measure.sh')
        paths[name].write_bytes(raw)
    paths['current'] = root / '.auto/measure.sh'; paths['current'].write_bytes(current)
    monkeypatch.setattr(research, 'ROOT', root)
    monkeypatch.setattr(research, 'BOUND_DISPATCH_SHA256', {'.auto/measure.sh': research.sha(bound)})
    args = ('.auto/measure.sh', research.sha(role), research.sha(fragment), research.sha(bound))
    research.verify_additive_dispatch(*args)
    if mutation == 'bound_hash':
        monkeypatch.setattr(research, 'BOUND_DISPATCH_SHA256', {'.auto/measure.sh': 'a'*64})
    elif mutation == 'duplicate':
        paths['current'].write_bytes(block('evidence-only-v1') + current)
    else:
        paths[mutation].write_bytes(paths[mutation].read_bytes() + b'drift\n')
    with pytest.raises(ValueError):
        research.verify_additive_dispatch(*args)
