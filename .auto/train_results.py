#!/usr/bin/env python3
"""TRAIN-only saved-reference verification, scoring and local gates. Never adoption."""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
import tempfile

import run_candidate as old
import train_run as run
import usage

ROOT, OUT = run.ROOT, run.OUT
OFFICIAL = Path('/tmp/ost-official-evaluator-3U4yO9/repo')
OFFICIAL_PYTHON = Path('/tmp/ost-official-evaluator-3U4yO9/env/bin/python')
COMMIT = '5e6957729b77a126006049305ad1ef241211a5b4'
load, require = run.load, run.require


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def by_id(path, ids):
    values = rows(path)
    require(len(values) == len(ids) and {r['id'] for r in values} == set(ids), 'TRAIN_ONLY_IDS_REQUIRED')
    return {r['id']: r for r in values}


def verify_official():
    require(subprocess.check_output(['git', '-C', str(OFFICIAL), 'rev-parse', 'HEAD'], text=True).strip() == COMMIT,
            'OFFICIAL_COMMIT_CHANGED')
    require(not subprocess.check_output(['git', '-C', str(OFFICIAL), 'status', '--porcelain', '--', 'evaluate.py'], text=True).strip(),
            'OFFICIAL_SOURCE_MODIFIED')
    provenance = load(OUT / 'official-rescore-evidence/provenance.json')
    require(provenance['commit'] == COMMIT and provenance['evaluate_sha256'] == old.digest((OFFICIAL / 'evaluate.py').read_bytes()),
            'OFFICIAL_HASH_CHANGED')


