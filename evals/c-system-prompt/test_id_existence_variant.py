"""Synthetic offline actual SDK tests for the one local membership tool."""
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

import pytest
sys.path.insert(0, str(Path(__file__).parent))
import variant
import analyze_runs as analysis
from test_evidence_variant import item_for

REPO = Path(__file__).resolve().parents[2]
NAME = 'id-existence-check'

@pytest.fixture(scope='module')
def local(tmp_path_factory):
    root = tmp_path_factory.mktemp('id-source')
    archive = subprocess.check_output(['git', 'archive', 'HEAD', 'track_2a/src', 'track_2a/dev/cscs', 'track_2a/dev/format'], cwd=REPO)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(root, filter='data')
    spec = variant.apply(root, NAME)
    sys.path.insert(0, str(root / 'track_2a/dev/format'))
    loader = importlib.util.spec_from_file_location('id_variant', root / 'track_2a/dev/format/run_comparison.py')
    r = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(r)
    (root / 'booklets').mkdir()
    rows = [json.loads(line) for line in (REPO / 'track_2a/dev/cscs/fixtures/cases-portable.jsonl').read_text().splitlines()]
    names = {Path(row['booklet']['path']).name for row in rows if 'booklet' in row}
    for name in sorted(names):
        (root / 'booklets' / name).symlink_to(REPO / 'booklets' / name)
    yield r, root, spec
    sys.path.remove(str(root / 'track_2a/dev/format'))


def test_membership_only_and_strict(local):
    r, root, spec = local
    assert (root / 'track_2a/dev/format/package-child.mjs').read_bytes() == (REPO / 'track_2a/dev/format/package-child.mjs').read_bytes()
    assert r.check_candidate_ids({'candidate_ids': []}, ['known']) == []
    assert r.check_candidate_ids({'candidate_ids': ['known', 'unknown', 'known']}, ['known']) == [
        {'candidate_id': 'known', 'exists': True}, {'candidate_id': 'unknown', 'exists': False}, {'candidate_id': 'known', 'exists': True}]
    for bad in [None, {}, {'candidate_ids': 'known'}, {'candidate_ids': [1]}, {'candidate_ids': [True]}, {'candidate_ids': ['known'] * 6}, {'candidate_ids': [], 'label': 1}]:
        with pytest.raises(ValueError, match='CHECK_ARGUMENTS'):
            r.check_candidate_ids(bad, ['known'])
    for audit, item in zip(spec['schema_audit'], r.prepare('C')['frozen']):
        tools = r.schemas(item['candidate_ids'])
        assert variant.digest(r.legacy.encode(tools[:2])) == audit['base_parent_schema_sha256']
        assert tools[0] == r.schemas(item['candidate_ids'], child=True)[0]
        assert variant.digest(r.legacy.encode(tools[0])) == audit['parent_submit_schema_sha256']


