#!/usr/bin/env python3
"""Run the production strategy-C pipeline on a prepared validation bundle and grade it.

Usage:
  run_bundle.py --bundle output/validation/role-review-v1 --job output/cscs/<name> [--grade]

The bundle holds cases.jsonl, booklets/ and (for grading only) expected.jsonl.
Contexts are built with the current src/ code, so this measures whatever page
selection and prompts are checked in. Requests go through the retry-aware
physical ledger with the same caps as the overnight protocols. Gold is read
only by the official grader, after all answers are stored.
"""
import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RUNNER = REPO / 'track_2a/dev/format/run_comparison.py'
TRANSPORT = REPO / '.auto/role_review_transport.py'
GRADER = REPO / 'evals/c-system-prompt/grader.py'
OFFICIAL = Path('/tmp/ost-official-evaluator-3U4yO9/repo')
SCORER_PYTHON = '/tmp/ost-official-evaluator-3U4yO9/env/bin/python'
REQUEST_LIMIT = 300
TOKEN_BUDGET = 78_720_000
INPUT_BYTES = 240_000
ARM_SECONDS = 5400


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def prepare(core, bundle, strategy='C', model=None, selection='vote_pages', case_ids=None):
    engine = core.legacy.engine()
    translations = {}
    cache = REPO / 'output/validation/claim-translations.json'
    if selection in ('claim_pages', 'claim_paragraphs') and cache.exists():
        translations = json.loads(cache.read_text())
    translation_tokens = [0]

    def translator(text, target):
        entry = translations.get(target + '\n' + text)
        if not entry:
            return None
        translation_tokens[0] += (entry.get('prompt_tokens') or 0) + (entry.get('completion_tokens') or 0)
        return entry['translation']
    cases = load_jsonl(bundle / 'cases.jsonl')
    frozen, oversize = [], []
    for case in cases:
        if case_ids is not None and case['id'] not in case_ids:
            continue
        if 'booklet' in case:
            case = {**case, 'booklet': {**case['booklet'], 'path': str((bundle / 'booklets' / Path(case['booklet']['path']).name).resolve())}}
        pages, messages = engine.context(case, bundle.resolve(), selection_strategy=selection, translator=translator)
        messages[0]['content'] += '\n\n' + core.legacy.PROTOCOL_REMINDER
        size = len(core.legacy.encode(messages))
        if size > INPUT_BYTES:
            # The physical ledger refuses such a request, so production would
            # deliver the neutral fallback for this case. Record it as such.
            oversize.append({'case': case, 'pages': pages, 'bytes': size})
            continue
        frozen.append({'case': case, 'pages': pages, 'messages': messages, 'messages_sha256': core.legacy.digest(core.legacy.encode(messages))})
    sources = {str(p.relative_to(REPO)): core.legacy.digest(p.read_bytes()) for p in (REPO / 'track_2a/src').glob('*.py')}
    base = {'version': 2, 'protocol_reminder': core.legacy.PROTOCOL_REMINDER, 'native_schema': 'offline proposal only, not sent',
            'case_sha256': core.legacy.digest((bundle / 'cases.jsonl').read_bytes()), 'models': core.MODELS,
            'request_limit': REQUEST_LIMIT, 'token_budget': TOKEN_BUDGET, 'request_token_reserve': core.RESERVE,
            'output_limit': 256, 'temperature': 0, 'selection_strategy': selection, 'sources': sources, 'frozen': frozen}
    core.legacy.prepare = lambda: base
    manifest = core.prepare(strategy, [i['case']['id'] for i in frozen])
    manifest.update(request_limit=REQUEST_LIMIT, token_budget=TOKEN_BUDGET, translation_tokens=translation_tokens[0])
    if strategy == 'R':
        manifest['models'] = [core.MODELS[1]]
    elif strategy != 'C':
        manifest['models'] = [model]
    return manifest, oversize