def selected_records(job, manifest, ids):
    """Open individual records only after identifying selected TRAIN indices."""
    state = load(job / 'state.json')
    require(state['manifest_sha256'] == usage.digest(manifest) and state['version'] == 'format-1'
            and state['blocked'] is False and state['reserved_tokens'] == 0, 'INVALID_LEDGER_STATE')
    require(manifest['strategy'] == 'C' and manifest['role_models'] == usage.MODELS
            and manifest['models'] == [usage.MODELS['parent']], 'ROLE_MODELS_CHANGED')
    selected = {i: item for i, item in enumerate(manifest['frozen']) if item['case']['id'] in ids}
    require(len(selected) == len(ids), 'SELECTED_RECORDS_MISSING')
    records, attempts, slots = {}, [], set()
    for category in ('cases', 'attempts'):
        for name, sha in state[category].items():
            require(isinstance(name, str) and re.fullmatch(r'70b-\d{2}-(?:case|parent-[012]|child-[01])\.json', name), 'RECORD_PATH_REFUSED')
            index = int(name.split('-')[1])
            if index not in selected:
                continue
            path = job / name
            require(not path.is_symlink(), 'RECORD_SYMLINK')
            record = load(path)
            require(usage.digest(record) == sha, 'RECORD_DIGEST_CHANGED')
            item = selected[index]
            require(record['case_index'] == index and record['model'] == usage.MODELS['parent'], 'CASE_OWNER_CHANGED')
            if category == 'cases':
                require(record['case_id'] == item['case']['id'], 'RECORD_CASE_CHANGED')
                records[record['case_id']] = record
                continue
            role, number = record['role'], record['number']
            require(role in usage.MODELS and type(number) is int and 0 <= number < (3 if role == 'parent' else 2), 'UNKNOWN_ROLE_OR_POSITION')
            require(name == f'70b-{index:02}-{role}-{number}.json', 'REQUEST_SLOT_CHANGED')
            slot = (index, role, number)
            require(slot not in slots, 'DUPLICATE_SLOT')
            slots.add(slot)
            require(record['request_model'] == usage.MODELS[role]
                    and all(record.get(k) is True for k in ('safe', 'usage_known', 'usage_valid', 'server_model_matches'))
                    and record['has_api_error'] is False, 'UNKNOWN_OR_INVALID_USAGE')
            require(record['source_sha256'] == item['messages_sha256'] == usage.digest(item['messages'])
                    and record['assembler_schema_sha256'] == item['schema_sha256'], 'SOURCE_OR_SCHEMA_DIGEST_CHANGED')
            require(all(isinstance(record[k], str) and re.fullmatch('[0-9a-f]{64}', record[k])
                        for k in ('payload_sha256', 'schema_sha256')), 'REQUEST_DIGEST_MISSING')
            response = record['response']
            require(response['model'] == usage.MODELS[role] and 'error' not in response
                    and response['usage'] == record['usage'] and len(response['choices']) == 1
                    and response['choices'][0]['finish_reason'] in ('stop', 'tool_calls', 'length')
                    and isinstance(response['choices'][0]['message'], dict), 'UNKNOWN_RESPONSE_END_STATE')
            u = record['usage']
            require(all(usage.integer(u.get(k)) for k in ('prompt_tokens', 'completion_tokens', 'total_tokens'))
                    and u['total_tokens'] == u['prompt_tokens'] + u['completion_tokens']
                    and type(record['generation_requests']) is int and record['generation_requests'] == 1, 'INVALID_USAGE_SUM')
            require(0 <= record['started_unix_ms'] <= record['completed_unix_ms']
                    and record['api_wait_ms'] >= 0, 'UNKNOWN_REQUEST_TIME')
            attempts.append(record)
    require(set(records) == set(ids), 'MISSING_CASE_RECORDS')
    totals = usage.empty()
    for group in totals.values():
        group['API_wait_seconds'] = 0
    for record in attempts:
        values = (record['usage']['prompt_tokens'], record['usage']['completion_tokens'], record['usage']['total_tokens'], 1)
        groups = [record['role']]
        if record['number'] >= (2 if record['role'] == 'parent' else 1):
            groups.append('repair_window')
        for group in groups:
            totals[group]['API_wait_seconds'] += record['api_wait_ms'] / 1000
            for key, value in zip(usage.FIELDS, values):
                totals[group][key] += value
    for index, item in selected.items():
        record = records[item['case']['id']]
        actual = [a for a in attempts if a['case_index'] == index]
        for role in usage.MODELS:
            numbers = sorted(a['number'] for a in actual if a['role'] == role)
            require(numbers == list(range(len(numbers))), 'NONCONTIGUOUS_ROLE_CALLS')
            require(record['sdk'] is not None and record['sdk']['counts'][role] == len(numbers), 'SDK_CALL_COUNT_MISMATCH')
        require(record['prediction']['metrics']['input_tokens'] == sum(a['usage']['prompt_tokens'] for a in actual)
                and record['prediction']['metrics']['output_tokens'] == sum(a['usage']['completion_tokens'] for a in actual), 'CASE_TOKEN_MISMATCH')
    if len(selected) == len(manifest['frozen']):
        summary = load(job / 'summary.json')
        calls = totals['parent']['calls'] + totals['child']['calls']
        tokens = totals['parent']['total_tokens'] + totals['child']['total_tokens']
        require(len(state['cases']) == len(selected) and len(state['attempts']) == calls, 'UNSELECTED_LEDGER_RECORDS')
        require(state['requests'] == summary['generation_requests'] == calls
                and state['tokens'] == summary['actual_total_tokens'] == tokens, 'LEDGER_TOTAL_MISMATCH')
    return records, totals


def reference():
    run.verify_protocol()
    verify_official()  # Source check only. No evaluator import, grading or inference.
    ids, _ = run.train_split()
    dest = OUT / 'hillclimb-v5-analysis'
    saved = load(dest / 'aggregate.json')['train']
    require(saved['cases'] == 36 and len(saved['repeats']) == 5
            and saved['Q_mean'] == run.BASE_Q
            and statistics.mean(r['Q'] for r in saved['repeats']) == run.BASE_Q, 'SAVED_TRAIN_Q_CHANGED')
    require(statistics.mean(r['Hit_A'] for r in saved['repeats']) == .5, 'SAVED_TRAIN_HIT_CHANGED')
    predictions, records, operations = [], [], []
    for repeat in range(1, 6):
        job = OUT / f'prompt-C-v5-r{repeat}'
        m = load(job / 'manifest.json')
        require(load(job / 'summary.json')['status'] == 'completed'
                and not any((job / f).exists() for f in run.FENCES), 'BASELINE_NOT_COMPLETE')
        require(old.sources(m)[run.RUNNER] == run.OLD_RUNNER, 'SAVED54_RUNNER_CHANGED')
        for item in m['frozen']:
            if item['case']['id'] in ids:
                require(item['messages'][0]['content'] == (run.PROMPTS / 'v5-system.txt').read_text()
                        + '\n\n' + m['protocol_reminder'], 'SAVED_TRAIN_V5_SYSTEM_CHANGED')
        rr, attributed = selected_records(job, m, ids)
        pred = by_id(dest / f'train-r{repeat}-predictions.jsonl', ids)
        require(all(pred[id] == rr[id]['prediction'] for id in ids), 'SAVED_TRAIN_PREDICTION_CHANGED')
        predictions.append(pred)
        records.append(rr)
        operations.append(attributed)
    return saved, predictions, records, operations


