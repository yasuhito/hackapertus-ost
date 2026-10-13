"""Read-only aggregate reporting and conservative local acceptance gates."""
import argparse
import json
import math
from pathlib import Path
import statistics

import usage

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/cscs'
VERSIONS = ('v3', 'v4', 'v5', 'v6', 'v7', 'v8', 'v9', 'v10')
FENCES = {'STOP.json', 'inflight.json', 'state.pending'}


def load(path):
    return json.loads(path.read_text())


def completed_jobs(out, version):
    if version not in VERSIONS:
        raise ValueError('REFUSED: selected saved candidate must be v3..v10')
    split = load(ROOT / 'evals/c-system-prompt/split.json')
    ids = split['train'] + split['test']
    assert len(ids) == len(set(ids)) == 54, 'SPLIT_IDS_CHANGED'
    summaries = []
    for repeat in range(1, 6):
        job = out / f'prompt-C-{version}-r{repeat}'
        assert job.is_dir() and not job.is_symlink(), 'MISSING_CANDIDATE_JOB'
        # Sidecar fences are included as well as nested job fences.
        for path in out.glob(f'prompt-C-{version}-r{repeat}*'):
            assert path.name not in FENCES and not any(f in path.name for f in FENCES), 'CANDIDATE_FENCE'
            if path.is_dir():
                assert not any(p.name in FENCES for p in path.rglob('*')), 'CANDIDATE_FENCE'
        summary = load(job / 'summary.json')
        assert summary['status'] == 'completed', 'INCOMPLETE_CANDIDATE'
        frozen = load(job / 'manifest.json')['frozen']
        actual = [r['case']['id'] for r in frozen]
        assert len(actual) == 54 and set(actual) == set(ids), 'MANIFEST_IDS_CHANGED'
        predictions = [json.loads(line)['id'] for line in (job / '70b-canonical.jsonl').read_text().splitlines()]
        assert len(predictions) == 54 and set(predictions) == set(ids), 'PREDICTION_IDS_CHANGED'
        summaries.append(summary)
    return summaries


def saved(out, version):
    summaries = completed_jobs(out, version)
    dest = out / f'hillclimb-{version}-analysis'
    assert not any(p.name in FENCES for p in dest.rglob('*')), 'ANALYSIS_FENCE'
    aggregate = load(dest / 'aggregate.json')
    comparison = load(dest / 'comparison.json')
    baseline = load(out / 'hillclimb-split5-date-balanced-analysis/aggregate.json')
    for part, count in (('train', 36), ('test', 18)):
        side = aggregate[part]
        assert side['cases'] == count and [r['repeat'] for r in side['repeats']] == list(range(1, 6)), 'INCOMPLETE_AGGREGATE'
        c = comparison['splits'][part]
        assert len(c['candidate_operations']) == 5, 'INCOMPLETE_OPERATIONS'
        assert math.isclose(side['Q_mean'], statistics.mean(r['Q'] for r in side['repeats']), abs_tol=1e-12)
        assert math.isclose(c['candidate_mean_Q'], side['Q_mean'], abs_tol=1e-12)
        assert math.isclose(c['baseline_mean_Q'], baseline[part]['Q_mean'], abs_tol=1e-12)
        assert math.isclose(c['gain'], side['Q_mean'] - baseline[part]['Q_mean'], abs_tol=1e-12)
        assert c['baseline_noise'] == baseline[part]['Q_temporal_detectable_difference']
        assert all(math.isfinite(r[k]) for r in side['repeats'] for k in ('Q', 'F1_A', 'F1_B', 'Hit_A'))
    assert [o['repeat'] for o in comparison['operations']] == list(range(1, 6)), 'INCOMPLETE_OPERATIONS'
    return aggregate, comparison, summaries


