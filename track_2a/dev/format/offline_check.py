#!/usr/bin/env python3
"""Finite synthetic-response CLI through the actual Pi SDK. No model accuracy claim."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import socket

import run_comparison as r


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--strategy', choices=['A', 'B', 'C'], required=True)
    parser.add_argument('--job', type=Path, required=True)
    args = parser.parse_args()
    def denied(*a, **k):
        raise AssertionError('OFFLINE_NETWORK_OR_CREDENTIAL_READ_DENIED')
    socket.socket = denied
    socket.create_connection = denied
    r.legacy.c.read_key = denied
    original = r.run_b
    r.run_b = lambda *a, **k: original(*a, **k, isolation_guard=True)
    manifest = r.prepare(args.strategy)
    manifest['mode'] = 'offline-synthetic; plumbing only, not model evaluation'
    r.initialize(args.job, manifest)
    fd = os.open(args.job / 'lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    actual_models = []
    class Fake:
        def __init__(self, model):
            self.model = model
        def request(self, method, path, payload):
            assert method == 'POST' and path == '/v1/chat/completions' and payload['model'] == self.model
            actual_models.append(self.model)
            message = {'role': 'assistant', 'content': json.dumps({'label': 1, 'evidence': []})}
            reason = 'stop'
            if 'tools' in payload:
                name = payload['tool_choice']['function']['name']
                arguments = {'mode': 'source_only'} if name == 'subagent' else {'label': 1, 'candidate_ids': []}
                message = {'role': 'assistant', 'content': None, 'tool_calls': [{'id': name + '-offline', 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(arguments)}}]}
                reason = 'tool_calls'
            return {'id': 'offline-synthetic', 'model': self.model, 'choices': [{'finish_reason': reason, 'message': message}], 'usage': {'prompt_tokens': 80, 'completion_tokens': 20, 'total_tokens': 100}}
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        prior = r.Ledger(args.job, manifest, Fake)
        prior_models = r.Counter(record.get('request_model', record['model']) for name, record in prior.records.items() if name in prior.state['attempts'])
        summary = r.run(args.job, manifest, Fake)
        if args.strategy == 'C':
            assert len(actual_models) == 162 - prior.state['requests']
            assert actual_models.count(r.MODELS[0]) == 54 - prior_models[r.MODELS[0]]
            assert actual_models.count(r.MODELS[1]) == 108 - prior_models[r.MODELS[1]]
            assert summary['generation_requests'] == 162 and summary['actual_total_tokens'] == 16200
            assert summary['calls_by_actual_model'] == {r.MODELS[1]: 108, r.MODELS[0]: 54}
            owner = summary['models'][r.MODELS[1]]
            assert owner['prompt_tokens'] == 12960 and owner['completion_tokens'] == 3240
            cases = [record for name, record in r.Ledger(args.job, manifest, Fake).records.items() if name.endswith('-case.json')]
            assert len(cases) == 54
            assert all(sum(e['type'] == 'package_child_completed' and e['model'] == r.MODELS[0] for e in record['sdk']['events']) == 1 for record in cases)
            before = len(actual_models)
            assert r.run(args.job, manifest, Fake) == summary
            assert len(actual_models) == before
        print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
