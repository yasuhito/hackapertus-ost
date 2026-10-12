"""ID-aligned diagnostics. Missing, duplicate, malformed and error rows are wrong."""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import statistics
from predict import LABELS


def valid(p, task="advanced"):
    if not isinstance(p, dict) or 'error' in p or type(p.get('label')) is not int or p['label'] not in LABELS or p.get('label_name') != LABELS[p['label']]:
        return False
    ev = p.get('evidence')
    metrics = p.get('metrics', {})
    if not isinstance(ev, list) or (task == 'advanced' and p['label'] != 1 and not ev):
        return False
    if not all(isinstance(e, dict) and ((type(e.get('page')) is int and e['page'] >= 1) if task == 'advanced' else e.get('page') is None) and isinstance(e.get('text'), str) and e['text'].strip() for e in ev):
        return False
    return all(type(metrics.get(k)) in (int, float) and math.isfinite(metrics[k]) and metrics[k] >= 0 for k in ('input_tokens', 'output_tokens', 'inference_time_ms'))


def macro(rows, predictions):
    f1 = []
    for label in range(3):
        tp = fp = fn = 0
        for r in rows:
            p = predictions.get(r['id'])
            y = p['label'] if valid(p, r.get('task', 'beginner')) else -1
            tp += y == label and r['label'] == label
            fp += y == label and r['label'] != label
            fn += y != label and r['label'] == label
        f1.append(2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0)
    return sum(f1) / 3


def score(gold, raw_predictions):
    if len({r['id'] for r in gold}) != len(gold):
        raise ValueError('duplicate gold IDs')
    identifiable = [p for p in raw_predictions if isinstance(p, dict) and type(p.get('id')) in (str, int)]
    counts = Counter(p['id'] for p in identifiable)
    predictions = {p['id']: p for p in identifiable if counts[p['id']] == 1}
    groups = defaultdict(list)
    for r in gold:
        groups['overall'].append(r)
        groups[r.get('task', 'beginner')].append(r)
        groups['claim_language:' + r.get('claim_language', 'unknown')].append(r)
        groups['reference_language:' + r.get('reference_language', 'unknown')].append(r)
        relation = 'unknown' if not r.get('claim_language') or not r.get('reference_language') else ('same' if r['claim_language'] == r['reference_language'] else 'cross')
        groups[relation].append(r)
    evidence_n = evidence_hits = excluded = 0
    for r in gold:
        if r.get('task', 'beginner') != 'advanced':
            continue
        if r['label'] == 1:
            continue
        if r.get('evidence_evaluable') is False or not r.get('evidence'):
            excluded += 1
            continue
        evidence_n += 1
        p = predictions.get(r['id'])
        if not valid(p, r.get('task', 'beginner')) or p['label'] != r['label']:
            continue
        # Strict exact gold passage; all gold passages must be returned.
        advanced = r.get('task') == 'advanced'
        evidence_hits += all(any(e['text'] == g['text'] and (not advanced or e['page'] == g['page']) for e in p['evidence']) for g in r['evidence'])
    selected = [predictions[r['id']] for r in gold if valid(predictions.get(r['id']), r.get('task', 'beginner'))]
    latencies = sorted(p['metrics']['inference_time_ms'] for p in selected)
    return {"macro_f1": {k: {"n": len(v), "value": macro(v, predictions)} for k, v in groups.items()},
            "evidence": {"exact_match_rate": evidence_hits / evidence_n if evidence_n else None,
                         "matched": evidence_hits, "evaluated": evidence_n, "excluded_no_page_or_gold": excluded},
            "tokens": {k: sum(p['metrics'][k] for p in selected) for k in ('input_tokens', 'output_tokens')},
            "latency_ms": {"mean": statistics.mean(latencies) if latencies else None,
                           "p95": latencies[math.ceil(.95 * len(latencies)) - 1] if latencies else None},
            "invalid_or_missing": sum(not valid(predictions.get(r['id']), r.get('task', 'beginner')) for r in gold),
            "unidentifiable_prediction_rows": len(raw_predictions) - len(identifiable),
            "duplicate_prediction_ids": sum(n > 1 for n in counts.values()),
            "extra_ids": len(set(counts) - {r['id'] for r in gold})}


def read_rows(path, tolerant=False):
    rows = []
    for line in Path(path).read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            if not tolerant:
                raise
            rows.append(None)
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--gold', required=True)
    p.add_argument('--predictions', required=True)
    p.add_argument('--output')
    args = p.parse_args()
    report = json.dumps(score(read_rows(args.gold), read_rows(args.predictions, True)), indent=2)
    if args.output:
        Path(args.output).write_text(report + '\n')
    print(report)

if __name__ == '__main__':
    main()
