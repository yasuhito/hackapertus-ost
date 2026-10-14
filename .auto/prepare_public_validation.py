"""Prepare additional public validation only. Never invokes a backend or scorer.

Run: python -B .auto/prepare_public_validation.py
Outputs are exclusive, ignored, and contain public text and isolated gold.
A partial directory requires explicit verified --resume-preparation into a new bundle.
"""
import subprocess
from email.parser import BytesParser
import inspect
import hashlib
import io
import os
import time
import http.client
import json
from collections import Counter
from pathlib import Path
import re
import signal
import sys
import unicodedata
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'output/validation/v16-public-v2'
SOURCE = ROOT / 'track_2a/data/source.jsonl'
REVISION = 'fc2b27600310778da6bbf445651ddbca22d86269'
DATASET = 'OSTswiss/MNLIoverSwissVotingBooklets'
SOURCE_URL = f'https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/v1.1.jsonl'
METADATA_URL = f'https://huggingface.co/api/datasets/{DATASET}/tree/{REVISION}'
SOURCE_SHA = '87ee4afd9c0ee8861106c50f05884481402ca668aecf927df68fc52d915b02fd'
SEED = 'ost-v16-public-validation-20261014-v1'
DATES = ('2020-09-27', '2021-03-07', '2024-03-03', '2024-06-09')
INPUT_FIELDS = ('booklet_publish_date', 'booklet_url', 'claim', 'claim_language',
                'reference_string', 'reference_language', 'vote')


def encoded(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                       allow_nan=False) + '\n').encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(obj):
    return sha(encoded(obj))


def normalize(text):
    # Pinned protocol semantics, not document_selection's accent-stripping NFKD.
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'(\w)[\-\u00ad]\s*\n\s*(?=\w)', r'\1', text)
    return ' '.join(text.replace('\u00ad', '').split()).casefold()


def canonical_url(url):
    p = urlsplit(url)
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path, p.query, ''))


def groups(row):
    return {'booklet': digest(canonical_url(row['booklet_url'])),
            'reference': digest([normalize(row['reference_string']), row['reference_language']]),
            'claim': digest([normalize(row['claim']), row['claim_language']])}


def input_hash(row):
    return digest({k: row[k] for k in INPUT_FIELDS})


def ranked(index, row):
    return digest([SEED, index, input_hash(row)])


def used_indices(split, size):
    ids = split['train'] + split['test']
    if len(ids) != 54 or len(set(ids)) != 54:
        raise ValueError('used IDs must be 54 unique')
    pairs = {}
    for cid in ids:
        match = re.fullmatch(r'ost-dev54-(\d+)-([AB])', cid)
        if not match or not 0 <= int(match[1]) < size:
            raise ValueError('invalid used ID/range')
        pairs.setdefault(int(match[1]), set()).add(match[2])
    if len(pairs) != 27 or any(tasks != {'A', 'B'} for tasks in pairs.values()):
        raise ValueError('used IDs must form 27 A/B pairs')
    return set(pairs)