def run(core, transport, job, manifest):
    job.mkdir(mode=0o700, parents=True)
    core.legacy.c.protect()
    started = time.monotonic()
    phase_end = time.time() + ARM_SECONDS
    original = core.run_b

    def bounded(*args, **kwargs):
        if time.time() >= phase_end:
            raise core.Stop('PHASE_DEADLINE_STOP')
        return original(*args, **kwargs, seconds=min(300, phase_end + 300 - time.time()))
    core.run_b = bounded
    try:
        core.initialize(job, manifest)
        side = transport.PhysicalLedger(core, job, time.monotonic() + ARM_SECONDS + 300)
        summary = core.run(job, manifest, side.client)
        summary['wall_seconds'] = time.monotonic() - started
        return summary
    finally:
        core.run_b = original


def grade(job, bundle, core, oversize, prefix='70b', predictions=None):
    report = job / 'official.json'
    predictions = predictions or job / f'{prefix}-canonical.jsonl'
    if oversize:
        rows = predictions.read_text(encoding='utf-8')
        zero = {'input_tokens': 0, 'output_tokens': 0, 'inference_time_ms': 0}
        extra = [core.submission.fallback(o['case'], o['pages'], zero) for o in oversize]
        predictions = job / 'canonical-with-oversize-fallbacks.jsonl'
        predictions.write_text(rows + ''.join(json.dumps(e, ensure_ascii=False) + '\n' for e in extra), encoding='utf-8')
    command = [SCORER_PYTHON, '-B', str(GRADER), '--official-repo', str(OFFICIAL), '--python', SCORER_PYTHON,
               '--predictions', str(predictions), '--expected', str(bundle / 'expected.jsonl'),
               '--cases', str(bundle / 'cases.jsonl'), '--output', str(report)]
    subprocess.run(command, check=True, capture_output=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    return json.loads(report.read_text())


def escalate(core, transport, job, bundle, manifest, prefix):
    cases = [json.loads(p.read_text()) for p in sorted(job.glob(f'{prefix}-*-case.json'))]
    booklet_ids = {i['case']['id'] for i in manifest['frozen'] if 'booklet' in i['case']}
    ids = {c['case_id'] for c in cases if c['case_id'] in booklet_ids and c.get('error') == 'NO_ACCEPTED_SUBMIT'}
    second_cases, oversize = [], []
    summary = {'wall_seconds': 0, 'generation_requests': 0}
    second_job = None
    if ids:
        second_manifest, oversize = prepare(core, bundle, strategy='R', selection='vote_pages', case_ids=ids)
        if second_manifest['frozen']:
            second_job = job.with_name(job.name + '-escalation')
            # Each phase gets the same independent transport/time limits.
            transport.ABSOLUTE_STOP = int(time.time()) + ARM_SECONDS + 600
            summary = run(core, transport, second_job, second_manifest)
            second_cases = [json.loads(p.read_text()) for p in sorted(second_job.glob('70b-*-case.json'))]
    recovered = {c['case_id']: c['prediction'] for c in second_cases if c['output_valid']}
    rows = load_jsonl(job / f'{prefix}-canonical.jsonl')
    predictions = job / 'canonical-escalated.jsonl'
    predictions.write_text(''.join(json.dumps(recovered.get(row['id'], row), ensure_ascii=False) + '\n' for row in rows), encoding='utf-8')
    return {'job': second_job, 'cases': second_cases, 'oversize': oversize, 'summary': summary,
            'escalated_cases': len(ids), 'escalation_recovered': len(recovered), 'predictions': predictions}


def metrics(job, summary, official, oversize, prefix='70b', escalation=None):
    cases = [json.loads(p.read_text()) for p in sorted(job.glob(f'{prefix}-*-case.json'))]
    oversize_count = len(oversize)
    physical = [json.loads(p.read_text()) for p in sorted((job / 'physical').glob('*-result.json'))]
    extra_cases = escalation['cases'] if escalation else []
    if escalation and escalation['job'] is not None:
        physical += [json.loads(p.read_text()) for p in sorted((escalation['job'] / 'physical').glob('*-result.json'))]
    tokens = sum(r['usage']['total_tokens'] for r in physical if r.get('usage_known'))
    a = official['official_report']['tasks']['A']
    b = official['official_report']['tasks']['B']
    return {
        'cases': len(cases) + oversize_count, 'fallbacks': sum(not c['output_valid'] for c in cases + extra_cases) + oversize_count + (len(escalation['oversize']) if escalation else 0),
        'oversize_context_fallbacks': oversize_count,
        'f1a': a['macro_f1'], 'f1b': b['macro_f1'], 'hita': a.get('evidence_score'),
        'evidence': a.get('evidence'), 'q': official['classification_objective']['value'],
        'physical_requests': len(physical), 'physical_non_200': sum(r.get('http_status') != 200 for r in physical),
        'known_tokens': tokens, 'all_usage_known': all(r.get('usage_known') for r in physical),
        'tokens_per_case': round(tokens / (len(cases) + oversize_count)) if cases else None,
        'translation_tokens_cached': json.loads((job / 'manifest.json').read_text()).get('translation_tokens', 0),
        'mean_case_seconds': round(sum(c['case_wall_ms'] for c in cases) / len(cases) / 1000, 2) if cases else None,
        'wall_seconds': round(summary.get('wall_seconds', 0) + (escalation['summary'].get('wall_seconds', 0) if escalation else 0)),
        **({key: escalation[key] for key in ('escalated_cases', 'escalation_recovered')} if escalation else {}),
        'diagnostics': summary['models'][next(iter(summary['models']))]['diagnostic_counts'],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--grade', action='store_true')
    parser.add_argument('--escalate', action='store_true', help='Retry booklet NO_ACCEPTED_SUBMIT cases with vote_pages in a separate job')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--strategy', choices=['A', 'C', 'S', 'R'], default='C', help='C: 70B parent + 8B child tools; A: one model, text JSON; S: one model, submit tool; R: input-routed model, submit tool')
    parser.add_argument('--model', choices=['8b', '70b'], default='70b')
    parser.add_argument('--selection', choices=['vote_pages', 'claim_spans', 'claim_pages', 'claim_paragraphs', 'full'], default='vote_pages')
    args = parser.parse_args()
    core = module(RUNNER, 'format_runner')
    model = core.MODELS[0] if args.model == '8b' else core.MODELS[1]
    if args.strategy == 'R':
        model = core.MODELS[1]
    prefix = '70b' if args.strategy == 'R' else args.model
    manifest, oversize = prepare(core, args.bundle, args.strategy, model, args.selection)
    sizes = [len(core.legacy.encode(i['messages'])) for i in manifest['frozen']] + [o['bytes'] for o in oversize]
    print(json.dumps({'prepared_cases': len(manifest['frozen']), 'oversize_context_fallbacks': [o['case']['id'] for o in oversize],
                      'context_bytes_max': max(sizes), 'context_bytes_mean': round(sum(sizes) / len(sizes)),
                      'manifest_sha256': core.legacy.digest(core.legacy.encode(manifest))}), flush=True)
    if args.prepare_only:
        return
    transport = module(TRANSPORT, 'role_review_transport')
    # The overnight module pins its own absolute stop; this runner stops when its arm ends.
    transport.ABSOLUTE_STOP = int(time.time()) + ARM_SECONDS + 600
    summary = run(core, transport, args.job, manifest)
    result = {'job': str(args.job), 'strategy': args.strategy, 'model': model, 'selection': args.selection, 'claim_spans': core.legacy.engine().CLAIM_SPANS, 'status': summary['status'], 'requests': summary['generation_requests']}
    escalation = escalate(core, transport, args.job, args.bundle, manifest, prefix) if args.escalate else None
    if escalation:
        result.update({key: escalation[key] for key in ('escalated_cases', 'escalation_recovered')})
        result['requests'] += escalation['summary']['generation_requests']
    if args.grade:
        official = grade(args.job, args.bundle, core, oversize, prefix,
                         predictions=escalation['predictions'] if escalation else None)
        result['metrics'] = metrics(args.job, summary, official, oversize, prefix, escalation)
    (args.job / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
