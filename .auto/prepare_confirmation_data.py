"""Materialize the reserved confirmation 60 from the frozen role-review selection.

Reads the already frozen selection (rows 30..59 of selection-freeze.json), which
was ranked by input hashes before any gold was read. Writes cases.jsonl,
expected.jsonl and booklets/ to a new exclusive directory. No model, scorer,
or historical mutation; the development bundle is left untouched.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.auto'))
import prepare_role_review_data as dev  # noqa: E402

DEST = ROOT / 'output/validation/role-review-confirm-v1'
SOURCE_DIRS = [ROOT / 'output/validation/role-review-v1/booklets',
               ROOT / 'output/validation/v16-public-v2-completion/booklets', ROOT / 'booklets']


def booklet(url):
    dev.old.validate_url(url)
    name = dev.sha(url.encode())[:16] + '.pdf'
    target = DEST / 'booklets' / name
    if target.exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    for directory in SOURCE_DIRS:
        source = directory / name
        if source.exists():
            data = source.read_bytes()
            dev.old.validate_pdf(data)
            dev.exclusive(target, data)
            dev.exclusive(target.with_suffix('.receipt.json'), {'url': url, 'sha256': dev.sha(data), 'bytes': len(data),
                                                                 'reused_from': str(source.relative_to(ROOT))})
            return target
    receipt = dev.old.download_pdf_curl(url, target)
    dev.require(receipt.get('verified'), 'PDF_DOWNLOAD_UNVERIFIED')
    return target


def main():
    dev.require(not DEST.exists(), 'EXCLUSIVE_DEST_ALREADY_EXISTS')
    rows = dev.source_rows()
    frozen = dev.verify_selection(rows)
    pins = frozen['selection'][30:]
    dev.require(len(pins) == 30 and all(p['section'] == 'confirm' for p in pins), 'CONFIRMATION_SELECTION_SHAPE')
    cases, expected, meta = [], [], []
    for pin in pins:
        row = rows[pin['source_index']]
        pdf = booklet(row['booklet_url'])
        for task, cid in zip(('A', 'B'), pin['case_ids']):
            case = {'id': cid, 'claim': {'text': row['claim'], 'language': row['claim_language']}, 'vote': row['vote']}
            if task == 'A':
                case['booklet'] = {'path': str(pdf), 'language': row['reference_language']}
            else:
                case['reference'] = {'text': row['reference_string'], 'language': row['reference_language']}
            cases.append(case)
        meta.append({'source_index': pin['source_index'], 'input_sha256': pin['input_sha256'], 'case_ids': pin['case_ids']})
    for pin in pins:
        row = rows[pin['source_index']]
        label = row['entailment_label']
        dev.require(type(label) is int and label in (0, 1, 2), 'OFFICIAL_LABEL_INVALID')
        for cid in pin['case_ids']:
            value = {'id': cid, 'label': label}
            if label != 1:
                value['reference'] = row['reference_string']
            expected.append(value)
    for name, records in (('cases', cases), ('expected', expected), ('source-metadata', meta)):
        dev.exclusive(DEST / (name + '.jsonl'), b''.join(dev.encoded(v) for v in records))
    artifacts = {str(p.relative_to(DEST)): dev.sha(p.read_bytes()) for p in sorted(DEST.rglob('*')) if p.is_file()}
    manifest = {'protocol': 'role-review-confirmation60-v1', 'source_sha256': dev.SOURCE_SHA, 'seed': dev.SEED,
                'selection_freeze_sha256': frozen['selection_freeze_sha256'], 'selection': pins,
                'case_order': [c['id'] for c in cases], 'task_counts': {'A': 30, 'B': 30}, 'artifact_sha256': artifacts,
                'opened_at': __import__('time').strftime('%Y-%m-%dT%H:%M:%S%z'), 'purpose': 'one-time v5 versus candidate comparison'}
    dev.exclusive(DEST / 'selection-manifest.json', manifest)
    print(json.dumps({'status': 'confirmation-complete', 'cases': len(cases), 'booklets': len({c['booklet']['path'] for c in cases if 'booklet' in c})}))


if __name__ == '__main__':
    main()