def verify_used(rows):
    split_path = ROOT / 'evals/c-system-prompt/split.json'
    fixture_path = ROOT / 'evals/c-system-prompt/cases.jsonl'
    split = json.loads(split_path.read_bytes())
    used = used_indices(split, len(rows))
    # Machine-only input check. Never inspect gold, outputs or why_hard.
    fixtures = [json.loads(line) for line in fixture_path.read_bytes().splitlines()]
    by_id = {f['id']: f['input'] for f in fixtures}
    ids = split['train'] + split['test']
    if len(fixtures) != 54 or set(by_id) != set(ids):
        raise ValueError('fixture IDs mismatch')
    for cid in ids:
        index = int(re.fullmatch(r'ost-dev54-(\d+)-[AB]', cid)[1])
        r, inp = rows[index], by_id[cid]
        if inp['id'] != cid or inp['claim'] != {'text': r['claim'], 'language': r['claim_language']} or inp['vote'] != r['vote']:
            raise ValueError('used source mapping mismatch')
        if cid.endswith('B') and inp['reference'] != {'text': r['reference_string'], 'language': r['reference_language']}:
            raise ValueError('used reference mapping mismatch')
        if cid.endswith('A') and (inp['booklet']['language'] != r['reference_language'] or
                                  Path(inp['booklet']['path']).name != sha(r['booklet_url'].encode())[:16] + '.pdf'):
            raise ValueError('used booklet language mismatch')
    return used, {'split_sha256': sha(split_path.read_bytes()), 'fixture_sha256': sha(fixture_path.read_bytes()),
                  'source_sha256': SOURCE_SHA, 'mapping': [
                      {'id': cid, 'split': name, 'source_index': int(re.fullmatch(r'ost-dev54-(\d+)-[AB]', cid)[1])}
                      for name in ('train', 'test') for cid in split[name]],
                  'used_rows': [{'source_index': i, 'input_sha256': input_hash(rows[i]),
                                 'group_digests': groups(rows[i])} for i in sorted(used)]}


def select(rows, quota=10, used=None):
    used = set() if used is None else set(used)
    if any(type(i) is not int or not 0 <= i < len(rows) for i in used):
        raise ValueError('invalid used index')
    for row in rows:
        if type(row.get('entailment_label')) is not int or row['entailment_label'] not in (0, 1, 2):
            raise ValueError('invalid source label')
        if any(not isinstance(row.get(k), str) or not row[k].strip() for k in INPUT_FIELDS):
            raise ValueError('invalid source input field')
        if row['claim_language'] not in ('de', 'fr', 'it') or row['reference_language'] not in ('de', 'fr', 'it'):
            raise ValueError('invalid language')
    indexed = [(i, row, groups(row)) for i, row in enumerate(rows)]
    historical = [x for x in indexed if x[0] in used]
    blocked = {k: {g[k] for _, _, g in historical} for k in ('reference', 'claim')}
    used_booklets = {g['booklet'] for _, _, g in historical}
    used_dates = {r['booklet_publish_date'] for _, r, _ in historical}
    reasons = Counter()
    eligible = []
    for item in indexed:
        i, row, g = item
        hits = (['used_index'] if i in used else []) + [k for k in blocked if g[k] in blocked[k]]
        reasons.update(hits)
        if not hits:
            eligible.append(item)
    representatives = {}
    for item in sorted(eligible, key=lambda x: (ranked(x[0], x[1]), x[0])):
        representatives.setdefault(item[2]['reference'], item)
    queues = {label: [x for x in representatives.values() if x[1]['entailment_label'] == label]
              for label in (0, 1, 2)}
    if any(len(q) < quota for q in queues.values()):
        raise ValueError('insufficient reference representatives; no reseed or relaxed filters')
    chosen = [queues[label][n] for n in range(quota) for label in (0, 1, 2)]
    audit = {'source_rows': len(rows), 'used_source_rows': len(historical),
             'excluded_union': len(rows) - len(eligible), 'exclusion_hits_nonexclusive': dict(reasons),
             'blocked_group_counts': {k: len(v) for k, v in blocked.items()},
             'eligible_rows': len(eligible), 'eligible_reference_groups': len(representatives),
             'representative_label_counts': {str(k): len(v) for k, v in queues.items()},
             'selected_rows': len(chosen), 'selected_reference_duplicates': len(chosen) - len({x[2]['reference'] for x in chosen}),
             'selected_used_index_overlaps': sum(i in used for i, _, _ in chosen),
             'selected_used_date_overlaps': sum(r['booklet_publish_date'] in used_dates for _, r, _ in chosen),
             'selected_used_booklet_overlaps': sum(g['booklet'] in used_booklets for _, _, g in chosen),
             'selected_used_booklet_unique_overlaps': len({g['booklet'] for _, _, g in chosen} & used_booklets),
             'selected_used_group_overlaps': {k: sum(g[k] in blocked[k] for _, _, g in chosen) for k in blocked}}
    return chosen, audit


