#!/usr/bin/env python3
"""Official saved-run scoring/noise and paired comparison. Aggregate stdout only."""
import argparse
import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path
import statistics

import numpy as np
import grader
import variant

MODEL = 'swiss-ai/Apertus-v1.5-70B'
CLI_ONLY = {'track_2a/dev/format/run_comparison.py', 'track_2a/dev/format/test_cli_paths.py'}


def load(path):
    return json.loads(path.read_text())


def jsonl(path):
    return [json.loads(x) for x in path.read_text().splitlines()]


def dump(path, obj):
    with path.open('x') as f:
        f.write(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def rows_out(path, rows):
    with path.open('x') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')


def fixture(repo):
    root = repo / 'evals/c-system-prompt'
    if hashlib.sha256((root / 'cases.jsonl').read_bytes()).hexdigest() != '79e8b0146c013f440bc9c290df4917b1a88d4d32fc18f80a0dec0c92cbef9c54':
        raise ValueError('FIXTURE_HASH_CHANGED')
    if hashlib.sha256((root / 'split.json').read_bytes()).hexdigest() != '963cb7cfaab01cb8b178cf0ce1d5207e464ad0a81b5868370186aa161d0be3d9':
        raise ValueError('FIXED_SPLIT_CHANGED')
    rows = jsonl(root / 'cases.jsonl')
    if len(rows) != 54 or len({r['id'] for r in rows}) != 54:
        raise ValueError('APPROVED_FIXTURE_REQUIRED')
    if {r['source_date'] for r in rows} != {'2020-09-27', '2021-03-07'}:
        raise ValueError('APPROVED_DATES_REQUIRED')
    split = load(root / 'split.json')
    return {r['id']: r for r in rows}, split


def sides(part, byid, split):
    parts = ['full'] if part == 'full' else ['train', 'test']
    for name in parts:
        ids = list(byid) if name == 'full' else split[name]
        chosen = set(ids)
        groups = [g for g in split['groups'].values() if set(g) <= chosen]
        if set(x for g in groups for x in g) != chosen:
            raise ValueError('SOURCE_GROUP_SPLIT_CHANGED')
        yield name, ids, groups


def f1(conf):
    tp = np.diagonal(conf, axis1=-2, axis2=-1)
    den = conf.sum(axis=-1) + conf.sum(axis=-2)
    active = den > 0
    return np.divide(2 * tp, den, out=np.zeros_like(tp), where=active).sum(axis=-1) / active.sum(axis=-1)


def q(fs):
    return (.30 * fs[..., 0] + .28 * fs[..., 1]) / .58


def confusion(predictions, ids, groups, byid, official):
    # Group x repeat x task x gold x predicted. Retain repeats for both estimands.
    conf = np.zeros((len(groups), len(predictions), 2, 3, 3))
    for g, group in enumerate(groups):
        for id in group:
            for r, preds in enumerate(predictions):
                label = official.label_of(preds[id])[0]
                if label not in (0, 1, 2):
                    raise ValueError('INVALID_CANONICAL_LABEL')
                conf[g, r, ['A', 'B'].index(id[-1]), byid[id]['expect']['label'], label] += 1
    return conf


def noise(values):
    sd = statistics.stdev(values) if len(values) > 1 else None
    return {'mean': statistics.mean(values), 'runSD': sd,
            'detectable_width': 2 * math.sqrt(2) * sd / math.sqrt(len(values)) if sd is not None else None}


def command_time(job):
    # Exact designated prefix only: never repair r4. or infer an absent start.
    start, end = [Path(str(job) + '-' + x + '.txt') for x in ['start', 'end']]
    s = float(start.read_text()) if start.is_file() else None
    e = float(end.read_text()) if end.is_file() else None
    return {'command_start': s, 'command_end': e,
            'command_seconds': e - s if s is not None and e is not None else None}


def operations(job, preds, ids, byid, official):
    records = {}
    # Parse named case records, never discover jobs or attempt records.
    for i in range(54):
        path = job / f'70b-{i:02}-case.json'
        if path.is_file():
            record = load(path)
            records[record['case_id']] = record
    rr = [records[id] for id in ids if id in records]
    complete = len(rr) == len(ids)
    walls = sorted(r['case_wall_ms'] for r in rr) if complete and all('case_wall_ms' in r for r in rr) else None
    metrics = [preds[id].get('metrics', {}) for id in ids]
    total = sum(m['input_tokens'] + m['output_tokens'] for m in metrics) if all('input_tokens' in m and 'output_tokens' in m for m in metrics) else None
    token_values = sorted(m['input_tokens'] + m['output_tokens'] for m in metrics) if total is not None else None
    waits = sorted(r['api_wait_ms'] for r in rr) if complete and all('api_wait_ms' in r for r in rr) else None
    summary_path = job / 'summary.json'
    summary = load(summary_path) if summary_path.is_file() else {}
    emissions = variant.child_emissions(None)
    selected_indices = {r['case_index'] for r in rr}
    for index in selected_indices:
        for number in range(2):
            path = job / f'70b-{index:02}-child-{number}.json'
            if path.is_file():
                counts = variant.child_emissions(load(path).get('response'))
                for k, v in counts.items():
                    emissions[k] += v
    return {**emissions, 'valid': sum(r['output_valid'] for r in rr) if complete else None,
            'fallback_neutral': sum(r.get('error') == 'NO_ACCEPTED_SUBMIT' and r['prediction']['label'] == 1 for r in rr) if complete else None,
            'contradiction_entailment': sum(byid[id]['expect']['label'] == 2 and official.label_of(preds[id])[0] == 0 for id in ids),
            'tokens': total, 'tokens_per_case': total / len(ids) if total is not None else None,
            'tokens_per_case_p95': token_values[math.ceil(.95 * len(token_values)) - 1] if token_values else None,
            'API_wait_mean_ms': statistics.mean(waits) if waits else None,
            'API_wait_p95_ms': waits[math.ceil(.95 * len(waits)) - 1] if waits else None,
            'case_mean_ms': statistics.mean(walls) if walls else None,
            'case_p95_ms': walls[math.ceil(.95 * len(walls)) - 1] if walls else None,
            'API_wait_ms': sum(r['api_wait_ms'] for r in rr) if complete and all('api_wait_ms' in r for r in rr) else None,
            'requests_full_run': summary.get('generation_requests'),
            **command_time(job)}


def source_hashes(m):
    return {k[k.index('track_2a/'):]: v for k, v in m['sources'].items()}


def normalize_case(case):
    case = dict(case)
    if 'booklet' in case:
        case['booklet'] = {**case['booklet'], 'path': Path(case['booklet']['path']).name}
    return case


def audit(jobs, allow_cli, requested_variant=None):
    manifests = [load(j / 'manifest.json') for j in jobs]
    variant_jobs = [j for j, m in zip(jobs, manifests) if m.get('variant')]
    if variant_jobs and requested_variant != variant.NAME:
        raise ValueError('VARIANT_REQUIRES_EXPLICIT_OPTION')
    if requested_variant and not variant_jobs:
        raise ValueError('REQUESTED_VARIANT_MISSING')
    historical_differences = []
    for job, m in zip(jobs, manifests):
        if m.get('variant'):
            variant.verify_manifest(m)
        elif requested_variant:
            historical_differences.append({'job': str(job), 'differences_from_current_base': variant.verify_baseline(m, allow_cli)})
    reference = manifests[0]
    if reference.get('strategy') != 'C' or reference.get('role_models') != {'parent': MODEL, 'child': 'swiss-ai/Apertus-v1.5-8B'}:
        raise ValueError('FIXED_C_ROLE_MODELS_REQUIRED')
    differences = []
    for job, m in zip(jobs, manifests):
        # Every cap/model/tool policy field must match; sources and SYSTEM are the only exceptions.
        if {k: v for k, v in m.items() if k not in (('sources', 'frozen', 'variant', 'variant_patch_sha256') if requested_variant else ('sources', 'frozen'))} != {k: v for k, v in reference.items() if k not in (('sources', 'frozen', 'variant', 'variant_patch_sha256') if requested_variant else ('sources', 'frozen'))}:
            raise ValueError('MODEL_CAP_POLICY_CHANGED')
        if len(m['frozen']) != 54:
            raise ValueError('FROZEN_CASE_COUNT_CHANGED')
        for a, b in zip(reference['frozen'], m['frozen']):
            if normalize_case(a['case']) != normalize_case(b['case']):
                raise ValueError('SOURCE_INPUT_CHANGED')
            if {k: v for k, v in a.items() if k not in ('case', 'messages', 'messages_sha256')} != {k: v for k, v in b.items() if k not in ('case', 'messages', 'messages_sha256')}:
                raise ValueError('PAGES_CANDIDATES_SCHEMA_CHANGED')
            if a['messages'][1:] != b['messages'][1:]:
                raise ValueError('USER_MESSAGES_CHANGED')
        a, b = source_hashes(reference), source_hashes(m)
        set_changes = set(a) ^ set(b)
        if set_changes - (CLI_ONLY if allow_cli else set()):
            raise ValueError('SOURCE_SET_CHANGED')
        changed = sorted(set_changes | {k for k in set(a) & set(b) if a[k] != b[k]})
        permitted = {'track_2a/src/predict.py'} | (CLI_ONLY if allow_cli else set())
        if requested_variant and bool(reference.get('variant')) != bool(m.get('variant')):
            spec, _ = variant.specification()
            permitted |= set(spec['role_hashes'])
        if set(changed) - permitted:
            raise ValueError('NON_PROMPT_CODE_CHANGED: ' + repr(changed))
        differences.append({'job': str(job), 'changed_source_hashes': changed,
                            'source_hash_differences': {k: {'reference': a.get(k), 'input': b.get(k)} for k in changed},
                            'system_changed': any(a['messages'][0] != b['messages'][0] for a, b in zip(reference['frozen'], m['frozen']))})
    return {'reference_job': str(jobs[0]), 'differences': differences,
            'cli_only_hash_allowance_explicit': allow_cli, 'requested_variant': requested_variant,
            'historical_baseline_source_differences': historical_differences,
            'caution': 'predict.py hash allowance cannot prove historical edits were SYSTEM-only; review provenance/source diff. CLI-only allowance is not permission for tool/model/cap changes.'}


def score(jobs, dest, part, byid, split, official_repo, python, samples):
    dest.mkdir()
    predictions = []
    for job in jobs:
        if any((job / x).exists() for x in ('inflight.json', 'state.pending', 'STOP.json')):
            raise ValueError('UNCERTAIN_JOB: read-only, no scoring completed-run claim')
        summary = load(job / 'summary.json')
        state = load(job / 'state.json')
        if summary.get('status') != 'completed' or state.get('blocked') or state.get('reserved_tokens') != 0:
            raise ValueError('COMPLETED_KNOWN_USAGE_JOB_REQUIRED')
        if summary.get('actual_total_tokens') != state.get('tokens') or not isinstance(state.get('tokens'), int):
            raise ValueError('KNOWN_USAGE_MISMATCH')
        names = {f'70b-{i:02}-case.json' for i in range(54)}
        if set(state.get('cases', {})) != names or not all((job / name).is_file() for name in names):
            raise ValueError('MISSING_COMPLETED_CASES')
        manifest_bytes = json.dumps(load(job / 'manifest.json'), ensure_ascii=False,
                                    sort_keys=True, allow_nan=False).encode()
        if state.get('version') != 'format-1' or state.get('manifest_sha256') != hashlib.sha256(manifest_bytes).hexdigest():
            raise ValueError('MANIFEST_LEDGER_MISMATCH')
        for record_name in state.get('attempts', {}):
            if not re.fullmatch(r'70b-\d{2}-(parent|child)-\d+\.json', record_name):
                raise ValueError('UNEXPECTED_ATTEMPT_RECORD_PATH')
            attempt = load(job / record_name)
            usage = attempt.get('usage', {})
            if attempt.get('usage_valid') is not True or not all(type(usage.get(k)) is int and usage[k] >= 0 for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')) or usage['total_tokens'] != usage['prompt_tokens'] + usage['completion_tokens']:
                raise ValueError('UNKNOWN_ATTEMPT_USAGE')
        for record_name, sha in {**state['attempts'], **state['cases']}.items():
            if not re.fullmatch(r'70b-\d{2}-((parent|child)-\d+|case)\.json', record_name):
                raise ValueError('UNEXPECTED_LEDGER_RECORD_PATH')
            record = load(job / record_name)
            encoded = json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()
            if hashlib.sha256(encoded).hexdigest() != sha:
                raise ValueError('LEDGER_RECORD_CHANGED')
        attempts = [load(job / name) for name in state.get('attempts', {})]
        if load(job / 'manifest.json').get('variant'):
            for attempt in attempts:
                if attempt['role'] == 'child' and attempt.get('child_output_audit') != variant.child_emissions(attempt.get('response')):
                    raise ValueError('RAW_CHILD_OUTPUT_AUDIT_MISMATCH')
        if len(attempts) != state.get('requests') or sum(a['usage']['total_tokens'] for a in attempts) != state['tokens']:
            raise ValueError('ATTEMPT_LEDGER_MISMATCH')
        rows = jsonl(job / '70b-canonical.jsonl')
        preds = {r['id']: r for r in rows}
        if len(rows) != 54 or set(preds) != set(byid):
            raise ValueError('PREDICTION_IDS_CHANGED')
        for name in names:
            record = load(job / name)
            if preds.get(record['case_id']) != record['prediction']:
                raise ValueError('CANONICAL_RECORD_MISMATCH')
        predictions.append(preds)
    result, confs = {}, {}
    official = None
    for name, ids, groups in sides(part, byid, split):
        expected, cases = dest / f'{name}-expected.jsonl', dest / f'{name}-cases.jsonl'
        rows_out(expected, [{'id': id, **byid[id]['expect']} for id in ids])
        rows_out(cases, [byid[id]['input'] for id in ids])
        runs = []
        for i, (job, preds) in enumerate(zip(jobs, predictions), 1):
            path = dest / f'{name}-r{i}-predictions.jsonl'
            rows_out(path, [preds[id] for id in ids])
            report = grader.grade(official_repo, python, path, expected, cases)
            # Load official helpers only after the pinned adapter checks succeed.
            if official is None:
                spec = importlib.util.spec_from_file_location('official', official_repo / 'evaluate.py')
                official = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(official)
            dump(dest / f'{name}-r{i}-scored.json', report)
            runs.append({'job': str(job), 'F1_A': report['official_report']['tasks']['A']['macro_f1'],
                         'F1_B': report['official_report']['tasks']['B']['macro_f1'],
                         'Q': report['classification_objective']['value'],
                         'Hit_A': report['primary_evidence_objective']['value'],
                         'safe_passes': report['safe_passes'],
                         'operations': operations(job, preds, ids, byid, official)})
        conf = confusion(predictions, ids, groups, byid, official)
        confs[name] = conf
        indices = np.random.default_rng(split['seed']).integers(0, len(groups), size=(samples, len(groups)))
        boot = conf[indices].sum(axis=1)
        pooled = q(f1(boot.sum(axis=1)))
        mean = q(f1(boot)).mean(axis=1)
        result[name] = {'cases': len(ids), 'source_groups': len(groups), 'runs': runs,
                        'metrics': {key: noise([r[key] for r in runs]) for key in ('F1_A', 'F1_B', 'Q')},
                        'child_label_emissions_total': sum(r['operations']['child_label_emissions'] for r in runs),
                        'child_label_free_all': all(r['operations']['child_label_emissions'] == 0 for r in runs),
                        'Hit_A_mean': statistics.mean(r['Hit_A'] for r in runs) if all(r['Hit_A'] is not None for r in runs) else None,
                        'Q_pooled': float(q(f1(conf.sum(axis=(0, 1))))),
                        'Q_pooled_group_bootstrap_95': np.quantile(pooled, [.025, .975]).tolist(),
                        'Q_mean_repeat_group_bootstrap_95': np.quantile(mean, [.025, .975]).tolist(),
                        'safe_all': all(all(r['safe_passes'].values()) for r in runs)}
    dump(dest / 'aggregate.json', result)
    return result, confs


def paired(base, candidate, seed, samples):
    if base.shape[0] != candidate.shape[0]:
        raise ValueError('SOURCE_GROUPS_CHANGED')
    indices = np.random.default_rng(seed).integers(0, len(base), size=(samples, len(base)))
    def estimands(conf):
        boot = conf[indices].sum(axis=1)
        return q(f1(boot.sum(axis=1))), q(f1(boot)).mean(axis=1)
    bp, bm = estimands(base)
    cp, cm = estimands(candidate)
    return {'pooled_delta95': np.quantile(cp - bp, [.025, .975]).tolist(),
            'mean_repeat_delta95': np.quantile(cm - bm, [.025, .975]).tolist()}


def adoption(comparisons, candidate, requested_variant=None):
    child_free = not requested_variant or all(candidate[side].get('child_label_free_all') is True for side in ('train', 'test'))
    return {'adopt_literal': child_free and all(r['literal_pass'] is True and r['candidate_safe_all'] for r in comparisons.values()),
            'adopt_strict': child_free and all(r['strict_reference_pass'] is True and r['candidate_safe_all'] for r in comparisons.values())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['score', 'compare'])
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--official-repo', type=Path, required=True)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--jobs', nargs='+', type=Path, required=True, help='baseline inputs; exact read-only paths')
    parser.add_argument('--candidate-jobs', nargs='+', type=Path)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--part', choices=['full', 'split'], default='split')
    parser.add_argument('--bootstrap-samples', type=int, default=20000)
    parser.add_argument('--variant', choices=[variant.NAME])
    parser.add_argument('--allow-cli-only-hash-changes', action='store_true')
    args = parser.parse_args()
    if args.bootstrap_samples <= 0:
        parser.error('bootstrap samples must be positive')
    if (args.command == 'compare') != bool(args.candidate_jobs):
        parser.error('compare requires --candidate-jobs; score does not accept it')
    if args.command == 'compare' and args.part != 'split':
        parser.error('adoption comparison requires BOTH train and test: --part split')
    args.jobs = [x.resolve() for x in args.jobs]
    candidates = [x.resolve() for x in args.candidate_jobs or []]
    if len(set(args.jobs)) != len(args.jobs) or len(set(candidates)) != len(candidates):
        parser.error('duplicate jobs within an arm are not independent repeats')
    dest = args.destination.resolve()
    # All generated raw/scored data must remain in ignored output.
    output = (args.repo.resolve() / 'output').resolve()
    if not dest.is_relative_to(output) or dest == output or dest.exists() or any(dest.is_relative_to(job) for job in args.jobs + candidates):
        parser.error('fresh destination under repo/output required')
    byid, split = fixture(args.repo.resolve())
    for job in args.jobs + candidates:
        frozen = load(job / 'manifest.json')['frozen']
        if len(frozen) != 54 or {item['case']['id'] for item in frozen} != set(byid):
            raise ValueError('FROZEN_IDS_CHANGED')
        for item in frozen:
            id = item['case']['id']
            if id not in byid or normalize_case(item['case']) != normalize_case(byid[id]['input']):
                raise ValueError('FROZEN_INPUT_DIFFERS_FROM_APPROVED_FIXTURE')
    source_audit = audit(args.jobs + candidates, args.allow_cli_only_hash_changes, args.variant)
    dest.mkdir(parents=True)
    base, bc = score(args.jobs, dest / 'baseline', args.part, byid, split,
                     args.official_repo.resolve(), args.python.absolute(), args.bootstrap_samples)
    result = {'version': 1, 'new_model_calls': 0, 'source_audit': source_audit, 'baseline': base,
              'bootstrap': {'samples': args.bootstrap_samples, 'seed': split['seed'],
                            'unit': 'same source groups and all repeats, jointly resampled',
                            'estimands': 'pooling confusion then F1 differs from mean repeat nonlinear F1'},
              'limitations': ['Previously exposed dev54, not unseen generalization.',
                              'Group bootstrap is case uncertainty, not generation noise; runSD uses observed repeats.',
                              'Groups may share booklets/votes; review operational/evidence regressions.']}
    if candidates:
        cand, cc = score(candidates, dest / 'candidate', args.part, byid, split,
                         args.official_repo.resolve(), args.python.absolute(), args.bootstrap_samples)
        comparisons = {}
        for name in base:
            gain = cand[name]['metrics']['Q']['mean'] - base[name]['metrics']['Q']['mean']
            width = base[name]['metrics']['Q']['detectable_width']
            comparisons[name] = {'gain': gain, 'baseline_noise': width,
                                 'literal_pass': gain >= .02 and gain > width if width is not None else None,
                                 'strict_reference_pass': gain >= width + .02 if width is not None else None,
                                 'candidate_safe_all': cand[name]['safe_all'],
                                 **paired(bc[name], cc[name], split['seed'], args.bootstrap_samples)}
        result.update(candidate=cand, comparison=comparisons,
                      **adoption(comparisons, cand, args.variant))
    dump(dest / 'analysis.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