@pytest.mark.parametrize('bad', [None, 'final', 'type', 'extra', 'six', 'child-check', 'repeat', 'skip', 'duplicate-check', 'early-check'])
def test_real_sdk(local, monkeypatch, tmp_path, bad):
    r, _, _ = local
    import socket
    def denied(*a, **kw):
        raise AssertionError('NO_NETWORK_OR_KEY_READ')
    monkeypatch.setattr(socket, 'socket', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(r.legacy.c, 'read_key', denied)
    item = item_for(r)
    id = item['candidate_ids'][0]
    payloads = []
    def post(role, number, payload):
        payloads.append((role, number, copy.deepcopy(payload)))
        assert payload['model'] == r.MODELS[1 if role == 'parent' else 0]
        assert payload['messages'][1]['content'] == item['messages'][1]['content']
        name = payload['tool_choice']['function']['name']
        if role == 'child':
            assert name == 'submit'
            assert [t['function']['name'] for t in payload['tools']] == ['submit']
            args = {'label': 0, 'candidate_ids': [id]}
            if bad == 'child-check' and number == 0:
                name, args = 'check_candidate_ids', {'candidate_ids': [id]}
        elif name == 'subagent':
            args = {'mode': 'source_only'}
        elif name == 'check_candidate_ids':
            args = {'candidate_ids': [id, 'unknown', id]}
            if bad == 'type': args = {'candidate_ids': [1]}
            if bad == 'extra': args['extra'] = 1
            if bad == 'six': args['candidate_ids'] *= 2
            if bad == 'skip': name, args = 'submit', {'label': 1, 'candidate_ids': []}
        else:
            if bad not in ('type', 'extra', 'six', 'skip'):
                check_msgs = [json.loads(m['content']) for m in payload['messages'] if m['role'] == 'tool' and m['tool_call_id'] == 'parent1']
                assert check_msgs == [[{'candidate_id': id, 'exists': True}, {'candidate_id': 'unknown', 'exists': False}, {'candidate_id': id, 'exists': True}]]
            # Deliberately independent final decision, not corrected to checked IDs/child label.
            args = {'label': 1, 'candidate_ids': []}
            if bad == 'final': args = {'label': 2, 'candidate_ids': []}
            if bad == 'repeat': name, args = 'check_candidate_ids', {'candidate_ids': []}
        wire = json.dumps(payload['tools'])
        assert all(x not in wire for x in ('uniqueItems', 'anyOf', '"const"'))
        response = {'id': 'offline', 'model': payload['model'], 'choices': [{'finish_reason': 'tool_calls', 'message': {'role': 'assistant', 'content': None, 'tool_calls': [{'id': role + str(number), 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(args)}}]}}], 'usage': {'prompt_tokens': 80, 'completion_tokens': 20, 'total_tokens': 100}}
        if role == 'parent' and ((bad == 'duplicate-check' and number == 1) or (bad == 'early-check' and number == 0)):
            response['choices'][0]['message']['tool_calls'].append({
                'id': 'extra-check', 'type': 'function',
                'function': {'name': 'check_candidate_ids', 'arguments': json.dumps({'candidate_ids': [id]})}})
        (tmp_path / f'70b-00-{role}-{number}.json').write_text(json.dumps({'request_model': payload['model'], 'response': response}))
        return response
    args, diagnostics, sdk = r.run_b(item, r.MODELS[1], post, strategy='C', isolation_guard=True, seconds=30)
    assert sdk['counts'] == {'parent': 3, 'child': 2 if bad == 'child-check' else 1}
    assert len([p for role, n, p in payloads if role == 'parent']) == 3
    assert [p['tool_choice']['function']['name'] for role, n, p in payloads if role == 'parent'] == ['subagent', 'check_candidate_ids', 'submit']
    if bad in (None, 'child-check', 'duplicate-check', 'early-check'):
        assert args == {'label': 1, 'candidate_ids': []}
        assert sdk['recommendation'] == args
        check = sdk['id_check']
        assert check['call_count'] == (2 if bad in ('duplicate-check', 'early-check') else 1)
        assert check['successful']
        assert check['inputs_results'] == [{'candidate_ids': [id, 'unknown', id], 'checks': [
            {'candidate_id': id, 'exists': True}, {'candidate_id': 'unknown', 'exists': False}, {'candidate_id': id, 'exists': True}]}]
        if bad == 'duplicate-check': assert 'CHECK_LIMIT_OR_ROLE' in diagnostics
        if bad == 'early-check': assert 'TOOL_ORDER_OR_ROLE' in diagnostics
        assert check['unknown_ids'] == ['unknown'] and check['checked_ids'] == [id, 'unknown', id]
        assert check['submitted_ids'] == [] and check['checked_vs_submitted_mismatch']
        assert analysis.id_check_structure({'sdk': sdk}) == (bad not in ('duplicate-check', 'early-check'))
        record = {'case_index': 0, 'sdk': sdk}
        assert analysis.id_check_attempts(tmp_path, record) == (bad is None)
        if bad is None:
            parent_path = tmp_path / '70b-00-parent-1.json'
            saved = json.loads(parent_path.read_text())
            saved['response']['model'] = r.MODELS[0]
            parent_path.write_text(json.dumps(saved))
            assert not analysis.id_check_attempts(tmp_path, record)
    else:
        assert args is None and sdk['recommendation'] is None and diagnostics
        assert sdk['id_check']['call_count'] == (2 if bad == 'repeat' else 0 if bad == 'skip' else 1)


