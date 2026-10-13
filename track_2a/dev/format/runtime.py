#!/usr/bin/env python3
"""Submitted JSONL runtime: injected endpoint only, same assembler and Pi bridge."""
import argparse
import json
import os
from pathlib import Path
import time

import run_comparison as r


def execute(input_path, output_path, strategy, client_factory=None):
    selected = os.environ.get('LLM_MODEL') or os.environ.get('LLM_NAME') or r.MODELS[0]
    model = next((allowed for allowed in r.MODELS if selected.casefold() == allowed.casefold()), None)
    if model is None:
        raise r.Stop('MODEL_REFUSED')
    if not output_path.parent.is_dir():
        output_path.parent.mkdir(parents=True, exist_ok=True)
    blob = input_path.read_bytes()
    rows = [r.submission.strict_json(line.decode('utf-8')) for line in blob.splitlines() if line.strip()]
    if len(rows) > 108 or len({row['id'] for row in rows}) != len(rows):
        raise r.Stop('INPUT_COUNT_OR_DUPLICATE_IDS')
    frozen = []
    preparation = []
    for case in rows:
        started = time.monotonic()
        pages, messages = r.legacy.engine().context(case, input_path.parent)
        messages[0]['content'] += '\n\n' + r.legacy.PROTOCOL_REMINDER
        ids = [c['span_id'] for c in r.candidates(pages, 'reference' in case)]
        frozen.append({'case': case, 'pages': pages, 'messages': messages, 'messages_sha256': r.legacy.digest(r.legacy.encode(messages)), 'candidate_ids': ids, 'schema_sha256': r.legacy.digest(r.legacy.encode(r.schemas(ids)))})
        preparation.append((time.monotonic() - started) * 1000)
    manifest = {'version': 'format-runtime-1', 'strategy': strategy, 'model': model, 'input_sha256': r.legacy.digest(blob), 'frozen': frozen, 'request_limit': r.LIMITS[strategy], 'token_budget': r.TOKEN_BUDGET, 'sources': {p.name: r.legacy.digest(p.read_bytes()) for p in [p for p in r.HERE.iterdir() if p.is_file() and p.suffix in ('.py', '.ts', '.mjs', '.json')] + [r.REPO / 'track_2a/src/submission.py']}}
    job = output_path.parent / 'tmp' / 'format-runtime'
    job.mkdir(mode=0o700, parents=True, exist_ok=True)
    import fcntl
    fd = os.open(job / 'lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        r.initialize(job, manifest)
        clients = {}
        def client(selected):
            if selected not in clients:
                clients[selected] = r.Transport(selected, submitted=True)
            return clients[selected]
        ledger = r.Ledger(job, manifest, client_factory or client)
        try:
            for index, item in enumerate(frozen):
                name = r.legacy.result_name(model, index).replace('.json', '-case.json')
                if name in ledger.state['cases']:
                    continue
                started = time.monotonic()
                post = lambda role, number, payload: ledger.post(model, index, role, number, payload, deadline=started + r.CASE_SECONDS)
                sdk = None
                if strategy == 'A':
                    args, diagnostics = r.run_a(item, model, post)
                else:
                    args, diagnostics, sdk = r.run_b(item, model, post)
                metrics, wait = r.metrics_for(ledger, model, index, preparation[index] + (time.monotonic() - started) * 1000)
                result = r.submission.assemble_tool(args, item['case'], item['pages'], metrics) if args is not None else r.submission.fallback(item['case'], item['pages'], metrics)
                ledger.save_case(name, {'prediction': result, 'error': None if args is not None else 'NO_ACCEPTED_SUBMIT', 'diagnostics': diagnostics, 'api_wait_ms': wait, 'sdk': sdk})
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
    parser.add_argument('--pipeline', choices=['A', 'B'], default=os.environ.get('PIPELINE', 'A'))
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