def cases_for(index, row, pdf):
    base = {'claim': {'text': row['claim'], 'language': row['claim_language']}, 'vote': row['vote']}
    result = []
    for task in ('A', 'B'):
        cid = f'ost-public-v16-{index:04d}-{task}'
        case = {**base, 'id': cid}
        if task == 'A':
            case['booklet'] = {'path': str(pdf), 'language': row['reference_language']}
        else:
            case['reference'] = {'text': row['reference_string'], 'language': row['reference_language']}
        expected = {'id': cid, 'label': row['entailment_label']}
        if row['entailment_label'] != 1:
            expected['reference'] = row['reference_string']
        result.append((case, expected))
    return result


def validate_url(url):
    p = urlsplit(url)
    if p.scheme != 'https' or p.hostname != 'www.bk.admin.ch' or p.port not in (None, 443) or p.username or p.password or p.fragment:
        raise ValueError('unexpected booklet URL domain/scheme')
    return url


class GovernmentRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


MAX_PDF = 30 * 1024 * 1024


class IncompletePDF(ValueError):
    pass


def validate_pdf(data):
    from pypdf import PdfReader, __version__
    if __version__ != '6.1.1':
        raise ValueError('pinned pypdf 6.1.1 required')
    if not data.startswith(b'%PDF') or len(data) > MAX_PDF:
        raise ValueError('invalid PDF header/size')
    if b'%%EOF' not in data[-2048:]:
        raise IncompletePDF('missing PDF EOF')
    reader = PdfReader(io.BytesIO(data))
    pages = len(reader.pages)
    if not pages:
        raise ValueError('empty PDF')
    return pages


def atomic_exclusive(path, data):
    temporary = path.with_name(path.name + '.pending')
    exclusive(temporary, data)
    try:
        os.link(temporary, path)  # Atomic and refuses any existing canonical name.
    finally:
        temporary.unlink()


def download_pdf(url, dest, attempts=3):
    validate_url(url)
    if dest.exists():
        raise FileExistsError(dest)
    if not 1 <= attempts <= 3:
        raise ValueError('invalid retry bound')
    for attempt in range(1, attempts + 1):
        data, receipt = b'', {'url': url, 'attempt': attempt}
        chunks = []
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'HackApertus-OST/1.0', 'Accept-Encoding': 'identity'})
            with urllib.request.build_opener(GovernmentRedirect()).open(request, timeout=60) as response:
                validate_url(response.geturl())
                receipt.update(status=response.status, final_url=response.geturl(), headers=dict(response.headers))
                if response.status != 200 or response.headers.get('Content-Range'):
                    raise ValueError('unexpected HTTP status/range')
                if response.headers.get('Content-Encoding', 'identity').lower() != 'identity':
                    raise ValueError('unexpected content encoding')
                length = response.headers.get('Content-Length')
                length = int(length) if length is not None else None
                if length is not None and (length < 0 or length > MAX_PDF):
                    raise ValueError('invalid PDF size')
                chunks, total = [], 0
                while True:
                    block = response.read(min(65536, MAX_PDF + 1 - total))
                    if not block:
                        break
                    chunks.append(block)
                    total += len(block)
                    if total > MAX_PDF:
                        data = b''.join(chunks)
                        raise ValueError('invalid PDF size')
                data = b''.join(chunks)
                if length is not None and len(data) != length:
                    raise IncompletePDF('Content-Length mismatch')
            pages = validate_pdf(data)
            receipt.update(bytes=len(data), sha256=sha(data), pages=pages, parser='pypdf-6.1.1',
                           path=str(dest.relative_to(ROOT)), verified=True)
            atomic_exclusive(dest, data)
            atomic_exclusive(dest.with_suffix('.receipt.json'), encoded(receipt))
            return receipt
        except Exception as exc:
            if isinstance(exc, urllib.error.HTTPError):
                receipt.update(status=exc.code, headers=dict(exc.headers or {}))
                exc.close()
            # Keep diagnostic bytes separate, never expose them as a verified PDF.
            if not data:
                data = b''.join(chunks) + (exc.partial if isinstance(exc, http.client.IncompleteRead) else b'')
            receipt.update(bytes=len(data), sha256=sha(data), error_type=type(exc).__name__, verified=False)
            exclusive(dest.with_name(dest.name + f'.attempt-{attempt}.failed'), data)
            exclusive(dest.with_name(dest.name + f'.attempt-{attempt}.json'), encoded(receipt))
            retryable = isinstance(exc, (IncompletePDF, http.client.IncompleteRead, urllib.error.URLError,
                                         TimeoutError, ConnectionError)) and not isinstance(exc, urllib.error.HTTPError)
            if not retryable or attempt == attempts:
                raise
            time.sleep(attempt)