@pytest.mark.parametrize('mutation', ['model', 'cap', 'data', 'submit', 'source', 'marker', 'mixed'])
def test_exact_audit(local, monkeypatch, tmp_path, mutation):
    r, _, spec = local
    monkeypatch.setenv('OST_VARIANT_PATCH_SHA256', spec['patch_sha256'])
    m = r.prepare('C')
    variant.verify_manifest(m, NAME)
    corrupt = copy.deepcopy(m)
    if mutation == 'model': corrupt['role_models']['child'] = r.MODELS[1]
    if mutation == 'cap': corrupt['parent_completion_limit'] = 4
    if mutation == 'data': corrupt['frozen'][0]['pages'] = ['changed']
    if mutation == 'submit': corrupt['frozen'][0]['schema_sha256'] = 'changed'
    if mutation == 'source': corrupt['sources']['track_2a/dev/format/sdk.ts'] = 'changed'
    if mutation == 'marker': corrupt['variant'] = variant.NAME
    if mutation == 'mixed': corrupt['sources']['track_2a/dev/format/package-child.mjs'] = variant.specification()[0]['role_hashes']['track_2a/dev/format/package-child.mjs']
    with pytest.raises(ValueError): variant.verify_manifest(corrupt, NAME)
    (tmp_path / 'manifest.json').write_text(json.dumps(m))
    with pytest.raises(ValueError, match='EXPLICIT_OPTION'): analysis.audit([tmp_path], False)
    with pytest.raises(ValueError): analysis.audit([tmp_path], False, variant.NAME)
    assert analysis.audit([tmp_path], False, NAME)['requested_variant'] == NAME


def test_historical_exact_and_schema_delta(local, monkeypatch, tmp_path):
    r, _, spec = local
    monkeypatch.setenv('OST_VARIANT_PATCH_SHA256', spec['patch_sha256'])
    m = r.prepare('C')
    (tmp_path / 'manifest.json').write_text(json.dumps(m))
    jobs = [REPO / 'output/cscs' / x for x in spec['historical_baseline_metadata']['approved_jobs']]
    if not all((j / 'manifest.json').exists() for j in jobs): pytest.skip('historical manifests unavailable')
    with pytest.raises(ValueError, match='REQUIRES_CLI_FLAG'): analysis.audit(jobs + [tmp_path], False, NAME)
    assert len(analysis.audit(jobs + [tmp_path], True, NAME)['differences']) == 6
    wrong = json.loads((jobs[0] / 'manifest.json').read_text())
    wrong['frozen'][0]['schema_sha256'] = m['frozen'][0]['schema_sha256']
    with pytest.raises(ValueError, match='FROZEN'): variant.verify_baseline(wrong, True, NAME)


def test_qualification_not_child_label_free():
    comparisons = {s: {'literal_pass': True, 'strict_reference_pass': True, 'candidate_safe_all': True} for s in ('train', 'test')}
    candidate = {s: {'child_label_free_all': False, 'id_check_structural_all': True} for s in ('train', 'test')}
    assert analysis.adoption(comparisons, candidate, NAME) == {'adopt_literal': True, 'adopt_strict': True}
    candidate['train']['id_check_structural_all'] = False
    assert analysis.adoption(comparisons, candidate, NAME) == {'adopt_literal': False, 'adopt_strict': False}


def test_schema_audit_delta_is_exact(local, monkeypatch):
    r, _, spec = local
    monkeypatch.setenv('OST_VARIANT_PATCH_SHA256', spec['patch_sha256'])
    m = r.prepare('C')
    variant.verify_schema_delta(m, spec)
    corrupt = copy.deepcopy(spec)
    corrupt['schema_audit'][0]['base_parent_schema_sha256'] = 'new-submit-schema'
    with pytest.raises(ValueError, match='FROZEN_DELTA'):
        variant.verify_schema_delta(m, corrupt)
    record = {'sdk': {'id_check': {'call_count': 1, 'successful': True, 'inputs_results': [{'candidate_ids': ['unknown'], 'checks': [{'candidate_id': 'unknown', 'exists': True}]}]}}}
    assert not analysis.id_check_structure(record, [])


def test_wrong_base_or_mixed_patch_refused(tmp_path):
    archive = subprocess.check_output(['git', 'archive', 'HEAD', 'track_2a/src', 'track_2a/dev/cscs', 'track_2a/dev/format'], cwd=REPO)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(tmp_path, filter='data')
    variant.apply(tmp_path, variant.NAME)
    with pytest.raises(ValueError, match='BASE_SOURCE'):
        variant.apply(tmp_path, NAME)
