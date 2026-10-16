"""Offline archived variant contracts; real Pi SDK with synthetic wire replies."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import io

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import variant
import analyze_runs as analysis


def _historical_base_matches():
    """These archived variants patch the dev/format sources as they were on 2026-10-13.
    After the single-call strategies and paragraph retrieval changed those files, the
    overlay can no longer apply; the archive stays reproducible from that commit."""
    repo = Path(__file__).resolve().parents[2]
    import hashlib as _h
    for name in variant.NAMES:
        spec = json.loads((variant.ROOT / (name + '.json')).read_text())
        for path, sha in spec['base_role_hashes'].items():
            if _h.sha256((repo / path).read_bytes()).hexdigest() != sha:
                return False
    return True


if not _historical_base_matches():
    pytest.skip('archived variant base sources (2026-10-13) differ from the current tree', allow_module_level=True)

REPO = Path(__file__).resolve().parents[2]

@pytest.fixture(scope='module')
def role(tmp_path_factory):
    root = tmp_path_factory.mktemp('evidence-source')
    archive = subprocess.check_output(['git', 'archive', 'HEAD', 'track_2a/src', 'track_2a/dev/cscs', 'track_2a/dev/format'], cwd=REPO)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(root, filter='data')
    spec = variant.apply(root)
    sys.path.insert(0, str(root / 'track_2a/dev/format'))
    loader = importlib.util.spec_from_file_location('evidence_roles', root / 'track_2a/dev/format/run_comparison.py')
    r = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(r)
    (root / 'booklets').mkdir()
    for line in (REPO / 'track_2a/dev/cscs/fixtures/cases-portable.jsonl').read_text().splitlines():
        row = json.loads(line)
        if 'booklet' in row:
            name = Path(row['booklet']['path']).name
            target = root / 'booklets' / name
            if not target.exists():
                target.symlink_to(REPO / 'booklets' / name)
    yield r, root, spec
    sys.path.remove(str(root / 'track_2a/dev/format'))


def item_for(r):
    pages = ['Original source text.\nConditions remain original.']
    ids = [x['span_id'] for x in r.candidates(pages, True)]
    return {'case': {'id': 'offline-B', 'reference': pages[0], 'claim': 'Synthetic offline claim.', 'language': 'de'},
            'pages': pages, 'candidate_ids': ids,
            'messages': [{'role': 'system', 'content': 'Parent classifier instructions.'},
                         {'role': 'user', 'content': 'Original source text.\nConditions remain original.\nSynthetic offline claim.'}]}


def test_strict_child_and_unchanged_parent(role):
    r, _, _ = role
    item = item_for(r)
    id = item['candidate_ids'][0]
    assert r.child_evidence({'candidate_ids': [id]}, item) == {'candidate_ids': [id], 'evidence': [{'page': None, 'text': item['pages'][0]}]}
    for args in [{'label': 0, 'candidate_ids': [id]}, {'candidate_ids': [id], 'extra': 1},
                 {'candidate_ids': [id, id]}, {'candidate_ids': ['unknown']}, {'candidate_ids': [id] * 6}]:
        with pytest.raises(ValueError):
            r.child_evidence(args, item)
    parent = r.schemas([id])[0]['function']['parameters']
    assert parent['required'] == ['label', 'candidate_ids']
    assert parent['properties']['label'] == {'enum': [0, 1, 2], 'type': 'integer'}
    child = r.schemas([id], child=True)[0]['function']['parameters']
    assert child['required'] == ['candidate_ids'] and child['additionalProperties'] is False
    assert 'uniqueItems' not in child['properties']['candidate_ids']
    # Strong uniqueness remains local in TypeBox and child_evidence; not HTTP.
    assert 'uniqueItems: true' in (r.HERE / 'submit-extension.ts').read_text()


@pytest.mark.parametrize('bad', [None, 'label', 'extra', 'duplicate', 'unknown', 'six'])
def test_real_sdk_evidence_and_rejected_repairs(role, monkeypatch, bad):
    r, _, _ = role
    import socket
    def denied(*a, **k):
        raise AssertionError('OFFLINE_NETWORK_OR_CREDENTIAL_READ_DENIED')
    monkeypatch.setattr(socket, 'socket', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(r.legacy.c, 'read_key', denied)
    item = item_for(r)
    id = item['candidate_ids'][0]
    raw = []
    payloads = []
    def post(role, number, payload):
        payloads.append((role, number, copy.deepcopy(payload)))
        name = payload['tool_choice']['function']['name']
        args = {'mode': 'source_only'} if name == 'subagent' else {'candidate_ids': [id]}
        if role == 'parent' and name == 'submit':
            tool = next(m for m in payload['messages'] if m['role'] == 'tool')
            assert json.loads(tool['content']) == {'candidate_ids': [id], 'evidence': [{'page': None, 'text': item['pages'][0]}]}
            assert payload['messages'][1]['content'] == item['messages'][1]['content']
            args['label'] = 2  # The parent, not child, supplies a decision.
        if role == 'child':
            assert 'uniqueItems' not in payload['tools'][0]['function']['parameters']['properties']['candidate_ids']
            assert 'Parent classifier instructions.' not in payload['messages'][0]['content']
            assert payload['messages'][1]['content'] == item['messages'][1]['content']
            if number == 0:
                if bad == 'label': args['label'] = 0
                if bad == 'extra': args['extra'] = 1
                if bad == 'duplicate': args['candidate_ids'] = [id, id]
                if bad == 'unknown': args['candidate_ids'] = ['unknown']
                if bad == 'six': args['candidate_ids'] = [id] * 6
        response = {'id': 'offline', 'model': payload['model'], 'choices': [{'finish_reason': 'tool_calls', 'message': {'role': 'assistant', 'content': None, 'tool_calls': [{'id': role + str(number), 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(args)}}]}}], 'usage': {'prompt_tokens': 80, 'completion_tokens': 20, 'total_tokens': 100}}
        if role == 'child': raw.append(copy.deepcopy(response))
        return response
    accepted, diagnostics, sdk = r.run_b(item, r.MODELS[1], post, strategy='C', isolation_guard=True)
    assert accepted == {'label': 2, 'candidate_ids': [id]}
    assert sdk['counts'] == {'parent': 2, 'child': 1 if bad is None else 2}
    assert len([e for e in sdk['events'] if e['type'] == 'package_child_completed']) == 1
    assert sum(variant.child_emissions(x)['child_label_emissions'] for x in raw) == (1 if bad == 'label' else 0)
    assert bool(diagnostics) == (bad is not None)


def test_raw_emissions_include_rejected_and_text():
    response = {'choices': [{'message': {'content': 'Recommended label: contradiction', 'tool_calls': [{'function': {'arguments': '{"label":0,"recommended_label":2}'}}]}}]}
    counts = variant.child_emissions(response)
    assert counts['child_label_fields'] == 2
    assert counts['child_label_text_emissions'] > 0


def test_exact_hash_audit_and_default_rejection(role, tmp_path, monkeypatch):
    r, _, spec = role
    monkeypatch.setenv('OST_VARIANT_PATCH_SHA256', spec['patch_sha256'])
    m = r.prepare('C')
    variant.verify_manifest(m)
    changed = copy.deepcopy(m)
    changed['frozen'][0]['schema_sha256'] = 'changed'
    with pytest.raises(ValueError, match='FROZEN_SOURCE'):
        variant.verify_manifest(changed)
    corrupt = copy.deepcopy(m)
    corrupt['sources'][next(iter(corrupt['sources']))] = 'changed'
    with pytest.raises(ValueError, match='EXACT_SOURCE'):
        variant.verify_manifest(corrupt)
    (tmp_path / 'manifest.json').write_text(json.dumps(m))
    with pytest.raises(ValueError, match='EXPLICIT_OPTION'):
        analysis.audit([tmp_path], False)
    assert analysis.audit([tmp_path], False, variant.NAME)['requested_variant'] == variant.NAME
    baseline = tmp_path / 'baseline'
    baseline.mkdir()
    base = copy.deepcopy(m)
    del base['variant']
    del base['variant_patch_sha256']
    base['sources'] = {**spec['source_hashes'], **spec['base_role_hashes']}
    (baseline / 'manifest.json').write_text(json.dumps(base))
    assert analysis.audit([baseline, tmp_path], False, variant.NAME)['requested_variant'] == variant.NAME
    base['sources']['track_2a/src/predict.py'] = 'mixed-prompt-change'
    (baseline / 'manifest.json').write_text(json.dumps(base))
    with pytest.raises(ValueError, match='BASE_EXACT_SOURCE'):
        analysis.audit([baseline, tmp_path], False, variant.NAME)


def test_variant_disallows_prompt_mix(tmp_path):
    result = subprocess.run([sys.executable, str(REPO / 'evals/c-system-prompt/run_batch.py'), '--repo', str(REPO), '--python', sys.executable, '--count', '1', '--prefix', str(tmp_path / 'job'), '--variant', variant.NAME, '--prompt-file', 'unused', '--metadata', 'unused'], capture_output=True, text=True)
    assert result.returncode == 2 and 'cannot be combined' in result.stderr
    assert not list(tmp_path.iterdir())


def test_ledger_counts_raw_before_validation(role, tmp_path, monkeypatch):
    r, _, spec = role
    monkeypatch.setenv('OST_VARIANT_PATCH_SHA256', spec['patch_sha256'])
    manifest = r.prepare('C')
    job = tmp_path / 'job'
    job.mkdir(mode=0o700)
    r.initialize(job, manifest)
    class Fake:
        def __init__(self, model): self.model = model
        def request(self, method, path, payload):
            return {'model': self.model, 'choices': [{'finish_reason': 'tool_calls', 'message': {'role': 'assistant', 'content': 'Recommended label: neutral', 'tool_calls': [{'id': 'child', 'type': 'function', 'function': {'name': 'submit', 'arguments': '{"candidate_ids":[],"label":1}'}}]}}], 'usage': {'prompt_tokens': 80, 'completion_tokens': 20, 'total_tokens': 100}}
    ledger = r.Ledger(job, manifest, Fake)
    item = manifest['frozen'][0]
    payload = {'model': r.MODELS[0], 'tools': r.schemas(item['candidate_ids'], child=True)}
    response = ledger.post(r.MODELS[1], 0, 'child', 0, payload)
    record = json.loads((job / '70b-00-child-0.json').read_text())
    assert record['child_output_audit'] == variant.child_emissions(response)
    assert record['child_output_audit']['child_label_fields'] == 1
    assert ledger.state['requests'] == 1 and ledger.state['tokens'] == 100
    assert ledger.state['reserved_tokens'] == 0 and not ledger.fence.exists()
    assert '"label":1' in record['response']['choices'][0]['message']['tool_calls'][0]['function']['arguments']


@pytest.mark.parametrize('arguments,content,labels,violations', [
    ('{"label":0,"recommended_label":2,"candidate_ids":[]}', None, 2, 2),
    ('{"label":0,', None, 1, 1),
    ('{"verdict":"entailment","candidate_ids":[]}', None, 1, 1),
    ('{"class":"contradiction","candidate_ids":[]}', None, 1, 1),
    ('{"candidate_ids":["neutral-entailment-label"]}', None, 0, 0),
    ('{"candidate_ids":["neutral-entailment-label"],', None, 0, 1),
    ('{"candidate_ids":[]}', 'Some natural language.', 0, 1),
    ('{"candidate_ids":[],"extra":7}', None, 0, 1),
])
def test_output_contract_before_masking(role, arguments, content, labels, violations):
    r, _, _ = role
    response = {'choices': [{'message': {'content': content, 'tool_calls': [{'function': {'arguments': arguments}}]}}]}
    counts = variant.child_emissions(response)
    assert counts == r.child_emissions(response)
    assert counts['child_label_emissions'] == labels
    assert counts['child_output_contract_violations'] == violations


def test_variant_adoption_requires_both_sides_label_free():
    comparisons = {side: {'literal_pass': True, 'strict_reference_pass': True, 'candidate_safe_all': True, 'gain': .9} for side in ('train', 'test')}
    for side in ('train', 'test'):
        cand = {name: {'child_label_free_all': name != side, 'child_label_emissions_total': int(name == side)} for name in ('train', 'test')}
        assert analysis.adoption(comparisons, cand, variant.NAME) == {'adopt_literal': False, 'adopt_strict': False}
        assert analysis.adoption(comparisons, cand) == {'adopt_literal': True, 'adopt_strict': True}
    cand = {side: {'child_label_free_all': True} for side in ('train', 'test')}
    assert analysis.adoption(comparisons, cand, variant.NAME) == {'adopt_literal': True, 'adopt_strict': True}


def test_approved_historical_baselines_exact_audit(role, tmp_path, monkeypatch):
    r, _, spec = role
    monkeypatch.setenv('OST_VARIANT_PATCH_SHA256', spec['patch_sha256'])
    m = r.prepare('C')
    (tmp_path / 'manifest.json').write_text(json.dumps(m))
    jobs = [REPO / 'output/cscs' / name for name in spec['historical_baseline_metadata']['approved_jobs']]
    if not all((j / 'manifest.json').exists() for j in jobs):
        pytest.skip('approved historical manifests unavailable')
    assert len(analysis.audit(jobs, False)['differences']) == 5
    with pytest.raises(ValueError, match='EXPLICIT_OPTION'):
        analysis.audit(jobs + [tmp_path], True)
    with pytest.raises(ValueError, match='REQUIRES_CLI_FLAG'):
        analysis.audit(jobs + [tmp_path], False, variant.NAME)
    audit = analysis.audit(jobs + [tmp_path], True, variant.NAME)
    assert len(audit['differences']) == 6
    assert len(audit['historical_baseline_source_differences']) == 5
    assert all(set(x['differences_from_current_base']) == analysis.CLI_ONLY for x in audit['historical_baseline_source_differences'])
    historical = {'sources': spec['historical_baseline_source_maps'][0]}
    corrupt = copy.deepcopy(historical)
    corrupt['sources']['track_2a/src/predict.py'] = 'unapproved'
    with pytest.raises(ValueError, match='BASE_EXACT_SOURCE'):
        variant.verify_baseline(corrupt, True)


@pytest.mark.parametrize('field', ['reasoning', 'reasoning_content'])
def test_only_visible_emitted_reasoning_fields_count(role, field):
    r, _, _ = role
    response = {'choices': [{'message': {'content': None, field: 'Recommended label: contradiction', 'tool_calls': [{'function': {'arguments': '{"candidate_ids":[]}'}}]}}]}
    counts = variant.child_emissions(response)
    assert counts == r.child_emissions(response)
    assert counts['child_label_text_emissions'] > 0
    assert counts['child_output_content_violations'] == 1