def metric(name, value):
    require(type(value) in (int, float) and math.isfinite(value), 'NONFINITE_METRIC')
    print(f'METRIC {name}={value:.17g}')


def baseline_report():
    saved, _, _, _ = reference()
    metric('baseline_train_Q', saved['Q_mean'])
    metric('train_Q_gain_v5', 0)
    metric('train_noise', max(saved['Q_temporal_detectable_difference'], run.LEGACY_NOISE))
    for key in ('F1_A', 'F1_B', 'Hit_A'):
        metric('baseline_train_' + key, statistics.mean(r[key] for r in saved['repeats']))
    print('Saved TRAIN reference verified read-only. No inference, baseline grading or TEST record reads.')


def import_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def paired_interval(basepred, candpred, gold, ids, groups, label_of):
    # Exact grouped paired nonlinear F1/bootstrap formula from compare_candidate.py.
    import numpy as np
    conf = np.zeros((2, len(groups), 2, 3, 3))
    for arm, predictions in enumerate((basepred, candpred)):
        for j, group in enumerate(groups):
            for id in group:
                for pred in predictions:
                    conf[arm, j, ['A', 'B'].index(id[-1]), gold[id]['label'], label_of(pred[id])[0]] += .2
    def f1(c):
        tp = np.diagonal(c, axis1=-2, axis2=-1)
        den = c.sum(axis=-1) + c.sum(axis=-2)
        active = den > 0
        return np.divide(2 * tp, den, out=np.zeros_like(tp), where=active).sum(axis=-1) / active.sum(axis=-1)
    indices = np.random.default_rng(20261016).integers(0, len(groups), size=(20000, len(groups)))
    boot = f1(conf[:, indices].sum(axis=2))
    q = (.30 * boot[:, :, 0] + .28 * boot[:, :, 1]) / .58
    return np.quantile(q[1] - q[0], [.025, .975]).tolist()


def gates(result):
    repeats = result['repeats']
    return {'literal_gain': result['gain'] >= .02 and result['gain'] > result['noise'],
            'F1_each_repeat': all(r['F1_A'] >= .60 and r['F1_B'] >= .75 for r in repeats),
            'canonical_validity': all(r['valid'] == 36 and r['fallback'] == 0 and r['safe'] for r in repeats),
            'evidence_non_regression': statistics.mean(r['Hit_A'] for r in repeats) >= .5}


def completed(version, attempt, grading=False):
    require(version in run.VERSIONS and attempt in (1, 2, 3), 'INVALID_SELECTOR')
    control = run.verify_protocol()
    record = load(run.attempt_path(version, attempt))
    require(record['status'] in (('grading', 'completed') if grading else ('completed',))
            and record['protocol_sha256'] == old.digest(run.CONTROL.read_bytes())
            and record['candidate_sha256'] == load(run.PROMPTS / f'{version}.json')['candidate_prompt_sha256'], 'BATCH_NOT_COMPLETED_OR_CHANGED')
    ids, _ = run.train_split()
    baseline = load(OUT / 'prompt-C-v5-r5/manifest.json')
    predictions, records, operations = [], [], []
    for repeat in range(1, 6):
        job = OUT / run.job_name(version, attempt, repeat)
        require(not job.is_symlink() and not any((job / f).exists() for f in run.FENCES), 'BATCH_FENCE')
        manifest, summary = load(job / 'manifest.json'), load(job / 'summary.json')
        provenance = load(Path(str(job) + '-provenance.json'))
        require(provenance['protocol_sha256'] == record['protocol_sha256']
                and provenance['runner_sha256'] == control['runner_sha256']
                and provenance['manifest_sha256'] == usage.digest(manifest), 'CONTEXT_FREEZE_CHANGED')
        run.audit(manifest, baseline, provenance['pdf_mapping'], control['runner_sha256'],
                  (run.PROMPTS / f'{version}-system.txt').read_text())
        require(summary['status'] == 'completed' and summary['models'][usage.MODELS['parent']]['cases'] == 36, 'BATCH_NOT_COMPLETE')
        rr, attributed = selected_records(job, manifest, ids)
        pred = by_id(job / '70b-canonical.jsonl', ids)
        require(all(pred[id] == rr[id]['prediction'] for id in ids), 'CANONICAL_MISMATCH')
        timing = load(Path(str(job) + '-timing.json'))
        require(timing['exit_code'] == 0 and timing['end'] >= timing['start'], 'COMMAND_TIME_UNKNOWN')
        predictions.append(pred)
        records.append(rr)
        operations.append({'repeat': repeat, 'usage': attributed, 'command_seconds': timing['end'] - timing['start'],
                           'API_wait_seconds': sum(r['api_wait_ms'] for r in rr.values()) / 1000,
                           'case_mean_ms': statistics.mean(r['case_wall_ms'] for r in rr.values()),
                           'case_p95_ms': sorted(r['case_wall_ms'] for r in rr.values())[math.ceil(.95 * 36) - 1]})
    return predictions, records, operations


