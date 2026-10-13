"""Seeded dev54 split, without consulting predictions or model scores."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random

SEED = 20261016


def split_cases(rows):
    if len(rows) != 54 or len({r['id'] for r in rows}) != 54:
        raise ValueError('EXPECTED_APPROVED_DEV54')
    pairs = defaultdict(list)
    for row in rows:
        pairs[row['provenance_group']].append(row)
    sources = defaultdict(list)
    for group in sorted(pairs):
        pair = pairs[group]
        if len(pair) != 2 or {r['id'][-1] for r in pair} != {'A', 'B'}:
            raise ValueError('UNPAIRED_SOURCE_ROW')
        a = next(r for r in pair if 'booklet' in r['input'])
        b = next(r for r in pair if 'reference' in r['input'])
        if any(row['source_date'] not in {'2020-09-27', '2021-03-07'} for row in pair):
            raise ValueError('UNAPPROVED_DATE')
        if a['expect']['label'] != b['expect']['label']:
            raise ValueError('PAIR_LABEL_MISMATCH')
        # Identical source passages also stay together, even across source-row IDs.
        ref = b['input']['reference']
        key = hashlib.sha256((ref['language'] + '\0' + ref['text']).encode()).hexdigest()
        sources[key].append(pair)
    keys = sorted(sources)
    random.Random(SEED).shuffle(keys)
    # Select 9 source rows for test, exactly 3 per label, without consulting outputs.
    states = {(0, 0, 0): []}
    for key in keys:
        counts = Counter(pair[0]['expect']['label'] for pair in sources[key])
        for state, chosen in list(states.items()):
            target = tuple(state[i] + counts[i] for i in range(3))
            if max(target) <= 3 and target not in states:
                states[target] = chosen + [key]
    if (3, 3, 3) not in states:
        raise ValueError('NO_GROUP_SAFE_BALANCED_SPLIT')
    test_groups = set(states[(3, 3, 3)])
    result = {'seed': SEED, 'train': [], 'test': [], 'groups': {},
              'method': 'Seeded source-group ordering, first reachable label-balanced subset by dynamic programming.',
              'grouping': 'A/B source-row pair plus exact same reference language/text.',
              'limitations': ['Previously exposed development data, not a true unseen test.',
                             'Different passages from the same booklet/vote may cross splits.']}
    for key in sorted(sources):
        ids = sorted(row['id'] for pair in sources[key] for row in pair)
        result['groups'][key] = ids
        result['test' if key in test_groups else 'train'].extend(ids)
    result['train'].sort()
    result['test'].sort()
    assert len(result['train']) == 36 and len(result['test']) == 18
    assert not set(result['train']) & set(result['test'])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cases', type=Path, default=Path(__file__).with_name('cases.jsonl'))
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('split.json'))
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.cases.read_text().splitlines() if line.strip()]
    result = split_cases(rows)
    with args.output.open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'seed': SEED, 'train_cases': len(result['train']),
                      'test_cases': len(result['test']), 'groups': len(result['groups'])}))


if __name__ == '__main__':
    main()