def exclusive(path, data):
    with path.open('xb') as target:
        target.write(data)


def check_source(data, official_sha):
    if official_sha != SOURCE_SHA or sha(data) != SOURCE_SHA:
        raise ValueError('pinned official/source SHA mismatch; stop')


def readonly(dest):
    manifest = json.loads((dest / 'selection-manifest.json').read_bytes())
    freeze = manifest.pop('freeze_sha256')
    if digest(manifest) != freeze:
        raise ValueError('manifest freeze mismatch')
    for path, expected in manifest['artifact_sha256'].items():
        if sha((dest / path).read_bytes()) != expected:
            raise ValueError('frozen artifact mismatch')
    return {'status': 'complete-read-only', 'freeze_sha256': freeze, 'cases': 60}


def prepare_context(case, predict, source_spans):
    pages, messages = predict.context(case, ROOT, 'vote_pages')
    spans = source_spans.candidates(pages, reference='reference' in case)
    payload = json.loads(messages[1]['content'])
    supplied = payload['source_spans']
    if not spans or supplied != [{k: s[k] for k in ('span_id', 'page', 'text')} for s in spans]:
        raise ValueError('context candidate mismatch/empty')
    if any(pages[int(s['span_id'][1:5]) - 1][s['start']:s['end']] != s['text'] for s in spans):
        raise ValueError('context source offset mismatch')
    # Exercise restoration without a model decision or any gold input.
    source_spans.restore('{"label":1,"evidence":[]}', pages, reference='reference' in case)
    record = {'id': case['id'], 'selected_pages': [n for n, p in enumerate(pages, 1) if p.strip()],
              'candidate_ids': [s['span_id'] for s in spans], 'messages_sha256': digest(messages),
              'selected_page_text_sha256': digest(pages), 'input_sha256': digest(case),
              'payload_keys': sorted(payload), 'span_schema_sha256': digest(sorted(supplied[0]))}
    return {'id': case['id'], 'messages': messages}, record