def compute(version, attempt, grading):
    saved, basepred, baserecords, baseusage = reference()
    candpred, candrecords, operations = completed(version, attempt, grading=grading)
    ids, groups = run.train_split()
    dest = OUT / f'train-{version}-a{attempt}-analysis'
    require(not dest.exists() if grading else dest.is_dir(), 'ANALYSIS_EXISTS_OR_MISSING')
    scores = []
    if grading:
        dest.mkdir()
        grader = import_module('train_grader', ROOT / 'evals/c-system-prompt/grader.py')
        # Reuse frozen TRAIN-only references and mapped inputs, never load cases/gold for TEST.
        expected = by_id(OUT / 'hillclimb-v5-analysis/train-expected.jsonl', ids)
        cases = by_id(OUT / 'hillclimb-v5-analysis/train-cases.jsonl', ids)
        for repeat, predictions in enumerate(candpred, 1):
            def jsonl(path, values):
                path.write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in values))
            # Grader temporary files are strictly outside all model workspaces.
            with tempfile.TemporaryDirectory(prefix='train-grade-', dir=OUT) as tmp:
                tmp = Path(tmp)
                jsonl(tmp / 'expected.jsonl', [expected[id] for id in ids])
                jsonl(tmp / 'cases.jsonl', [cases[id] for id in ids])
                jsonl(tmp / 'predictions.jsonl', [predictions[id] for id in ids])
                score = grader.grade(OFFICIAL, OFFICIAL_PYTHON, tmp / 'predictions.jsonl', tmp / 'expected.jsonl', tmp / 'cases.jsonl')
            run.exclusive(dest / f'train-r{repeat}.json', score)
            scores.append(score)
    else:
        scores = [load(dest / f'train-r{i}.json') for i in range(1, 6)]
    repeats = []
    for i, (score, rr) in enumerate(zip(scores, candrecords), 1):
        require(score['official_commit'] == COMMIT
                and score['official_evaluate_sha256'] == old.digest((OFFICIAL / 'evaluate.py').read_bytes()), 'SCORE_PROTOCOL_CHANGED')
        a, b = (score['official_report']['tasks'][task]['macro_f1'] for task in ('A', 'B'))
        repeats.append({'repeat': i, 'F1_A': a, 'F1_B': b, 'Q': (.30 * a + .28 * b) / .58,
                        'Hit_A': score['primary_evidence_objective']['value'], 'safe': all(score['safe_passes'].values()),
                        'valid': sum(r['output_valid'] for r in rr.values()),
                        'fallback': sum(r['error'] is not None for r in rr.values())})
    official = import_module('train_official', OFFICIAL / 'evaluate.py')
    gold = by_id(OUT / 'hillclimb-v5-analysis/train-expected.jsonl', ids)
    q = statistics.mean(r['Q'] for r in repeats)
    result = {'candidate': version, 'attempt': attempt, 'protocol_sha256': old.digest(run.CONTROL.read_bytes()),
              'baseline_Q': saved['Q_mean'], 'Q': q, 'gain': q - saved['Q_mean'],
              'noise': max(saved['Q_temporal_detectable_difference'], run.LEGACY_NOISE),
              'repeats': repeats, 'operations': operations,
              'paired_group_delta95': paired_interval(basepred, candpred, gold, ids, groups, official.label_of),
              'secondary_deltas': {key: statistics.mean(r[key] for r in repeats)
                                   - statistics.mean(r[key] for r in saved['repeats']) for key in ('F1_A', 'F1_B', 'Hit_A')},
              'baseline_usage': baseusage,
              'secondary_operations': {'token_delta': sum(p['metrics']['input_tokens'] + p['metrics']['output_tokens']
                  for predictions in candpred for p in predictions.values()) - sum(p['metrics']['input_tokens'] + p['metrics']['output_tokens']
                  for predictions in basepred for p in predictions.values()),
                  'contradiction_entailment_delta': sum(gold[id]['label'] == 2 and official.label_of(p[id])[0] == 0 for p in candpred for id in ids)
                   - sum(gold[id]['label'] == 2 and official.label_of(p[id])[0] == 0 for p in basepred for id in ids)}}
    result['secondary_operations']['case_mean_ms_delta'] = statistics.mean(
        r['case_wall_ms'] for rr in candrecords for r in rr.values()) - statistics.mean(
        r['case_wall_ms'] for rr in baserecords for r in rr.values())
    result['secondary_operations']['API_wait_seconds_delta'] = sum(
        r['api_wait_ms'] for rr in candrecords for r in rr.values()) / 1000 - sum(
        r['api_wait_ms'] for rr in baserecords for r in rr.values()) / 1000
    result['gates'] = gates(result)
    result['strict_supplemental'] = result['gain'] >= result['noise'] + .02
    if grading:
        run.exclusive(dest / 'comparison.json', result)
    else:
        require(load(dest / 'comparison.json') == result, 'SAVED_REPORT_CHANGED')
    return result


