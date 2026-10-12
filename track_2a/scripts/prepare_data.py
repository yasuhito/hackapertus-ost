"""Public dataset has train only. Derive dev by voting date, never use test."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from predict import pdf_pages
from download_booklets import filename


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, default=Path("track_2a/data/source.jsonl"))
    p.add_argument("--pdf-dir", type=Path, default=Path("/workspace/ost-booklets"))
    p.add_argument("--output-dir", type=Path, default=Path("track_2a/data"))
    args = p.parse_args()
    rows = [json.loads(line) for line in args.source.open()]
    dates = sorted({r['booklet_publish_date'] for r in rows}, key=lambda d: hashlib.sha256(('ost-dev-v1:' + d).encode()).hexdigest())
    dev_dates = set(dates[:max(1, round(len(dates) * .2))])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    buckets = {"train": [], "dev": []}
    advanced_gold = []
    for i, row in enumerate(rows):
        split = "dev" if row['booklet_publish_date'] in dev_dates else "train"
        meta = {"claim_language": row['claim_language'], "reference_language": row['reference_language'],
                "date": row['booklet_publish_date']}
        case = {"id": f"ost-{i:04d}-beginner", "reference": {"text": row['reference_string']},
                "claim": {"text": row['claim']}, "label": row['entailment_label'],
                "task": "beginner", **meta, "evidence": [{"page": 1, "text": row['reference_string']}] if row['entailment_label'] != 1 else []}
        buckets[split].append(case)
        if split == "dev":
            advanced = {k: v for k, v in case.items() if k not in ('reference', 'evidence')}
            advanced.update(id=f"ost-{i:04d}-advanced", task="advanced", vote=row['vote'],
                            booklet={"path": str((args.pdf_dir / filename(row['booklet_url'])).resolve())})
            # Dataset has no page annotations. Only exact extraction matches are eligible.
            pages = pdf_pages(advanced['booklet']['path'])
            matches = [{"page": j, "text": row['reference_string']} for j, text in enumerate(pages, 1) if row['reference_string'] in text]
            advanced['evidence'] = matches if row['entailment_label'] != 1 else []
            advanced['evidence_evaluable'] = bool(matches) or row['entailment_label'] == 1
            advanced_gold.append(advanced)
    def write(name, items):
        (args.output_dir / name).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in items))
    for split, items in buckets.items():
        write(f'{split}_gold.jsonl', items)
        write(f'{split}_cases.jsonl', [{k: v for k, v in r.items() if k not in ('label', 'evidence')} for r in items])
    write('dev_advanced_gold.jsonl', advanced_gold)
    write('dev_advanced_cases.jsonl', [{k: v for k, v in r.items() if k not in ('label', 'evidence', 'evidence_evaluable')} for r in advanced_gold])
    stats = {"dataset": "OSTswiss/MNLIoverSwissVotingBooklets", "gated": False, "official_splits": {"train": len(rows)},
             "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(), "fields": list(rows[0]),
             "counts": {k: dict(Counter(str(r[k]) for r in rows)) for k in ('claim_language', 'reference_language', 'entailment_label')},
             "split_policy": "sha256(ost-dev-v1:date), first round(20% dates) dev", "dev_dates": sorted(dev_dates),
             "derived_sizes": {k: len(v) for k, v in buckets.items()}, "booklets": len({r['booklet_url'] for r in rows}),
             "advanced_dev_exact_page_annotations": sum(bool(r['evidence']) for r in advanced_gold)}
    (args.output_dir / 'dataset_stats.json').write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))

if __name__ == '__main__':
    main()