def selection_from_source(data):
    rows = [json.loads(line) for line in data.splitlines()]
    if len(rows) != 1488:
        raise ValueError('unexpected source size')
    used, used_audit = verify_used(rows)
    chosen, audit = select(rows, used=used)
    pins = [{'source_index': i, 'input_sha256': input_hash(r), 'rank_sha256': ranked(i, r),
             'group_digests': g, 'case_ids': [f'ost-public-v16-{i:04d}-{t}' for t in ('A', 'B')]}
            for i, r, g in chosen]
    manifest = {'protocol': 'additional-public-validation-v2', 'seed': SEED,
                'recipe': 'exclude only 27 current used source indices and their normalized reference-language/claim-language groups; public dates and booklets allowed; rank SHA256 canonical JSON [seed,index,input_digest]; lowest-ranked reference representative BEFORE label quotas; round-robin 0,1,2 ten each; no reseed/filter adjustment',
                'normalization': 'NFKC; word-hyphen newline dehyphenation; remove soft hyphens; collapse Unicode whitespace; casefold',
                'source_url': SOURCE_URL, 'metadata_url': METADATA_URL, 'revision': REVISION,
                'source_sha256': SOURCE_SHA, 'excluded_dates': [], 'used_source': used_audit, 'dataset_fields': sorted(rows[0]),
                'ranking_input_fields': list(INPUT_FIELDS), 'selection': pins, 'counts': audit,
                'distribution': {k: dict(Counter(str(r[k]) for _, r, _ in chosen)) for k in ('booklet_publish_date', 'claim_language', 'reference_language', 'entailment_label')},
                'cross_language_rows': sum(r['claim_language'] != r['reference_language'] for _, r, _ in chosen),
                'task_counts': {'A': 30, 'B': 30}, 'case_label_counts': {'0': 20, '1': 20, '2': 20},
                'paired_source_and_label': True, 'historical_train_caveat': 'Historical train 1157 used for mock training. Additional public validation not used in this prompt improvement, not secret unseen benchmark.',
                'evaluated': False}
    manifest['selection_freeze_sha256'] = digest(pins)
    return chosen, audit, manifest


FROZEN_SELECTION = 'acf1805ca02358e8913ead392e587247b2b0f36d7300e8114e790307807e8007'
FROZEN_FILE = '73a1facf98d42b6334b2547c64e004e0ece355b78f1fe27daf4410073e11df92'


def verify_resume(old):
    frozen_bytes = (old / 'selection-freeze.json').read_bytes()
    if sha(frozen_bytes) != FROZEN_FILE:
        raise ValueError('stored freeze file mismatch')
    frozen = json.loads(frozen_bytes)
    if frozen['selection_freeze_sha256'] != FROZEN_SELECTION or digest(frozen['selection']) != FROZEN_SELECTION:
        raise ValueError('selection freeze mismatch')
    metadata = json.loads((old / 'official-source-metadata.json').read_bytes())
    if metadata['url'] != METADATA_URL or metadata['revision'] != REVISION:
        raise ValueError('official metadata mismatch')
    data = SOURCE.read_bytes()
    check_source(data, metadata['file']['lfs']['oid'])
    chosen, audit, current = selection_from_source(data)
    comparison = dict(frozen)
    original_code = comparison.pop('preparation_code_sha256', None)
    if comparison != current:
        raise ValueError('recomputed source/mapping/recipe/ranking freeze mismatch')
    if original_code is not None:
        current['preparation_code_sha256'] = original_code
    current['completion'] = {'original_freeze_file_sha256': FROZEN_FILE,
                             'original_selection_freeze_sha256': FROZEN_SELECTION,
                             'original_freeze_path': str((old / 'selection-freeze.json').relative_to(ROOT)),
                             'transport': 'bounded-direct-curl-http1.1-no-redirect',
                             'ranking_recipe_code_sha256': sha(''.join(inspect.getsource(f) for f in
                                 (normalize, groups, input_hash, ranked, select, selection_from_source)).encode()),
                             'original_code_hash_recorded': original_code is not None,
                             'selection_verification': 'exact recomputation only; no new selection'}
    return chosen, audit, current


def curl_headers(data):
    # curl may include proxy CONNECT or interim headers before the final response.
    blocks = re.split(rb'\r?\n\r?\n', data.strip())
    blocks = [b for b in blocks if b.startswith(b'HTTP/')]
    if not blocks:
        raise ValueError('missing HTTP headers')
    first, rest = blocks[-1].split(b'\n', 1)
    status = int(first.split()[1])
    headers = dict(BytesParser().parsebytes(rest).items())
    return status, headers


