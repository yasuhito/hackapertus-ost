#!/usr/bin/env python3
"""Submitted JSONL runtime: injected endpoint only, same assembler and Pi bridge."""
import argparse
import json
import os
from pathlib import Path
import time

import run_comparison as r


def translate_claim(job, case, target, client_factory):
    """Cache context inputs privately; the attempt log contains only safe metadata."""
    cache = job / ('translation-' + r.legacy.digest(r.legacy.encode(case)) + '.json')
    if cache.exists():
        return r.legacy.load(cache)
    record = {'case_id': case['id'], 'target': target, 'ok': False,
              'usage': None, 'finish_reason': None, 'error_type': None}
    translation = None
    try:
        language = {'de': 'German', 'fr': 'French', 'it': 'Italian'}[target]
        payload = {'model': r.MODELS[0], 'messages': [
            {'role': 'system', 'content': f'Translate the user text into {language}. Output only the translation, nothing else.'},
            {'role': 'user', 'content': case['claim']['text']}],
            'temperature': 0, 'max_tokens': 256, 'stream': False}
        response = client_factory(r.MODELS[0]).request('POST', '/v1/chat/completions', payload)
        if isinstance(response, dict):
            usage = response.get('usage')
            if r.legacy.usage_known(usage):
                record['usage'] = {key: usage[key] for key in ('prompt_tokens', 'completion_tokens', 'total_tokens')}
            choice = response['choices'][0]
            finish = choice.get('finish_reason')
            record['finish_reason'] = finish if finish in ('stop', 'length') else None
            content = choice['message']['content']
            if isinstance(content, str) and content.strip() and record['finish_reason'] and record['usage'] is not None:
                translation = content.strip()
                record['ok'] = True
        if not record['ok']:
            record['error_type'] = 'INVALID_TRANSLATION_RESPONSE'
    except Exception as exc:
        record['error_type'] = type(exc).__name__
    fd = os.open(job / 'translations.jsonl', os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'ab') as log:
        log.write(r.legacy.encode(record) + b'\n')
        log.flush()
        os.fsync(log.fileno())
    result = {'translation': translation, 'usage': record['usage']}
    # Cache failures too: retrying retrieval on resume could change frozen context.
    r.legacy.exclusive(cache, result)
    return result


def case_metrics(ledger, model, index, wall_ms, translation_usage):
    metrics, wait = r.metrics_for(ledger, model, index, wall_ms)
    if translation_usage is not None:
        metrics['input_tokens'] += translation_usage['prompt_tokens']
        metrics['output_tokens'] += translation_usage['completion_tokens']
    return metrics, wait


