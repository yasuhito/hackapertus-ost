#!/usr/bin/env bash
# run_experiment starts checks in another process: use the successful measurement context.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
export PYTHONDONTWRITEBYTECODE=1
python3 -B - <<'PY'
import json
import os
from pathlib import Path
import subprocess
import sys
context = json.loads(Path('.auto/check-context.json').read_text())
mode, candidate = context['mode'], context['candidate']
if mode in ('train_baseline', 'train_candidate'):
    import sys
    sys.path.insert(0, '.auto')
    import train_run as train
    assert context.get('protocol_sha256') == train.old.digest(train.CONTROL.read_bytes()), 'TRAIN_CONTEXT_CHANGED'
    train.verify_protocol()
    if mode == 'train_baseline':
        assert candidate == '' and context.get('attempt') is None, 'TRAIN_SELECTOR_CONFLICT'
        command = [sys.executable, '-B', '.auto/train_results.py', '--baseline', '--check']
    else:
        assert candidate in train.VERSIONS and type(context.get('attempt')) is int and context['attempt'] in (1, 2, 3), 'TRAIN_SELECTOR_MISSING'
        command = ['/tmp/ost-official-evaluator-3U4yO9/env/bin/python', '-B', '.auto/train_results.py', '--candidate', candidate, '--attempt', str(context['attempt']), '--check']
    subprocess.run(command, check=True)
elif mode == 'baseline':
    assert candidate == '' and not os.environ.get('AUTO_CANDIDATE'), 'CHECK_SELECTOR_CONFLICT'
    subprocess.run(['bash', '.auto/measure.sh', '--baseline'], check=True)
else:
    assert mode == 'candidate' and candidate in ('v3', 'v4', 'v5', 'v6', 'v7', 'v8', 'v9', 'v10', 'v11', 'v12', 'v13', 'v12-retry1', 'v13-retry1'), 'CHECK_SELECTOR_MISSING'
    assert not os.environ.get('AUTO_BASELINE'), 'CHECK_SELECTOR_CONFLICT'
    assert os.environ.get('AUTO_CANDIDATE', candidate) == candidate, 'CHECK_SELECTOR_CONFLICT'
    subprocess.run([sys.executable, '-B', '.auto/results.py', '--candidate', candidate, '--check'], check=True)
PY