def check_http_pdf(status, headers, data):
    h = {k.lower(): v for k, v in headers.items()}
    if status != 200 or 'content-range' in h or h.get('content-encoding', 'identity').lower() != 'identity':
        raise ValueError('unexpected HTTP status/range/encoding')
    length = int(h['content-length']) if 'content-length' in h else None
    if len(data) > MAX_PDF or (length is not None and not 0 <= length <= MAX_PDF):
        raise ValueError('invalid PDF size')
    if length is not None and len(data) != length:
        raise IncompletePDF('Content-Length mismatch')
    return validate_pdf(data)


def download_pdf_curl(url, dest, attempts=3):
    validate_url(url)
    if dest.exists() or dest.with_suffix('.receipt.json').exists():
        raise FileExistsError(dest)
    if not 1 <= attempts <= 3:
        raise ValueError('invalid retry bound')
    for attempt in range(1, attempts + 1):
        body = dest.with_name(dest.name + f'.curl-{attempt}.body')
        header = dest.with_name(dest.name + f'.curl-{attempt}.headers')
        # Exclusive reservation prevents curl from overwriting diagnostic evidence.
        exclusive(body, b'')
        exclusive(header, b'')
        receipt = {'url': url, 'final_url': url, 'attempt': attempt, 'transport': 'curl-http1.1-no-redirect'}
        data = b''
        try:
            result = subprocess.run(['curl', '--fail', '--show-error', '--silent', '--location',
                                     '--max-redirs', '0', '--proto', '=https', '--http1.1',
                                     '--max-time', '120', '--max-filesize', str(MAX_PDF),
                                     '--dump-header', str(header), '--output', str(body), url],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=125)
            data = body.read_bytes()
            status, headers = curl_headers(header.read_bytes())
            receipt.update(status=status, headers=headers, curl_exit=result.returncode)
            if result.returncode:
                if result.returncode in (18, 28, 35, 52, 55, 56):
                    raise IncompletePDF('curl transport failure')
                raise ValueError('curl failed')
            pages = check_http_pdf(status, headers, data)
            receipt.update(bytes=len(data), sha256=sha(data), pages=pages, parser='pypdf-6.1.1',
                           path=str(dest.relative_to(ROOT)), verified=True,
                           headers_path=str(header.relative_to(ROOT)))
            atomic_exclusive(dest, data)
            atomic_exclusive(dest.with_suffix('.receipt.json'), encoded(receipt))
            body.unlink()
            return receipt
        except Exception as exc:
            data = body.read_bytes()
            receipt.update(bytes=len(data), sha256=sha(data), verified=False, error_type=type(exc).__name__)
            exclusive(dest.with_name(dest.name + f'.attempt-{attempt}.failed'), data)
            exclusive(dest.with_name(dest.name + f'.attempt-{attempt}.json'), encoded(receipt))
            body.unlink()
            if not isinstance(exc, (IncompletePDF, subprocess.TimeoutExpired)) or attempt == attempts:
                raise
            time.sleep(attempt)