def execute(input_path, output_path, strategy, client_factory=None):
    if strategy not in r.LIMITS:
        raise r.Stop('ROLE_MODEL_REFUSED')
    selected = os.environ.get('LLM_MODEL') or os.environ.get('LLM_NAME') or r.MODELS[1 if strategy in ('C', 'S') else 0]
    if strategy == 'R':
        selected = r.MODELS[1]
    model = next((allowed for allowed in r.MODELS if selected.casefold() == allowed.casefold()), None)
    if model is None:
        raise r.Stop('MODEL_REFUSED')
    r.fixed_role_model(strategy, model, 'parent')
    if not output_path.parent.is_dir():
        output_path.parent.mkdir(parents=True, exist_ok=True)
    blob = input_path.read_bytes()
    rows = [r.submission.strict_json(line.decode('utf-8')) for line in blob.splitlines() if line.strip()]
    if len(rows) > 100000 or len({row['id'] for row in rows}) != len(rows):
        raise r.Stop('INPUT_COUNT_OR_DUPLICATE_IDS')
    selection = os.environ.get('CONTEXT_SELECTION', 'vote_pages')
    if selection not in ('vote_pages', 'claim_pages', 'full'):
        raise r.Stop('CONTEXT_SELECTION_REFUSED')
    claim_spans = int(os.environ.get('CLAIM_SPANS', '8'))
    engine = r.legacy.engine()
    engine.CLAIM_SPANS = claim_spans
    job = output_path.parent / 'tmp' / 'format-runtime'
    job.mkdir(mode=0o700, parents=True, exist_ok=True)
    identity = {'context_selection': selection, 'claim_spans': claim_spans}
    if (job / 'manifest.json').exists():
        previous = r.legacy.load(job / 'manifest.json')
        if any(previous.get(key) != value for key, value in identity.items()):
            raise r.Stop('MANIFEST_CHANGED')
    clients = {}
    def client(selected):
        if selected not in clients:
            clients[selected] = r.Transport(selected, submitted=True)
        return clients[selected]
    client_factory = client_factory or client
    frozen = []
    translation_usages = []
    preparation = []
    for case in rows:
        started = time.monotonic()
        translated = {'translation': None, 'usage': None}
        target = case.get('booklet', {}).get('language')
        if selection == 'claim_pages' and target and case['claim'].get('language') != target:
            translated = translate_claim(job, case, target, client_factory)
        pages, messages = engine.context(case, input_path.parent, selection_strategy=selection,
                                         translator=lambda text, language: translated['translation'])
        translation_usages.append(translated['usage'])
        messages[0]['content'] += '\n\n' + r.legacy.PROTOCOL_REMINDER
        ids = [c['span_id'] for c in r.candidates(pages, 'reference' in case)]
        frozen.append({'case': case, 'pages': pages, 'messages': messages, 'messages_sha256': r.legacy.digest(r.legacy.encode(messages)), 'candidate_ids': ids, 'schema_sha256': r.legacy.digest(r.legacy.encode(r.schemas(ids, strategy=strategy)))})
        preparation.append((time.monotonic() - started) * 1000)
    request_limit = 5 * len(rows)
    manifest = {**identity, 'version': 'format-runtime-1', 'strategy': strategy, 'model': model, 'input_sha256': r.legacy.digest(blob), 'frozen': frozen, 'request_limit': request_limit, 'token_budget': request_limit * r.RESERVE, 'sources': {p.name: r.legacy.digest(p.read_bytes()) for p in [p for p in r.HERE.iterdir() if p.is_file() and p.suffix in ('.py', '.ts', '.mjs', '.json')] + [r.REPO / 'track_2a/src/submission.py']}}
    if strategy == 'C':
        manifest.update(models=[model], role_models={'parent': r.MODELS[1], 'child': r.MODELS[0]})
    if strategy in ('S', 'R'):
        manifest['models'] = [model]
    import fcntl
    fd = os.open(job / 'lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        r.initialize(job, manifest)
        ledger = r.Ledger(job, manifest, client_factory)
        for index, item in enumerate(frozen):
            name = r.legacy.result_name(model, index).replace('.json', '-case.json')
            if name in ledger.state['cases']:
                continue
            request_model = r.case_model(strategy, model, item['case'])
            started = time.monotonic()
            def post(role, number, payload):
                if ledger.state['requests'] + ledger.state.get('uncertain_requests', 0) >= request_limit:
                    raise r.Stop('HARD_BUDGET_STOP_BEFORE_SEND')
                return ledger.post(request_model, index, role, number, payload, deadline=started + r.CASE_SECONDS)
            sdk = None
            diagnostics = []
            error = None
            try:
                if strategy == 'A':
                    args, diagnostics = r.run_a(item, model, post)
                else:
                    args, diagnostics, sdk = r.run_b(item, request_model, post, strategy=strategy)
                metrics, wait = case_metrics(ledger, model, index, preparation[index] + (time.monotonic() - started) * 1000, translation_usages[index])
                result = r.submission.assemble_tool(args, item['case'], item['pages'], metrics) if args is not None else r.submission.fallback(item['case'], item['pages'], metrics)
                error = None if args is not None else 'NO_ACCEPTED_SUBMIT'
            except Exception as exc:
                error = str(exc) if isinstance(exc, r.Stop) else 'CASE_FAILED'
                diagnostics.append(error)
                if ledger.fence.exists():
                    ledger.fence.unlink()
                ledger.state['reserved_tokens'] = 0
                if error != 'UNKNOWN_MODEL_USAGE_OR_RESPONSE_ALL_STOP':
                    ledger.state['blocked'] = False
                # Preserve spent request slots without inventing usage records for
                # transport failures. The shared ledger validates recorded counts.
                missing = ledger.state['requests'] - len(ledger.state['attempts'])
                ledger.state['uncertain_requests'] = ledger.state.get('uncertain_requests', 0) + missing
                ledger.state['requests'] -= missing
                r.legacy.state_write(job / 'state.json', ledger.state)
                for attempt in ledger.state['attempts']:
                    if attempt not in ledger.records:
                        record = r.legacy.load(job / attempt)
                        if r.legacy.usage_known(record['usage']):
                            ledger.records[attempt] = record
                metrics, wait = case_metrics(ledger, model, index, preparation[index] + (time.monotonic() - started) * 1000, translation_usages[index])
                result = r.submission.fallback(item['case'], item['pages'], metrics)
            ledger.save_case(name, {'model': model, 'request_model': request_model, 'prediction': result, 'error': error, 'diagnostics': diagnostics, 'api_wait_ms': wait, 'sdk': sdk})
        try:
            records = [ledger.records[r.legacy.result_name(model, i).replace('.json', '-case.json')] for i in range(len(rows))]
            expected = b''.join(r.legacy.encode(record['prediction']) + b'\n' for record in records)
            if output_path.exists() and output_path.read_bytes() != expected:
                raise r.Stop('EXISTING_OUTPUT_CHANGED')
            if not output_path.exists():
                r.legacy.exclusive_jsonl(output_path, [record['prediction'] for record in records])
            sidecar = output_path.with_suffix(output_path.suffix + '.diagnostics.jsonl')
            if not sidecar.exists():
                r.legacy.exclusive_jsonl(sidecar, [{'id': record['prediction']['id'], 'error': record['error'], 'diagnostics': record['diagnostics']} for record in records])
            evaluation = output_path.with_suffix(output_path.suffix + '.evaluation.jsonl')
            if not evaluation.exists():
                r.legacy.exclusive_jsonl(evaluation, [{**record['prediction'], **({'error': record['error']} if record['error'] else {})} for record in records])
        except BaseException as exc:
            if not (job / 'STOP.json').exists():
                r.legacy.exclusive(job / 'STOP.json', {'status': 'STOP', 'reason': 'RUNTIME_FAILED_NO_RETRY', **({'http_status': exc.http_status} if type(getattr(exc, 'http_status', None)) is int else {})})
            raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--pipeline', choices=['A', 'B', 'C', 'S', 'R'], default=os.environ.get('PIPELINE', 'A'))
    args = parser.parse_args()
    r.legacy.c.protect()
    execute(args.input, args.output, args.pipeline)


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except BaseException:
        print('STOP: runtime fenced; no automatic retry or credential/error-body logging.', file=r.sys.stderr)
        raise SystemExit(1)