def report(out, version, check=False):
    aggregate, comparison, summaries = saved(out, version)
    role_usage = usage.candidate_usage(out, version, summaries,
                                       load(ROOT / 'evals/c-system-prompt/split.json'))
    for scope, prefix in [('totals', 'candidate')] + [(part, f'candidate_{part}') for part in ('train', 'test')]:
        for role in usage.GROUPS:
            for key in usage.FIELDS:
                value = sum((row['totals'] if scope == 'totals' else row['splits'][scope])[role][key]
                            for row in role_usage)
                print(f'METRIC {prefix}_{role}_{key}={value}')
    failures = []
    gains = []
    for part in ('train', 'test'):
        side, c = aggregate[part], comparison['splits'][part]
        gains.append(c['gain'])
        print(f"METRIC candidate_{part}_Q={side['Q_mean']:.17g}")
        print(f"METRIC {part}_Q_gain={c['gain']:.17g}")
        print(f"METRIC {part}_baseline_noise={c['baseline_noise']:.17g}")
        for key in ('F1_A', 'F1_B', 'Hit_A'):
            print(f"METRIC {part}_{key}_mean={statistics.mean(r[key] for r in side['repeats']):.17g}")
        for row, op in zip(side['repeats'], c['candidate_operations']):
            print(f"{part} repeat {row['repeat']}: F1_A={row['F1_A']:.17g} F1_B={row['F1_B']:.17g} Hit_A={row['Hit_A']:.17g} valid={op['valid']} fallback_neutral={op['fallback_neutral']} safe={row['safe_passes']}")
            print(f"{part} repeat {row['repeat']} operations: {json.dumps(op, sort_keys=True)}")
            if row['F1_A'] < .60 or row['F1_B'] < .75:
                failures.append(f'{part} repeat {row["repeat"]}: F1 threshold')
            if not all(row['safe_passes'].values()) or op['valid'] != side['cases']:
                failures.append(f'{part} repeat {row["repeat"]}: validity/safety')
        hit_delta = c['candidate_Hit_A_mean'] - c['baseline_Hit_A_mean']
        print(f'METRIC {part}_Hit_reference_surrogate_gain={hit_delta:.17g}')
        if c['gain'] < .02 or c['gain'] <= c['baseline_noise']:
            failures.append(f'{part}: gain must be >=0.02 and > measured baseline noise')
    print(f'METRIC min_Q_gain={min(gains):.17g}')
    for key, label in (('seconds', 'command_seconds'), ('API_wait_seconds', 'API_wait_seconds'), ('tokens', 'total_tokens'), ('POST', 'generation_requests')):
        values = [op.get(key) for op in comparison['operations']]
        if all(isinstance(value, (int, float)) for value in values):
            print(f'METRIC candidate_{label}={sum(values):.17g}')
        else:
            print(f'candidate {label}: unknown')
    for op, summary, attributed in zip(comparison['operations'], summaries, role_usage):
        print('repeat operations: ' + json.dumps(op, sort_keys=True))
        for model, data in summary['models'].items():
            print(f"repeat {op['repeat']} {model}: prompt_tokens={data.get('prompt_tokens', 'unknown')} completion_tokens={data.get('completion_tokens', 'unknown')} calls_by_role={data.get('calls_by_role', 'unknown')}")
        print('repeat role usage: ' + json.dumps({'repeat': op['repeat'], **attributed}, sort_keys=True))
        if any(data['output_valid'] != 54 or data.get('evaluation_failures', 0) for data in summary['models'].values()):
            failures.append(f'repeat {op["repeat"]}: invalid summary')
    print('Repair-window usage is a subset of parent/child usage, attributed by request position (parent >=2, child >=1). Saved payloads are unavailable, so this does not identify decoded-payload schema repairs.')
    print('Hit is a local reference surrogate, not the official overall score. min_Q_gain is a conservative split minimum, not production adoption.')
    if check and failures:
        raise SystemExit('REJECTED: ' + '; '.join(failures))
    if check:
        print('PASS: local candidate gates only. STOP: production adoption requires separate approval.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, choices=VERSIONS)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    report(OUT, args.candidate, args.check)


if __name__ == '__main__':
    main()
