"""One fixed, input-only public selection; no model, scorer, or historical mutation.

--freeze selects development and reserved confirmation by input hashes only.
--complete prepares ONLY the development bundle after verifying that freeze.
No reselection or implicit resume is supported. No selected text/gold is printed.
"""
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'output/validation/role-review-v1'
SEED = 'ost-role-review-overnight-20261015-v1'
SCOPE = 'outside_documented_local_real_llm_prompt_development'
SOURCE_SHA = '87ee4afd9c0ee8861106c50f05884481402ca668aecf927df68fc52d915b02fd'
BYTE_CAP = 240000
OLD_FREEZES = {
    'output/validation/v16-public-v1/selection-freeze.json': '4df6645a7e56bd3e9099f9eee8be92507fd0c7ac99c84dde0be2ee286853bdcc',
    'output/validation/v16-public-v2/selection-freeze.json': '73a1facf98d42b6334b2547c64e004e0ece355b78f1fe27daf4410073e11df92',
    'output/validation/v16-public-v2-completion/selection-freeze.json': '73a1facf98d42b6334b2547c64e004e0ece355b78f1fe27daf4410073e11df92',
}


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


old = module(ROOT / '.auto/prepare_public_validation.py', 'role_data_primitives')
encoded, sha, digest = old.encoded, old.sha, old.digest


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    data = value if isinstance(value, bytes) else encoded(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def load(path):
    return json.loads(path.read_bytes())


def source_rows():
    data = (ROOT / 'track_2a/data/source.jsonl').read_bytes()
    require(sha(data) == SOURCE_SHA, 'SOURCE_CHANGED')
    rows = [json.loads(line) for line in data.splitlines()]
    require(len(rows) == 1488, 'SOURCE_ROW_COUNT')
    return rows


def exclusions(rows):
    indices, audit = old.verify_used(rows)
    evidence = {'evals/c-system-prompt/split.json': audit['split_sha256'],
                'evals/c-system-prompt/cases.jsonl': audit['fixture_sha256']}
    for relative, expected in OLD_FREEZES.items():
        raw = (ROOT / relative).read_bytes()
        require(sha(raw) == expected, 'HISTORICAL_FREEZE_CHANGED')
        frozen = json.loads(raw)
        require(frozen['source_sha256'] == SOURCE_SHA and frozen['revision'] == old.REVISION,
                'HISTORICAL_SOURCE_CHANGED')
        require(digest(frozen['selection']) == frozen['selection_freeze_sha256'], 'HISTORICAL_SELECTION_CHANGED')
        for pin in frozen['selection']:
            i = pin['source_index']
            require(type(i) is int and 0 <= i < len(rows), 'HISTORICAL_INDEX')
            require(old.input_hash(rows[i]) == pin['input_sha256'] and old.groups(rows[i]) == pin['group_digests'],
                    'HISTORICAL_MAPPING_CHANGED')
            indices.add(i)
        evidence[relative] = expected
    require(len(indices) == 62, 'EXCLUSION_UNION_CHANGED')
    for relative in ('.auto/role-review-exposure-audit.md', '.auto/role-review-data-plan.md'):
        evidence[relative] = sha((ROOT / relative).read_bytes())
    return indices, evidence


def select_inputs(rows, used, count=60):
    """Never access label/baseline_score; adding/replacing labels cannot affect rank."""
    blocked = [old.groups(rows[i]) for i in sorted(used)]
    refs, claims = ({g['reference'] for g in blocked}, {g['claim'] for g in blocked})
    ranks = sorted((digest([SEED, i, old.input_hash(row)]), i) for i, row in enumerate(rows))
    selected = []
    for rank, i in ranks:
        group = old.groups(rows[i])
        if i in used or group['reference'] in refs or group['claim'] in claims:
            continue
        selected.append({'source_index': i, 'rank_sha256': rank, 'input_sha256': old.input_hash(rows[i]),
                         'group_digests': group})
        refs.add(group['reference']); claims.add(group['claim'])
        if len(selected) == count:
            break
    require(len(selected) == count, 'INSUFFICIENT_INPUT_ONLY_POOL')
    for n, pin in enumerate(selected):
        section = 'dev' if n < 30 else 'confirm'
        pin['section'] = section
        pin['case_ids'] = [f'ost-role-review-{section}-{pin["source_index"]:04d}-{t}' for t in ('A', 'B')]
    return selected


def selection(rows):
    used, evidence = exclusions(rows)
    pins = select_inputs(rows, used)
    return {'protocol': 'role-review-overnight-data-v1', 'source_sha256': SOURCE_SHA,
            'revision': old.REVISION, 'seed': SEED, 'provenance_scope': SCOPE,
            'universal_unseen_claim': False, 'unverified_history': 'Unrecorded runs and individual historical inspection cannot be excluded; not a secret or training-unseen holdout.',
            'recipe': 'Rank canonical SHA256 [seed,index,input_hash] ascending; exclude62 known rows and their claim/reference-language groups; greedily take60 distinct claim/reference groups; first30 development,next30 reserved confirmation; no labels/quotas/date/PDF filters or substitution.',
            'excluded_indices': sorted(used), 'exclusion_evidence_sha256': evidence,
            'selection': pins, 'selection_freeze_sha256': digest(pins),
            'input_byte_cap': BYTE_CAP, 'pdf_byte_cap': old.MAX_PDF,
            'code_sha256': {str(Path(__file__).relative_to(ROOT)): sha(Path(__file__).read_bytes()),
                            '.auto/prepare_public_validation.py': sha((ROOT / '.auto/prepare_public_validation.py').read_bytes()),
                            '.auto/test_prepare_role_review_data.py': sha((ROOT / '.auto/test_prepare_role_review_data.py').read_bytes())}}


def freeze():
    require(not DEST.exists(), 'EXCLUSIVE_DEST_ALREADY_EXISTS')
    rows = source_rows()
    metadata_path = ROOT / 'output/validation/v16-public-v2-completion/official-source-metadata.json'
    metadata = load(metadata_path)
    require(metadata['revision'] == old.REVISION and metadata['file']['lfs']['oid'] == SOURCE_SHA,
            'PUBLISHER_METADATA_CHANGED')
    result = selection(rows)
    result['publisher_metadata_sha256'] = sha(metadata_path.read_bytes())
    result['freeze_sha256'] = digest(result)
    exclusive(DEST / 'selection-freeze.json', result)
    exclusive(DEST / 'official-source-metadata.json', metadata)
    print(json.dumps({'status': 'blinded-selection-frozen', 'development_rows': 30, 'reserved_rows': 30,
                      'selection_file_sha256': sha((DEST / 'selection-freeze.json').read_bytes())}))


def verify_selection(rows):
    frozen = load(DEST / 'selection-freeze.json')
    body = {k: v for k, v in frozen.items() if k != 'freeze_sha256'}
    require(digest(body) == frozen['freeze_sha256'], 'SELECTION_FREEZE_CHANGED')
    expected = selection(rows)
    require(all(frozen.get(k) == v for k, v in expected.items()), 'SELECTION_RECOMPUTATION_CHANGED')
    require(sha((DEST / 'official-source-metadata.json').read_bytes()) == frozen['publisher_metadata_sha256'],
            'PUBLISHER_RECEIPT_CHANGED')
    return frozen


def http_receipt(record):
    if record.get('status') == 200:
        return record
    inherited = record.get('original_receipt')
    return http_receipt(inherited) if isinstance(inherited, dict) else None


def booklet(url):
    old.validate_url(url)
    target = DEST / 'booklets' / (sha(url.encode())[:16] + '.pdf')
    if target.exists():
        receipt = load(target.with_suffix('.receipt.json'))
        require(receipt['url'] == url and sha(target.read_bytes()) == receipt['sha256'], 'PREPARATION_PDF_CHANGED')
        old.validate_pdf(target.read_bytes())
        return target, receipt
    source_dir = ROOT / 'output/validation/v16-public-v2-completion/booklets'
    cache_manifest_path = source_dir.parent / 'selection-manifest.json'
    require(sha(cache_manifest_path.read_bytes()) == 'b08743451bdbb67476ce2fc8641c34824fe1ae1d1fa10a7c2d14d512d4036dc4',
            'HISTORICAL_COMPLETION_MANIFEST_CHANGED')
    cache_manifest = load(cache_manifest_path)
    for source in sorted(source_dir.glob('*.receipt.json')):
        record = load(source)
        proof = http_receipt(record)
        if record.get('url') != url or not record.get('verified') or proof is None:
            continue
        source_pdf = ROOT / record['path']
        require(source_pdf.resolve().is_relative_to(source_dir.resolve()) and not source_pdf.is_symlink(), 'CACHE_PDF_PATH')
        require(proof.get('url') == url, 'CACHE_HTTP_URL')
        artifacts = cache_manifest['artifact_sha256']
        require(sha(source.read_bytes()) == artifacts[str(source.relative_to(source_dir.parent))], 'CACHE_RECEIPT_CHANGED')
        data = source_pdf.read_bytes()
        require(sha(data) == record['sha256'] == artifacts[str(source_pdf.relative_to(source_dir.parent))], 'CACHE_PDF_CHANGED')
        pages = old.check_http_pdf(proof['status'], proof.get('headers', {}), data)
        receipt = {'url': url, 'path': str(target.relative_to(ROOT)), 'sha256': sha(data), 'bytes': len(data),
                   'pages': pages, 'parser': 'pypdf-6.1.1', 'verified': True,
                   'reused_from': str(source_pdf.relative_to(ROOT)), 'proof_path': str(source.relative_to(ROOT)),
                   'proof_sha256': sha(source.read_bytes()), 'original_receipt': record}
        exclusive(target, data); exclusive(target.with_suffix('.receipt.json'), receipt)
        return target, receipt
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    receipt = old.download_pdf_curl(url, target)
    return target, receipt


def complete():
    require(not (DEST / 'selection-manifest.json').exists(), 'COMPLETE_BUNDLE_ALREADY_EXISTS')
    require(not (DEST / 'preparation-start.json').exists(), 'PARTIAL_PREPARATION_NO_IMPLICIT_RESUME')
    rows = source_rows()
    frozen = verify_selection(rows)
    exclusive(DEST / 'preparation-start.json', {'selection_file_sha256': sha((DEST / 'selection-freeze.json').read_bytes())})
    sys.path.insert(0, str(ROOT / 'track_2a/src'))
    import predict
    import source_spans
    pins = frozen['selection'][:30]
    cases, expected, contexts, audits, source_meta, pdf_records = [], [], [], [], [], {}
    # Prepare documents and input-only cases BEFORE materializing owner-only expected labels.
    for pin in pins:
        row = rows[pin['source_index']]
        pdf, receipt = booklet(row['booklet_url'])
        pdf_records[receipt['url']] = receipt
        for task, cid in zip(('A', 'B'), pin['case_ids']):
            case = {'id': cid, 'claim': {'text': row['claim'], 'language': row['claim_language']}, 'vote': row['vote']}
            if task == 'A':
                case['booklet'] = {'path': str(pdf), 'language': row['reference_language']}
            else:
                case['reference'] = {'text': row['reference_string'], 'language': row['reference_language']}
            context, audit = old.prepare_context(case, predict, source_spans)
            require(len(encoded(context['messages'])) <= BYTE_CAP, 'PREPARED_CONTEXT_BYTE_CAP')
            cases.append(case); contexts.append(context); audits.append(audit)
        source_meta.append({'source_index': pin['source_index'], 'input_sha256': pin['input_sha256'], 'case_ids': pin['case_ids']})
    for pin in pins:
        row = rows[pin['source_index']]
        label = row['entailment_label']
        require(type(label) is int and label in (0, 1, 2), 'OFFICIAL_LABEL_INVALID')
        for cid in pin['case_ids']:
            value = {'id': cid, 'label': label}
            if label != 1:
                value['reference'] = row['reference_string']
            expected.append(value)
    for name, records in (('cases', cases), ('expected', expected), ('prepared-contexts', contexts),
                          ('context-audit', audits), ('source-metadata', source_meta)):
        exclusive(DEST / (name + '.jsonl'), b''.join(encoded(v) for v in records))
    exclusive(DEST / 'booklets/manifest.json', list(pdf_records.values()))
    artifacts = {str(p.relative_to(DEST)): sha(p.read_bytes()) for p in sorted(DEST.rglob('*')) if p.is_file()}
    manifest = {'protocol': 'role-review-development60-v1', 'source_sha256': SOURCE_SHA, 'revision': old.REVISION,
                'seed': SEED, 'provenance_scope': SCOPE, 'universal_unseen_claim': False,
                'selection_file_sha256': artifacts['selection-freeze.json'],
                'selection_freeze_sha256': frozen['selection_freeze_sha256'], 'selection': pins,
                'case_order': [v['id'] for v in cases], 'task_counts': {'A': 30, 'B': 30},
                'artifact_sha256': artifacts, 'selection_before_expected': True, 'evaluated': False,
                'code_sha256': frozen['code_sha256'], 'context_strategy': 'vote_pages',
                'system_sha256': sha(predict.SYSTEM.encode()), 'reserved_confirmation_prepared': False}
    manifest['freeze_sha256'] = digest(manifest)
    exclusive(DEST / 'selection-manifest.json', manifest)
    print(json.dumps({'status': 'development-complete', 'cases': len(cases), 'pdfs': len(pdf_records),
                      'freeze_sha256': manifest['freeze_sha256'], 'reserved_confirmation_prepared': False}))


if __name__ == '__main__':
    require(len(sys.argv) == 2 and sys.argv[1] in ('--freeze', '--complete'), 'EXPLICIT_PREPARATION_MODE_REQUIRED')
    freeze() if sys.argv[1] == '--freeze' else complete()