def report(result, check=False):
    metric('baseline_train_Q', result['baseline_Q'])
    metric('candidate_train_Q', result['Q'])
    metric('train_Q_gain_v5', result['gain'])
    metric('train_noise', result['noise'])
    for key in ('F1_A', 'F1_B', 'Hit_A'):
        metric('candidate_train_' + key, statistics.mean(r[key] for r in result['repeats']))
        metric('train_' + key + '_delta', result['secondary_deltas'][key])
    for group in usage.GROUPS:
        for field in usage.FIELDS:
            metric('candidate_train_' + group + '_' + field, sum(op['usage'][group][field] for op in result['operations']))
        metric('candidate_train_' + group + '_API_wait_seconds', sum(op['usage'][group]['API_wait_seconds'] for op in result['operations']))
    for key in ('command_seconds', 'API_wait_seconds'):
        metric('candidate_train_' + key, sum(op[key] for op in result['operations']))
    print(json.dumps({k: result[k] for k in ('repeats', 'operations', 'paired_group_delta95', 'secondary_operations', 'gates', 'strict_supplemental')}, sort_keys=True))
    for prior in range(1, result['attempt']):
        failed = load(run.attempt_path(result['candidate'], prior))
        print(json.dumps({'failed_attempt': prior, 'status': failed['status'], 'failed_request_usage': failed['failed_request_usage']}))
    print('Completed batch tokens exclude failed attempts and are not total session cost. Repair positions are a subset, not a third role. Hit is a frozen reference surrogate, at ceiling 6/12; no evidence improvement claim. STOP before final validation or adoption.')
    if check:
        require(all(result['gates'].values()), 'CHECKS_FAILED: TRAIN quality gates')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', action='store_true')
    parser.add_argument('--candidate', choices=run.VERSIONS)
    parser.add_argument('--attempt', type=int, choices=(1, 2, 3))
    parser.add_argument('--score', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.baseline:
        require(not args.candidate and not args.attempt and not args.score, 'SELECTOR_CONFLICT')
        baseline_report()
    else:
        require(args.candidate is not None and args.attempt is not None, 'EXPLICIT_CANDIDATE_ATTEMPT_REQUIRED')
        report(compute(args.candidate, args.attempt, args.score), args.check)


if __name__ == '__main__':
    main()