def reuse_selected_pdf(url, target):
    candidates = []
    for directory in (DEST / 'booklets', ROOT / 'output/validation/v16-public-v1/booklets'):
        for path in sorted(directory.glob('*.receipt.json')):
            record = json.loads(path.read_bytes())
            if record.get('url') == url and record.get('verified'):
                candidates.append((ROOT / record['path'], record, path))
        if (directory / 'manifest.json').exists():
            for record in json.loads((directory / 'manifest.json').read_bytes()):
                if record.get('url') == url:
                    candidates.append((ROOT / record['path'], record, directory / 'manifest.json'))
    diagnostic = ROOT / 'output/validation/pdf-diagnostic-v3'
    if url == 'https://www.bk.admin.ch/dam/de/sd-web/aSmZ7rOvZDrG/2020-02-09_erlaeuterungen_des_bundesrates.pdf':
        status, headers = curl_headers((diagnostic / 'headers.txt').read_bytes())
        candidates.append((diagnostic / 'booklet.pdf', {'url': url, 'status': status, 'headers': headers,
                           'sha256': '9df0813f2728c9de6dd29b132acf11d3e13bf7a011b7e6475a4c8b5155c889c8'}, diagnostic / 'headers.txt'))
    for path, old, proof in candidates:
        if old.get('status') != 200:
            continue  # Hash-only legacy records do not prove a complete HTTP transfer.
        data = path.read_bytes()
        if sha(data) != old['sha256']:
            raise ValueError('existing PDF receipt hash mismatch')
        try:
            pages = validate_pdf(data)
        except Exception:
            continue  # Failed v1 PDFs are never canonical reuse candidates.
        if 'status' in old:
            check_http_pdf(old['status'], old.get('headers', {}), data)
        # v2 reused records inherit the original same-URL v1 receipt and pinned hash.
        record = {'url': url, 'path': str(target.relative_to(ROOT)), 'sha256': sha(data),
                  'bytes': len(data), 'pages': pages, 'parser': 'pypdf-6.1.1', 'verified': True,
                  'reused_from': str(path.relative_to(ROOT)), 'proof_path': str(proof.relative_to(ROOT)),
                  'proof_sha256': sha(proof.read_bytes()), 'original_receipt': old}
        atomic_exclusive(target, data)
        atomic_exclusive(target.with_suffix('.receipt.json'), encoded(record))
        return record
    return None


