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
    parser.add_argument('--strategy', choices=['A', 'B'], required=True)
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
    class Fake:
        def __init__(self, model):
            self.model = model
        def request(self, method, path, payload):
            assert method == 'POST' and path == '/v1/chat/completions' and payload['model'] == self.model
            message = {'role': 'assistant', 'content': json.dumps({'label': 1, 'evidence': []})}
            reason = 'stop'
            if 'tools' in payload:
                name = payload['tool_choice']['function']['name']
                arguments = {} if name == 'subagent' else {'label': 1, 'candidate_ids': []}
                message = {'role': 'assistant', 'content': None, 'tool_calls': [{'id': name + '-offline', 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(arguments)}}]}
                reason = 'tool_calls'
            return {'id': 'offline-synthetic', 'model': self.model, 'choices': [{'finish_reason': reason, 'message': message}], 'usage': {'prompt_tokens': 80, 'completion_tokens': 20, 'total_tokens': 100}}
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        print(json.dumps(r.run(args.job, manifest, Fake), ensure_ascii=False))


if __name__ == '__main__':
    main()
