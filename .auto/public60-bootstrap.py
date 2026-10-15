"""Read-only PUBLIC60 paired cluster bootstrap; run with the pinned evaluator venv."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
ROOT = Path('output/cscs')
BUNDLE = Path('output/validation/v16-public-v2-completion')
OFFICIAL = Path('/tmp/ost-official-evaluator-3U4yO9/repo/evaluate.py')
OUT = ROOT / 'public60b-bootstrap.json'
SEED, SAMPLES = 20261016, 20000


def load(path):
    return json.loads(path.read_text())


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def macro(cm):
    denominator = cm.sum(axis=-1) + cm.sum(axis=-2)
    f1 = np.divide(2 * np.diagonal(cm, axis1=-2, axis2=-1), denominator,
                   out=np.zeros(denominator.shape), where=denominator > 0)
    present = (denominator > 0).sum(axis=-1)
    return np.divide(f1.sum(axis=-1), present, out=np.zeros(present.shape), where=present > 0)


def scorer_tests():
    spec = importlib.util.spec_from_file_location('pinned_official', OFFICIAL)
    official = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(official)
    cases = [[], [(0, 0)], [(0, 0), (1, 1)], [(0, 0), (0, 2)],
             [(0, 1), (1, 0)], [(0, 0), (1, 2), (2, 2)]]
    for pairs in cases:
        cm = np.zeros((3, 3), dtype=int)
        for gold, pred in pairs:
            cm[gold, pred] += 1
        answer = official.macro_f1(pairs)
        assert abs(float(macro(cm)) - (answer[0] if isinstance(answer, tuple) else answer)) < 1e-12
    assert float(macro(np.diag([1, 0, 0]))) == 1.0
    return len(cases)


def main():
    protocol_path = ROOT / 'public60-continue-v16-protocol.json'
    phase_paths = [ROOT / f'public60b-{v}-analysis.json' for v in ('v5', 'v16')]
    protocol = load(protocol_path)
    jobs = [sorted([j for j in protocol['jobs'] if j['variant'] == v], key=lambda j: j['repeat'])
            for v in ('v5', 'v16')]
    assert all([j['repeat'] for j in group] == list(range(1, 6)) for group in jobs)
    assert [j['name'] for j in jobs[0]] == ['public60-v5-r1'] + [f'public60b-v5-r{i}' for i in range(2, 6)]
    assert [j['name'] for j in jobs[1]] == [f'public60b-v16-r{i}' for i in range(1, 6)]
    predictions = [[ROOT / j['name'] / '70b-canonical.jsonl' for j in group] for group in jobs]
    expected_path, manifest_path, metadata_path = [BUNDLE / name for name in
        ('expected.jsonl', 'selection-manifest.json', 'source-metadata.jsonl')]
    inputs = [protocol_path, *phase_paths, expected_path, manifest_path, metadata_path, OFFICIAL,
              *[p for group in predictions for p in group]]
    before = {str(p): sha(p) for p in inputs}
    tests = scorer_tests()
    assert protocol['bootstrap_samples'] == SAMPLES and protocol['bootstrap_seed'] == SEED
    phases = [load(p) for p in phase_paths]
    assert all(p['protocol_sha256'] == before[str(protocol_path)] for p in phases)
    expected = [{k: row[k] for k in ('id', 'label')} for row in rows(expected_path)]
    ids = [r['id'] for r in expected]
    assert len(ids) == len(set(ids)) == 60
    gold = np.array([r['label'] for r in expected])
    assert all(type(r['label']) is int and r['label'] in range(3) for r in expected)
    task = np.array([i.rsplit('-', 1)[-1] == 'B' for i in ids], dtype=int)
    assert all(i.rsplit('-', 1)[-1] in ('A', 'B') for i in ids) and task.sum() == 30
    selection = load(manifest_path)['selection']
    metadata = rows(metadata_path)
    meta = {r['source_index']: r for r in metadata}
    assert len(meta) == len(metadata) == len(selection) == 30
    assert len({s['group_digests']['reference'] for s in selection}) == 30
    pair_map, dates = {}, {}
    for index, item in enumerate(selection):
        pair = item['case_ids']
        assert len(pair) == 2 and {i.rsplit('-', 1)[-1] for i in pair} == {'A', 'B'}
        source = meta[item['source_index']]
        assert source['group_digests'] == item['group_digests']
        assert source['input_sha256'] == item['input_sha256']
        for case_id in pair:
            assert case_id not in pair_map
            pair_map[case_id], dates[case_id] = index, source['date']
    assert set(pair_map) == set(ids)
    # Row contribution: variant x repeat x row x task x gold x prediction.
    contribution = np.zeros((2, 5, 60, 2, 3, 3), dtype=np.int64)
    for variant, group in enumerate(predictions):
        for repeat, path in enumerate(group):
            records = rows(path)
            by_id = {r['id']: r['label'] for r in records}
            assert len(records) == len(by_id) == 60 and set(by_id) == set(ids)
            assert all(type(x) is int and x in range(3) for x in by_id.values())
            assert phases[variant]['artifacts'][str(path)] == before[str(path)]
            contribution[variant, repeat, np.arange(60), task, gold, [by_id[i] for i in ids]] = 1
    def quality(cm):
        return (macro(cm) @ np.array([.30, .28])) / .58
    full_q = quality(contribution.sum(axis=2))
    official_q = np.array([[r['Q'] for r in p['results']] for p in phases])
    assert full_q.shape == (2, 5) and np.max(np.abs(full_q - official_q)) < 1e-12
    points = full_q.mean(axis=1)
    reports = {}
    for name, labels in [('source_row_pairs', [pair_map[i] for i in ids]),
                         ('date_clusters', [dates[i] for i in ids])]:
        _, inverse = np.unique(labels, return_inverse=True)
        count = int(inverse.max()) + 1
        grouped = np.stack([contribution[:, :, inverse == g].sum(axis=2) for g in range(count)])
        rng = np.random.default_rng(SEED)  # Reset the predeclared seed for each grouping.
        draws = rng.integers(count, size=(SAMPLES, count))
        weights = np.zeros((SAMPLES, count), dtype=np.int64)
        np.add.at(weights, (np.arange(SAMPLES)[:, None], draws), 1)
        cm = np.tensordot(weights, grouped, axes=(1, 0))
        q = quality(cm).mean(axis=-1)  # Average five repeat Qs, never pool repeats.
        delta = q[:, 1] - q[:, 0]
        ci = np.quantile(delta, [.025, .975], method='linear').tolist()
        reports[name] = {'groups': count, 'delta_percentile_95_ci': ci,
                         'ci_crosses_zero': bool(ci[0] <= 0 <= ci[1])}
    after = {str(p): sha(p) for p in inputs}
    assert before == after
    result = {'samples': SAMPLES, 'seed': SEED, 'baseline_Q': float(points[0]),
              'candidate_Q': float(points[1]), 'delta_Q': float(points[1] - points[0]),
              'per_repeat_Q': full_q.tolist(), 'groupings': reports,
              'tests': {'official_macro_cases': tests, 'full_Q_tolerance': 1e-12,
                        'ids_pairs_repeats_verified': True},
              'sha256_before': before, 'sha256_after': after, 'inputs_unchanged': True,
              'gate_status': 'FAILED before bootstrap: 12 vs 7 fallbacks; gain < 0.02. No research adoption; public-data uncertainty only.'}
    assert not OUT.exists(), 'Refusing to overwrite an existing bootstrap result'
    OUT.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('baseline_Q', 'candidate_Q', 'delta_Q', 'groupings', 'inputs_unchanged')}))


if __name__ == '__main__':
    import argparse
    argparse.ArgumentParser(description=__doc__).parse_args()
    main()