def execute(dest=DEST, resume=False):
    if dest.exists() and any(dest.iterdir()):
        if (dest / 'selection-manifest.json').exists():
            return readonly(dest)
        raise ValueError('partial preparation exists; refusal to overwrite/reselect')
    dest.mkdir(parents=True, exist_ok=True)
    phase, current_url = 'source-verification', METADATA_URL
    try:
        if resume:
            chosen, audit, manifest = verify_resume(DEST)
            exclusive(dest / 'selection-freeze.json', (DEST / 'selection-freeze.json').read_bytes())
            exclusive(dest / 'official-source-metadata.json', (DEST / 'official-source-metadata.json').read_bytes())
        else:
            with urllib.request.urlopen(METADATA_URL, timeout=40) as response:
                metadata = json.load(response)
            entry = next(x for x in metadata if x.get('path') == 'v1.1.jsonl')
            official_sha = entry.get('lfs', {}).get('oid')
            data = SOURCE.read_bytes()
            check_source(data, official_sha)
            exclusive(dest / 'official-source-metadata.json', encoded({'url': METADATA_URL, 'revision': REVISION, 'file': entry}))
            phase = 'selection'
            chosen, audit, manifest = selection_from_source(data)
            manifest['preparation_code_sha256'] = sha(Path(__file__).read_bytes())
            exclusive(dest / 'selection-freeze.json', encoded(manifest))
        sys.path[:0] = [str(ROOT / 'track_2a/src'), str(ROOT / 'track_2a/scripts'), str(ROOT / 'track_2a/dev/cscs/vendor')]
        from download_booklets import filename
        import predict
        import source_spans
        phase = 'pdf-download'
        (dest / 'booklets').mkdir()
        pdf_records = []
        for url in sorted({r['booklet_url'] for _, r, _ in chosen}):
            current_url = url
            target = dest / 'booklets' / filename(url)
            if resume:
                record = reuse_selected_pdf(url, target)
                pdf_records.append(record if record else download_pdf_curl(url, target))
                continue
            old_dir = ROOT / 'output/validation/v16-public-v1/booklets' 
            old_records = json.loads((old_dir / 'manifest.json').read_bytes())
            old = next((x for x in old_records if x['url'] == url), None)
            reused = False
            if old:
                old_path = ROOT / old['path']
                old_data = old_path.read_bytes()
                if sha(old_data) == old['sha256']:
                    try:
                        pages = validate_pdf(old_data)
                    except Exception:
                        pass
                    else:
                        record = {'url': url, 'path': str(target.relative_to(ROOT)), 'sha256': sha(old_data),
                                  'bytes': len(old_data), 'pages': pages, 'parser': 'pypdf-6.1.1',
                                  'verified': True, 'reused_from': old['path']}
                        atomic_exclusive(target, old_data)
                        atomic_exclusive(target.with_suffix('.receipt.json'), encoded(record))
                        pdf_records.append(record)
                        reused = True
            if not reused:
                pdf_records.append(download_pdf(url, target))
        exclusive(dest / 'booklets/manifest.json', encoded(pdf_records))
        phase, current_url = 'offline-context', None
        cases, expected, source_meta, contexts, context_audit = [], [], [], [], []
        for i, row, g in chosen:
            source_meta.append({'source_index': i, 'date': row['booklet_publish_date'],
                                'claim_language': row['claim_language'], 'reference_language': row['reference_language'],
                                'group_digests': g, 'input_sha256': input_hash(row)})
            for case, gold in cases_for(i, row, (dest / 'booklets' / filename(row['booklet_url'])).resolve()):
                prepared, checked = prepare_context(case, predict, source_spans)
                cases.append(case)
                expected.append(gold)
                contexts.append(prepared)
                context_audit.append(checked)
        for name, values in [('cases', cases), ('expected', expected), ('source-metadata', source_meta),
                             ('prepared-contexts', contexts), ('context-audit', context_audit)]:
            exclusive(dest / f'{name}.jsonl', b''.join(encoded(v) for v in values))
        manifest['code_sha256'] = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in
                                  [Path(__file__).resolve(), ROOT / 'track_2a/src/predict.py', ROOT / 'track_2a/src/document_selection.py', ROOT / 'track_2a/src/source_spans.py', ROOT / 'track_2a/scripts/download_booklets.py']}
        manifest['system_sha256'] = sha(predict.SYSTEM.encode())
        manifest['final_verification_sha256'] = sha(predict.FINAL_VERIFICATION.encode())
        manifest['context_strategy'] = 'current-v5-vote_pages'
        # Post-selection exact normalized full-reference coverage only, not a score/filter.
        coverage = Counter()
        for context, gold in zip(contexts, expected):
            if 'reference' in gold:
                payload = json.loads(context['messages'][1]['content'])
                source = ' '.join(s['text'] for s in payload['source_spans'])
                task = context['id'][-1]
                coverage[f'{task}_nonneutral'] += 1
                coverage[f'{task}_full_reference_in_candidates'] += int(normalize(gold['reference']) in normalize(source))
        manifest['postselection_exact_reference_coverage'] = dict(coverage)
        manifest['artifact_sha256'] = {str(p.relative_to(dest)): sha(p.read_bytes()) for p in sorted(dest.rglob('*')) if p.is_file()}
        manifest['freeze_sha256'] = digest(manifest)
        exclusive(dest / 'selection-manifest.json', encoded(manifest))
        return {'status': 'complete', 'cases': len(cases), 'freeze_sha256': manifest['freeze_sha256'],
                'counts': audit, 'distribution': manifest['distribution'], 'cross_language_rows': manifest['cross_language_rows']}
    except Exception as exc:
        # Never print source text, PDF extraction text or context exception contents.
        exclusive(dest / 'failure.json', encoded({'phase': phase, 'url': current_url,
                  'error_type': type(exc).__name__, 'http_status': getattr(exc, 'code', None), 'complete': False}))
        raise RuntimeError(f'preparation stopped: {phase}, {type(exc).__name__}; see ignored failure.json') from None


if __name__ == '__main__':
    def deadline(signum, frame):
        raise TimeoutError('bounded preparation deadline')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(8000 if sys.argv[1:] == ['--resume-preparation'] else 600)
    try:
        if sys.argv[1:] not in ([], ['--resume-preparation']):
            raise ValueError('only --resume-preparation supported')
        resume = bool(sys.argv[1:])
        print(json.dumps(execute(ROOT / 'output/validation/v16-public-v2-completion' if resume else DEST,
                                 resume=resume), sort_keys=True))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
